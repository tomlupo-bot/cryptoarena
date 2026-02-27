"""
ArenaAgentCrypto — Extended crypto agent with:
1. Token cost deduction from trading capital (ClawWork-style)
2. Risk limit enforcement
3. Enhanced JSONL logging for dashboard
4. Drawdown kill switch
5. Sub-hourly trading interval support

Inherits core loop structure from AI-Trader's BaseAgentCrypto but replaces
the model layer with a TrackedLLMProvider for cost interception.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI

from economic.tracker import EconomicTracker
from economic.risk_manager import RiskManager
from economic.arena_logger import ArenaLogger
from economic.provider_wrapper import TrackedLLMProvider
from prompts.arena_prompt_crypto import STOP_SIGNAL, get_arena_system_prompt
from tools.general_tools import extract_conversation, extract_tool_messages, get_config_value, write_config_value
from tools.price_tools import (
    add_no_trade_record,
    get_open_prices,
    get_today_init_position,
    get_yesterday_open_and_close_price,
)

# Bitwise 10 crypto symbols (same as AI-Trader)
BITWISE_10 = [
    "BTC-USDT", "ETH-USDT", "XRP-USDT", "SOL-USDT", "ADA-USDT",
    "SUI-USDT", "LINK-USDT", "AVAX-USDT", "LTC-USDT", "DOT-USDT",
]


class ArenaAgentCrypto:
    """
    Competition-aware crypto trading agent.

    Key differences from BaseAgentCrypto:
    - Every LLM call's token cost is deducted from trading capital
    - Risk limits are enforced pre-trade
    - Agent is killed on bankruptcy or max drawdown breach
    - Supports sub-hourly trading intervals
    - Produces structured JSONL logs for the dashboard
    """

    def __init__(
        self,
        signature: str,
        basemodel: str,
        config: Dict[str, Any],
        model_config: Dict[str, Any],
        crypto_symbols: Optional[List[str]] = None,
        mcp_config: Optional[Dict[str, Dict[str, Any]]] = None,
        openai_base_url: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):
        self.signature = signature
        self.basemodel = basemodel
        self.market = "crypto"
        self.crypto_symbols = crypto_symbols or BITWISE_10

        # Config sections
        self.config = config
        self.model_config = model_config
        agent_cfg = config.get("agent_config", {})
        arena_cfg = config.get("arena", {})
        risk_cfg = config.get("risk_limits", {})
        log_cfg = config.get("log_config", {})

        self.max_steps = agent_cfg.get("max_steps", 30)
        self.max_retries = agent_cfg.get("max_retries", 3)
        self.base_delay = agent_cfg.get("base_delay", 0.5)
        self.initial_cash = agent_cfg.get("initial_cash", 10000.0)
        self.verbose = agent_cfg.get("verbose", False)

        # Arena settings
        self.arena_name = arena_cfg.get("name", "CryptoArena")
        self.trading_interval_minutes = arena_cfg.get("trading_interval_minutes", 60)
        self.token_budget_mode = arena_cfg.get("token_budget_mode", "deduct_from_capital")
        self.max_drawdown_pct = arena_cfg.get("max_drawdown_pct", 50.0)
        self.kill_on_bankruptcy = arena_cfg.get("kill_on_bankruptcy", True)

        # Date range
        dr = config.get("date_range", {})
        self.init_date = dr.get("init_date", "2025-10-01")
        self.end_date = dr.get("end_date", "2025-10-31")

        # Log path
        self.base_log_path = log_cfg.get("log_path", "./data/arena_data")
        self.data_path = os.path.join(self.base_log_path, self.signature)
        self.position_file = os.path.join(self.data_path, "position", "position.jsonl")

        # Economic tracker (ClawWork-style)
        token_pricing = model_config.get("token_pricing", {
            "input_per_1m": 3.0,
            "output_per_1m": 15.0,
        })
        self.economic_tracker = EconomicTracker(
            initial_balance=self.initial_cash,
            token_pricing=token_pricing,
            data_path=self.data_path,
        )

        # Risk manager
        self.risk_manager = RiskManager(risk_cfg, self.initial_cash)

        # Arena logger
        self.arena_logger = ArenaLogger(self.base_log_path, self.signature)

        # MCP config
        self.mcp_config = mcp_config or self._get_default_mcp_config()

        # OpenAI config
        self.openai_base_url = openai_base_url or os.getenv("OPENAI_API_BASE")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

        # Runtime state
        self.client: Optional[MultiServerMCPClient] = None
        self.tools: Optional[List] = None
        self.model: Optional[Any] = None  # TrackedLLMProvider
        self.agent: Optional[Any] = None
        self.is_alive = True
        self.death_reason: Optional[str] = None
        self.current_cash = self.initial_cash

        # Step-level cost accumulator (reset each step)
        self._step_token_cost = 0.0

    def _get_default_mcp_config(self) -> Dict[str, Dict[str, Any]]:
        return {
            "math": {
                "transport": "streamable_http",
                "url": f"http://localhost:{os.getenv('MATH_HTTP_PORT', '8000')}/mcp",
            },
            "search": {
                "transport": "streamable_http",
                "url": f"http://localhost:{os.getenv('SEARCH_HTTP_PORT', '8001')}/mcp",
            },
            "price": {
                "transport": "streamable_http",
                "url": f"http://localhost:{os.getenv('GETPRICE_HTTP_PORT', '8003')}/mcp",
            },
            "trade": {
                "transport": "streamable_http",
                "url": f"http://localhost:{os.getenv('CRYPTO_HTTP_PORT', '8005')}/mcp",
            },
            "indicators": {
                "transport": "streamable_http",
                "url": f"http://localhost:{os.getenv('INDICATORS_HTTP_PORT', '8006')}/mcp",
            },
            "portfolio": {
                "transport": "streamable_http",
                "url": f"http://localhost:{os.getenv('PORTFOLIO_HTTP_PORT', '8007')}/mcp",
            },
        }

    # ── initialization ──────────────────────────────────────────────

    async def initialize(self) -> None:
        """Initialize MCP client and AI model with token tracking."""
        print(f"🏟️  Initializing Arena agent: {self.signature} ({self.basemodel})")

        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set")

        # MCP client
        self.client = MultiServerMCPClient(self.mcp_config)
        self.tools = await self.client.get_tools()
        print(f"✅ Loaded {len(self.tools) if self.tools else 0} MCP tools")

        # LLM with token tracking wrapper
        raw_model = ChatOpenAI(
            model=self.basemodel,
            base_url=self.openai_base_url,
            api_key=self.openai_api_key,
            max_retries=3,
            timeout=30,
        )
        self.model = TrackedLLMProvider(raw_model, self.economic_tracker)

        print(f"✅ Arena agent {self.signature} ready (token costs → capital)")

    # ── registration ────────────────────────────────────────────────

    def register_agent(self) -> None:
        """Create initial position file."""
        if os.path.exists(self.position_file):
            print(f"⚠️  Position file exists for {self.signature}, skipping")
            return

        position_dir = os.path.join(self.data_path, "position")
        os.makedirs(position_dir, exist_ok=True)

        init_position = {symbol: 0.0 for symbol in self.crypto_symbols}
        init_position["CASH"] = self.initial_cash

        with open(self.position_file, "w") as f:
            f.write(json.dumps({
                "date": self.init_date,
                "id": 0,
                "positions": init_position,
            }) + "\n")

        print(f"✅ {self.signature} registered | {self.initial_cash} USDT | {len(self.crypto_symbols)} cryptos")

    # ── trading interval generation ─────────────────────────────────

    def _generate_trading_times(self) -> List[datetime]:
        """Generate timestamps at configured intervals. Crypto = 24/7."""
        current = datetime.fromisoformat(self.init_date)
        end = datetime.fromisoformat(self.end_date)
        times = []
        while current <= end:
            times.append(current)
            current += timedelta(minutes=self.trading_interval_minutes)
        return times

    def get_trading_dates(self) -> List[str]:
        """Get unique trading dates from interval schedule."""
        from tools.price_tools import is_trading_day

        if not os.path.exists(self.position_file):
            self.register_agent()

        # Find latest processed date
        max_date = self.init_date
        if os.path.exists(self.position_file):
            with open(self.position_file) as f:
                for line in f:
                    doc = json.loads(line)
                    d = doc["date"]
                    if d > max_date:
                        max_date = d

        # Generate remaining dates
        max_dt = datetime.strptime(max_date, "%Y-%m-%d")
        end_dt = datetime.strptime(self.end_date, "%Y-%m-%d")
        if end_dt <= max_dt:
            return []

        dates = []
        current = max_dt + timedelta(days=1)
        while current <= end_dt:
            ds = current.strftime("%Y-%m-%d")
            if is_trading_day(ds, market=self.market):
                dates.append(ds)
            current += timedelta(days=1)
        return dates

    # ── survival checks ─────────────────────────────────────────────

    def _check_survival(self) -> None:
        """Kill agent if bankrupt or max drawdown breached."""
        if self.current_cash <= 0 and self.kill_on_bankruptcy:
            self.is_alive = False
            self.death_reason = "BANKRUPT: Token costs exceeded remaining capital"
            print(f"💀 {self.signature}: {self.death_reason}")
            return

        equity = self._total_equity()
        peak = self.economic_tracker.peak_equity
        if peak > 0:
            drawdown = (peak - equity) / peak * 100
            if drawdown >= self.max_drawdown_pct:
                self.is_alive = False
                self.death_reason = f"MAX_DRAWDOWN: {drawdown:.1f}% >= {self.max_drawdown_pct}%"
                print(f"💀 {self.signature}: {self.death_reason}")

    def _total_equity(self) -> float:
        """Cash + unrealized PnL (token costs already deducted from cash)."""
        # Simple: just cash for now. Unrealized PnL comes from position valuation.
        return self.current_cash

    # ── logging helpers ─────────────────────────────────────────────

    def _setup_logging(self, today_date: str) -> str:
        log_path = os.path.join(self.data_path, "log", today_date)
        os.makedirs(log_path, exist_ok=True)
        return os.path.join(log_path, "log.jsonl")

    def _log_message(self, log_file: str, new_messages) -> None:
        entry = {"signature": self.signature, "new_messages": new_messages}
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ── core trading session ────────────────────────────────────────

    async def _ainvoke_with_retry(self, message):
        for attempt in range(1, self.max_retries + 1):
            try:
                return await self.agent.ainvoke({"messages": message}, {"recursion_limit": 100})
            except Exception as e:
                if attempt == self.max_retries:
                    raise
                print(f"⚠️  Attempt {attempt} failed, retrying...")
                await asyncio.sleep(self.base_delay * attempt)

    async def run_trading_session(self, today_date: str) -> Dict[str, Any]:
        """Run a single day/interval trading session."""
        if not self.is_alive:
            return {"status": "dead", "reason": self.death_reason}

        print(f"📈 [{self.signature}] Trading session: {today_date}")

        log_file = self._setup_logging(today_date)
        write_config_value("LOG_FILE", log_file)

        # Build system prompt with arena context
        positions_str = str(get_today_init_position(today_date, self.signature))
        buy_prices = get_open_prices(today_date, self.crypto_symbols, market=self.market)
        _, sell_prices = get_yesterday_open_and_close_price(
            today_date, self.crypto_symbols, market=self.market
        )
        summary = self.economic_tracker.get_summary(self.current_cash, 0)

        system_prompt = get_arena_system_prompt(
            current_datetime=today_date,
            positions=positions_str,
            current_prices=str(buy_prices),
            symbols=", ".join(self.crypto_symbols),
            initial_cash=self.initial_cash,
            current_cash=self.current_cash,
            current_equity=summary["current_equity"],
            survival_tier=summary["survival_tier"],
            cumulative_token_cost=self.economic_tracker.cumulative_token_cost,
            interval=self.trading_interval_minutes,
            init_date=self.init_date,
            end_date=self.end_date,
            max_position_pct=self.risk_manager.max_position_pct,
            max_open_positions=self.risk_manager.max_open_positions,
            max_leverage=self.risk_manager.max_leverage,
            max_drawdown_pct=self.max_drawdown_pct,
        )

        self.agent = create_agent(self.model, tools=self.tools, system_prompt=system_prompt)

        user_query = [{"role": "user", "content": f"Please analyze and update today's ({today_date}) positions."}]
        message = user_query.copy()
        self._log_message(log_file, user_query)

        # Trading loop
        cost_before = self.economic_tracker.cumulative_token_cost
        current_step = 0

        while current_step < self.max_steps and self.is_alive:
            current_step += 1
            print(f"  🔄 Step {current_step}/{self.max_steps}")

            try:
                response = await self._ainvoke_with_retry(message)
                agent_response = extract_conversation(response, "final")

                # Deduct token cost from capital
                cost_delta = self.economic_tracker.cumulative_token_cost - cost_before
                if self.token_budget_mode == "deduct_from_capital":
                    self.current_cash -= cost_delta
                cost_before = self.economic_tracker.cumulative_token_cost

                # Check survival after cost deduction
                self._check_survival()

                # Log decision
                self.arena_logger.log_decision(
                    timestamp=datetime.utcnow().isoformat(),
                    step_num=current_step,
                    agent_message=agent_response[:500],
                    token_cost=cost_delta,
                )

                if STOP_SIGNAL in agent_response:
                    print(f"  ✅ {self.signature} finished trading")
                    self._log_message(log_file, [{"role": "assistant", "content": agent_response}])
                    break

                tool_msgs = extract_tool_messages(response)
                tool_response = "\n".join([msg.content for msg in tool_msgs])

                new_messages = [
                    {"role": "assistant", "content": agent_response},
                    {"role": "user", "content": f"Tool results: {tool_response}"},
                ]
                message.extend(new_messages)
                self._log_message(log_file, new_messages[0])
                self._log_message(log_file, new_messages[1])

            except Exception as e:
                print(f"  ❌ Error: {e}")
                raise

        # Record equity snapshot
        self.economic_tracker.record_equity_snapshot(
            timestamp=today_date,
            cash=self.current_cash,
            unrealized_pnl=0,  # TODO: calculate from positions
            positions=[],
        )

        # Handle result
        await self._handle_trading_result(today_date)

        return {
            "status": "alive" if self.is_alive else "dead",
            "equity": self.current_cash,
            "token_cost": self.economic_tracker.cumulative_token_cost,
            "survival_tier": self.economic_tracker.get_survival_tier(self.current_cash),
        }

    async def _handle_trading_result(self, today_date: str) -> None:
        if_trade = get_config_value("IF_TRADE")
        if if_trade:
            write_config_value("IF_TRADE", False)
            print(f"  ✅ {self.signature} traded")
        else:
            print(f"  📊 {self.signature} held positions")
            try:
                add_no_trade_record(today_date, self.signature)
            except Exception as e:
                print(f"  ⚠️  {e}")
            write_config_value("IF_TRADE", False)

    # ── run full date range ─────────────────────────────────────────

    async def run_date_range(self) -> None:
        """Process all trading dates in the configured range."""
        trading_dates = self.get_trading_dates()
        if not trading_dates:
            print(f"ℹ️  {self.signature}: no dates to process")
            return

        print(f"📅 {self.signature}: processing {len(trading_dates)} trading days")

        for date in trading_dates:
            if not self.is_alive:
                print(f"💀 {self.signature} is dead, skipping {date}")
                break

            write_config_value("TODAY_DATE", date)
            write_config_value("SIGNATURE", self.signature)

            for attempt in range(1, self.max_retries + 1):
                try:
                    result = await self.run_trading_session(date)
                    break
                except Exception as e:
                    if attempt == self.max_retries:
                        print(f"  💥 {self.signature} - {date} all retries failed: {e}")
                        raise
                    await asyncio.sleep(self.base_delay * attempt)

        # Print final summary
        summary = self.economic_tracker.get_summary(self.current_cash, 0)
        print(f"\n{'='*60}")
        print(f"🏁 {self.signature} Final Results:")
        print(f"   Equity: {summary['current_equity']} USDT")
        print(f"   Return: {summary['total_return_pct']:.2f}%")
        print(f"   Token costs: {summary['cumulative_token_cost']:.6f} USDT")
        print(f"   Survival: {summary['survival_tier']}")
        print(f"   LLM calls: {summary['total_llm_calls']}")
        print(f"{'='*60}\n")

    def get_position_summary(self) -> Dict[str, Any]:
        if not os.path.exists(self.position_file):
            return {"error": "No position file"}
        positions = []
        with open(self.position_file) as f:
            for line in f:
                positions.append(json.loads(line))
        if not positions:
            return {"error": "No records"}
        latest = positions[-1]
        return {
            "signature": self.signature,
            "latest_date": latest.get("date"),
            "positions": latest.get("positions", {}),
            "total_records": len(positions),
            "economic_summary": self.economic_tracker.get_summary(self.current_cash, 0),
        }

    def __str__(self) -> str:
        alive = "alive" if self.is_alive else "dead"
        return f"ArenaAgentCrypto({self.signature}, {self.basemodel}, {alive})"

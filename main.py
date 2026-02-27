"""
CryptoArena — Main entry point.

Runs a competitive LLM crypto trading arena where multiple models
compete head-to-head with token costs deducted from trading capital.

Usage:
    python main.py [config_path]
    python main.py configs/arena_crypto_config.json
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from agent.arena_agent_crypto import ArenaAgentCrypto
from tools.general_tools import write_config_value


def load_config(config_path=None):
    if config_path is None:
        config_path = Path(__file__).parent / "configs" / "arena_crypto_config.json"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        print(f"❌ Config not found: {config_path}")
        sys.exit(1)

    with open(config_path, "r") as f:
        config = json.load(f)
    print(f"✅ Loaded config: {config_path}")
    return config


async def main(config_path=None):
    config = load_config(config_path)

    arena_cfg = config.get("arena", {})
    dr = config.get("date_range", {})
    log_cfg = config.get("log_config", {})

    print(f"\n{'='*60}")
    print(f"🏟️  CryptoArena: {arena_cfg.get('name', 'Unnamed')}")
    print(f"📅 Period: {dr['init_date']} → {dr['end_date']}")
    print(f"⏱️  Interval: {arena_cfg.get('trading_interval_minutes', 60)} min")
    print(f"💀 Kill on bankruptcy: {arena_cfg.get('kill_on_bankruptcy', True)}")
    print(f"📉 Max drawdown: {arena_cfg.get('max_drawdown_pct', 50)}%")
    print(f"{'='*60}\n")

    enabled_models = [m for m in config["models"] if m.get("enabled", True)]
    print(f"🤖 Competitors: {[m['signature'] for m in enabled_models]}\n")

    agents = []
    results = []

    for model_cfg in enabled_models:
        signature = model_cfg["signature"]
        basemodel = model_cfg["basemodel"]

        print(f"{'─'*40}")
        print(f"🤖 Initializing: {signature} ({basemodel})")

        write_config_value("SIGNATURE", signature)
        write_config_value("IF_TRADE", False)
        write_config_value("MARKET", "crypto")
        write_config_value("LOG_PATH", log_cfg.get("log_path", "./data/arena_data"))

        agent = ArenaAgentCrypto(
            signature=signature,
            basemodel=basemodel,
            config=config,
            model_config=model_cfg,
            openai_base_url=model_cfg.get("openai_base_url"),
            openai_api_key=model_cfg.get("openai_api_key"),
        )

        await agent.initialize()
        agents.append(agent)

    # Run each agent sequentially (parallel mode possible with main_parallel.py)
    for agent in agents:
        print(f"\n{'='*60}")
        print(f"🏁 Running: {agent.signature}")
        print(f"{'='*60}")

        try:
            await agent.run_date_range()
            summary = agent.get_position_summary()
            results.append({
                "team": agent.signature,
                "model": agent.basemodel,
                "status": "alive" if agent.is_alive else "dead",
                "death_reason": agent.death_reason,
                **summary.get("economic_summary", {}),
            })
        except Exception as e:
            print(f"❌ {agent.signature} crashed: {e}")
            results.append({
                "team": agent.signature,
                "model": agent.basemodel,
                "status": "crashed",
                "error": str(e),
            })

    # Print final leaderboard
    print(f"\n\n{'='*60}")
    print(f"🏆 CryptoArena Final Leaderboard")
    print(f"{'='*60}")

    alive = [r for r in results if r.get("status") == "alive"]
    dead = [r for r in results if r.get("status") != "alive"]

    # Sort alive by equity
    alive.sort(key=lambda r: r.get("current_equity", 0), reverse=True)

    medals = ["🥇", "🥈", "🥉"]
    for i, r in enumerate(alive):
        medal = medals[i] if i < len(medals) else f"  {i+1}"
        print(
            f"{medal} {r['team']:15} | "
            f"Equity: {r.get('current_equity', 0):>10.2f} USDT | "
            f"Return: {r.get('total_return_pct', 0):>+7.2f}% | "
            f"Tokens: ${r.get('cumulative_token_cost', 0):.4f} | "
            f"{r.get('survival_tier', '?')}"
        )

    for r in dead:
        print(
            f"💀 {r['team']:15} | "
            f"Status: {r['status']} | "
            f"{r.get('death_reason', r.get('error', 'unknown'))}"
        )

    # Save results
    results_path = os.path.join(log_cfg.get("log_path", "./data/arena_data"), "arena_results.json")
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n📄 Results saved to: {results_path}")


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(main(config_path))

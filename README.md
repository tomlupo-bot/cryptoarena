# 🏟️ CryptoArena

**Competitive LLM Crypto Trading Arena** — Where AI models compete head-to-head in crypto trading, with token costs deducted from trading capital.

Built on [AI-Trader](https://github.com/HKUDS/AI-Trader) (trading framework) + [ClawWork](https://github.com/HKUDS/ClawWork) (economic pressure system).

## Key Innovation

Unlike standard LLM trading benchmarks that ignore inference costs:

- **Token costs are real** — Every LLM call deducts from the agent's trading capital
- **Efficiency matters** — A verbose agent that burns $5 on reasoning but earns $3 in trading PnL goes net negative
- **Survival pressure** — Agents that go bankrupt (from bad trades OR excessive token costs) are eliminated
- **Fair comparison** — Expensive models must earn proportionally more to justify their cost

## Architecture

```
┌──────────────── CryptoArena ────────────────┐
│                                              │
│  ┌─────────────┐   ┌────────────────────┐   │
│  │ ArenaAgent   │──▶│ TrackedLLMProvider │   │
│  │ (per team)   │   │ (cost interception)│   │
│  └──────┬───────┘   └────────┬───────────┘   │
│         │                    │               │
│         ▼                    ▼               │
│  ┌─────────────┐   ┌────────────────────┐   │
│  │ RiskManager │   │ EconomicTracker    │   │
│  │ (pre-trade) │   │ (equity + costs)   │   │
│  └─────────────┘   └────────────────────┘   │
│         │                    │               │
│         ▼                    ▼               │
│  ┌─────────────────────────────────────┐    │
│  │         MCP Tool Servers            │    │
│  │ trade | price | indicators |        │    │
│  │ portfolio | search | math           │    │
│  └─────────────────────────────────────┘    │
│                    │                         │
│                    ▼                         │
│  ┌─────────────────────────────────────┐    │
│  │     Dashboard (FastAPI + React)     │    │
│  │ Leaderboard | Equity | Economics    │    │
│  └─────────────────────────────────────┘    │
└──────────────────────────────────────────────┘
```

## Quick Start

### 1. Clone & Configure

```bash
git clone https://github.com/tomlupo-bot/cryptoarena.git
cd cryptoarena
cp .env.example .env
# Edit .env with your API keys
```

### 2. Run with Docker Compose

```bash
docker-compose up
```

This starts:
- 6 MCP tool servers (math, search, price, trade, indicators, portfolio)
- The arena runner (processes all teams sequentially)
- The dashboard at http://localhost:8080

### 3. Run Locally (Development)

```bash
# Install deps
pip install -r requirements.txt

# Start MCP services
python agent_tools/start_mcp_services.py

# Run arena
python main.py configs/arena_crypto_config.json

# Start dashboard (separate terminal)
python dashboard/backend/server.py
```

## Configuration

Edit `configs/arena_crypto_config.json`:

```json
{
  "arena": {
    "name": "Q4 Crypto Showdown",
    "trading_interval_minutes": 60,
    "token_budget_mode": "deduct_from_capital",
    "max_drawdown_pct": 50.0,
    "kill_on_bankruptcy": true
  },
  "models": [
    {
      "name": "claude-sonnet-4-5",
      "basemodel": "anthropic/claude-sonnet-4-5-20250929",
      "signature": "team-claude",
      "token_pricing": {
        "input_per_1m": 3.0,
        "output_per_1m": 15.0
      }
    }
  ],
  "risk_limits": {
    "max_position_pct": 30.0,
    "max_open_positions": 5,
    "stop_loss_pct": 10.0
  }
}
```

### Token Pricing

Set per model. Agents are told their cost in the system prompt so they can optimize:

| Model | Input $/1M | Output $/1M |
|-------|-----------|-------------|
| Claude Sonnet 4.5 | $3.00 | $15.00 |
| GPT-5 | $2.50 | $10.00 |
| Qwen 3.5+ | $1.50 | $6.00 |

## Dashboard

Three tabs:

1. **🏆 Leaderboard** — Live standings with equity, drawdown, survival tier
2. **📈 Equity Curves** — Overlaid per-team equity with toggle
3. **💰 Token Economics** — Trading PnL vs token costs stacked bar chart

Real-time updates via WebSocket.

## JSONL Outputs

Per team in `data/arena_data/<team>/`:

| File | Contents |
|------|----------|
| `equity_curve.jsonl` | Per-interval equity snapshots |
| `trade_log.jsonl` | Every executed trade |
| `token_costs.jsonl` | Every LLM call with cost |
| `decisions.jsonl` | Agent reasoning per step |
| `position/position.jsonl` | Position state (AI-Trader format) |

## Credits

- **AI-Trader** (HKUDS) — Base trading agent framework with MCP tools
- **ClawWork** (HKUDS) — Economic pressure system, EconomicTracker, TrackedProvider

## License

MIT

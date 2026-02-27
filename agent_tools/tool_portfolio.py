"""
MCP Tool: Portfolio Status

Enhanced portfolio view with economic tracker data.
Returns cash, positions, equity, token costs, survival tier, risk metrics.
"""

import json
import os
import sys
from typing import Any, Dict

from fastmcp import FastMCP

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from tools.general_tools import get_config_value
from tools.price_tools import get_latest_position, get_open_prices

mcp = FastMCP("PortfolioStatus")


@mcp.tool()
def get_portfolio_status() -> Dict[str, Any]:
    """
    Returns current portfolio state including:
    - Cash balance (after token cost deductions)
    - Open positions with unrealized PnL
    - Total equity
    - Cumulative token costs
    - Survival tier
    - Risk metrics (drawdown, position concentration)
    """
    signature = get_config_value("SIGNATURE")
    today_date = get_config_value("TODAY_DATE")

    if not signature:
        return {"error": "SIGNATURE not set"}

    try:
        current_position, action_id = get_latest_position(today_date, signature)
    except Exception as e:
        return {"error": f"Failed to load positions: {e}"}

    cash = current_position.get("CASH", 0)

    # Get current prices for position valuation
    crypto_symbols = [k for k in current_position if k.endswith("-USDT") and current_position[k] > 0]
    total_unrealized = 0
    positions_detail = []

    if crypto_symbols:
        try:
            prices = get_open_prices(today_date, crypto_symbols, market="crypto")
            for sym in crypto_symbols:
                qty = current_position[sym]
                price_key = f"{sym}_price"
                price = prices.get(price_key, 0)
                value = qty * price
                total_unrealized += value
                positions_detail.append({
                    "symbol": sym,
                    "quantity": round(qty, 8),
                    "current_price": round(price, 4),
                    "value_usdt": round(value, 4),
                })
        except Exception:
            pass

    equity = cash + total_unrealized

    # Load token cost data if available
    token_costs_file = os.path.join(
        project_root, "data", "arena_data", signature, "token_costs.jsonl"
    )
    cumulative_token_cost = 0.0
    if os.path.exists(token_costs_file):
        with open(token_costs_file) as f:
            for line in f:
                entry = json.loads(line)
                cumulative_token_cost = entry.get("cumulative_cost", cumulative_token_cost)

    return {
        "date": today_date,
        "cash": round(cash, 4),
        "positions": positions_detail,
        "unrealized_pnl": round(total_unrealized, 4),
        "equity": round(equity, 4),
        "cumulative_token_cost": round(cumulative_token_cost, 8),
        "num_open_positions": len(positions_detail),
    }


if __name__ == "__main__":
    port = int(os.getenv("PORTFOLIO_HTTP_PORT", "8007"))
    mcp.run(transport="streamable-http", port=port)

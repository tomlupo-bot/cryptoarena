"""
MCP Tool: Funding Rates (optional, for perp-futures competitions)

Queries historical funding rate data for basis/carry trade analysis.
"""

import json
import os
import sys
from typing import Any, Dict

from fastmcp import FastMCP

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

mcp = FastMCP("FundingRates")


@mcp.tool()
def get_funding_rates(symbol: str, lookback_days: int, current_date: str) -> Dict[str, Any]:
    """
    Query historical funding rates for a crypto symbol.

    Args:
        symbol: e.g. 'BTC-USDT'
        lookback_days: Number of days to look back
        current_date: Current date (YYYY-MM-DD) for anti-look-ahead

    Returns:
        Dictionary with funding rate history.
    """
    data_path = os.path.join(project_root, "data", "crypto", "funding_rates.jsonl")
    if not os.path.exists(data_path):
        return {
            "error": "Funding rate data not available. This is an optional feature.",
            "symbol": symbol,
        }

    rates = []
    with open(data_path) as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("symbol") == symbol and entry.get("date") <= current_date:
                rates.append(entry)

    rates = sorted(rates, key=lambda x: x["date"])[-lookback_days:]

    if not rates:
        return {"symbol": symbol, "rates": [], "message": "No funding rate data found"}

    avg_rate = sum(r.get("rate", 0) for r in rates) / len(rates)
    return {
        "symbol": symbol,
        "lookback_days": lookback_days,
        "rates": rates,
        "avg_funding_rate": round(avg_rate, 6),
        "latest_rate": rates[-1].get("rate", 0) if rates else None,
    }


if __name__ == "__main__":
    port = int(os.getenv("FUNDING_HTTP_PORT", "8008"))
    mcp.run(transport="streamable-http", port=port)

"""
MCP Tool: Technical Indicators

Computed from local price data (no API cost to the agent).
Supports: SMA, EMA, RSI, MACD, Bollinger Bands, ATR, VWAP.
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

mcp = FastMCP("TechnicalIndicators")


def _load_price_series(symbol: str, end_date: str, lookback: int = 100) -> List[Dict[str, float]]:
    """Load OHLCV data from crypto_merged.jsonl up to end_date."""
    data_path = os.path.join(project_root, "data", "crypto", "crypto_merged.jsonl")
    if not os.path.exists(data_path):
        return []

    series = {}
    with open(data_path, "r") as f:
        for line in f:
            doc = json.loads(line)
            meta = doc.get("Meta Data", {})
            if meta.get("2. Symbol") != symbol:
                continue
            ts = doc.get("Time Series (Daily)", {})
            for date_str, vals in ts.items():
                if date_str <= end_date:
                    series[date_str] = {
                        "open": float(vals.get("1. open") or vals.get("1. buy price") or 0),
                        "high": float(vals.get("2. high", 0)),
                        "low": float(vals.get("3. low", 0)),
                        "close": float(vals.get("4. close") or vals.get("4. sell price") or 0),
                        "volume": float(vals.get("5. volume", 0)),
                    }
            break

    sorted_dates = sorted(series.keys())[-lookback:]
    return [{"date": d, **series[d]} for d in sorted_dates]


def _sma(closes: List[float], period: int) -> Optional[float]:
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def _ema(closes: List[float], period: int) -> Optional[float]:
    if len(closes) < period:
        return None
    mult = 2 / (period + 1)
    ema = sum(closes[:period]) / period
    for price in closes[period:]:
        ema = (price - ema) * mult + ema
    return ema


def _rsi(closes: List[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


@mcp.tool()
def get_indicators(symbol: str, indicator: str, current_date: str, period: int = 14) -> Dict[str, Any]:
    """
    Compute a technical indicator for a crypto symbol.

    Args:
        symbol: e.g. 'BTC-USDT'
        indicator: One of 'SMA', 'EMA', 'RSI', 'MACD', 'BBANDS', 'ATR'
        current_date: Date up to which to compute (YYYY-MM-DD), anti-look-ahead
        period: Lookback period (default 14)

    Returns:
        Dictionary with indicator values.
    """
    series = _load_price_series(symbol, current_date, lookback=200)
    if not series:
        return {"error": f"No price data for {symbol}", "symbol": symbol}

    closes = [bar["close"] for bar in series]
    highs = [bar["high"] for bar in series]
    lows = [bar["low"] for bar in series]
    ind = indicator.upper()

    if ind == "SMA":
        val = _sma(closes, period)
        return {"symbol": symbol, "indicator": "SMA", "period": period, "value": val, "date": current_date}

    elif ind == "EMA":
        val = _ema(closes, period)
        return {"symbol": symbol, "indicator": "EMA", "period": period, "value": val, "date": current_date}

    elif ind == "RSI":
        val = _rsi(closes, period)
        return {"symbol": symbol, "indicator": "RSI", "period": period, "value": round(val, 2) if val else None, "date": current_date}

    elif ind == "MACD":
        ema12 = _ema(closes, 12)
        ema26 = _ema(closes, 26)
        if ema12 is None or ema26 is None:
            return {"error": "Not enough data for MACD", "symbol": symbol}
        macd_line = ema12 - ema26
        return {
            "symbol": symbol, "indicator": "MACD",
            "macd_line": round(macd_line, 4),
            "ema12": round(ema12, 4), "ema26": round(ema26, 4),
            "date": current_date,
        }

    elif ind == "BBANDS":
        sma_val = _sma(closes, period)
        if sma_val is None:
            return {"error": "Not enough data", "symbol": symbol}
        variance = sum((c - sma_val) ** 2 for c in closes[-period:]) / period
        std = variance ** 0.5
        return {
            "symbol": symbol, "indicator": "BBANDS", "period": period,
            "middle": round(sma_val, 4),
            "upper": round(sma_val + 2 * std, 4),
            "lower": round(sma_val - 2 * std, 4),
            "date": current_date,
        }

    elif ind == "ATR":
        if len(closes) < period + 1:
            return {"error": "Not enough data for ATR", "symbol": symbol}
        trs = []
        for i in range(1, len(series)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            trs.append(tr)
        atr = sum(trs[-period:]) / period
        return {"symbol": symbol, "indicator": "ATR", "period": period, "value": round(atr, 4), "date": current_date}

    else:
        return {"error": f"Unknown indicator: {indicator}. Use SMA, EMA, RSI, MACD, BBANDS, or ATR."}


if __name__ == "__main__":
    port = int(os.getenv("INDICATORS_HTTP_PORT", "8006"))
    mcp.run(transport="streamable-http", port=port)

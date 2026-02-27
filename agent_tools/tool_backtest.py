"""
MCP Tool: Backtesting with VectorBT
Provides agents with backtesting capabilities for crypto trading strategies.
Based on: https://github.com/marketcalls/vectorbt-backtesting-skills
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import numpy as np
import pandas as pd
import vectorbt as vbt

from tools.general_tools import get_config_value

mcp = FastMCP("Backtesting")


def _load_price_series(symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """Load OHLCV from local crypto data."""
    data_path = os.path.join(project_root, "data", "crypto", "crypto_merged.jsonl")
    if not os.path.exists(data_path):
        return None

    records = []
    with open(data_path) as f:
        for line in f:
            doc = json.loads(line)
            meta = doc.get("Meta Data", {})
            if meta.get("2. Symbol") != symbol:
                continue
            ts = doc.get("Time Series (Daily)", {})
            for date_str, ohlcv in ts.items():
                if start_date <= date_str <= end_date:
                    records.append({
                        "date": date_str,
                        "open": float(ohlcv["1. open"]),
                        "high": float(ohlcv["2. high"]),
                        "low": float(ohlcv["3. low"]),
                        "close": float(ohlcv["4. close"]),
                        "volume": float(ohlcv["5. volume"]),
                    })

    if not records:
        return None

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df


@mcp.tool()
def backtest_sma_crossover(
    symbol: str,
    start_date: str,
    end_date: str,
    fast_period: int = 10,
    slow_period: int = 30,
    initial_cash: float = 10000.0,
    fees: float = 0.001,
) -> dict:
    """Backtest SMA crossover strategy on a crypto symbol.
    
    Tests a simple moving average crossover: buy when fast SMA crosses above slow SMA,
    sell when it crosses below. Returns performance metrics.

    Args:
        symbol: Crypto symbol (e.g., 'BTC-USDT', 'ETH-USDT')
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        fast_period: Fast SMA period (default 10)
        slow_period: Slow SMA period (default 30)
        initial_cash: Starting capital (default 10000)
        fees: Trading fees as decimal (default 0.001 = 0.1%)

    Returns:
        Dictionary with backtest results including total return, sharpe, max drawdown.
    """
    df = _load_price_series(symbol, start_date, end_date)
    if df is None or len(df) < slow_period + 5:
        return {"error": f"Insufficient data for {symbol} ({start_date} to {end_date})"}

    close = df["close"]
    fast_sma = vbt.MA.run(close, window=fast_period)
    slow_sma = vbt.MA.run(close, window=slow_period)

    entries = fast_sma.ma_crossed_above(slow_sma)
    exits = fast_sma.ma_crossed_below(slow_sma)

    pf = vbt.Portfolio.from_signals(
        close, entries, exits,
        init_cash=initial_cash,
        fees=fees,
        freq="1D",
    )

    stats = pf.stats()
    return {
        "symbol": symbol,
        "strategy": f"SMA({fast_period}/{slow_period})",
        "period": f"{start_date} to {end_date}",
        "total_return_pct": round(float(stats.get("Total Return [%]", 0)), 2),
        "sharpe_ratio": round(float(stats.get("Sharpe Ratio", 0)), 3),
        "sortino_ratio": round(float(stats.get("Sortino Ratio", 0)), 3),
        "max_drawdown_pct": round(float(stats.get("Max Drawdown [%]", 0)), 2),
        "win_rate_pct": round(float(stats.get("Win Rate [%]", 0)), 2),
        "total_trades": int(stats.get("Total Trades", 0)),
        "profit_factor": round(float(stats.get("Profit Factor", 0)), 3),
        "final_value": round(float(pf.final_value()), 2),
        "buy_hold_return_pct": round(float((close.iloc[-1] / close.iloc[0] - 1) * 100), 2),
    }


@mcp.tool()
def backtest_rsi_strategy(
    symbol: str,
    start_date: str,
    end_date: str,
    rsi_period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
    initial_cash: float = 10000.0,
    fees: float = 0.001,
) -> dict:
    """Backtest RSI mean-reversion strategy: buy when RSI < oversold, sell when RSI > overbought.

    Args:
        symbol: Crypto symbol (e.g., 'BTC-USDT')
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        rsi_period: RSI lookback period (default 14)
        oversold: Buy threshold (default 30)
        overbought: Sell threshold (default 70)
        initial_cash: Starting capital
        fees: Trading fees as decimal

    Returns:
        Backtest results with return, sharpe, drawdown metrics.
    """
    df = _load_price_series(symbol, start_date, end_date)
    if df is None or len(df) < rsi_period + 5:
        return {"error": f"Insufficient data for {symbol}"}

    close = df["close"]
    rsi = vbt.RSI.run(close, window=rsi_period)

    entries = rsi.rsi_below(oversold)
    exits = rsi.rsi_above(overbought)

    pf = vbt.Portfolio.from_signals(
        close, entries, exits,
        init_cash=initial_cash,
        fees=fees,
        freq="1D",
    )

    stats = pf.stats()
    return {
        "symbol": symbol,
        "strategy": f"RSI({rsi_period}, {oversold}/{overbought})",
        "period": f"{start_date} to {end_date}",
        "total_return_pct": round(float(stats.get("Total Return [%]", 0)), 2),
        "sharpe_ratio": round(float(stats.get("Sharpe Ratio", 0)), 3),
        "sortino_ratio": round(float(stats.get("Sortino Ratio", 0)), 3),
        "max_drawdown_pct": round(float(stats.get("Max Drawdown [%]", 0)), 2),
        "win_rate_pct": round(float(stats.get("Win Rate [%]", 0)), 2),
        "total_trades": int(stats.get("Total Trades", 0)),
        "final_value": round(float(pf.final_value()), 2),
        "buy_hold_return_pct": round(float((close.iloc[-1] / close.iloc[0] - 1) * 100), 2),
    }


@mcp.tool()
def backtest_custom_signals(
    symbol: str,
    start_date: str,
    end_date: str,
    buy_dates: str,
    sell_dates: str,
    initial_cash: float = 10000.0,
    fees: float = 0.001,
) -> dict:
    """Backtest custom buy/sell signals on historical data.

    Args:
        symbol: Crypto symbol (e.g., 'BTC-USDT')
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        buy_dates: Comma-separated buy dates (e.g., '2025-10-01,2025-10-05')
        sell_dates: Comma-separated sell dates (e.g., '2025-10-03,2025-10-07')
        initial_cash: Starting capital
        fees: Trading fees

    Returns:
        Backtest results.
    """
    df = _load_price_series(symbol, start_date, end_date)
    if df is None or len(df) < 2:
        return {"error": f"Insufficient data for {symbol}"}

    close = df["close"]
    entries = pd.Series(False, index=close.index)
    exits = pd.Series(False, index=close.index)

    for d in buy_dates.split(","):
        d = d.strip()
        if d:
            dt = pd.Timestamp(d)
            if dt in entries.index:
                entries[dt] = True

    for d in sell_dates.split(","):
        d = d.strip()
        if d:
            dt = pd.Timestamp(d)
            if dt in exits.index:
                exits[dt] = True

    pf = vbt.Portfolio.from_signals(
        close, entries, exits,
        init_cash=initial_cash,
        fees=fees,
        freq="1D",
    )

    stats = pf.stats()
    return {
        "symbol": symbol,
        "strategy": "Custom Signals",
        "total_return_pct": round(float(stats.get("Total Return [%]", 0)), 2),
        "sharpe_ratio": round(float(stats.get("Sharpe Ratio", 0)), 3),
        "max_drawdown_pct": round(float(stats.get("Max Drawdown [%]", 0)), 2),
        "total_trades": int(stats.get("Total Trades", 0)),
        "final_value": round(float(pf.final_value()), 2),
    }


@mcp.tool()
def get_available_symbols() -> dict:
    """List all available crypto symbols and their date ranges in the local dataset.

    Returns:
        Dictionary of symbols with their available date ranges and number of data points.
    """
    data_path = os.path.join(project_root, "data", "crypto", "crypto_merged.jsonl")
    if not os.path.exists(data_path):
        return {"error": "No price data found"}

    symbols = {}
    with open(data_path) as f:
        for line in f:
            doc = json.loads(line)
            meta = doc.get("Meta Data", {})
            sym = meta.get("2. Symbol", "")
            date = meta.get("3. Last Refreshed", "")
            if sym not in symbols:
                symbols[sym] = {"dates": []}
            symbols[sym]["dates"].append(date)

    result = {}
    for sym, info in symbols.items():
        dates = sorted(info["dates"])
        result[sym] = {
            "first_date": dates[0],
            "last_date": dates[-1],
            "data_points": len(dates),
        }
    return result


if __name__ == "__main__":
    port = int(os.getenv("BACKTEST_HTTP_PORT", "8008"))
    mcp.run(transport="streamable-http", port=port)

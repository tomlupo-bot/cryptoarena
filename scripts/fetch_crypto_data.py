#!/usr/bin/env python3
"""Fetch historical crypto OHLCV data and write to crypto_merged.jsonl format."""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import urllib.request
except ImportError:
    pass

SYMBOLS = [
    "BTC-USDT", "ETH-USDT", "XRP-USDT", "SOL-USDT", "ADA-USDT",
    "SUI-USDT", "LINK-USDT", "AVAX-USDT", "LTC-USDT", "DOT-USDT",
]

# Map to CoinGecko IDs
COINGECKO_IDS = {
    "BTC-USDT": "bitcoin",
    "ETH-USDT": "ethereum", 
    "XRP-USDT": "ripple",
    "SOL-USDT": "solana",
    "ADA-USDT": "cardano",
    "SUI-USDT": "sui",
    "LINK-USDT": "chainlink",
    "AVAX-USDT": "avalanche-2",
    "LTC-USDT": "litecoin",
    "DOT-USDT": "polkadot",
}


def fetch_coingecko_ohlc(coin_id, days=90):
    """Fetch OHLC from CoinGecko (free, no key needed)."""
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc?vs_currency=usd&days={days}"
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "CryptoArena/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fetch_coingecko_market_range(coin_id, from_ts, to_ts):
    """Fetch market chart range from CoinGecko."""
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range?vs_currency=usd&from={from_ts}&to={to_ts}"
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "CryptoArena/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def build_daily_jsonl(symbol, coin_id, start_date, end_date):
    """Build daily JSONL entries for a symbol."""
    # Use OHLC endpoint (gives 4-hourly candles for 90 days, daily for >90)
    days = (end_date - start_date).days + 10
    print(f"  Fetching {symbol} ({coin_id}) for {days} days...")
    
    try:
        ohlc_data = fetch_coingecko_ohlc(coin_id, days=days)
    except Exception as e:
        print(f"  ⚠️ OHLC failed for {symbol}: {e}")
        return []

    # Group by date for daily candles
    daily = {}
    for ts, o, h, l, c in ohlc_data:
        dt = datetime.utcfromtimestamp(ts / 1000)
        date_str = dt.strftime("%Y-%m-%d")
        if date_str not in daily:
            daily[date_str] = {"open": o, "high": h, "low": l, "close": c, "volume": 0}
        else:
            daily[date_str]["high"] = max(daily[date_str]["high"], h)
            daily[date_str]["low"] = min(daily[date_str]["low"], l)
            daily[date_str]["close"] = c  # last close of the day

    entries = []
    for date_str in sorted(daily.keys()):
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        if dt.date() < start_date.date() or dt.date() > end_date.date():
            continue
        d = daily[date_str]
        entry = {
            "Meta Data": {
                "1. Information": "Daily Prices (open, high, low, close) and Volumes",
                "2. Symbol": symbol,
                "3. Last Refreshed": date_str,
            },
            "Time Series (Daily)": {
                date_str: {
                    "1. open": str(d["open"]),
                    "2. high": str(d["high"]),
                    "3. low": str(d["low"]),
                    "4. close": str(d["close"]),
                    "5. volume": str(int(d.get("volume", 1000000))),
                }
            }
        }
        entries.append(entry)
    
    return entries


def build_hourly_jsonl(symbol, coin_id, start_date, end_date):
    """Build hourly JSONL entries from market_chart/range."""
    from_ts = int(start_date.timestamp())
    to_ts = int(end_date.timestamp())
    
    print(f"  Fetching hourly {symbol}...")
    try:
        data = fetch_coingecko_market_range(coin_id, from_ts, to_ts)
    except Exception as e:
        print(f"  ⚠️ Hourly failed for {symbol}: {e}")
        return []
    
    prices = data.get("prices", [])
    entries = []
    
    # Group into hourly candles
    hourly = {}
    for ts, price in prices:
        dt = datetime.utcfromtimestamp(ts / 1000)
        hour_key = dt.strftime("%Y-%m-%d %H:00:00")
        if hour_key not in hourly:
            hourly[hour_key] = {"open": price, "high": price, "low": price, "close": price}
        else:
            hourly[hour_key]["high"] = max(hourly[hour_key]["high"], price)
            hourly[hour_key]["low"] = min(hourly[hour_key]["low"], price)
            hourly[hour_key]["close"] = price
    
    for hour_key in sorted(hourly.keys()):
        d = hourly[hour_key]
        entry = {
            "Meta Data": {
                "1. Information": "Intraday (60min) open, high, low, close prices and volumes",
                "2. Symbol": symbol,
                "3. Last Refreshed": hour_key,
            },
            "Time Series (60min)": {
                hour_key: {
                    "1. open": str(d["open"]),
                    "2. high": str(d["high"]),
                    "3. low": str(d["low"]),
                    "4. close": str(d["close"]),
                    "5. volume": "1000000",
                }
            }
        }
        entries.append(entry)
    
    return entries


def main():
    start_date = datetime(2025, 9, 25)  # A bit before Oct 1 for lookback
    end_date = datetime(2025, 10, 5)    # Test window + buffer
    
    if len(sys.argv) > 1:
        end_date = datetime.strptime(sys.argv[1], "%Y-%m-%d")
    if len(sys.argv) > 2:
        start_date = datetime.strptime(sys.argv[2], "%Y-%m-%d")

    out_dir = Path(__file__).resolve().parents[1] / "data" / "crypto"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    daily_path = out_dir / "crypto_merged.jsonl"
    hourly_path = out_dir / "crypto_hourly.jsonl"
    
    all_daily = []
    all_hourly = []
    
    import time
    
    for symbol in SYMBOLS:
        coin_id = COINGECKO_IDS[symbol]
        
        daily_entries = build_daily_jsonl(symbol, coin_id, start_date, end_date)
        all_daily.extend(daily_entries)
        print(f"  ✅ {symbol}: {len(daily_entries)} daily entries")
        
        time.sleep(1.5)  # Rate limit
        
        hourly_entries = build_hourly_jsonl(symbol, coin_id, start_date, end_date)
        all_hourly.extend(hourly_entries)
        print(f"  ✅ {symbol}: {len(hourly_entries)} hourly entries")
        
        time.sleep(1.5)
    
    with open(daily_path, "w") as f:
        for entry in all_daily:
            f.write(json.dumps(entry) + "\n")
    
    with open(hourly_path, "w") as f:
        for entry in all_hourly:
            f.write(json.dumps(entry) + "\n")
    
    print(f"\n✅ Written {len(all_daily)} daily entries to {daily_path}")
    print(f"✅ Written {len(all_hourly)} hourly entries to {hourly_path}")


if __name__ == "__main__":
    main()

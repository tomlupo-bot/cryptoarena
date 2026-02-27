#!/usr/bin/env python3
"""Fetch crypto OHLCV from Binance public API (no key needed)."""

import json
import time
import urllib.request
from datetime import datetime
from pathlib import Path

SYMBOLS = {
    "BTC-USDT": "BTCUSDT",
    "ETH-USDT": "ETHUSDT",
    "XRP-USDT": "XRPUSDT",
    "SOL-USDT": "SOLUSDT",
    "ADA-USDT": "ADAUSDT",
    "SUI-USDT": "SUIUSDT",
    "LINK-USDT": "LINKUSDT",
    "AVAX-USDT": "AVAXUSDT",
    "LTC-USDT": "LTCUSDT",
    "DOT-USDT": "DOTUSDT",
}

START = datetime(2025, 9, 25)
END = datetime(2025, 10, 5)


def fetch_klines(binance_symbol, interval, start_ms, end_ms):
    url = (f"https://api.binance.com/api/v3/klines?"
           f"symbol={binance_symbol}&interval={interval}"
           f"&startTime={start_ms}&endTime={end_ms}&limit=1000")
    req = urllib.request.Request(url, headers={"User-Agent": "CryptoArena/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main():
    out_dir = Path(__file__).resolve().parents[1] / "data" / "crypto"
    out_dir.mkdir(parents=True, exist_ok=True)

    start_ms = int(START.timestamp() * 1000)
    end_ms = int(END.timestamp() * 1000)

    daily_entries = []
    hourly_entries = []

    for arena_sym, binance_sym in SYMBOLS.items():
        print(f"Fetching {arena_sym}...")

        # Daily
        try:
            klines = fetch_klines(binance_sym, "1d", start_ms, end_ms)
            for k in klines:
                dt = datetime.utcfromtimestamp(k[0] / 1000)
                date_str = dt.strftime("%Y-%m-%d")
                daily_entries.append({
                    "Meta Data": {
                        "1. Information": "Daily Prices",
                        "2. Symbol": arena_sym,
                        "3. Last Refreshed": date_str,
                    },
                    "Time Series (Daily)": {
                        date_str: {
                            "1. open": k[1], "2. high": k[2],
                            "3. low": k[3], "4. close": k[4],
                            "5. volume": k[5],
                        }
                    }
                })
            print(f"  ✅ {len(klines)} daily candles")
        except Exception as e:
            print(f"  ❌ daily: {e}")

        time.sleep(0.3)

        # Hourly
        try:
            klines = fetch_klines(binance_sym, "1h", start_ms, end_ms)
            for k in klines:
                dt = datetime.utcfromtimestamp(k[0] / 1000)
                ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                hourly_entries.append({
                    "Meta Data": {
                        "1. Information": "Intraday (60min)",
                        "2. Symbol": arena_sym,
                        "3. Last Refreshed": ts_str,
                    },
                    "Time Series (60min)": {
                        ts_str: {
                            "1. open": k[1], "2. high": k[2],
                            "3. low": k[3], "4. close": k[4],
                            "5. volume": k[5],
                        }
                    }
                })
            print(f"  ✅ {len(klines)} hourly candles")
        except Exception as e:
            print(f"  ❌ hourly: {e}")

        time.sleep(0.3)

    with open(out_dir / "crypto_merged.jsonl", "w") as f:
        for e in daily_entries:
            f.write(json.dumps(e) + "\n")

    with open(out_dir / "crypto_hourly.jsonl", "w") as f:
        for e in hourly_entries:
            f.write(json.dumps(e) + "\n")

    print(f"\n✅ {len(daily_entries)} daily, {len(hourly_entries)} hourly entries written")


if __name__ == "__main__":
    main()

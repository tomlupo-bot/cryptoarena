#!/usr/bin/env python3
"""Fetch wider crypto data from Binance for a proper test."""
import json, time, urllib.request
from datetime import datetime
from pathlib import Path

SYMBOLS = {
    "BTC-USDT": "BTCUSDT", "ETH-USDT": "ETHUSDT", "XRP-USDT": "XRPUSDT",
    "SOL-USDT": "SOLUSDT", "ADA-USDT": "ADAUSDT", "SUI-USDT": "SUIUSDT",
    "LINK-USDT": "LINKUSDT", "AVAX-USDT": "AVAXUSDT", "LTC-USDT": "LTCUSDT",
    "DOT-USDT": "DOTUSDT",
}

# Sep 20 - Oct 15 for enough lookback + trading window
START = datetime(2025, 9, 20)
END = datetime(2025, 10, 15)

def fetch_klines(sym, interval, start_ms, end_ms):
    url = f"https://api.binance.com/api/v3/klines?symbol={sym}&interval={interval}&startTime={start_ms}&endTime={end_ms}&limit=1000"
    req = urllib.request.Request(url, headers={"User-Agent": "CryptoArena/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

def main():
    out_dir = Path(__file__).resolve().parents[1] / "data" / "crypto"
    out_dir.mkdir(parents=True, exist_ok=True)
    start_ms, end_ms = int(START.timestamp()*1000), int(END.timestamp()*1000)
    daily_entries, hourly_entries = [], []

    for arena_sym, binance_sym in SYMBOLS.items():
        print(f"Fetching {arena_sym}...", end=" ", flush=True)
        try:
            klines = fetch_klines(binance_sym, "1d", start_ms, end_ms)
            for k in klines:
                dt = datetime.utcfromtimestamp(k[0]/1000)
                ds = dt.strftime("%Y-%m-%d")
                daily_entries.append({"Meta Data":{"1. Information":"Daily Prices","2. Symbol":arena_sym,"3. Last Refreshed":ds},"Time Series (Daily)":{ds:{"1. open":k[1],"2. high":k[2],"3. low":k[3],"4. close":k[4],"5. volume":k[5]}}})
            print(f"{len(klines)}d", end=" ", flush=True)
        except Exception as e:
            print(f"daily err: {e}", end=" ")
        time.sleep(0.2)

        # Hourly in chunks (1000 limit = ~41 days at 1h, should be fine)
        try:
            klines = fetch_klines(binance_sym, "1h", start_ms, end_ms)
            for k in klines:
                dt = datetime.utcfromtimestamp(k[0]/1000)
                ts = dt.strftime("%Y-%m-%d %H:%M:%S")
                hourly_entries.append({"Meta Data":{"1. Information":"Intraday (60min)","2. Symbol":arena_sym,"3. Last Refreshed":ts},"Time Series (60min)":{ts:{"1. open":k[1],"2. high":k[2],"3. low":k[3],"4. close":k[4],"5. volume":k[5]}}})
            print(f"{len(klines)}h ✅")
        except Exception as e:
            print(f"hourly err: {e}")
        time.sleep(0.2)

    with open(out_dir/"crypto_merged.jsonl","w") as f:
        for e in daily_entries: f.write(json.dumps(e)+"\n")
    with open(out_dir/"crypto_hourly.jsonl","w") as f:
        for e in hourly_entries: f.write(json.dumps(e)+"\n")
    print(f"\n✅ {len(daily_entries)} daily, {len(hourly_entries)} hourly")

if __name__=="__main__": main()

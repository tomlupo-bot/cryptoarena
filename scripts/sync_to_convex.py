#!/usr/bin/env python3
"""
Sync arena results to Convex (shared with Mission Control deployment).
Run after arena completes or during a run for live updates.

Usage:
    python sync_to_convex.py --experiment-name "3-Day Test" --data-dir ./data/arena_data
"""
import argparse
import json
import os
import sys
from pathlib import Path

import requests

CONVEX_URL = os.getenv("CONVEX_URL", "https://giant-eel-625.eu-west-1.convex.cloud")


def convex_mutation(name: str, args: dict):
    """Call a Convex mutation via HTTP."""
    resp = requests.post(
        f"{CONVEX_URL}/api/mutation",
        json={"path": f"arena:{name}", "args": args},
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    if "errorMessage" in result:
        print(f"  ❌ {name}: {result['errorMessage']}")
        return None
    return result.get("value")


def read_jsonl(path: Path):
    if not path.exists():
        return []
    entries = []
    with open(path) as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    return entries


def sync(experiment_name: str, data_dir: Path, config_path: Path = None):
    print(f"🔄 Syncing to Convex: {experiment_name}")

    # Load config
    config = {}
    if config_path and config_path.exists():
        config = json.loads(config_path.read_text())

    date_range = config.get("date_range", {})
    teams_config = config.get("models", [])
    team_names = [m["signature"] for m in teams_config if m.get("enabled", True)]

    # Create or find experiment
    experiment_id = convex_mutation("createExperiment", {
        "name": experiment_name,
        "config": config,
        "dateRange": {
            "initDate": date_range.get("init_date", "unknown"),
            "endDate": date_range.get("end_date", "unknown"),
        },
        "teams": team_names,
    })
    print(f"  📋 Experiment: {experiment_id}")

    if not experiment_id:
        print("  ❌ Failed to create experiment")
        return

    # Load results
    results_path = data_dir / "arena_results.json"
    if results_path.exists():
        results = json.loads(results_path.read_text())
        total_cost = 0

        for r in results:
            total_cost += r.get("cumulative_token_cost", 0)
            convex_mutation("upsertTeamResult", {
                "experimentId": experiment_id,
                "team": r["team"],
                "model": r.get("model", "unknown"),
                "status": r.get("status", "alive"),
                "equity": r.get("current_equity", 10000),
                "returnPct": r.get("total_return_pct", 0),
                "drawdownPct": r.get("max_drawdown_pct", 0),
                "tokenCost": r.get("cumulative_token_cost", 0),
                "llmCalls": r.get("total_llm_calls", 0),
                "survivalTier": r.get("survival_tier", "unknown"),
                "deathReason": r.get("death_reason"),
            })
            print(f"  ✅ {r['team']}: ${r.get('current_equity', 0):,.2f}")

        # Update experiment status
        convex_mutation("updateExperimentStatus", {
            "id": experiment_id,
            "status": "completed",
            "completedAt": int(os.path.getmtime(results_path) * 1000),
            "totalTokenCost": total_cost,
        })

    # Sync equity curves and trades per team
    if not data_dir.exists():
        print(f"  ⚠️ Data dir not found: {data_dir}")
        return

    for team_dir in sorted(data_dir.iterdir()):
        if not team_dir.is_dir() or team_dir.name.startswith("."):
            continue
        team = team_dir.name

        # Equity curve
        equity_data = read_jsonl(team_dir / "equity_curve.jsonl")
        if equity_data:
            batch = []
            for s in equity_data:
                batch.append({
                    "experimentId": experiment_id,
                    "team": team,
                    "timestamp": s.get("timestamp", ""),
                    "equity": s.get("equity", 0),
                    "cash": s.get("cash", 0),
                    "drawdownPct": s.get("drawdown_pct", 0),
                    "tokenCost": s.get("cumulative_token_cost", 0),
                    "survivalTier": s.get("survival_tier", "unknown"),
                })
            # Batch in chunks of 50
            for i in range(0, len(batch), 50):
                convex_mutation("bulkAddEquity", {"snapshots": batch[i:i+50]})
            print(f"  📈 {team}: {len(equity_data)} equity snapshots")

        # Trades
        positions = read_jsonl(team_dir / "position" / "position.jsonl")
        trades = []
        for p in positions:
            action = p.get("this_action", {})
            if action:
                trades.append({
                    "experimentId": experiment_id,
                    "team": team,
                    "date": p.get("date", ""),
                    "action": action.get("action", "unknown"),
                    "symbol": action.get("symbol", "unknown"),
                    "amount": action.get("amount", 0),
                    "cashAfter": p.get("positions", {}).get("CASH"),
                })
        if trades:
            for i in range(0, len(trades), 50):
                convex_mutation("bulkAddTrades", {"trades": trades[i:i+50]})
            print(f"  📊 {team}: {len(trades)} trades")

    print("✅ Sync complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="Arena Run")
    parser.add_argument("--data-dir", default="./data/arena_data")
    parser.add_argument("--config", default="./configs/arena_crypto_config.json")
    args = parser.parse_args()
    sync(args.name, Path(args.data_dir), Path(args.config))

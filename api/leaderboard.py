"""Vercel serverless function — /api/leaderboard"""
import json
import os
from http.server import BaseHTTPRequestHandler
from pathlib import Path

DATA_PATH = Path(os.getenv("ARENA_DATA_PATH", "./data/arena_data"))

def read_jsonl(path):
    if not path.exists(): return []
    entries = []
    with open(path) as f:
        for line in f:
            if line.strip(): entries.append(json.loads(line))
    return entries

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        teams = [d.name for d in DATA_PATH.iterdir() if d.is_dir() and not d.name.startswith(".")] if DATA_PATH.exists() else []
        leaderboard = []
        for team in teams:
            equity_path = DATA_PATH / team / "equity_curve.jsonl"
            snapshots = read_jsonl(equity_path)
            latest = snapshots[-1] if snapshots else {}
            leaderboard.append({
                "team": team,
                "equity": latest.get("equity", 10000),
                "cash": latest.get("cash", 10000),
                "drawdown_pct": latest.get("drawdown_pct", 0),
                "survival_tier": latest.get("survival_tier", "unknown"),
                "cumulative_token_cost": latest.get("cumulative_token_cost", 0),
                "num_snapshots": len(snapshots),
            })
        leaderboard.sort(key=lambda x: x["equity"], reverse=True)
        medals = ["🥇", "🥈", "🥉"]
        for i, entry in enumerate(leaderboard):
            entry["rank"] = i + 1
            entry["medal"] = medals[i] if i < 3 else f"#{i+1}"

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"leaderboard": leaderboard}).encode())

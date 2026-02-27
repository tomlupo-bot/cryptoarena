"""
CryptoArena Dashboard API — FastAPI + WebSocket

Serves arena data for the React dashboard:
- Leaderboard
- Equity curves
- Trade logs
- Token economics
- Real-time updates via WebSocket
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="CryptoArena Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = Path(os.getenv("ARENA_DATA_PATH", "./data/arena_data"))


def _read_jsonl(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def _get_teams() -> List[str]:
    if not DATA_PATH.exists():
        return []
    return [
        d.name for d in DATA_PATH.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]


# ── REST endpoints ──────────────────────────────────────────────


@app.get("/api/teams")
def get_teams():
    return {"teams": _get_teams()}


@app.get("/api/leaderboard")
def get_leaderboard():
    """Return current standings sorted by equity."""
    teams = _get_teams()
    standings = []

    for team in teams:
        team_dir = DATA_PATH / team
        equity_data = _read_jsonl(team_dir / "equity_curve.jsonl")
        token_data = _read_jsonl(team_dir / "token_costs.jsonl")

        if equity_data:
            latest = equity_data[-1]
            standings.append({
                "team": team,
                "equity": latest.get("equity", 0),
                "cash": latest.get("cash", 0),
                "drawdown_pct": latest.get("drawdown_pct", 0),
                "survival_tier": latest.get("survival_tier", "unknown"),
                "cumulative_token_cost": latest.get("cumulative_token_cost", 0),
                "num_snapshots": len(equity_data),
            })
        else:
            standings.append({
                "team": team,
                "equity": 0,
                "survival_tier": "unknown",
                "num_snapshots": 0,
            })

    standings.sort(key=lambda x: x.get("equity", 0), reverse=True)

    # Add rank and medals
    medals = ["🥇", "🥈", "🥉"]
    for i, s in enumerate(standings):
        s["rank"] = i + 1
        s["medal"] = medals[i] if i < len(medals) else ""
        if s.get("survival_tier") == "dead":
            s["medal"] = "💀"

    return {"leaderboard": standings}


@app.get("/api/equity/{team}")
def get_equity_curve(team: str):
    data = _read_jsonl(DATA_PATH / team / "equity_curve.jsonl")
    if not data:
        raise HTTPException(404, f"No equity data for {team}")
    return {"team": team, "equity_curve": data}


@app.get("/api/trades/{team}")
def get_trade_log(team: str, limit: int = 100):
    data = _read_jsonl(DATA_PATH / team / "trade_log.jsonl")
    return {"team": team, "trades": data[-limit:], "total": len(data)}


@app.get("/api/token_costs/{team}")
def get_token_costs(team: str):
    data = _read_jsonl(DATA_PATH / team / "token_costs.jsonl")
    if not data:
        raise HTTPException(404, f"No token cost data for {team}")

    total_cost = data[-1].get("cumulative_cost", 0) if data else 0
    avg_cost = total_cost / len(data) if data else 0

    return {
        "team": team,
        "total_cost": total_cost,
        "total_calls": len(data),
        "avg_cost_per_call": round(avg_cost, 8),
        "costs": data,
    }


@app.get("/api/economics")
def get_economics_overview():
    """Token costs vs trading PnL for all teams."""
    teams = _get_teams()
    overview = []

    for team in teams:
        equity_data = _read_jsonl(DATA_PATH / team / "equity_curve.jsonl")
        token_data = _read_jsonl(DATA_PATH / team / "token_costs.jsonl")

        equity = equity_data[-1].get("equity", 0) if equity_data else 0
        initial = equity_data[0].get("equity", 10000) if equity_data else 10000
        token_cost = token_data[-1].get("cumulative_cost", 0) if token_data else 0

        overview.append({
            "team": team,
            "initial_equity": initial,
            "current_equity": equity,
            "trading_pnl": round(equity - initial + token_cost, 4),
            "token_cost": round(token_cost, 8),
            "net_return": round(equity - initial, 4),
            "token_cost_pct": round(token_cost / initial * 100, 4) if initial > 0 else 0,
        })

    return {"economics": overview}


@app.get("/api/decisions/{team}")
def get_decisions(team: str, limit: int = 50):
    data = _read_jsonl(DATA_PATH / team / "decisions.jsonl")
    return {"team": team, "decisions": data[-limit:], "total": len(data)}


@app.get("/api/results")
def get_arena_results():
    results_path = DATA_PATH / "arena_results.json"
    if not results_path.exists():
        raise HTTPException(404, "Arena not completed yet")
    with open(results_path) as f:
        return json.load(f)


# ── WebSocket for real-time updates ─────────────────────────────

active_connections: List[WebSocket] = []


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Send leaderboard update every 5 seconds
            leaderboard = get_leaderboard()
            await websocket.send_json({
                "type": "leaderboard_update",
                "data": leaderboard,
                "timestamp": datetime.utcnow().isoformat(),
            })
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        active_connections.remove(websocket)


# ── Static files (serve frontend build) ─────────────────────────

frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

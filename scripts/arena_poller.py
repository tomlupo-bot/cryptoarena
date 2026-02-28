#!/usr/bin/env python3
"""
Arena Poller — Watches Convex for pending experiments and launches them.
Run as a daemon or cron job every 30s.

Usage:
    python arena_poller.py          # Single check
    python arena_poller.py --watch  # Continuous polling (30s interval)
"""
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

CONVEX_URL = os.getenv("CONVEX_URL", "https://giant-eel-625.eu-west-1.convex.cloud")
ARENA_DIR = Path(__file__).parent.parent
PID_FILE = ARENA_DIR / "data" / "arena.pid"


def convex_query(name, args=None):
    data = json.dumps({"path": f"arena:{name}", "args": args or {}}).encode()
    req = urllib.request.Request(
        f"{CONVEX_URL}/api/query",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=15)
    result = json.loads(resp.read())
    return result.get("value")


def convex_mutation(name, args):
    data = json.dumps({"path": f"arena:{name}", "args": args}).encode()
    req = urllib.request.Request(
        f"{CONVEX_URL}/api/mutation",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read()).get("value")


def is_arena_running():
    if not PID_FILE.exists():
        return False
    pid = int(PID_FILE.read_text().strip())
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        PID_FILE.unlink(missing_ok=True)
        return False


def build_config(experiment):
    """Convert Convex experiment config to arena config JSON."""
    cfg = experiment.get("config", {})
    teams_config = cfg.get("teams", [])
    dr = experiment.get("dateRange", {})

    models = []
    for t in teams_config:
        models.append({
            "name": t["name"],
            "basemodel": t["model"],
            "signature": t["signature"],
            "enabled": True,
            "openai_base_url": "https://openrouter.ai/api/v1",
            "token_pricing": {
                "input_per_1m": t["tokenPricing"]["inputPer1m"],
                "output_per_1m": t["tokenPricing"]["outputPer1m"],
                "source": "openrouter",
            },
        })

    return {
        "agent_type": "ArenaAgentCrypto",
        "market": "crypto",
        "date_range": {
            "init_date": dr.get("initDate", "2025-10-01"),
            "end_date": dr.get("endDate", "2025-10-03"),
        },
        "arena": {
            "name": experiment.get("name", "Arena"),
            "trading_interval_minutes": cfg.get("tradingIntervalMinutes", 60),
            "token_budget_mode": "deduct_from_capital",
            "max_drawdown_pct": cfg.get("maxDrawdownPct", 50.0),
            "kill_on_bankruptcy": True,
        },
        "models": models,
        "agent_config": {
            "max_steps": 30,
            "max_retries": 3,
            "base_delay": 0.5,
            "initial_cash": cfg.get("initialCash", 10000.0),
            "verbose": True,
        },
        "risk_limits": {
            "max_position_pct": 30.0,
            "max_leverage": 1.0,
            "max_open_positions": 5,
            "stop_loss_pct": 10.0,
        },
        "log_config": {"log_path": "./data/arena_data"},
    }


def start_arena(experiment):
    """Build config and launch arena process."""
    experiment_id = experiment["_id"]

    # Write config
    config = build_config(experiment)
    config_path = ARENA_DIR / "configs" / "generated_config.json"
    config_path.write_text(json.dumps(config, indent=2))

    # Clear old data
    data_dir = ARENA_DIR / "data" / "arena_data"
    if data_dir.exists():
        import shutil
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    # Mark as running
    convex_mutation("updateExperimentStatus", {
        "id": experiment_id,
        "status": "running",
        "startedAt": int(time.time() * 1000),
    })

    # Start MCP services
    print("🔧 Starting MCP services...")
    subprocess.run(["bash", str(ARENA_DIR / "scripts" / "start_services.sh")], timeout=15)

    # Launch arena
    log_file = ARENA_DIR / "data" / "arena_run.log"
    env = os.environ.copy()
    env["PYTHONPATH"] = f"/tmp/pylibs:{ARENA_DIR}:{env.get('PYTHONPATH', '')}"
    env["CRYPTO_HTTP_PORT"] = "8005"

    # Load .env
    env_file = ARENA_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()

    print(f"🏟️ Launching arena: {experiment.get('name')}")
    with open(log_file, "w") as lf:
        proc = subprocess.Popen(
            [sys.executable, str(ARENA_DIR / "main.py"), str(config_path)],
            stdout=lf, stderr=subprocess.STDOUT,
            cwd=str(ARENA_DIR), env=env,
        )

    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(proc.pid))
    print(f"  PID: {proc.pid}")

    # Wait for completion in a separate thread or just return
    # The sync script will be called after completion
    return proc


def check_and_launch():
    """Single poll cycle."""
    if is_arena_running():
        print("🏟️ Arena already running, skipping")
        return

    pending = convex_query("getPendingExperiment")
    if not pending:
        return

    print(f"📋 Found pending experiment: {pending.get('name')}")
    proc = start_arena(pending)

    # Wait for completion
    print("⏳ Waiting for arena to complete...")
    proc.wait()
    print(f"  Exit code: {proc.returncode}")

    # Sync results to Convex
    experiment_id = pending["_id"]
    print("🔄 Syncing results to Convex...")
    sync_env = os.environ.copy()
    sync_env["PYTHONPATH"] = f"/tmp/pylibs:{ARENA_DIR}"
    subprocess.run(
        [sys.executable, str(ARENA_DIR / "scripts" / "sync_to_convex.py"),
         "--name", pending.get("name", "Arena"),
         "--data-dir", str(ARENA_DIR / "data" / "arena_data"),
         "--config", str(ARENA_DIR / "configs" / "generated_config.json")],
        cwd=str(ARENA_DIR), env=sync_env,
    )

    PID_FILE.unlink(missing_ok=True)
    print("✅ Arena run complete")


def watch():
    """Continuous polling."""
    print("👀 Arena poller started (30s interval)")
    while True:
        try:
            check_and_launch()
        except Exception as e:
            print(f"❌ Error: {e}")
        time.sleep(30)


if __name__ == "__main__":
    if "--watch" in sys.argv:
        watch()
    else:
        check_and_launch()

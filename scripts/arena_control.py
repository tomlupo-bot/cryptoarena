#!/usr/bin/env python3
"""
Arena Control — Start/Stop/Status/Deploy for CryptoArena.
Called by Quark via exec. Manages arena runs as background processes.
"""
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ARENA_DIR = Path(__file__).parent.parent
PID_FILE = ARENA_DIR / "data" / "arena.pid"
STATUS_FILE = ARENA_DIR / "data" / "arena_status.json"
DATA_DIR = ARENA_DIR / "data" / "arena_data"
DASHBOARD_DATA = ARENA_DIR / "dashboard" / "frontend" / "public" / "data"


def start(config_path=None):
    """Start arena in background."""
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text().strip())
        try:
            os.kill(pid, 0)
            print(f"❌ Arena already running (PID {pid}). Use 'stop' first.")
            return
        except ProcessError:
            PID_FILE.unlink()

    config = config_path or str(ARENA_DIR / "configs" / "arena_crypto_config.json")
    log_file = ARENA_DIR / "data" / "arena_run.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = f"/tmp/pylibs:{ARENA_DIR}:{env.get('PYTHONPATH', '')}"
    env["CRYPTO_HTTP_PORT"] = "8005"

    with open(log_file, "w") as lf:
        proc = subprocess.Popen(
            [sys.executable, str(ARENA_DIR / "main.py"), config],
            stdout=lf, stderr=subprocess.STDOUT,
            cwd=str(ARENA_DIR), env=env
        )

    PID_FILE.write_text(str(proc.pid))
    STATUS_FILE.write_text(json.dumps({
        "status": "running",
        "pid": proc.pid,
        "config": config,
        "started_at": datetime.utcnow().isoformat(),
    }, indent=2))

    print(f"🏟️ Arena started (PID {proc.pid})")
    print(f"📄 Log: {log_file}")


def stop():
    """Stop running arena."""
    if not PID_FILE.exists():
        print("ℹ️ No arena running.")
        return

    pid = int(PID_FILE.read_text().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        print(f"🛑 Arena stopped (PID {pid})")
    except ProcessLookupError:
        print(f"ℹ️ Process {pid} already dead.")

    PID_FILE.unlink(missing_ok=True)
    if STATUS_FILE.exists():
        status = json.loads(STATUS_FILE.read_text())
        status["status"] = "stopped"
        status["stopped_at"] = datetime.utcnow().isoformat()
        STATUS_FILE.write_text(json.dumps(status, indent=2))


def status():
    """Check arena status + current standings."""
    # Process status
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text().strip())
        try:
            os.kill(pid, 0)
            print(f"🏟️ Arena RUNNING (PID {pid})")
        except ProcessLookupError:
            print("⚠️ Arena process died")
            PID_FILE.unlink()
    else:
        print("💤 Arena not running")

    if STATUS_FILE.exists():
        s = json.loads(STATUS_FILE.read_text())
        print(f"   Config: {s.get('config', '?')}")
        print(f"   Started: {s.get('started_at', '?')}")

    # Results
    results_file = DATA_DIR / "arena_results.json"
    if results_file.exists():
        results = json.loads(results_file.read_text())
        print(f"\n🏆 Leaderboard ({len(results)} teams):")
        for r in sorted(results, key=lambda x: x.get("current_equity", 0), reverse=True):
            status_icon = "💀" if r.get("status") != "alive" else "✅"
            print(f"   {status_icon} {r['team']:16} | ${r.get('current_equity', 0):>10.2f} | "
                  f"{r.get('total_return_pct', 0):>+7.2f}% | "
                  f"tokens: ${r.get('cumulative_token_cost', 0):.4f}")
    else:
        # Check team directories for partial data
        if DATA_DIR.exists():
            teams = [d.name for d in DATA_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")]
            if teams:
                print(f"\n📊 Teams found: {', '.join(teams)}")

    # Last lines of log
    log_file = ARENA_DIR / "data" / "arena_run.log"
    if log_file.exists():
        lines = log_file.read_text().strip().split("\n")
        print(f"\n📄 Last 5 log lines:")
        for line in lines[-5:]:
            print(f"   {line}")


def deploy():
    """Push results to GitHub → Vercel auto-deploys."""
    # Copy arena data to dashboard public dir for static serving
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)

    # Aggregate all data into a single JSON for the frontend
    dashboard_payload = {"teams": [], "generated_at": datetime.utcnow().isoformat()}

    if DATA_DIR.exists():
        for team_dir in sorted(DATA_DIR.iterdir()):
            if not team_dir.is_dir() or team_dir.name.startswith("."):
                continue
            team_data = {"name": team_dir.name, "equity_curve": [], "positions": [], "token_costs": []}

            for fname, key in [("equity_curve.jsonl", "equity_curve"),
                               ("position/position.jsonl", "positions"),
                               ("token_costs.jsonl", "token_costs")]:
                fpath = team_dir / fname
                if fpath.exists():
                    with open(fpath) as f:
                        team_data[key] = [json.loads(l) for l in f if l.strip()]

            dashboard_payload["teams"].append(team_data)

    # Write results
    results_file = DATA_DIR / "arena_results.json"
    if results_file.exists():
        dashboard_payload["results"] = json.loads(results_file.read_text())

    out_file = DASHBOARD_DATA / "arena.json"
    out_file.write_text(json.dumps(dashboard_payload, indent=2))
    print(f"✅ Dashboard data written to {out_file}")

    # Git commit + push
    os.chdir(ARENA_DIR)
    subprocess.run(["git", "add", "-A"], check=True)
    result = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if result.returncode == 0:
        print("ℹ️ No changes to deploy.")
        return

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    subprocess.run(["git", "commit", "-m", f"arena results update {ts}"], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)
    print("🚀 Pushed to GitHub → Vercel will auto-deploy")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: arena_control.py [start|stop|status|deploy] [config_path]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "start":
        start(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "stop":
        stop()
    elif cmd == "status":
        status()
    elif cmd == "deploy":
        deploy()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

"""
watch.py — Claude uses this to check job status without timing out.
Reads the log tail and status file. Called by Claude via Desktop Commander.
"""

import sys, os, json

LOG_DIR  = "logs"
STATUS_F = "logs/status.json"
TAIL     = int(sys.argv[1]) if len(sys.argv) > 1 else 50

# Status
if os.path.exists(STATUS_F):
    with open(STATUS_F) as f:
        s = json.load(f)
    running = "RUNNING" if s["running"] else f"DONE (exit {s['exit_code']})"
    print(f"[{running}] {s['job']}  started={s['started']}  finished={s.get('finished','...')}")
    log_path = s["log"]
else:
    logs = sorted([f for f in os.listdir(LOG_DIR) if f.endswith(".log")]) if os.path.exists(LOG_DIR) else []
    if not logs:
        print("No jobs found."); sys.exit(0)
    log_path = os.path.join(LOG_DIR, logs[-1])
    print(f"[No status] Reading latest log: {log_path}")

# Tail the log
if os.path.exists(log_path):
    with open(log_path) as f:
        lines = f.readlines()
    print(f"\n--- Last {TAIL} lines of {os.path.basename(log_path)} ---")
    print("".join(lines[-TAIL:]))
    print(f"--- Total lines: {len(lines)} ---")
else:
    print(f"Log not found: {log_path}")

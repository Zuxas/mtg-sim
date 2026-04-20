"""
monitor.py — Run any sim job and write live output to a log file.
Claude watches the log and picks up when the job finishes.

Usage:
    python monitor.py <script> [args...]

Examples:
    python monitor.py generate_matchup_data.py --n 1000
    python monitor.py ml/rl_trainer.py --iterations 5 --games-per-iter 5000
    python monitor.py event_simulator.py --rounds 9 --players 300
"""

import sys, os, subprocess, time, json
from datetime import datetime

LOG_DIR   = "logs"
STATUS_F  = "logs/status.json"
os.makedirs(LOG_DIR, exist_ok=True)

def run(cmd_args):
    job_name  = os.path.basename(cmd_args[0]).replace(".py","")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path  = f"{LOG_DIR}/{job_name}_{timestamp}.log"

    status = {
        "job":       job_name,
        "args":      cmd_args,
        "started":   timestamp,
        "finished":  None,
        "exit_code": None,
        "log":       log_path,
        "running":   True,
    }
    with open(STATUS_F, "w") as f:
        json.dump(status, f, indent=2)

    print(f"[monitor] Starting: python {' '.join(cmd_args)}")
    print(f"[monitor] Log: {log_path}")
    print(f"[monitor] Status: {STATUS_F}")
    print(f"[monitor] Claude can now watch this job.\n")

    with open(log_path, "w", buffering=1) as log:
        log.write(f"# Job: {' '.join(cmd_args)}\n")
        log.write(f"# Started: {datetime.now()}\n\n")
        proc = subprocess.Popen(
            [sys.executable] + cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        for line in proc.stdout:
            sys.stdout.write(line)
            log.write(line)
            log.flush()
        proc.wait()

    status["finished"]  = datetime.now().strftime("%Y%m%d_%H%M%S")
    status["exit_code"] = proc.returncode
    status["running"]   = False
    with open(STATUS_F, "w") as f:
        json.dump(status, f, indent=2)

    print(f"\n[monitor] Done. Exit code: {proc.returncode}")
    print(f"[monitor] Log: {log_path}")
    return proc.returncode

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python monitor.py <script.py> [args...]")
        sys.exit(1)
    sys.exit(run(sys.argv[1:]))

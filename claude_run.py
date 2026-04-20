"""CLAUDE PROCESSES AUTHORIZED - MTG Sim runner wrapper.
All sim scripts should be run through this wrapper so they're identifiable.
Usage: python claude_run.py your_script.py
"""
import sys, os, ctypes

# Set console window title so process is identifiable
if sys.platform == 'win32':
    ctypes.windll.kernel32.SetConsoleTitleW("CLAUDE PROCESSES AUTHORIZED - MTG Sim")

# Set process priority to below-normal so it doesn't hog CPU
if sys.platform == 'win32':
    import subprocess
    pid = os.getpid()
    subprocess.run(['wmic', 'process', 'where', f'processid={pid}', 'CALL', 'setpriority', '16384'], 
                   capture_output=True)

sys.stdout.reconfigure(encoding='utf-8')
print("[CLAUDE PROCESSES AUTHORIZED] Starting...")

if len(sys.argv) > 1:
    script = sys.argv[1]
    sys.argv = sys.argv[1:]  # shift args
    exec(open(script, encoding='utf-8').read())
else:
    print("Usage: python claude_run.py <script.py>")

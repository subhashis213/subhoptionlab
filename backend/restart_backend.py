import os
import signal
import subprocess
import time

cmd = "ps aux | grep uvicorn | grep -v grep | awk '{print $2}'"
output = subprocess.check_output(cmd, shell=True).decode().split('\n')
for pid in output:
    if pid:
        try:
            os.kill(int(pid), signal.SIGTERM)
            print(f"Killed uvicorn PID: {pid}")
        except:
            pass

time.sleep(2)

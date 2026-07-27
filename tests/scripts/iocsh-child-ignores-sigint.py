#!/usr/bin/env python
"""Fake iocsh: the wrapper dies on SIGINT while its child ignores it.

Models the case teardown has to handle. iocsh runs the real IOC as a child; if
SIGINT stops the wrapper but the child ignores it, killing only the wrapper
leaves the child running. Only killing the whole group takes it down.
"""

import subprocess
import sys
import time

child = subprocess.Popen(
    [
        sys.executable,
        "-c",
        "import signal, time; signal.signal(signal.SIGINT, signal.SIG_IGN); "
        "time.sleep(60)",
    ]
)
print(f"GRANDCHILD_PID={child.pid}", flush=True)
print("iocRun: All initialization complete", flush=True, file=sys.stderr)
time.sleep(60)

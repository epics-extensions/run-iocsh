#!/usr/bin/env python
"""Fake iocsh: leaves a child running, then the wrapper exits immediately.

Models a wrapper that dies while the real IOC keeps running. Discarding the IOC
has to take the whole group down, not just check the already-dead wrapper.
"""

import subprocess
import sys

child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
print(f"GRANDCHILD_PID={child.pid}", flush=True)

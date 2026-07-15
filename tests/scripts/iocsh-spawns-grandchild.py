#!/usr/bin/env python
"""Fake iocsh: spawns a grandchild (as real iocsh spawns softIocPVX), then hangs.

The real iocsh is a Python wrapper that runs softIocPVX as a child, so killing
the wrapper alone orphans the IOC. This models that: it prints its grandchild's
PID, then neither it nor the grandchild ever exits on its own.
"""

import subprocess
import sys
import time

child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
print(f"GRANDCHILD_PID={child.pid}", flush=True)
print("iocRun: All initialization complete", flush=True, file=sys.stderr)
time.sleep(60)

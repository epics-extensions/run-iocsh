#!/usr/bin/env python
"""Fake iocsh: loads a snippet, then hangs before readiness and ignores exit.

Models an IOC that deadlocks during asInit -- e.g. asCheckClientIP=1 in an
environment without reliable DNS. It never reaches iocInit, so readiness never
appears, and it never reads stdin, so the exit command has no effect. The only
way to tear it down is to kill it.
"""

import sys
import time

print('epicsEnvSet IOCSH_TOP "/tmp"', flush=True)
print("iocshLoad /tmp/st.cmd", flush=True)
print("DEBUG: PID for iocsh 1 ", flush=True, file=sys.stderr)
time.sleep(60)

#!/usr/bin/env python
"""Fake iocsh: a healthy IOC that reaches iocInit, then exits 0.

Transcribed from real output captured with require 6.0.0 / epics-base 7.0.9.0.
Note which stream carries what: EPICS sends errlog to stderr, so "Starting
iocInit" and the readiness line arrive there, while the shell's own command
echoes go to stdout. An earlier version printed readiness on stdout, where no
real IOC emits it.
"""

import sys

print('epicsEnvSet IOCSH_TOP "/tmp"', flush=True)
print("iocshLoad /tmp/st.cmd", flush=True)

print("DEBUG: PID for iocsh 594402 ", flush=True, file=sys.stderr)
print("DEBUG: Executed from /tmp ", flush=True, file=sys.stderr)
print("Starting iocInit", flush=True, file=sys.stderr)
print("iocRun: All initialization complete", flush=True, file=sys.stderr)
sys.exit(0)

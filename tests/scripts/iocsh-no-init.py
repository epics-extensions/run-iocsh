#!/usr/bin/env python
"""Fake iocsh --no-init: loads the startup script but never runs iocInit.

require's IOC shell has a --no-init flag, which omits the iocInit call from the
temporary startup script it generates. The shell still loads modules and runs
the snippet, but nothing reaches iocInit, so the readiness line never appears
and no amount of waiting will produce it. It then reads the exit command from
stdin and exits 0.

Transcribed from real output captured with require 6.0.0 / epics-base 7.0.9.0
on darwin-aarch64, running ``iocsh --no-init`` over a one-line startup script.
Note ``dlload`` is on stdout, with the shell's other command echoes -- only the
IOC shell's own DEBUG logging goes to stderr here.
"""

import sys

print("INFO: PVXS QSRV2 is loaded, permitted, and ENABLED.", flush=True)
print('epicsEnvSet IOCSH_TOP "/tmp"', flush=True)
print("errlogInit2 2048 2047", flush=True)
print("dlload /path/to/lib/librequire.dylib", flush=True)
print("iocshLoad /tmp/st.cmd", flush=True)
print('epicsEnvSet("FOO", "bar")', flush=True)
print("Starting e3 IOC shell version 6.0.0", flush=True)

print("DEBUG: PID for iocsh 32396 ", flush=True, file=sys.stderr)
print("DEBUG: Executed from /tmp ", flush=True, file=sys.stderr)

sys.stdin.readline()
print("Exiting e3 IOC shell", flush=True)
sys.exit(0)

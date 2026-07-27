#!/usr/bin/env python
"""Fake iocsh: require cannot load a module, so it aborts before iocInit.

Transcribed from real output captured with require 6.0.0 / epics-base 7.0.9.0,
running ``iocsh -r definitelynotamodule``. require reports the failure, aborts
the startup script and exits non-zero, so readiness never appears. An earlier
version of this fake printed the readiness line after the error and exited 0,
contradicting what require actually does.

The shared-library line is emitted by the dynamic linker for the same event, so
it is not an independent signal.
"""

import sys

name = sys.argv[-1] if len(sys.argv) > 1 else "mock"

print('epicsEnvSet IOCSH_TOP "/tmp"', flush=True)
print(f"require {name}", flush=True)
print("Exiting e3 IOC shell", flush=True)

print("DEBUG: PID for iocsh 594445 ", flush=True, file=sys.stderr)
print("DEBUG: Executed from /tmp ", flush=True, file=sys.stderr)
print(f"Error loading module: {name}.", flush=True, file=sys.stderr)
print(
    f"lib{name}.so: cannot open shared object file: No such file or directory",
    flush=True,
    file=sys.stderr,
)
print("Fail to load modules.", flush=True, file=sys.stderr)
print("Aborting startup script.", flush=True, file=sys.stderr)
sys.exit(255)

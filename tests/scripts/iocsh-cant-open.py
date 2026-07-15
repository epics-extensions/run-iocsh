#!/usr/bin/env python
"""Fake iocsh: iocshLoad of a missing snippet, which the IOC survives.

Transcribed from real output captured with require 6.0.0 / epics-base 7.0.9.0,
running a startup script whose only command was an ``iocshLoad`` of a file that
does not exist. The IOC reports it, carries on to iocInit and exits 0. The
return code says nothing went wrong, so the output is the only signal.

The message is emitted by the IOC shell itself and is unprefixed. Modules
prefix their own messages (autosave uses ``__FILE__:__func__``), so an
unprefixed "Can't open" is the shell's.
"""

import sys

filename = sys.argv[-1] if len(sys.argv) > 1 else "unknown"

print('epicsEnvSet IOCSH_TOP "/tmp"', flush=True)
print(f'iocshLoad("{filename}")', flush=True)

print("DEBUG: PID for iocsh 594457 ", flush=True, file=sys.stderr)
print(f"Can't open {filename}: No such file or directory", flush=True, file=sys.stderr)
print("Starting iocInit", flush=True, file=sys.stderr)
print("iocRun: All initialization complete", flush=True, file=sys.stderr)
sys.exit(0)

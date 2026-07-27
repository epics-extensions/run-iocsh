#!/usr/bin/env python
"""Fake iocsh: a malformed database, which the IOC reports and then survives.

Transcribed from real output captured with require 6.0.0 / epics-base 7.0.9.0,
loading a record with an undefined macro. The IOC reaches iocInit and exits 0,
so these lines are the only signal that anything went wrong.

The ERROR prefixes are ANSI-wrapped: since epics-base 7.0.7 these go through
ERL_ERROR, which embeds the escapes in the string literal at compile time.
Before that change the same lines were un-colourised, which is how an earlier
version of this fake silently stopped matching real output.
"""

import sys

print('epicsEnvSet IOCSH_TOP "/tmp"', flush=True)
print('dbLoadRecords("/tmp/bad.db")', flush=True)

print("DEBUG: PID for iocsh 594491 ", flush=True, file=sys.stderr)
print(
    "\033[31;1mERROR\033[0m: Bad character '$' in Record/Alias name"
    ' "foo:#$(PRE,undefined)Heartbeat"',
    flush=True,
    file=sys.stderr,
)
print(
    "\033[31;1mERROR\033[0m:  at or before ')' in file \"/tmp/bad.db\" line 1",
    flush=True,
    file=sys.stderr,
)
print("\033[31;1mERROR\033[0m: syntax error", flush=True, file=sys.stderr)
print(
    "\033[31;1mERROR\033[0m failed to load '/tmp/bad.db'", flush=True, file=sys.stderr
)
print("Starting iocInit", flush=True, file=sys.stderr)
print("iocRun: All initialization complete", flush=True, file=sys.stderr)
sys.exit(0)

#!/usr/bin/env python
"""Fake iocsh: EPICS colourises errlog, so ERROR arrives ANSI-wrapped on stderr.

Transcribed from real output captured with require 6.0.0 / epics-base 7.0.9.0,
running a startup script whose only command was ``dbLoadRecords`` of a file that
does not exist. Note the IOC still reaches iocInit and exits 0 -- the failed
database load is reported *only* through this line.

Since epics-base 7.0.7, ``errlog.h`` defines::

    #define ERL_ERROR ANSI_RED("ERROR")

which expands at compile time to "\\033[31;1m" "ERROR" "\\033[0m", so the escapes
are emitted even when stderr is a pipe. See
https://github.com/epics-base/epics-base/issues/911.
"""

import sys

# stdout carries the shell's own echoes; diagnostics all go to stderr.
print('epicsEnvSet IOCSH_TOP "/tmp"', flush=True)
print('dbLoadRecords("/tmp/nosuch.db")', flush=True)

# require's iocsh logs at DEBUG unconditionally, so these DEBUG lines always
# precede the real diagnostics on stderr.
print("DEBUG: PID for iocsh 594490 ", flush=True, file=sys.stderr)
print("DEBUG: Executed from /tmp ", flush=True, file=sys.stderr)
print(
    'filename="../dbStatic/dbLexRoutines.c" line number=277 dbRead opening file'
    " /tmp/nosuch.db",
    flush=True,
    file=sys.stderr,
)
print(
    "\033[31;1mERROR\033[0m failed to load '/tmp/nosuch.db'",
    flush=True,
    file=sys.stderr,
)
print("Starting iocInit", flush=True, file=sys.stderr)
print("iocRun: All initialization complete", flush=True, file=sys.stderr)
sys.exit(0)

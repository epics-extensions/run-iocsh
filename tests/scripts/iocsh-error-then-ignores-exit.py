#!/usr/bin/env python
"""Fake iocsh: logs a real (ANSI) ERROR, becomes ready, then ignores exit.

Transcribed shape from require 6.0.0 / epics-base 7.0.9.0: a failed dbLoadRecords
is reported through an ANSI-wrapped ERROR on stderr, the IOC still reaches
iocInit, and here it then refuses to exit -- so exit() must time out and kill it.
"""

import sys
import time

print('epicsEnvSet IOCSH_TOP "/tmp"', flush=True)
print(
    "\033[31;1mERROR\033[0m failed to load '/tmp/nosuch.db'",
    flush=True,
    file=sys.stderr,
)
print("Starting iocInit", flush=True, file=sys.stderr)
print("iocRun: All initialization complete", flush=True, file=sys.stderr)
sys.stdout.close()
time.sleep(30)

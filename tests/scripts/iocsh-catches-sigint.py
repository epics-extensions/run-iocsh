#!/usr/bin/env python
"""Fake iocsh: exits cleanly on SIGINT, as EPICS does on Ctrl-C.

Used to show the teardown sends SIGINT first, giving the IOC the chance to shut
down cleanly rather than being killed outright.
"""

import signal
import sys
import time


def _on_sigint(signum, frame):  # noqa: ANN001, ANN202, ARG001
    print("CLEAN_SHUTDOWN_ON_SIGINT", flush=True)
    sys.exit(0)


signal.signal(signal.SIGINT, _on_sigint)
print("iocRun: All initialization complete", flush=True, file=sys.stderr)
time.sleep(60)

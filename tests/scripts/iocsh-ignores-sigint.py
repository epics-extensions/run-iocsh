#!/usr/bin/env python
"""Fake iocsh: ignores SIGINT and hangs, so only SIGKILL can stop it.

Models an IOC that does not respond to the clean-shutdown signal, forcing the
teardown to escalate to SIGKILL.
"""

import signal
import sys
import time

signal.signal(signal.SIGINT, signal.SIG_IGN)
print("iocRun: All initialization complete", flush=True, file=sys.stderr)
time.sleep(60)

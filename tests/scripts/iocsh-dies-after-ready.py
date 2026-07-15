#!/usr/bin/env python
"""Fake iocsh: becomes ready, then exits cleanly (rc 0) after a short delay.

Synthetic rather than transcribed: it models timing, an IOC that reaches
readiness and then dies partway through a settle window, not the exact text of
any real message. A healthy IOC does not exit on its own after iocInit; the
settle check exists to catch one that does.
"""

import sys
import time

print("iocRun: All initialization complete", flush=True, file=sys.stderr)
time.sleep(0.3)
sys.exit(0)

#!/usr/bin/env python
"""Fake iocsh: prints readiness, closes its own stdout, then sleeps forever."""

import os
import time

print("iocRun: All initialization complete", flush=True)
os.close(1)
time.sleep(10)

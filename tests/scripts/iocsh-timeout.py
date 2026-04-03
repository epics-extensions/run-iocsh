#!/usr/bin/env python
"""Fake iocsh: prints the readiness line then sleeps forever (exit timeout test)."""

import time

print("iocRun: All initialization complete", flush=True)
time.sleep(10)

#!/usr/bin/env python
"""Fake iocsh: prints the readiness line then exits 0."""

import sys

print("iocRun: All initialization complete", flush=True)
sys.exit(0)

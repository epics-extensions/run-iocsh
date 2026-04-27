#!/usr/bin/env python
"""Fake iocsh: prints readiness line, reads exit command, then exits non-zero."""

import sys

print("iocRun: All initialization complete", flush=True)
sys.stdin.readline()
sys.exit(1)

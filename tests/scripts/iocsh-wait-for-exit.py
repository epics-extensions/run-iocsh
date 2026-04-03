#!/usr/bin/env python
"""Fake iocsh: prints the readiness line, waits for stdin, then exits 0."""

import sys

print("iocRun: All initialization complete", flush=True)
sys.stdin.readline()

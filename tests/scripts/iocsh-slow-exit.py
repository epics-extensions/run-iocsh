#!/usr/bin/env python
"""Fake iocsh: prints readiness line, reads exit command, then exits after a brief delay."""

import sys
import time

print("iocRun: All initialization complete", flush=True)
sys.stdin.readline()
time.sleep(0.15)

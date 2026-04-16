#!/usr/bin/env python
"""Fake iocsh: emits a CUSTOM_ERROR: line, prints the readiness line, then exits 0."""

import sys

print("CUSTOM_ERROR: something went wrong", flush=True)
print("iocRun: All initialization complete", flush=True)
sys.exit(0)

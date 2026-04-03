#!/usr/bin/env python
"""Fake iocsh: emits 'File does not exist' for a hardcoded filename, then exits 0."""

import sys

print("File fake does not exist", flush=True)
print("iocRun: All initialization complete", flush=True)
sys.exit(0)

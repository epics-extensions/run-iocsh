#!/usr/bin/env python
"""Fake iocsh: emits a 'Can't open' error for the last positional arg, then exits 0."""

import sys

filename = sys.argv[-1] if len(sys.argv) > 1 else "unknown"
print(f"Can't open {filename}: No such file or directory", flush=True)
print("iocRun: All initialization complete", flush=True)
sys.exit(0)

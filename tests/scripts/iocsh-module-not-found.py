#!/usr/bin/env python
"""Fake iocsh: emits a module-not-available message, prints readiness line, exits 0."""

import sys

name = sys.argv[-1] if len(sys.argv) > 1 else "mock"
print(f"Error loading module: {name}.", flush=True, file=sys.stderr)
print("Fail to load modules.", flush=True, file=sys.stderr)
print("iocRun: All initialization complete", flush=True)
sys.exit(0)

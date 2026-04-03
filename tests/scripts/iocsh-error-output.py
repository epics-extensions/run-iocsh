#!/usr/bin/env python
"""Fake iocsh: emits ERROR: lines, prints the readiness line, then exits 0."""

import sys

print("ERROR: Bad character '$' in Record/Alias name", flush=True)
print("ERROR: syntax error", flush=True)
print("ERROR: failed to load 'save_restoreStatus.db'", flush=True)
print("Starting iocInit", flush=True)
print("iocRun: All initialization complete", flush=True)
sys.exit(0)

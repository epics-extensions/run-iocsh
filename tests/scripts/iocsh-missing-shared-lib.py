#!/usr/bin/env python
"""Fake iocsh: emits a missing shared library error, prints readiness line, exits 0."""

import sys

print("liblib: cannot open shared object file: No such file or directory", flush=True)
print("iocRun: All initialization complete", flush=True)
sys.exit(0)

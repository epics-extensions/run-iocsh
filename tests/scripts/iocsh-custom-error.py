#!/usr/bin/env python
"""Fake iocsh: prints a custom error tag line then the readiness line and exits 0."""

import sys

print("CUSTOM_ERROR: something went wrong", flush=True)
print("iocRun: All initialization complete", flush=True)
sys.exit(0)

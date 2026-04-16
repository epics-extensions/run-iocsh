#!/usr/bin/env python
"""Fake iocsh: exits immediately without printing the readiness line."""

import sys

print("Starting IOC...", flush=True)
sys.exit(1)

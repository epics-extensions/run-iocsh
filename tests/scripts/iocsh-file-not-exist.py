#!/usr/bin/env python
"""Fake iocsh: the startup script itself does not exist, so the shell exits.

Transcribed from real output captured with require 6.0.0 / epics-base 7.0.9.0,
running ``iocsh`` against a startup script that does not exist. The IOC never
starts, so readiness never appears.

This message comes from require's Python IOC shell, which logs it at debug level
immediately before exiting non-zero. It is only visible because the shell calls
basicConfig(level=DEBUG) unconditionally, so raising require's default log level
would silently remove it -- a fragile signal to match on.
"""

import sys

filename = sys.argv[-1] if len(sys.argv) > 1 else "/nonexistent/st.cmd"

print("Starting e3 IOC shell version 6.0.0", flush=True)
print("Exiting e3 IOC shell", flush=True)

print("DEBUG: PID for iocsh 594440 ", flush=True, file=sys.stderr)
print(f"DEBUG: File {filename} does not exist. Exiting. ", flush=True, file=sys.stderr)
sys.exit(255)

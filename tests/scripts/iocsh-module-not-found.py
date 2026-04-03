#!/usr/bin/env python
"""Fake iocsh: emits a module-not-available message, prints readiness line, exits 0."""

import sys

module_name = sys.argv[2] if len(sys.argv) > 2 else "mock,fake"
name, _, version = module_name.partition(",")
if version:
    print(f"Module {name} version {version} not available", flush=True, file=sys.stderr)
else:
    print(f"Module {name} not available", flush=True, file=sys.stderr)
print("iocRun: All initialization complete", flush=True)
sys.exit(0)

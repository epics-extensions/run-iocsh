#!/usr/bin/env python
"""Fake iocsh: the dynamic linker cannot open a module's shared library.

The message shape is real, captured with require 6.0.0 / epics-base 7.0.9.0 --
it is glibc's, surfaced through require's dlopen. Isolating it is not: in every
capture it arrived together with "Error loading module", because a module that
will not load produces both. Since the module detector is checked first, that
one wins, and this one is only reachable on its own if a module resolves but its
library then fails to open. That case has not been captured, so this fake is a
real message in a synthetic setting.

This message is Linux-only: dyld reports the same failure differently, so this
detector matches nothing on macOS.
"""

import sys

print('epicsEnvSet IOCSH_TOP "/tmp"', flush=True)

print(
    "libfoo.so: cannot open shared object file: No such file or directory",
    flush=True,
    file=sys.stderr,
)
print("Starting iocInit", flush=True, file=sys.stderr)
print("iocRun: All initialization complete", flush=True, file=sys.stderr)
sys.exit(0)

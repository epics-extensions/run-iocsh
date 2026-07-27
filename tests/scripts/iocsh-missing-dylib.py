#!/usr/bin/env python
"""Fake iocsh: the dynamic linker cannot open a module's library, macOS wording.

The message shape is real, captured with require 6.0.0 / epics-base 7.0.9.0 on
macOS/arm64 (darwin-aarch64) running ``iocsh -r definitelynotamodule``. dyld
reports this nothing like glibc does: there is no "cannot open shared object
file" anywhere, and the library is a .dylib, so the Linux-only detector matched
nothing here.

Isolating it is synthetic, for the same reason as the Linux fake: in every
capture this line arrived together with "Error loading module", and that
detector is checked first.

Truncated: the real line lists every path dyld tried, one per search location.
"""

import sys

print('epicsEnvSet IOCSH_TOP "/tmp"', flush=True)

print(
    "dlopen(libfoo.dylib, 0x000A): tried: 'libfoo.dylib' (no such file), "
    "'/System/Volumes/Preboot/Cryptexes/OSlibfoo.dylib' (no such file), "
    "'/usr/lib/libfoo.dylib' (no such file, not in dyld cache)",
    flush=True,
    file=sys.stderr,
)
print("Starting iocInit", flush=True, file=sys.stderr)
print("iocRun: All initialization complete", flush=True, file=sys.stderr)
sys.exit(0)

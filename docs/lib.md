# Python Library

The `run-iocsh` package provides a Python library for programmatically running
and controlling IOC processes. The main exports are:

- **`IOC`**: context manager for managing an IOC process
- **`run_iocsh()`**: convenience wrapper for simple run-and-check use cases
- **`wait_for()`**: standalone polling utility for readiness checks
- **Exception classes**: typed errors for different failure modes

## Usage patterns

Both patterns use the same `IOC` class. Output is checked automatically when
the context manager exits — any errors in stdout or stderr raise a typed
exception. Access `ioc.stdout` and `ioc.stderr` to inspect the output directly.

### Run-and-check

Start the IOC, wait for `iocInit` to complete, then exit. Useful for
module-loading tests, `dbl` output checks, or startup script validation.

```python
import re
from run_iocsh import IOC

with IOC("st.cmd") as ioc:
    ioc.wait_for_output()
# output checked automatically; inspect stdout for assertions
pvs = re.findall(r"^MY_IOC:(.+)$", ioc.stdout, re.MULTILINE)
assert "SomeRecord" in pvs
```

`run_iocsh()` is a one-liner for this pattern:

```python
from run_iocsh import run_iocsh

ioc = run_iocsh("st.cmd")
# ioc.stdout / ioc.stderr available for inspection
```

### Live IOC

Keep the IOC running while tests interact with it over CA or PVA:

```python
import pytest
from p4p.client.thread import Context
from run_iocsh import IOC, wait_for


@pytest.fixture(scope="session")
def ioc():
    with IOC("st.cmd") as proc:
        proc.wait_for_output()                                    # wait for iocInit
        wait_for(lambda: ctxt.get("MY:IOC:Ready") is not None)    # wait for PVA (optional)
        yield proc


@pytest.fixture(scope="session")
def ctxt():
    with Context("pva") as ctx:
        yield ctx


def test_pv_value(ioc, ctxt):
    assert ctxt.get("MY:IOC:SomePV") == 42
```

## Readiness

EPICS IOCs typically go through up to three phases before they are fully ready:

### Phase 1 — iocInit complete

All IOCs print this line when `iocInit` finishes:

```python
ioc.wait_for_output()  # default: "iocRun: All initialization complete"
```

### Phase 2 — protocol or module layer ready (optional)

Some modules initialise asynchronously after iocInit. Use `wait_for` to poll
until a PV becomes available or another condition is met:

```python
wait_for(lambda: ctxt.get("MY:IOC:Ready") is not None, timeout=10)
```

### Phase 3 — background poll settled (optional)

Drivers that poll a device in the background may need time after phase 2 before
their first values arrive. This is driver-specific; use an explicit
`time.sleep()` when necessary.

## `wait_for`

Poll a predicate until it returns `True`. Exceptions raised by the predicate
are swallowed and treated as `False`, which is useful when the condition depends
on a resource that may not yet be available:

```python
from run_iocsh import wait_for

# context.get() raises until the IOC is ready - wait_for retries silently
wait_for(lambda: ctxt.get("MY:PV") is not None, timeout=10)

# Works for any predicate
wait_for(lambda: save_file.exists(), timeout=10)
```

Raises `TimeoutError` on expiry.

## `wait_for_output`

Block until a pattern appears in stdout or stderr:

```python
# Default: "iocRun: All initialization complete" - works for all soft IOC variants
ioc.wait_for_output()

# Custom pattern for a specific module readiness signal
ioc.wait_for_output("autosave: All ok", timeout=10)

# Returns immediately if pattern already in accumulated output
ioc.wait_for_output()  # second call is instant
```

If the IOC exits before the pattern appears, raises `IocshStartupError` with
the last 500 characters of stdout and stderr. If the timeout expires while the
IOC is still running, raises `IocshTimeoutError`.

## Non-default executables

Pass `executable=` to use any IOC binary. Extra arguments for the executable
go into positional arguments. `softIocPVA` is available with EPICS base 7+
and can be used without e3:

```python
# Standard EPICS base soft IOC
IOC("-D", "/path/to/softIoc.dbd", "st.cmd", executable="softIocPVA")

# Compiled IOC application
IOC(executable="/path/to/my/ioc")
```

On the CLI:

```bash
run-iocsh --executable softIocPVA -D /path/to/softIoc.dbd st.cmd
```

## `check_output` and `fail_on`

`check_output()` is called automatically when the `IOC` context manager exits
cleanly. It applies the following checks against the accumulated output:

| Check | Exception |
| --- | --- |
| `Module X not available` | `IocshModuleNotFoundError` |
| `Can't open ...` / `File ... does not exist` | `IocshFileNotFoundError` |
| `libX: cannot open shared object file` | `IocshMissingSharedLibraryError` |
| `^ERROR` (DB loading errors, macro errors, syntax errors) | `IocshPatternMatchError` |
| Non-zero exit code | `IocshProcessError` |

The `^ERROR` pattern is stored in `RE_BUILTIN_FAIL_ON` and catches errors that
EPICS prints before `iocInit` but after which the IOC still exits 0 — a common
source of false-pass failures in CI.

### Adding patterns

Pass `fail_on` to `IOC.__init__` to check for additional patterns on top of the
built-in checks:

```python
with IOC("st.cmd", fail_on=["^WARNING:", r"FATAL\b"]) as ioc:
    ioc.wait_for_output()
```

Or call `check_output()` explicitly inside the `with` block when needed:

```python
with IOC("st.cmd") as ioc:
    ioc.wait_for_output()
    ioc.check_output(fail_on=["^WARNING:"])
```

### CLI

```bash
run-iocsh --fail-on "^WARNING" st.cmd
```

`--fail-on` patterns are added on top of the built-in `^ERROR` check.

## caplog integration

IOC output is logged at `DEBUG` level, line by line, as it arrives. Use
`caplog.at_level(logging.DEBUG, logger="run_iocsh")` to capture it in pytest.
This is especially useful for asserting on startup output without needing to
wait for the IOC to exit first:

```python
import logging

def test_ioc_loads_correctly(caplog):
    with caplog.at_level(logging.DEBUG, logger="run_iocsh"):
        with IOC("st.cmd") as ioc:
            ioc.wait_for_output()
            assert "require_registerRecordDeviceDriver" in caplog.text
```

On failure, pytest displays the captured log, giving full IOC output context
without any extra teardown code.

## Exception reference

For the full exception hierarchy see the
[API reference](autoapi/run_iocsh/index.html#exceptions).

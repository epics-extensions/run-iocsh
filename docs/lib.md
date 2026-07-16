# Python Library

The `run-iocsh` package provides a Python library for programmatically running
and controlling IOC processes. The main exports are:

- **`IOC`**: context manager for managing an IOC process
- **`run_iocsh()`**: convenience wrapper for simple run-and-check use cases
- **`wait_for()`**: standalone polling utility for readiness checks
- **`DEFAULT_DETECTORS`**: the replaceable set of error detectors
- **Exception classes**: typed errors for different failure modes

## Usage patterns

Both patterns use the same `IOC` class. Output is checked automatically when
the context manager exits cleanly — any errors raise a typed exception.

Three properties expose the captured output. `ioc.output` is both streams in the
order the lines arrived, and is what patterns are matched against; `ioc.stdout`
and `ioc.stderr` are each stream on its own. Prefer `output` unless you
specifically care which stream a line came from: EPICS sends errlog to stderr,
so nearly everything interesting — including `iocRun: All initialization
complete` — arrives there, while stdout carries the shell's own echoes.

ANSI escapes are stripped as output is captured. EPICS colourises errlog even
when its output is a pipe, which would otherwise defeat any pattern anchored at
the start of a line.

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
# ioc.output / ioc.stdout / ioc.stderr available for inspection
```

`run_iocsh()` names each phase of the run separately:

| Argument | Meaning |
| --- | --- |
| `pattern` | what counts as ready |
| `init_timeout` | how long to wait for it |
| `wait_for_init` | whether to wait at all — `False` for an IOC that never reaches `iocInit` |
| `settle` | how long to keep the IOC running once ready |
| `exit_timeout` | how long the IOC gets to shut down after being told to exit |

Every timeout follows the same rule: `None` waits forever, a number is seconds,
`0` checks once without blocking.

`settle` also makes the run require the IOC to stay up: with a non-zero `settle`,
an IOC that becomes ready and then exits on its own before the window is up
raises `IocshExitedError`, even on a clean exit code. It defaults to `0`, where
no survival is required.

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
their first values arrive. Nothing observable marks it: the fetch leaves no
trace in the IOC's output, and waiting for the value itself would only test that
the test passes. An explicit `time.sleep()` is the honest option here.

`run_iocsh()` exposes the same idea as `settle`, which keeps the IOC running for
a fixed time before exiting. It defaults to 0.

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

Raises `IocshTimeoutError` on expiry, which is also a builtin `TimeoutError`,
so either will catch it.

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

If the IOC exits before the pattern appears, the
[detectors](#replacing-the-detectors) run first, so a recognised cause is
reported as itself — a missing module raises
`IocshModuleNotFoundError` rather than a generic startup failure. If nothing is
recognised, `IocshStartupError` is raised with the last 500 characters of the
output. If the timeout expires while the IOC is still running, raises
`IocshTimeoutError`.

`timeout=None` waits forever and `timeout=0` checks the buffered output once
without blocking, as everywhere else in this library.

## Tearing down an IOC that will not exit

`exit()` sends the exit command and waits for the IOC to exit, killing it and
raising `IocshTimeoutError` if it does not within `exit_timeout`. That is the
right default, but an IOC that deadlocks during `asInit` never reaches a shell
that reads stdin, so `exit()` can only time out. For that case, `kill()` stops
the process outright without raising:

```python
ioc = IOC("st.cmd")
ioc.start()
ioc.wait_for_output("some snippet loaded", timeout=10)
ioc.kill()
ioc.check_output()  # captured output is intact; the kill signal is not counted
```

A killed IOC's return code is the signal it was sent, so `check_output()` does
not report it as a process failure — the `fail_on` and detector checks still
apply.

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
cleanly. It applies `fail_on`, then `DEFAULT_DETECTORS`, then the return code:

| Check | Exception |
| --- | --- |
| `^ERROR` (DB load failures, macro errors, syntax errors) | `IocshPatternMatchError` |
| `Error loading module: X` | `IocshModuleNotFoundError` |
| `Can't open ...` / `File ... does not exist` | `IocshFileNotFoundError` |
| a library the dynamic linker could not open | `IocshMissingSharedLibraryError` |
| Non-zero exit code | `IocshProcessError` |

The `^ERROR` pattern is stored in `RE_BUILTIN_FAIL_ON`. It matters because an
IOC can fail and still exit 0 — a database that will not load is reported only
in the output, so the return code alone would call that run a success.

:::{warning}
`check_output()` runs only when the context manager exits **cleanly**. If you
drive the IOC with explicit `start()` and `exit()` calls, nothing checks the
output and `fail_on` never applies — the IOC can log errors all run and the test
will pass. Call `check_output()` yourself after `exit()` in that case.
:::

### Replacing the detectors

`DEFAULT_DETECTORS` matches messages emitted by e3/require, not by this library.
Upstream has changed all of it before without warning, so treat it as a default
rather than a rule. The shared-library detector matches both glibc's and dyld's
wording, since the two platforms phrase it differently.

Replace the set for an IOC that is not require-based, or on a platform whose
messages differ:

```python
from run_iocsh import DEFAULT_DETECTORS, IOC


def detect_my_failure(output: str) -> None:
    if "MY_DRIVER: init failed" in output:
        raise RuntimeError("driver failed to initialise")


# Extend
IOC("st.cmd", detectors=(*DEFAULT_DETECTORS, detect_my_failure))

# Or replace entirely, e.g. for an IOC that is not require-based
IOC("st.cmd", detectors=(detect_my_failure,))
```

A detector takes the captured output and raises if it recognises a failure.
Returning without raising means it found nothing.

### Adding patterns

Pass `fail_on` to `IOC.__init__`. It **replaces** `DEFAULT_FAIL_ON` rather than
extending it, so include the default explicitly to keep the `^ERROR` check —
dropping it re-opens the false negative it exists to catch:

```python
from run_iocsh import DEFAULT_FAIL_ON, IOC

with IOC("st.cmd", fail_on=(*DEFAULT_FAIL_ON, "^WARNING:", r"FATAL\b")) as ioc:
    ioc.wait_for_output()
```

`check_output()` runs only after the process has exited, so to check explicitly,
drive the lifecycle by hand rather than calling it inside the `with` block. It
defaults to the `fail_on` and `detectors` the IOC was constructed with:

```python
ioc = IOC("st.cmd", fail_on=(*DEFAULT_FAIL_ON, "^WARNING:"))
ioc.start()
ioc.wait_for_output()
ioc.exit()
ioc.check_output()  # applies the instance's fail_on
```

### CLI

```bash
run-iocsh --fail-on "^WARNING" st.cmd
```

Unlike the library, the CLI **adds** `--fail-on` patterns on top of the built-in
`^ERROR` check; pass `--no-default-fail-on` to drop it. See the
[CLI reference](cli.md) for the full set of flags.

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

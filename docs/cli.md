# Command Line Interface

The `run-iocsh` command-line tool runs an IOC, waits for `iocInit` to complete,
sleeps for a configurable delay, then sends an exit command and checks the output.

## Basic usage

```bash
run-iocsh st.cmd
```

## Command line options

```text
$ run-iocsh -h
usage: run-iocsh [-h] [--delay DELAY] [--timeout TIMEOUT]
                 [--executable EXECUTABLE] [--fail-on PATTERN]

Run iocsh and send the exit command after <delay> seconds

options:
  -h, --help            show this help message and exit
  --delay DELAY         time (in seconds) to wait after iocInit before
                        sending the exit command [default: 0]
  --timeout TIMEOUT     time (in seconds) to wait when sending the exit
                        command [default: 5]
  --executable EXEC     iocsh executable to use [default: iocsh]
  --fail-on PATTERN     raise if regex PATTERN matches stdout/stderr (may be
                        given multiple times)
```

## Examples

### Default settings

Runs `iocsh`, waits for `iocInit` to complete, then exits immediately:

```bash
run-iocsh st.cmd
```

### Custom delay and timeout

```bash
run-iocsh --delay 10 --timeout 3 st.cmd
```

`--delay` is the settle time **after** `iocInit` completes, not a total wait.
The tool always waits for `iocRun: All initialization complete` before sleeping.

### Non-default executables

Pass `--executable` to use any IOC binary. Extra arguments are forwarded as-is:

```bash
# Standard EPICS base soft IOC (EPICS 7+)
run-iocsh --executable softIocPVA -D /path/to/softIoc.dbd st.cmd

# Compiled IOC application
run-iocsh --executable /path/to/my/ioc
```

### Passing arguments to iocsh

All unrecognised arguments are passed through to the underlying executable:

```bash
run-iocsh -r iocstats st.cmd
run-iocsh -r iocstats -c "dbLoadRecords('my.db')" st.cmd
```

### Fail on output patterns

```bash
run-iocsh --fail-on "^ERROR:" --fail-on "^Warning:.*critical" st.cmd
```

Each `--fail-on` pattern is **added to** the built-in checks — `^ERROR:` is
always active on the CLI regardless. To opt out of built-in checks use the
Python API directly (see `BUILTIN_FAIL_ON` in the library documentation).

## Error handling

The tool exits with status 1 if any `RunIocshError` or `FileNotFoundError`
occurs. All errors are logged with full context.

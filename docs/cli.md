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
usage: run-iocsh [-h] [--delay DELAY] [--exit-timeout EXIT_TIMEOUT]
                 [--init-timeout INIT_TIMEOUT] [--pattern PATTERN]
                 [--executable EXECUTABLE] [--fail-on PATTERN]
                 [--no-default-fail-on]

Run iocsh and send the exit command after <delay> seconds

options:
  -h, --help            show this help message and exit
  --delay DELAY         time (in seconds) to wait after iocInit before sending
                        exit (default: 5.0)
  --exit-timeout EXIT_TIMEOUT
                        time (in seconds) to wait for the IOC to exit after
                        sending exit (default: 10.0)
  --init-timeout INIT_TIMEOUT
                        time (in seconds) to wait for the IOC to become ready
                        (default: 5.0)
  --pattern PATTERN     regex to wait for before considering the IOC ready
                        (default: iocRun: All initialization complete)
  --executable EXECUTABLE
                        IOC executable to run (default: iocsh)
  --fail-on PATTERN     raise if regex PATTERN matches output; ^ERROR is
                        always checked (may be given multiple times) (default:
                        [])
  --no-default-fail-on  disable the always-active ^ERROR check (default:
                        False)
```

## Examples

### Default settings

Runs `iocsh`, waits for `iocInit` to complete, then exits immediately:

```bash
run-iocsh st.cmd
```

### Custom delay and exit timeout

```bash
run-iocsh --delay 10 --exit-timeout 3 st.cmd
```

`--delay` is the settle time **after** `iocInit` completes, not a total wait.

### Waiting for something other than iocInit

`--init-timeout` bounds the wait for readiness, and `--pattern` chooses what
counts as ready. Both are separate from `--exit-timeout`, which only bounds how
long the IOC gets to shut down after being told to exit:

```bash
run-iocsh --pattern "autosave: All ok" --init-timeout 30 st.cmd
```

Without `--pattern`, the tool waits for `iocRun: All initialization complete`
before sleeping.

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
run-iocsh --fail-on "^Warning:.*critical" st.cmd
```

The built-in `^ERROR` pattern is always active. Each `--fail-on` pattern is
**added on top** of it. To disable the built-in check entirely:

```bash
run-iocsh --no-default-fail-on st.cmd
run-iocsh --no-default-fail-on --fail-on "^MY_ERROR:" st.cmd
```

## Error handling

The tool exits with status 1 if any `RunIocshError` or `FileNotFoundError`
occurs. All errors are logged with full context.

In addition to the configurable `^ERROR` pattern check, the following
conditions are always detected and raised as errors:

- Failed module load (`Error loading module: ...`) — `IocshModuleNotFoundError`
- File not found (`Can't open ...` / `File ... does not exist`) — `IocshFileNotFoundError`
- Missing shared library (`lib...: cannot open shared object file`) — `IocshMissingSharedLibraryError`
- Non-zero exit code — `IocshProcessError`

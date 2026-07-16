# Command Line Interface

The `run-iocsh` command-line tool runs an IOC, waits for `iocInit` to complete,
keeps it running for a configurable settle time, then sends an exit command and
checks the output.

## Basic usage

```bash
run-iocsh st.cmd
```

## Command line options

```text
$ run-iocsh -h
usage: run-iocsh [-h] [--settle SETTLE] [--exit-timeout EXIT_TIMEOUT]
                 [--init-timeout INIT_TIMEOUT] [--pattern PATTERN]
                 [--no-wait-for-init] [--executable EXECUTABLE]
                 [--fail-on PATTERN] [--no-default-fail-on]

Run iocsh and send the exit command after <settle> seconds

options:
  -h, --help            show this help message and exit
  --settle SETTLE       time (in seconds) to keep the IOC running after it is
                        ready (default: 5.0)
  --exit-timeout EXIT_TIMEOUT
                        time (in seconds) to wait for the IOC to exit after
                        sending exit (default: 10.0)
  --init-timeout INIT_TIMEOUT
                        time (in seconds) to wait for the IOC to become ready
                        (default: 5.0)
  --pattern PATTERN     regex to wait for before considering the IOC ready
                        (default: iocRun: All initialization complete)
  --no-wait-for-init    do not wait for the IOC to become ready (e.g. with
                        iocsh --no-init) (default: False)
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

Runs `iocsh`, waits for `iocInit` to complete, keeps the IOC running for the
default five-second settle, then sends the exit command. If the IOC exits on its
own before the settle is up, the run fails.

```bash
run-iocsh st.cmd
```

### Custom settle and exit timeout

```bash
run-iocsh --settle 10 --exit-timeout 3 st.cmd
```

`--settle` is time **after** `iocInit` completes, not a total wait. It is what
makes the run check the IOC stays up: an IOC that starts cleanly and then dies
two seconds later still fails.

### Waiting for something other than iocInit

`--init-timeout` bounds the wait for readiness, and `--pattern` chooses what
counts as ready. Both are separate from `--exit-timeout`, which only bounds how
long the IOC gets to shut down after being told to exit:

```bash
run-iocsh --pattern "autosave: All ok" --init-timeout 30 st.cmd
```

Without `--pattern`, the tool waits for `iocRun: All initialization complete`
before sleeping.

### IOCs that never reach iocInit

Some IOCs are not meant to get that far — `iocsh --no-init` omits `iocInit`
entirely. Waiting for readiness there can only ever time out, so skip the wait.
Unrecognised arguments such as `--no-init` are passed straight through to the IOC
executable:

```bash
run-iocsh --no-wait-for-init --settle 2 --no-init st.cmd
```

A startup script that deadlocks during `asInit` — never reaching `iocInit` and
never reading stdin — cannot be shut down with the exit command; the library's
`IOC.kill()` is the way to tear one down and still inspect what it loaded.

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

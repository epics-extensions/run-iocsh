# Command Line Interface

The `run-iocsh` command-line tool provides a simple way to run an IOC (Input/Output Controller)
and automatically send an exit command after a specified delay. This is particularly useful for testing EPICS applications.

## Basic usage

The tool runs `iocsh` with the provided arguments, waits for a specified delay, then sends an "exit" command to terminate
the IOC cleanly.

## Command line options

Let's see the available command-line options:

```bash
$ run-iocsh -h
usage: run-iocsh [-h] [--delay DELAY] [--timeout TIMEOUT]

Run iocsh and send the exit command after <delay> seconds

options:
  -h, --help         show this help message and exit
  --delay DELAY      time (in seconds) to wait before sending the exit command [default: 5]
  --timeout TIMEOUT  time (in seconds) to wait when sending the exit command [default: 5]
```

## Examples

### Running with default settings

The simplest usage runs `iocsh` with default settings (5-second delay, 5-second timeout):

```bash
$ run-iocsh st.cmd
```

### Customizing delay and timeout

You can customize the delay before sending the exit command and the timeout for the exit operation:

```bash
$ run-iocsh --delay 10 --timeout 3 st.cmd
```

All arguments after the options are passed directly to `iocsh`:

```bash
$ run-iocsh -r iocstats
```

```bash
$ run-iocsh -r iocstats -c dbLoadRecords("my.db") -c dbl
```

## Error handling

The command-line tool exits with a non-zero status code if any errors occur. All errors are logged with detailed
information to help diagnose issues.

Common error scenarios include missing files, unavailable EPICS modules, process errors, timeouts, and missing shared libraries.

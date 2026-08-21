# run-iocsh

Python library and CLI for automated testing of EPICS IOC startup scripts.
Starts an IOC, waits for `iocInit` to complete, and raises typed exceptions
if errors are detected in the output.

It was written for e3, which is still its primary target, and two defaults
carry that with them: the executable is `iocsh`, and `DEFAULT_DETECTORS`
matches messages emitted by require. Both are replaceable and any IOC
executable works, but a site that does not use require should replace the
detectors before trusting a passing run - see
[non-default executables](lib.md#non-default-executables) and
[replacing the detectors](lib.md#replacing-the-detectors).

## Installation

Requires Python 3.11 or later.

```bash
pip install run-iocsh
```

It is also packaged for
[conda-forge](https://anaconda.org/conda-forge/run-iocsh):

```bash
conda install -c conda-forge run-iocsh
```

Note that neither installs an IOC. That comes from elsewhere — e3's `iocsh`,
EPICS base's `softIocPVA`, or a compiled IOC application — and is found on
`PATH` or given as a full path.

```{toctree}
:maxdepth: 2
:caption: Documentation

cli
lib
```

```{toctree}
:maxdepth: 2
:caption: API Reference

autoapi/run_iocsh/index
```

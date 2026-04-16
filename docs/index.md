# run-iocsh

Python library and CLI for automated testing of EPICS IOC startup scripts.
Starts an IOC, waits for `iocInit` to complete, and raises typed exceptions
if errors are detected in the output. Works with any IOC executable, not just
e3/iocsh.

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

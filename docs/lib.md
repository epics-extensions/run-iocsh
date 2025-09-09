# Python Library

The `run-iocsh` package provides a Python library for programmatically running and controlling IOC processes.
This is useful for, for example, automated testing.

The main components of the library are:

- **`IOC`**: A class for managing IOC processes
- **`run_iocsh()`**: A convenience function for simple use cases
- **Exception classes**: For handling different error conditions (see API reference for details)

## Using the `IOC` class

The most convenient way to use the `IOC` class is as a context manager:

```python
with IOC("st.cmd") as ioc:
    # Interact with IOC
    pass

ioc.check_output()
# Parse `ioc.outs` and `ioc.errs` to assert messages
```

For more control, you can manually start and stop the IOC:

```python
ioc = IOC("st.cmd", timeout=10.0)

try:
    ioc.start()
    print(f"IOC started: {ioc.is_running()}")

    ioc.exit()
    print(f"IOC stopped: {ioc.is_running()}")

    ioc.check_output()

except Exception as e:
    print(f"Error: {e}")
    if ioc.is_running():
        ioc.exit()
```

This can be handy to, for example, start a simulated device together with the IOC.

## Using the `run_iocsh` function

```python
DELAY = 5  # seconds

try:
    run_iocsh(DELAY, "st.cmd")
    print("IOC completed successfully")
except RunIocshError as e:
    print(f"IOC failed: {e}")
```

You can also provide a custom timeout:

```python
run_iocsh(DELAY, "st.cmd", timeout=10)
```

## Error handling

The library provides specific exception types for different error conditions. Here's a practical example of error handling:

```python
try:
    with IOC("st.cmd") as ioc:
        # Your code here
        pass
except RunIocshError as e:
    print(f"IOC error: {e}")
except FileNotFoundError as e:
    print(f"File not found: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Exception reference

For detailed information about all available exception types, their specific use cases, and inheritance hierarchy,
see the [API reference](autoapi/run_iocsh/index.html#exceptions).

## Examples

Here are examples based on common usage patterns:

```python
import os
from pathlib import Path
from run_iocsh import IOC

test_dir = Path(__file__).absolute().parent
cmd_file = test_dir / "cmds" / "test.cmd"

ioc = IOC(cmd_file.as_posix())

try:
    with ioc:
        import time
        time.sleep(10)  # Wait for IOC to initialize

        print(f"IOC running: {ioc.is_running()}")
        # Add your test code here

except Exception as e:
    print(f"Test failed: {e}")
    ioc.check_output()
```

```python
import pytest
from pathlib import Path
from run_iocsh import IOC

# Session based scope can be handy to re-use the same IOC instead of starting one per test function
@pytest.fixture(scope="session")
def ioc():
    """Session-scoped IOC fixture for all tests."""
    test_script = Path(__file__).absolute().parent / "test.cmd"
    with IOC(test_script) as instance:
        yield instance
    ioc.check_output()  # If you want to access stdout and stderr, else this can be left out

@pytest.mark.usefixtures("ioc")
def test_my_ioc_functionality():
    """Test that uses the session-scoped IOC."""
    # Add your test code here
```

```python
import time
from run_iocsh import IOC
from p4p.client.thread import Context

def test_pv_read_write():
    with IOC("test.cmd"), Context("pva") as ctxt:
        time.sleep(10)  # Wait for IOC to initialize

        pv_write = "PREFIX:TestString-SP"
        pv_read = "PREFIX:TestString-RB"

        test_value = "Some value"
        ctxt.put(pv_write, test_value)

        result = ctxt.get(pv_read)
        assert result == test_value
```

```python
import asyncio
from run_iocsh import IOC
from p4p.client.asyncio import Context

# Instead of having to sleep for a set time, we can await the writes and the reads
async def test_pv_read_write_async():
    with IOC("test.cmd") as ioc:
        async with Context("pva") as ctxt:
            pv_write = "PREFIX:TestString-SP"
            pv_read = "PREFIX:TestString-RB"

            test_value = "Some value"
            await ctxt.put(pv_write, test_value)

            result = await ctxt.get(pv_read)
            assert result == test_value
```

### Passing arguments to `iocsh`

The `IOC` class accepts arbitrary arguments that are passed directly to the `iocsh` command:

```python
from run_iocsh import IOC

# Load EPICS modules
ioc = IOC("-r", "iocstats", "-r", "autosave")

# Load database files
ioc = IOC("st.cmd", "-c", "dbLoadRecords('my.db')")
```

## API reference

For complete API documentation, see the [auto-generated API reference](autoapi/run_iocsh/index.html).

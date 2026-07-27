run-iocsh
=========

Python wrapper to run ``iocsh`` (or another IOC executable) for automated
testing of EPICS applications. It starts an IOC, waits for ``iocInit`` to
complete, and raises typed exceptions if errors are detected in the output.

Requires Python >= 3.11 and an activated e3 environment (or any environment
providing the IOC executable).

**Documentation:** https://e3.pages.ess.eu/run-iocsh

Installation
------------

.. code-block:: console

    $ pip install run-iocsh -i https://artifactory.esss.lu.se/artifactory/api/pypi/pypi-virtual/simple

Quick Start
-----------

**Command Line:**

.. code-block:: console

    $ run-iocsh st.cmd

**Python Library:**

.. code-block:: python

    from run_iocsh import IOC

    with IOC("st.cmd") as ioc:
        ioc.wait_for_output()
        # IOC is running; interact with PVs here

    # ioc.output, ioc.stdout and ioc.stderr available for inspection

License
-------

BSD-2

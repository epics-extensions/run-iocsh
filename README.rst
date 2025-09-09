run-iocsh
=========

Python wrapper to run ``iocsh`` for testing EPICS applications. It starts an IOC (shell), and automatically sends an exit command after a specified delay, raising exceptions if errors occur.

Requires Python >= 3.6 (development requires >= 3.7) and an activated e3 environment.

**Repository:** https://gitlab.esss.lu.se/e3/run-iocsh

**Documentation:** http://e3.pages.esss.lu.se/run-iocsh

Installation
------------

.. code-block:: console

    $ pip install run-iocsh -i https://artifactory.esss.lu.se/artifactory/api/pypi/pypi-virtual/simple

Quick Start
-----------

**Command Line:**

.. code-block:: console

    $ run-iocsh --delay 5 st.cmd

**Python Library:**

.. code-block:: python

    from run_iocsh import IOC

    with IOC("st.cmd") as ioc:
        # Test your EPICS PVs, etc.
        pass

Documentation
-------------

For detailed usage instructions, examples, and API reference, see the `full documentation <http://e3.pages.esss.lu.se/run-iocsh>`_.

License
-------

BSD-2

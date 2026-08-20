run-iocsh
=========

Python wrapper to run an IOC executable for automated testing of EPICS
applications. It starts an IOC, waits for ``iocInit`` to complete, and raises
typed exceptions if errors are detected in the output.

Requires Python >= 3.11 and an IOC executable, found on ``PATH`` or given
as a full path.

It was written for e3, which is still its primary target, and two defaults
carry that with them: the executable is ``iocsh``, and the error detectors
match messages emitted by require. Both are replaceable and any IOC executable
works, but a site that does not use require should replace the detectors
before trusting a passing run.

**Documentation:** https://epics-extensions.github.io/run-iocsh

Installation
------------

.. code-block:: console

    $ pip install run-iocsh

It is also packaged for `conda-forge <https://anaconda.org/conda-forge/run-iocsh>`_:

.. code-block:: console

    $ conda install -c conda-forge run-iocsh

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

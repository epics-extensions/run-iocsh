run-iocsh
=========

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black

.. image:: https://gitlab.esss.lu.se/ics-infrastructure/run-iocsh/badges/master/pipeline.svg

.. image:: https://gitlab.esss.lu.se/ics-infrastructure/run-iocsh/badges/master/coverage.svg


Wrapper to run iocsh.bash for test.

**run-iocsh is only meant to be used for testing!** It runs `iocsh.bash` and sends the **exit** command after a delay.
It raises an exception if an error occurred.

Requires Python >= 3.6

Quick start
-----------

::

    $ run-iocsh -h
    usage: run-iocsh [-h] [--name NAME] [--delay DELAY] [--timeout TIMEOUT]

    Run iocsch.bash and send the exit command after <delay> seconds

    optional arguments:
      -h, --help     show this help message and exit
      --name NAME    name of the iocsh script [default: iocsh.bash]
      --delay DELAY  time (in seconds) to wait before to send the exit command
                     [default: 5]
      --timeout TIMEOUT  time (in seconds) to wait when sending the exit command
                     [default: 5]

All other arguments are passed to the iocsh script::

    $ run-iocsh -r iocstats
    2019-03-19 10:12:57,016 DEBUG: Running: ['iocsh.bash', '-r', 'iocstats']
    2019-03-19 10:13:02,148 INFO: ========== stdout ============================
    Starting iocInit
    iocRun: All initialization complete
    #
    ...
    #
    require iocstats
    Module iocstats version 3.1.15 found in /opt/conda/envs/epics/modules/iocstats/3.1.15/
    Loading library /opt/conda/envs/epics/modules/iocstats/3.1.15/lib/linux-x86_64/libiocstats.so
    Loaded iocstats version 3.1.15
    Loading dbd file /opt/conda/envs/epics/modules/iocstats/3.1.15/dbd/iocstats.dbd
    Calling function iocstats_registerRecordDeviceDriver
    Loading module info records for iocstats
    ...
    iocInit
    ############################################################################
    ## EPICS R3.15.5
    ## EPICS Base built Mar 15 2019
    ############################################################################
    8253dcedf67c.2117 > exit
    ============================================================================
    2019-03-19 10:13:02,149 INFO: ========== stderr ============================
    ============================================================================
    2019-03-19 10:13:02,149 DEBUG: return code: 0


    $ run-iocsh cmds/test1.cmd
    ...

Installation
------------

::

    $ pip install run-iocsh -i https://artifactory.esss.lu.se/artifactory/api/pypi/pypi-virtual/simple


License
-------

BSD-2

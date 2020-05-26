# import pytest
from run_iocsh import IOC
from epics import PV
from time import sleep


def test_runiocsh_with_pvaccess():
    ioc = IOC()
    ioc.run("iocsh.bash", "tests/cmds/test_pv.cmd")

    pv = PV("TEST")
    assert int(pv.get()) == 5

    pv.put("17")
    sleep(1)
    assert int(pv.get()) == 17

    ioc.exit()

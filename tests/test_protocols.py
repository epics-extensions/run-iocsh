from time import sleep

from run_iocsh import IOC


def test_runiocsh_ca() -> None:
    from epics import PV

    with IOC("tests/cmds/test_pv.cmd"):
        pv = PV("TEST")
        value_in_db = 5
        assert int(pv.get()) == value_in_db

        new_value = 17
        pv.put(str(new_value))
        sleep(0.1)
        assert int(pv.get()) == new_value


def test_pvapy() -> None:
    from pvaccess import Channel, PvDouble

    with IOC("tests/cmds/test_pv.cmd"):
        channel = Channel("TEST")
        value = 13.0
        channel.put(PvDouble(value))
        sleep(0.1)
        assert channel.get().get()["value"] == value


def test_p4p() -> None:
    from p4p.client.thread import Context

    assert "pva" in Context.providers()

    with IOC("tests/cmds/test_pv.cmd"), Context("pva") as ctxt:
        value = 19
        ctxt.put("TEST", value)
        assert ctxt.get("TEST") == value

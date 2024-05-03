from pathlib import Path
from string import Template
from time import sleep

import pytest

from run_iocsh import IOC


@pytest.fixture(scope="session")
def tmp_cmd_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp_dir = tmp_path_factory.mktemp("data")

    db_file_contents = """\
    record(ai, "TEST") {
        field(INP,  "5")
    }
    """
    cmd_file_contents = Template("""\
    dbLoadRecords("${db_file}")
    """)

    tmp_db_file = tmp_dir / "test_pv.db"
    tmp_db_file.write_text(db_file_contents)

    tmp_cmd_file = tmp_dir / "test.cmd"
    tmp_cmd_file.write_text(
        cmd_file_contents.substitute(db_file=tmp_db_file.as_posix())
    )

    return tmp_cmd_file


def test_runiocsh_ca(tmp_cmd_file: str) -> None:
    from epics import PV

    with IOC(tmp_cmd_file.as_posix()):
        pv = PV("TEST")
        value_in_db = 5
        assert int(pv.get()) == value_in_db

        new_value = 17
        pv.put(str(new_value))
        sleep(0.1)
        assert int(pv.get()) == new_value


def test_pvapy(tmp_cmd_file: str) -> None:
    from pvaccess import Channel, PvDouble

    with IOC(tmp_cmd_file.as_posix()):
        channel = Channel("TEST")
        value = 13.0
        channel.put(PvDouble(value))
        sleep(0.1)
        assert channel.get().get()["value"] == value


def test_p4p(tmp_cmd_file: str) -> None:
    from p4p.client.thread import Context

    assert "pva" in Context.providers()

    with IOC(tmp_cmd_file.as_posix()), Context("pva") as ctxt:
        value = 19
        ctxt.put("TEST", value)
        assert ctxt.get("TEST") == value

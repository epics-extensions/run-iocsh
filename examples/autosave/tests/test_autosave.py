import logging
import time
from textwrap import dedent

import pytest
from p4p.client.thread import Context

from run_iocsh import IOC, wait_for
from tests.utils import (
    IOC_TIMEOUT_SECONDS,
    IOCNAME,
    create_startup_script_content,
)

LOG = logging.getLogger(__name__)

SAVE_TIMEOUT_SECONDS = 10.0

# Autosave pass0 restores before iocInit; pass1 and settings restore after iocInit.
# The PVA server isn't fully up during pass0 restore, so pass0-related PVs take longer
# to become accessible over PVA on slow CI than the default wait_for timeout allows.
_PASS0_PVA_WAIT_SECONDS = 30.0


def sav_file_complete(path) -> bool:
    try:
        return "<END>" in path.read_text()
    except FileNotFoundError:
        return False


@pytest.fixture
def test_db(tmp_path):
    (tmp_path / "test.db").write_text(
        dedent("""\
        record(longout, "$(P):Pass0Val") {
            field(VAL, 0)
            info(autosaveFields_pass0, "VAL")
        }

        record(longout, "$(P):Pass1Val") {
            field(VAL, 0)
            info(autosaveFields_pass1, "VAL")
        }

        record(ao, "$(P):SettingsVal") {
            field(VAL, 0.0)
            info(autosaveFields, "VAL")
        }
    """)
    )


@pytest.fixture
def running_ioc(tmp_path, test_db):
    st = tmp_path / "st.cmd"
    st.write_text(create_startup_script_content(tmp_path, with_test_db=True))
    with IOC.ready(st.as_posix(), "--iocname", IOCNAME) as ioc:
        yield
    LOG.error("IOC stdout:\n%s", ioc.stdout)
    LOG.error("IOC stderr:\n%s", ioc.stderr)


@pytest.fixture(scope="session")
def context():
    with Context("pva") as ctx:
        yield ctx


@pytest.mark.usefixtures("running_ioc")
class TestStatusPVs:
    def test_is_alive_becomes_running(self, context):
        wait_for(
            lambda: context.get(f"{IOCNAME}:AS-IsAlive") == 1,
            timeout=IOC_TIMEOUT_SECONDS,
        )

    def test_pass0_status_accessible(self, context):
        wait_for(
            lambda: context.get(f"{IOCNAME}:AS-Pass0-Status") is not None,
            timeout=_PASS0_PVA_WAIT_SECONDS,
        )

    def test_pass1_status_accessible(self, context):
        wait_for(
            lambda: context.get(f"{IOCNAME}:AS-Pass1-Status") is not None,
            timeout=IOC_TIMEOUT_SECONDS,
        )


@pytest.mark.usefixtures("running_ioc")
class TestSaveFileCreation:
    @pytest.mark.parametrize("name", ["settings", "values_pass0", "values_pass1"])
    def test_req_file_generated(self, tmp_path, name):
        req = tmp_path / "req" / f"{name}.req"
        wait_for(req.exists, timeout=SAVE_TIMEOUT_SECONDS)

    @pytest.mark.parametrize("name", ["settings", "values_pass0", "values_pass1"])
    def test_sav_file_created(self, tmp_path, name):
        sav = tmp_path / "save" / f"{name}.sav"
        wait_for(lambda: sav_file_complete(sav), timeout=SAVE_TIMEOUT_SECONDS)


class TestMonitorTriggeredSave:
    @pytest.mark.parametrize(
        ("pv_suffix", "sav_name", "test_value"),
        [
            ("Pass0Val", "values_pass0", 54321),
            ("Pass1Val", "values_pass1", 12345),
            ("SettingsVal", "settings", 99.5),
        ],
    )
    def test_value_saved_and_restored_on_monitor_change(
        self, tmp_path, context, test_db, pv_suffix, sav_name, test_value
    ):
        st = tmp_path / "st.cmd"
        st.write_text(create_startup_script_content(tmp_path, with_test_db=True))
        sav = tmp_path / "save" / f"{sav_name}.sav"
        pv = f"{IOCNAME}:{pv_suffix}"

        with IOC.ready(st.as_posix(), "--iocname", IOCNAME):
            wait_for(
                lambda: context.get(pv) is not None,
                timeout=_PASS0_PVA_WAIT_SECONDS,
            )
            put_at = time.time()
            context.put(pv, test_value)
            wait_for(
                lambda: sav_file_complete(sav) and sav.stat().st_mtime >= put_at,
                timeout=SAVE_TIMEOUT_SECONDS,
            )

        restore_timeout = (
            _PASS0_PVA_WAIT_SECONDS if pv_suffix == "Pass0Val" else IOC_TIMEOUT_SECONDS
        )

        with IOC.ready(st.as_posix(), "--iocname", IOCNAME):
            wait_for(
                lambda: abs(float(context.get(pv)) - float(test_value)) < 0.01,
                timeout=restore_timeout,
            )

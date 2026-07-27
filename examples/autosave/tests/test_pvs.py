import logging
import re

from run_iocsh import run_iocsh
from tests.utils import IOCNAME, create_startup_script_content

LOG = logging.getLogger(__name__)


_REQUIRE_PVS = {
    "#Modules",
    "#ModulesLabels",
    "#ModulesVersions",
    "#Components",
    "#ComponentsLabels",
    "#ComponentsVersions",
    "Require-Version",
}

_AUTOSAVE_PVS = {
    "AS-Disable",
    "AS-DisableMaxSeconds",
    "AS-IsAlive",
    "AS-LastOperation",
    "AS-RebootStatus",
    "AS-RebootStatus-Msg",
    "AS-RebootTime",
    "AS-WorstStatus",
    "AS-WorstStatus-Msg",
    *(
        f"AS-Pass{p}-{s}"
        for p in (0, 1)
        for s in ("Filename", "MethodBits", "Method", "Status", "Status-Msg", "Time")
    ),
    "#AS-Heartbeat",
    "#AS-Trigger",
}


def test_autosave_pvs(tmp_path):
    content = create_startup_script_content(tmp_path, with_dbl=True)
    st = tmp_path / "st.cmd"
    st.write_text(content)
    ioc = run_iocsh(st.as_posix(), "--iocname", IOCNAME)
    LOG.error("IOC stdout:\n%s", ioc.stdout)
    LOG.error("IOC stderr:\n%s", ioc.stderr)
    pvs = re.findall(
        rf"^{re.escape(IOCNAME)}:([^\s]+)\s*$",
        ioc.stdout,
        re.MULTILINE,
    )
    assert set(pvs) - _REQUIRE_PVS == _AUTOSAVE_PVS

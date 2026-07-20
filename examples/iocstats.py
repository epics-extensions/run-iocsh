import logging
import re
from textwrap import dedent

from run_iocsh import run_iocsh

LOG = logging.getLogger(__name__)

IOCNAME = "TEST"

_IOCSTATS_PVS = {
    # public
    "Heartbeat",
    "IOCVERSION",
    "ReloadACF",
    "StartCount",
    "Uptime",
    # internal
    "#ABORT_ON_ASSERT",
    "#AvailableFDs",
    "#CA_ADDR_LIST",
    "#CA_AUTO_ADDR_LIST",
    "#CA_AUTO_ARRAY_BYTES",
    "#CA_BEACON_PERIOD",
    "#CAClientConnections",
    "#CAClientCount",
    "#CA_CONN_TMO",
    "#CallbackQueueSize",
    "#CA_MAX_ARRAY_BYTES",
    "#CA_MAX_SEARCH_PERIOD",
    "#CA_MCAST_TTL",
    "#CA_NAME_SERVERS",
    "#CA_REPEATER_PORT",
    "#CA_SERVER_PORT",
    "#CAS_AUTO_BEACON_ADDR_LIST",
    "#CAS_BEACON_ADDR_LIST",
    "#CAS_BEACON_PERIOD",
    "#CAS_BEACON_PORT",
    "#CAS_IGNORE_ADDR_LIST",
    "#CAS_INTF_ADDR_LIST",
    "#CAS_SERVER_PORT",
    "#CAScanRate",
    "#CBHighQueueHigh",
    "#CBHighQueueHighPct",
    "#CBHighQueueOverruns",
    "#CBHighQueueUsed",
    "#CBHighQueueUsedPct",
    "#CBLowQueueHigh",
    "#CBLowQueueHighPct",
    "#CBLowQueueOverruns",
    "#CBLowQueueUsed",
    "#CBLowQueueUsedPct",
    "#CBMedQueueHigh",
    "#CBMedQueueHighPct",
    "#CBMedQueueOverruns",
    "#CBMedQueueUsed",
    "#CBMedQueueUsedPct",
    "#CPUCount",
    "#CPUScanRate",
    "#FDScanRate",
    "#GenTimeErrCount",
    "#GenTimeErrReset",
    "#GenTimeEventProvider",
    "#GenTimeHighestProvider",
    "#GenTimeSource",
    "#GenTimeTime",
    "#IOC-CPULoad",
    "#IOC_IGNORE_SERVERS",
    "#IOC_LOG_FILE_COMMAND",
    "#IOC_LOG_FILE_LIMIT",
    "#IOC_LOG_FILE_NAME",
    "#IOC_LOG_INET",
    "#IOC_LOG_PORT",
    "#KernelVersion",
    "#MaxNumberFDs",
    "#ParentPID",
    "#PID",
    "#PVAS_AUTO_BEACON_ADDR_LIST",
    "#PVAS_BEACON_ADDR_LIST",
    "#PVAS_BEACON_PERIOD",
    "#PVAS_BROADCAST_PORT",
    "#PVAS_INTF_ADDR_LIST",
    "#PVAS_PROVIDER_NAMES",
    "#PVAS_SERVER_PORT",
    "#PVA_ADDR_LIST",
    "#PVA_AUTO_ADDR_LIST",
    "#PVA_BEACON_PERIOD",
    "#PVA_CONN_TMO",
    "#PVA_MAX_ARRAY_BYTES",
    "#PVA_MAX_SEARCH_PERIOD",
    "#PVA_SERVER_PORT",
    "#ScanOnceQueueHigh",
    "#ScanOnceQueueHighPct",
    "#ScanOnceQueueOverruns",
    "#ScanOnceQueueSize",
    "#ScanOnceQueueUsed",
    "#ScanOnceQueueUsedPct",
    "#StartTOD",
    "#SuspendedTaskCount",
    "#TS_NTP_INET",
    "#TZ",
    "#UsedFDs",
}

_REQUIRE_PVS = {
    "#Modules",
    "#ModulesLabels",
    "#ModulesVersions",
    "#Components",
    "#ComponentsLabels",
    "#ComponentsVersions",
    "Require-Version",
}

EXPECTED_PVS = _IOCSTATS_PVS


def test_pvs(tmp_path):
    startup_script_content = dedent(f"""\
    require iocstats

    iocshLoad("$(iocstats_DIR)/iocStats.iocsh", "IOCNAME={IOCNAME}")

    afterInit('dbl')
    """)

    p = tmp_path / "st.cmd"
    p.write_text(startup_script_content)
    ioc = run_iocsh(p.as_posix(), "--iocname", IOCNAME)
    LOG.error("IOC stdout:\n%s", ioc.stdout)
    LOG.error("IOC stderr:\n%s", ioc.stderr)
    pvs = re.findall(rf"^{re.escape(IOCNAME)}:(.+)$", ioc.stdout, re.MULTILINE)
    assert set(pvs) - _REQUIRE_PVS == EXPECTED_PVS

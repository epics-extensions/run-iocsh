from textwrap import dedent

IOCNAME = "TEST"

IOC_TIMEOUT_SECONDS = 10.0


def create_startup_script_content(
    tmp_path,
    *,
    with_dbl: bool = False,
    with_test_db: bool = False,
    period: int = 2,
) -> str:
    period_macros = (
        f"AUTOSAVE_SETTINGS_PERIOD={period},"
        f"AUTOSAVE_VALUES_PASS0_PERIOD={period},"
        f"AUTOSAVE_VALUES_PASS1_PERIOD={period}"
    )
    content = dedent(f"""\
        require autosave

        epicsEnvSet("AS_TOP", "{tmp_path}")
        epicsEnvSet("IOCDIR", ".")
        iocshLoad("$(autosave_DIR)/autosave.iocsh", "{period_macros}")
    """)
    if with_test_db:
        content += '\ndbLoadRecords("$(E3_CMD_TOP)/test.db", "P=$(IOCNAME)")\n'
    if with_dbl:
        content += '\nafterInit("dbl")\n'
    return content

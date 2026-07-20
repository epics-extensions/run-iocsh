import pytest
from p4p.client.thread import Context

from run_iocsh import wait_for

PREFIX = "TEST:"
READBACK_TIMEOUT_SECONDS = 5.0


@pytest.fixture(scope="module")
def ctx(ioc):
    c = Context("pva")
    yield c
    c.close()


def test_read_register(ctx):
    val = ctx.get(PREFIX + "READ")
    assert val == 0


def test_write_and_readback(ctx):
    ctx.put(PREFIX + "WRITE", 42)
    wait_for(lambda: ctx.get(PREFIX + "READ") == 42, timeout=READBACK_TIMEOUT_SECONDS)

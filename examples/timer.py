from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep

import pytest
from p4p.client.thread import Context

from run_iocsh import IOC, wait_for

TEST_DIR = Path(__file__).absolute().parent
TEST_SCRIPT = TEST_DIR / "st_test.cmd"
STARTUP_ARGS = [TEST_SCRIPT]


@pytest.fixture(scope="session")
def ioc() -> Iterator[IOC]:
    with IOC.ready(*STARTUP_ARGS) as ioc:
        yield ioc
    # leaving the block exits the IOC and runs check_output()


@pytest.fixture(scope="session")
def ctxt() -> Iterator[Context]:
    with Context("pva") as ctx:
        yield ctx


def test_starts_stopped(ioc: IOC, ctxt: Context) -> None:
    assert ctxt.get("timer:test:TimerRun") == 0


def test_timerrun_can_be_set(ioc: IOC, ctxt: Context) -> None:
    ctxt.put("timer:test:WaitSecond", 10)
    # Give the .1s scan one tick to update the 'Remaining' logic
    sleep(0.2)

    ctxt.put("timer:test:TimerRun", 1)
    wait_for(lambda: ctxt.get("timer:test:TimerRun") == 1)

    ctxt.put("timer:test:TimerRun", 0)
    wait_for(lambda: ctxt.get("timer:test:TimerRun") == 0)


def test_countdown(ioc: IOC, ctxt: Context) -> None:
    ctxt.put("timer:test:WaitHour", 0)
    ctxt.put("timer:test:WaitMinute", 2)
    ctxt.put("timer:test:WaitSecond", 0)
    sleep(0.2)

    # Start countdown
    ctxt.put("timer:test:TimerRun", 1)
    sleep(10)
    t = datetime.strptime(ctxt.get("timer:test:RemainingTime"), "%H:%M:%S")
    delta = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second).total_seconds()

    assert delta == pytest.approx(110, abs=1)


def test_expire(ioc: IOC, ctxt: Context) -> None:
    ctxt.put("timer:test:WaitHour", 0)
    ctxt.put("timer:test:WaitMinute", 0)
    ctxt.put("timer:test:WaitSecond", 10)
    sleep(0.2)

    # set example PVs
    ctxt.put("example:test:TestBi", 0)
    ctxt.put("example:test:TestValue", 10)
    ctxt.put("example:test:TestAi", 0)

    # start timer, then wait for it to expire
    ctxt.put("timer:test:TimerRun", 1)
    wait_for(lambda: ctxt.get("timer:test:TimerRun") == 0, timeout=15)

    assert ctxt.get("example:test:TestBi") == 1
    assert ctxt.get("example:test:TestAi") == 10

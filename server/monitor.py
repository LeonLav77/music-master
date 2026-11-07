"""Live monitoring: the amp's sound to any listener on the network.

Uses the amp input the tuner opened, so it starts after the tuner - and
hotplug.py closes it first and opens it last when it reopens that input.
Without the amp input there is nothing to send.

There is nothing to switch on: sending starts when a listener asks and
stops when it stops asking (see capture/monitor.py). _watch() writes to
the log who started and stopped listening.
"""

import asyncio
import contextlib
import logging

from capture import Monitor
from capture.stream import BLOCK
from server import tuner

WATCH_INTERVAL = 1.0     # seconds between looks at who is listening

log = logging.getLogger("uvicorn.error")

monitor = None


def open_monitor():
    global monitor
    if tuner.capture is None:
        log.warning("Monitor disabled: no input from the amp")
        return
    try:
        monitor = Monitor(tuner.capture)
    except OSError as exc:      # the port is taken, e.g. by a second server
        log.warning("Monitor disabled: %s", exc)
        return
    log.info("Monitor: blocks of %d frames, capture latency %.1f ms",
             BLOCK, tuner.capture.latency() * 1000)


async def close_monitor():
    global monitor
    closing, monitor = monitor, None
    if closing is not None:
        await asyncio.to_thread(closing.close)


async def _watch():
    sending_to = set()
    overruns = 0
    while True:
        # Blocks the card dropped because nobody read them in time - the
        # price of too small a buffer.
        capture = tuner.capture
        if capture is not None:
            if capture.overruns > overruns:
                log.warning("Capture: %d blocks dropped so far", capture.overruns)
            overruns = capture.overruns   # back to 0 when hotplug reopens it

        listeners = set() if monitor is None else set(monitor.listeners)
        for host, port in listeners - sending_to:
            log.info("Monitor: sending to %s:%d", host, port)
        for host, port in sending_to - listeners:
            log.info("Monitor: %s:%d stopped listening", host, port)
        sending_to = listeners
        await asyncio.sleep(WATCH_INTERVAL)


@contextlib.asynccontextmanager
async def lifespan(app):
    open_monitor()

    task = asyncio.create_task(_watch())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        await close_monitor()

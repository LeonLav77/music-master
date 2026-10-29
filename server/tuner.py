"""The tuner: always listening to the dry guitar while the server runs.

Opened in the lifespan. If the amp's USB input cannot be opened the rest
of the server still runs, and the page shows the tuner as unavailable.

The Tuner thread updates its reading about 14 times a second. _watch()
looks just as often and broadcasts when the reading changed - so while
a note rings every browser gets a "tuner" message per reading, and while
the guitar is silent, nothing.
"""

import asyncio
import contextlib
import logging

from capture import Capture, CaptureError, Tuner
from server import browsers

WATCH_INTERVAL = 0.07    # seconds between checks: one reading's worth

log = logging.getLogger("uvicorn.error")

capture = None
tuner = None


def state_message():
    if tuner is None:
        return {"type": "tuner", "available": False}
    reading = tuner.reading
    if reading is None:
        return {"type": "tuner", "available": True, "note": None}
    name, octave, cents = reading
    return {"type": "tuner", "available": True, "note": name, "octave": octave, "cents": round(cents, 1)}


async def _watch():
    sent = None
    while True:
        state = state_message()
        if state != sent:
            sent = state
            await browsers.broadcast(state)
        await asyncio.sleep(WATCH_INTERVAL)


@contextlib.asynccontextmanager
async def lifespan(app):
    global capture, tuner
    try:
        capture = Capture()
        tuner = Tuner(capture)
    except CaptureError as exc:
        log.warning("Tuner disabled: %s", exc)

    task = asyncio.create_task(_watch())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        if tuner is not None:
            tuner.close()
        if capture is not None:
            capture.close()

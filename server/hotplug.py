"""Switching the amp on or off while the server runs.

The tuner and recorder need the Katana's USB input, which only exists
while the amp is on - and at boot the server is often up before it.

Trying again is not enough: PortAudio, which sounddevice is built on,
lists the sound cards once, when it starts, and never looks again. A
Katana switched on after that is not in its list however often we ask.
So when the Katana comes or goes, everything that uses a sound card is
closed, PortAudio is restarted, and everything is opened again. The
headphone jack too: restarting PortAudio closes every stream it has.

Whether the Katana is there is read from /proc/asound/cards, the
kernel's own list of sound cards, which is always up to date.

Reopening the jack cuts off a song or the metronome. That only happens
when the amp is switched on or off - and the jack plays into the amp's
AUX, so with the amp off nobody hears it anyway. The metronome keeps its
tempo and volume.

The Katana's input can also stall with the amp on: the card stays
listed, MIDI keeps working, but the amp sends only empty USB packets, so
no audio arrives - the tuner freezes on its last note and the recorder
records nothing, with no error anywhere. Reopening restarts the amp's
audio and fixes it, so that is done here too, when no audio has come for
STALL seconds. If it stalls again straight away the wait doubles each
time, up to STALL_MAX, so a stall reopening cannot fix does not cut off
the metronome every few seconds.
"""

import asyncio
import contextlib
import logging
from pathlib import Path

import sounddevice

from capture.stream import KATANA_NAME
from server import audio, recorder, tuner

CARDS = Path("/proc/asound/cards")
CHECK_INTERVAL = 2.0     # seconds between looks at the list of cards
SETTLE = 1.0             # seconds a Katana that just appeared gets to be ready
STALL = 3.0              # seconds without audio before the input counts as stalled
STALL_MAX = 60.0         # the longest the wait grows to after repeated stalls

log = logging.getLogger("uvicorn.error")


def _plugged():
    try:
        return KATANA_NAME.lower() in CARDS.read_text().lower()
    except OSError:
        return False


def _restart_portaudio():
    # sounddevice starts PortAudio when it is imported; these two are how
    # its documentation says to make it list the cards again.
    sounddevice._terminate()
    sounddevice._initialize()


async def _reopen():
    # Users first, so nothing is left holding a stream that is closed.
    await recorder.close_recorder()
    await tuner.close_input()
    metronome = await audio.close_player()

    await asyncio.to_thread(_restart_portaudio)

    await audio.open_player(metronome)
    await tuner.open_input()
    recorder.open_recorder()


async def _watch():
    if not CARDS.exists():
        return           # not Linux: no list to watch, the input stays as opened
    # Not _plugged(): if the Katana appeared after PortAudio started but
    # before this first look, the input failed to open although the card
    # is there - and this way that counts as a change too.
    was_plugged = tuner.capture is not None
    stall_limit = STALL
    while True:
        plugged = _plugged()
        capture = tuner.capture
        if plugged != was_plugged:
            was_plugged = plugged
            log.info("Amp %s: reopening the sound cards", "on" if plugged else "off")
            if plugged:
                await asyncio.sleep(SETTLE)
            await _reopen()
        elif capture is not None and capture.silent_for() > stall_limit:
            log.warning("Amp input stalled: no audio for %.0f s, reopening the sound cards", stall_limit)
            await _reopen()
            stall_limit = min(stall_limit * 2, STALL_MAX)
        elif capture is not None and capture.last_block is not None and capture.silent_for() < 1.0:
            stall_limit = STALL      # audio is arriving again: back to the short wait
        await asyncio.sleep(CHECK_INTERVAL)


@contextlib.asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(_watch())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

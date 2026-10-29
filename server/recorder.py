"""The recorder: takes of what you hear, saved in recordings/.

Uses the amp input the tuner opened and the player audio.py opened, so it
starts after both. Without the amp input there is no recorder; without
the player, takes are just the amp.

A take is named after the moment it started, plus the song that was
playing when it stopped: "2026-10-29 16-05-32 seek and destroy.wav".
Stopping mixes the AUX part in - a second or two for a long take - so it
runs off the event loop, and meanwhile the state says "saving".

_watch() sends the state to every browser when it changes: about four
times a second while recording, as the time and the level move.
"""

import asyncio
import contextlib
import logging
import os
import re
import time
import wave
from pathlib import Path

from capture import Recorder, RecorderError
from server import audio, browsers, tuner

ROOT = Path(__file__).resolve().parent.parent
RECORDINGS_DIR = ROOT / "recordings"
WATCH_INTERVAL = 0.25    # seconds between state checks

log = logging.getLogger("uvicorn.error")

recorder = None
_saving = False          # stop() is mixing the take


# --- State -----------------------------------------------------------------

def state_message():
    if recorder is None:
        return {"type": "recorder", "available": False}
    return {
        "type": "recorder",
        "available": True,
        "recording": recorder.is_recording(),
        "saving": _saving,
        "elapsed": round(recorder.elapsed(), 1),
        "peak": round(recorder.peak, 3),
        "error": recorder.error,
    }


def _seconds(path):
    try:
        with wave.open(str(path)) as file:
            return round(file.getnframes() / file.getframerate(), 1)
    except (OSError, wave.Error):
        return None


def _unfinished():
    """The take still being recorded or mixed, if any."""
    if recorder is not None and (recorder.is_recording() or _saving):
        return recorder.path
    return None


def recordings_message():
    """The finished takes, newest first."""
    takes = [path for path in RECORDINGS_DIR.glob("*.wav")
             if path != _unfinished() and not path.name.endswith(".mixed.wav")]
    takes.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return {
        "type": "recordings",
        "recordings": [
            {"name": path.name, "seconds": _seconds(path), "bytes": path.stat().st_size}
            for path in takes
        ],
    }


def existing(name):
    """The path of take `name`, refusing anything outside recordings/."""
    path = RECORDINGS_DIR / name
    if (path.parent != RECORDINGS_DIR or path.suffix != ".wav" or not path.is_file()
            or path == _unfinished()):
        raise RecorderError(f"No such recording {name!r}")
    return path


# --- Messages from the browsers ------------------------------------------

async def handle(message):
    """A "recorder" message from a browser: start or stop."""
    if recorder is None:
        raise RecorderError("No input from the amp - is it on and plugged in?")
    action = message["action"]
    if action == "start":
        if _saving:
            raise RecorderError("Still saving the last take")
        recorder.start(RECORDINGS_DIR / f"{time.strftime('%Y-%m-%d %H-%M-%S')}.wav")
    elif action == "stop":
        await _stop()
    else:
        raise ValueError(f"Unknown recorder action {action!r}")


def _song_name():
    """The song in the player, as a file-name-safe "seek and destroy"."""
    track = audio.player.track if audio.player is not None else None
    if track is None:
        return None
    words = re.sub(r"[^\w]+", " ", Path(track.name).stem.replace("_", " ")).strip()
    return words or None


async def _stop():
    global _saving
    if not recorder.is_recording():
        return
    song = _song_name()
    _saving = True
    try:
        path = await asyncio.to_thread(recorder.stop)
    finally:
        _saving = False
    if song:
        named = path.with_name(f"{path.stem} {song}.wav")
        os.replace(path, named)
    await browsers.broadcast(recordings_message())


def remove(name):
    existing(name).unlink()


# --- The watcher and the lifespan ----------------------------------------

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
    global recorder
    RECORDINGS_DIR.mkdir(exist_ok=True)
    # Left behind by a server that stopped mid-take: the take itself plays
    # (its header is kept up to date), its AUX part cannot be mixed in now.
    for leftover in [*RECORDINGS_DIR.glob("*.aux"), *RECORDINGS_DIR.glob("*.mixed.wav")]:
        leftover.unlink()
    if tuner.capture is not None:
        recorder = Recorder(tuner.capture, audio.player)
    else:
        log.warning("Recorder disabled: no input from the amp")

    task = asyncio.create_task(_watch())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        if recorder is not None and recorder.is_recording():
            recorder.stop()

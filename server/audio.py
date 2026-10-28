"""The link to the audio: the one Player and Library the server shares.

Both open in the lifespan. If the headphone jack cannot be opened the rest
of the server still runs - the amp does not need it - and playback
messages get an error back.

Actions are queued to the audio thread and take effect on its next block,
so nothing here broadcasts straight after one. _watch() is the only sender
of playback state: it looks ten times a second and broadcasts when
something changed - including a track ending on its own.
"""

import asyncio
import contextlib
import logging
from pathlib import Path

from playback import Library, PlaybackError, Player
from server import browsers

ROOT = Path(__file__).resolve().parent.parent
TRACKS_DIR = ROOT / "tracks"
WATCH_INTERVAL = 0.1     # seconds between state checks
TRACKS_EVERY = 10        # check the folder on every 10th, once a second
JUMP = 0.3               # seconds off from where browsers think a song is

log = logging.getLogger("uvicorn.error")

player = None
library = None
_loading = None          # name of the track being decoded to play, if any
_song_volume = 1.0       # for every song, not just the one playing


# --- State -----------------------------------------------------------------

def state_message():
    if player is None:
        return {"type": "playback", "available": False}
    metronome, track = player.metronome, player.track
    return {
        "type": "playback",
        "available": True,
        "loading": _loading,
        "song_volume": _song_volume,
        "metronome": {
            "running": metronome.is_running(),
            "bpm": metronome.bpm,
            "beats_per_bar": metronome.beats_per_bar,
            "volume": metronome.volume,
        },
        "track": None if track is None else {
            "name": track.name,
            "playing": track.is_playing(),
            # Started, but still in the count-in: not moving yet.
            "counting_in": track.is_waiting(player.position),
            "elapsed": round(track.elapsed(), 2),
            "duration": round(track.duration(), 2),
        },
    }


def tracks_message():
    return {
        "type": "tracks",
        "tracks": [{"name": name, "ready": library.is_ready(name)} for name in library.names()],
    }


# --- Messages from the browsers ------------------------------------------

def _number(message, key, low, high, default=None):
    value = message.get(key, default)
    if value is None:
        raise KeyError(key)
    value = float(value)
    if not low <= value <= high:
        raise ValueError(f"{key} must be between {low} and {high}")
    return value


async def handle(message):
    """A "metronome" or "track" message from a browser."""
    if player is None:
        raise PlaybackError("No audio output - is the headphone jack free?")
    if message["type"] == "metronome":
        _metronome(message)
    else:
        await _track(message)


def _metronome(message):
    metronome = player.metronome
    if "bpm" in message:
        metronome.bpm = _number(message, "bpm", 20, 400)
    if "beats_per_bar" in message:
        metronome.beats_per_bar = int(_number(message, "beats_per_bar", 1, 12))
    if "volume" in message:
        metronome.volume = _number(message, "volume", 0, 1)
    if "running" in message:
        if message["running"]:
            # One or the other: a recorded song drifts from the click.
            player.pause()
            player.start_metronome()
        else:
            player.stop_metronome()


async def _track(message):
    global _loading, _song_volume
    action = message["action"]

    if action == "play":
        name = message["name"]
        count_in = int(_number(message, "count_in", 0, 16, default=4))
        first_beat = _number(message, "first_beat", 0, 60, default=0)
        _loading = name
        try:
            # Instant if preloaded; seconds if not - so off the event loop.
            track = await asyncio.to_thread(library.get, name)
        finally:
            _loading = None
        track.volume = _song_volume
        player.play(track, count_in=count_in, first_beat=first_beat)
    elif action == "pause":
        player.pause()
    elif action == "resume":
        player.resume()
    elif action == "stop":
        player.pause()
        player.seek(0)
        player.stop_metronome()
    elif action == "seek":
        player.seek(_number(message, "seconds", 0, 24 * 3600))
    elif action == "volume":
        _song_volume = _number(message, "value", 0, 1)
        if player.track is not None:
            player.track.volume = _song_volume
    else:
        raise ValueError(f"Unknown track action {action!r}")


def remove(name):
    """Delete a song, stopping it first if it is the one playing."""
    if player is not None and player.track is not None and player.track.name == name:
        player.pause()
        player.stop_metronome()
    library.remove(name)


# --- The watcher and the lifespan ----------------------------------------

def _without_elapsed(state):
    # While playing, elapsed changes every check and the browser moves its
    # own progress bar. While paused it only changes on a seek, which the
    # browser does need to hear about.
    track = state.get("track")
    if not track or not track["playing"]:
        return state
    return {**state, "track": {**track, "elapsed": None}}


def _jumped(state, sent, sent_at, now):
    """True when a playing track is not where the browsers think it is -
    they count on from the last elapsed they were sent, so a seek or a
    restart has to be sent even though nothing else changed."""
    track = state.get("track")
    before = sent.get("track") if sent else None
    if not track or not before or not track["playing"] or not before["playing"]:
        return False
    # The song does not move during a count-in. When the count-in ends,
    # counting_in changes, so that is sent anyway.
    expected = before["elapsed"] + (0 if before["counting_in"] else now - sent_at)
    return abs(track["elapsed"] - expected) > JUMP


async def _watch():
    loop = asyncio.get_running_loop()
    sent, sent_at = None, 0.0
    last_tracks = None
    checks = 0
    while True:
        state = state_message()
        now = loop.time()
        changed = sent is None or _without_elapsed(state) != _without_elapsed(sent)
        if changed or _jumped(state, sent, sent_at, now):
            sent, sent_at = state, now
            await browsers.broadcast(state)

        if checks % TRACKS_EVERY == 0:
            tracks = tracks_message()
            if tracks != last_tracks:
                last_tracks = tracks
                await browsers.broadcast(tracks)
        checks += 1
        await asyncio.sleep(WATCH_INTERVAL)


@contextlib.asynccontextmanager
async def lifespan(app):
    global player, library
    library = Library(TRACKS_DIR)
    try:
        player = Player()
    except PlaybackError as exc:
        log.warning("Playback disabled: %s", exc)

    task = asyncio.create_task(_watch())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        if player is not None:
            player.close()
        library.close()

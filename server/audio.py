"""HTTP API for backing-track playback.

A sibling of `server.api`, not a part of it. The two share a server and
nothing else: this router never touches MIDI, never takes the amp lock, and
would keep working with the amp unplugged.

That separation is the whole design. `api._lock` is held for the duration
of every amp operation, and some of them - a channel change, a wah rock -
run for seconds. Playing a four-minute backing track under the same lock
would freeze every knob on the surface until the song ended. The two
subsystems contend for nothing, so they take different locks.

Mount it the same way as the amp API:

    app.include_router(audio.router)

State lives in one Player, because there is one pair of speakers. Its
methods block - subprocess calls, ffmpeg - so handlers push them to a
thread rather than stalling the event loop and every WebSocket on it.
"""

import asyncio
import contextlib
import sys
import shutil
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from katana_amp import audio

ROOT = Path(__file__).resolve().parent.parent

# Backing tracks live here. Created on demand: a fresh checkout has no
# tracks/ and the first download should not fail on a missing directory.
TRACK_DIR = ROOT / "tracks"

router = APIRouter()

_player = audio.Player()

# One playback operation at a time. Two concurrent plays would each stop
# the other's process halfway through starting their own, and the loser
# would leave a temp dir behind.
_lock = asyncio.Lock()

# How transport state reaches the browser.
#
# There is one WebSocket on this server and it belongs to the amp API, so
# this module does not keep its own client set - an earlier version did,
# and since nothing ever added to it every broadcast was silently dropped.
# `server.app` injects the amp API's broadcaster here at startup instead.
#
# The dependency points this way round deliberately: the amp API still
# knows nothing about audio, and this module still knows nothing about
# WebSockets. Left unset - the API mounted on its own, or a test importing
# only this module - broadcasting is simply a no-op.
_publish = None


def set_publisher(fn):
    """Route transport updates to `fn`, an async callable taking a dict."""
    global _publish
    _publish = fn

# Set while a download is running, so a second request can be refused with
# something better than two yt-dlp processes writing the same file.
_fetching = None


class PlayRequest(BaseModel):
    """What to play, and how to count into it."""

    track: str
    volume: float = 1.0
    sink: str | None = None
    start: float = 0.0

    # Make-up gain in dB, for playing with other people. `volume` only ever
    # attenuates - this is the one that goes above the recording's own
    # level, at the cost of rebuilding the audio before playback starts.
    boost_db: float = 0.0

    # The count-in. None or bpm=0 means none at all. Expressed as bars and a
    # time signature rather than a beat count because that is how the
    # request arrives from a musician - "one bar of 4/4 at 120".
    bpm: int | None = None
    bars: int = 1
    beats_per_bar: int = 4


class SeekRequest(BaseModel):
    position: float


class VolumeRequest(BaseModel):
    volume: float


class FetchRequest(BaseModel):
    url: str


async def _broadcast(message):
    """Push transport state to every listening client, if anyone is wired up."""
    if _publish is None:
        return
    await _publish(message)


async def _announce():
    """Tell clients where the transport is now."""
    status = await asyncio.to_thread(_player.status)
    await _broadcast({"type": "audio", **status})
    return status


def _resolve(name):
    """Turn a client-supplied track name into a path inside TRACK_DIR.

    The name comes off the wire, so it is checked the same way the .tsl
    loader checks its filenames: resolve it and require the result to still
    be in the directory. Without this, "../../etc/passwd" is a track.
    """
    path = (TRACK_DIR / name).resolve()
    if path.parent != TRACK_DIR.resolve() or not path.is_file():
        raise HTTPException(404, f"No such track: {name}")
    return path


# --- Library ---------------------------------------------------------------

@router.get("/api/audio/tracks")
async def list_tracks():
    """Everything playable in tracks/.

    Probing durations is a subprocess per file, so it goes to a thread -
    on a Pi with a full shelf this is the slowest endpoint here.
    """
    TRACK_DIR.mkdir(exist_ok=True)
    return await asyncio.to_thread(audio.scan, TRACK_DIR)


@router.get("/api/audio/limits")
async def limits():
    """Ranges the UI should respect, so they live in one place."""
    return {"max_boost_db": audio.MAX_BOOST_DB}


@router.get("/api/audio/sinks")
async def list_sinks():
    """Output devices, with the re-amping one flagged rather than hidden."""
    found = await asyncio.to_thread(audio.sinks)
    return {"sinks": found, "default": next((s["name"] for s in found if s["analog"]), None)}


@router.delete("/api/audio/tracks/{name}")
async def delete_track(name: str):
    """Remove a track from the library. Deletes the file.

    The whole thing runs under the playback lock, including the unlink.
    Checking "is this playing?" and then deleting as two separate steps
    left a gap a play request could land in - the check would pass, the
    file would vanish underneath the player that had just started it, and
    the next seek would fail on a path that no longer existed.
    """
    path = _resolve(name)

    async with _lock:
        # status() can rmtree a finished track's scratch dir, so it is
        # filesystem work and does not belong on the event loop.
        current = await asyncio.to_thread(_player.status)
        stopped = False
        if current["track"] == path.name:
            await asyncio.to_thread(_player.stop)
            stopped = True
        await asyncio.to_thread(path.unlink)

    if stopped:
        await _announce()
    return {"deleted": path.name}


# --- Transport -------------------------------------------------------------

@router.get("/api/audio/status")
async def status():
    """Where the transport is. Cheap - no subprocess, no device query."""
    return await asyncio.to_thread(_player.status)


@router.post("/api/audio/play")
async def play(body: PlayRequest):
    """Start a track, optionally after a count-in.

    Blocking work - ffmpeg for the count-in, ffprobe for the duration -
    runs in a thread. The lock is held across it so a second play request
    arriving mid-build cannot start a competing process.
    """
    path = _resolve(body.track)

    count_in = None
    if body.bpm:
        if not 30 <= body.bpm <= 300:
            raise HTTPException(422, "BPM must be between 30 and 300")
        if not 1 <= body.bars <= 8:
            raise HTTPException(422, "Count-in must be 1-8 bars")
        if not 2 <= body.beats_per_bar <= 12:
            raise HTTPException(422, "Beats per bar must be 2-12")
        count_in = (body.bpm, body.bars * body.beats_per_bar, body.beats_per_bar)

    if not 0 <= body.boost_db <= audio.MAX_BOOST_DB:
        raise HTTPException(
            422, f"Boost must be between 0 and {audio.MAX_BOOST_DB:g} dB"
        )

    async with _lock:
        try:
            result = await asyncio.to_thread(
                _player.play, path,
                sink=body.sink, volume=body.volume,
                count_in=count_in, start=max(0.0, body.start),
                db=body.boost_db,
            )
        except audio.AudioError as exc:
            raise HTTPException(400, str(exc))

    await _broadcast({"type": "audio", **result})
    return result


@router.post("/api/audio/pause")
async def pause():
    """Hold the track. Resumes from the same place, not the same second."""
    async with _lock:
        await asyncio.to_thread(_player.pause)
    return await _announce()


@router.post("/api/audio/resume")
async def resume():
    async with _lock:
        await asyncio.to_thread(_player.resume)
    return await _announce()


@router.post("/api/audio/stop")
async def stop():
    async with _lock:
        await asyncio.to_thread(_player.stop)
    return await _announce()


@router.post("/api/audio/volume")
async def set_volume(body: VolumeRequest):
    """Change the level of the track already playing.

    Cheap and immediate, unlike the boost: this only scales the stream
    PipeWire is already feeding the jack, so it takes effect mid-song with
    no rebuild and no restart. Safe to send while a fader is being dragged.
    """
    async with _lock:
        try:
            applied = await asyncio.to_thread(_player.set_volume, body.volume)
        except audio.AudioError as exc:
            raise HTTPException(422, str(exc))
    return {"volume": body.volume, "applied": applied}


@router.post("/api/audio/seek")
async def seek(body: SeekRequest):
    """Jump to a position.

    This restarts the player process, so it is a real operation rather than
    a cursor move - the UI should send it on release, not while dragging.
    """
    async with _lock:
        try:
            result = await asyncio.to_thread(_player.seek, body.position)
        except audio.AudioError as exc:
            raise HTTPException(400, str(exc))
    await _broadcast({"type": "audio", **result})
    return result


# --- Downloads -------------------------------------------------------------

def _find_ytdlp():
    """Locate yt-dlp, venv first.

    It is a dependency in requirements.txt, so under a service it lives in
    the venv's bin directory - which is not on PATH, because systemd runs the
    interpreter by absolute path rather than activating anything. Looking
    only at PATH reports it missing on exactly the install where it is
    definitely present.
    """
    beside = Path(sys.executable).parent / "yt-dlp"
    if beside.is_file():
        return str(beside)
    return shutil.which("yt-dlp")


def _download(url, directory):
    """Fetch one video's audio into `directory` with yt-dlp.

    Audio only, re-encoded to mp3: the native format of a YouTube stream is
    usually opus in a webm container, which pw-play will not open. This
    trades a little quality for a file the rest of the module can treat
    exactly like a local one - which is the point, since a fetched track
    should still play with the wifi off.
    """
    ytdlp = _find_ytdlp()
    if ytdlp is None:
        raise audio.AudioError(
            "yt-dlp is not installed - run: pip install yt-dlp"
        )

    result = subprocess.run(
        [ytdlp,
         "--extract-audio", "--audio-format", "mp3", "--audio-quality", "0",
         # No playlists: one link should not quietly fetch four hours.
         "--no-playlist",
         # Keep the filename tame - it becomes a URL path segment later.
         "--restrict-filenames",
         "--output", str(Path(directory) / "%(title)s.%(ext)s"),
         "--print", "after_move:filepath",
         url],
        capture_output=True, text=True, timeout=900,
    )
    if result.returncode != 0:
        # yt-dlp's own message is far more useful than anything we could
        # write - it distinguishes a private video from a dead link from a
        # format problem.
        detail = result.stderr.strip().splitlines()
        raise audio.AudioError(detail[-1] if detail else "Download failed")

    path = result.stdout.strip().splitlines()
    if not path:
        raise audio.AudioError("Download reported no file")
    return Path(path[-1])


@router.post("/api/audio/fetch")
async def fetch(body: FetchRequest):
    """Download a YouTube link into the library.

    Held open for the length of the download rather than returning a job
    id: a backing track is a few megabytes and the browser can wait. If
    this ever grows a progress bar, that is the point to make it a task and
    push percentages over the WebSocket - the client set is already here.
    """
    global _fetching

    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(422, "That does not look like a link")
    if _fetching is not None:
        raise HTTPException(409, f"Already fetching {_fetching}")

    TRACK_DIR.mkdir(exist_ok=True)
    _fetching = url
    await _broadcast({"type": "fetch", "state": "started", "url": url})
    try:
        path = await asyncio.to_thread(_download, url, TRACK_DIR)
    except audio.AudioError as exc:
        await _broadcast({"type": "fetch", "state": "failed", "url": url, "detail": str(exc)})
        raise HTTPException(400, str(exc))
    except subprocess.TimeoutExpired:
        await _broadcast({"type": "fetch", "state": "failed", "url": url, "detail": "timed out"})
        raise HTTPException(504, "The download took too long and was stopped")
    finally:
        _fetching = None

    track = {
        "name": path.stem,
        "file": path.name,
        "duration": await asyncio.to_thread(audio.duration, path),
        "size": path.stat().st_size,
        "added": path.stat().st_mtime,
    }
    await _broadcast({"type": "fetch", "state": "done", "url": url, "track": track})
    return track


# --- Lifecycle -------------------------------------------------------------

@contextlib.asynccontextmanager
async def lifespan(app):
    """Make sure a track does not outlive the server.

    pw-play is a child process: without this, killing the server on a Pi
    leaves a backing track playing into the amp with nothing left to stop
    it.
    """
    TRACK_DIR.mkdir(exist_ok=True)
    try:
        yield
    finally:
        await asyncio.to_thread(_player.stop)

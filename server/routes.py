"""The HTTP endpoints: one-off actions and reads.

Live changes - knobs, channel switches - go over the WebSocket instead
(websocket.py). Everything here goes through the shared amp link in amp.py.
"""

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from capture import RecorderError
from katana_amp import katana
from katana_amp import tsl
from katana_amp.katana import CHANNELS, Katana, KatanaError
from katana_amp.param import Param
from playback import TrackError
from playback.library import check_name
from server import amp, audio, browsers, recorder

# Tone Studio patch files live here, next to the project root.
ROOT = Path(__file__).resolve().parent.parent
PATCH_DIR = ROOT / "patches"
MAX_UPLOAD = 200 * 1024 * 1024   # bytes; a long WAV is ~100 MB

router = APIRouter()

SCHEMA = Param.schema()


class Value(BaseModel):
    value: int


# --- Schema and state ------------------------------------------------------

@router.get("/api/parameters")
async def parameters():
    return SCHEMA


@router.get("/api/status")
async def status():
    return {
        "connected": amp.is_online(),
        "port": katana.is_connected(),
        "parameters": len(amp.cache),
    }


@router.post("/api/refresh")
async def refresh():
    async with amp.lock:
        values = await amp.call(amp.refresh, read=True)
    await browsers.broadcast(amp.state_message())
    return values


# --- Channels and stored patches -------------------------------------------

@router.get("/api/channels")
async def channels():
    """The selectable channels, and the names of the stored patches."""
    async with amp.lock:
        try:
            names = await amp.call(Katana.read_patch_names, read=True)
        except KatanaError as exc:
            raise HTTPException(503, str(exc))
    return {"channels": CHANNELS, "patches": names}


@router.post("/api/patch/{number}")
async def save_patch(number: int):
    """Copy the live sound into stored channel 1-9. Overwrites it permanently."""
    if not 1 <= number <= 9:
        raise HTTPException(422, "Patch number must be 1-9")
    async with amp.lock:
        try:
            written = await amp.call(Katana.copy_live_to_patch, number)
            names = await amp.call(Katana.read_patch_names, read=True)
        except KatanaError as exc:
            raise HTTPException(503, str(exc))
    await browsers.broadcast({"type": "patches", "names": names})
    return {"patch": number, "bytes": written, "names": names}


# --- Backing tracks and metronome ------------------------------------------

@router.get("/api/tracks")
async def tracks():
    """The audio files in tracks/, newest first, and which are in memory."""
    return audio.tracks_message()["tracks"]


@router.put("/api/tracks/{filename}")
async def upload_track(filename: str, request: Request):
    """Add a song: the request body is the file itself.

    Answers once the song is decoded and in memory, so it plays instantly -
    and a file that turns out not to be audio is refused and removed.
    """
    try:
        check_name(filename)
    except TrackError as exc:
        raise HTTPException(422, str(exc))

    library = audio.library
    temporary = library.upload_path()
    size = 0
    try:
        with open(temporary, "wb") as file:
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_UPLOAD:
                    raise HTTPException(413, f"Songs can be at most {MAX_UPLOAD // 2**20} MB")
                file.write(chunk)
        if size == 0:
            raise HTTPException(422, "The file is empty")
        name, decoding = library.add(temporary, filename)
    finally:
        # Gone already if add() moved it in; otherwise an aborted upload.
        temporary.unlink(missing_ok=True)

    try:
        await asyncio.wrap_future(decoding)
    except TrackError as exc:
        library.remove(name)
        audio.log.warning("Upload %s refused: %s", filename, exc)
        raise HTTPException(422, f"{filename} is not a playable audio file")
    return {"name": name, "bytes": size}


@router.delete("/api/tracks/{filename}")
async def delete_track(filename: str):
    """Delete a song from tracks/. Stops it first if it is playing."""
    try:
        audio.remove(filename)
    except TrackError as exc:
        raise HTTPException(404, str(exc))
    return {"deleted": filename}


@router.get("/api/playback")
async def playback():
    """What the metronome and the track are doing right now."""
    return audio.state_message()


# --- Recordings --------------------------------------------------------------

@router.get("/api/recordings")
async def recordings():
    """The finished takes in recordings/, newest first."""
    return recorder.recordings_message()["recordings"]


@router.get("/api/recordings/{filename}")
async def recording(filename: str, download: bool = False):
    """A take's WAV: to play in the browser, or with ?download=1 to save."""
    try:
        path = recorder.existing(filename)
    except RecorderError as exc:
        raise HTTPException(404, str(exc))
    return FileResponse(path, media_type="audio/wav",
                        content_disposition_type="attachment" if download else "inline",
                        filename=filename)


@router.delete("/api/recordings/{filename}")
async def delete_recording(filename: str):
    """Delete a take."""
    try:
        recorder.remove(filename)
    except RecorderError as exc:
        raise HTTPException(404, str(exc))
    await browsers.broadcast(recorder.recordings_message())
    return {"deleted": filename}


# --- Footswitch messages ---------------------------------------------------

@router.post("/api/cc/{control}")
async def send_cc(control: int, body: Value):
    """Send a raw Control Change - the footswitch messages the amp documents."""
    if not 0 <= control <= 127:
        raise HTTPException(422, "CC number must be 0-127")
    if not 0 <= body.value <= 127:
        raise HTTPException(422, "CC value must be 0-127")
    async with amp.lock:
        try:
            await amp.call(Katana.send_control_change, control, body.value)
        except KatanaError as exc:
            raise HTTPException(503, str(exc))
    return {"cc": control, "value": body.value}


# --- Tone Studio patches ---------------------------------------------------

@router.get("/api/tsl")
async def list_tsl():
    """The .tsl files in patches/, and the patches inside them."""
    files = []
    for path in sorted(PATCH_DIR.glob("*.tsl")):
        try:
            patches = tsl.load(str(path))
        except Exception as exc:
            files.append({"file": path.name, "error": str(exc)})
            continue
        # A preview of each patch, so the browser can show what a tone is
        # before loading it. Cheap - the file is already parsed.
        preview = (
            Param.AMP_TYPE, Param.GAIN, Param.VOLUME, Param.BASS, Param.MIDDLE,
            Param.TREBLE, Param.PRESENCE, Param.BOOST_SWITCH, Param.BOOST_TYPE,
            Param.BOOST_DRIVE, Param.DELAY_SWITCH, Param.DELAY_TYPE,
            Param.DELAY_TIME, Param.REVERB_SWITCH, Param.REVERB_TYPE,
            Param.REVERB_LEVEL, Param.FX1_SWITCH, Param.FX1_TYPE,
            Param.FX2_SWITCH, Param.FX2_TYPE, Param.NOISE_SUPPRESSOR_SWITCH,
        )
        entries = []
        for index, patch in enumerate(patches):
            settings = patch.settings()
            entry = {
                "index": index,
                "name": patch.name,
                "settings": {param.value: settings[param] for param in preview if param in settings},
            }
            bands = Param.eq_bands()
            eq = [settings[band] for band in bands if band in settings]
            if len(eq) == len(bands):
                entry["eq"] = eq
            entries.append(entry)

        files.append({"file": path.name, "patches": entries})
    return files


@router.post("/api/tsl/{filename}/{index}")
async def load_tsl(filename: str, index: int):
    """Load one patch out of a .tsl file into the amp."""
    path = PATCH_DIR / filename
    # Keep the caller inside patches/ - no traversal out of it.
    if path.parent.resolve() != PATCH_DIR.resolve() or not path.exists():
        raise HTTPException(404, f"No such file {filename!r}")

    try:
        patches = tsl.load(str(path))
    except Exception as exc:
        raise HTTPException(400, str(exc))
    if not 0 <= index < len(patches):
        raise HTTPException(404, f"{filename} has no patch {index}")

    async with amp.lock:
        try:
            applied, skipped = await amp.call(patches[index].apply)
            values = await amp.call(amp.refresh, read=True)
        except KatanaError as exc:
            raise HTTPException(503, str(exc))
    await browsers.broadcast(
        {"type": "patch", "name": patches[index].name, "values": values}
    )
    return {"name": patches[index].name, "applied": applied, "skipped": skipped}

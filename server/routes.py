"""The HTTP endpoints: one-off actions and reads.

Live changes - knobs, channel switches - go over the WebSocket instead
(websocket.py). Everything here goes through the shared amp link in amp.py.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from katana_amp import katana
from katana_amp import tsl
from katana_amp.katana import CHANNELS, Katana, KatanaError
from katana_amp.param import Param
from server import amp, browsers

# Tone Studio patch files live here, next to the project root.
ROOT = Path(__file__).resolve().parent.parent
PATCH_DIR = ROOT / "patches"

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

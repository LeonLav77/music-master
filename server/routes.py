"""The HTTP endpoints: one-off actions and reads.

Live changes - knobs, channel switches - go over the WebSocket instead
(live.py). Everything here goes through the shared amp link in amp.py.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from katana_amp import controls
from katana_amp import tsl
from katana_amp.katana import CHANNELS, KatanaError
from katana_amp.params import EQ_BANDS, Param, describe_parameters
from server import amp

# Tone Studio patch files live here, next to the project root.
ROOT = Path(__file__).resolve().parent.parent
PATCH_DIR = ROOT / "patches"

router = APIRouter()

SCHEMA = describe_parameters()


class Value(BaseModel):
    value: int


class Sweep(BaseModel):
    start: int = Field(0, ge=0, le=100)
    end: int = Field(100, ge=0, le=100)
    steps: int = Field(25, ge=2, le=200)
    # Bounded, like rock's total: the lock is held for the whole sweep.
    delay: float = Field(0.04, ge=0, le=0.5)


class Rock(BaseModel):
    """A repeating wah gesture: `intervals` sweeps, `seconds` each."""

    intervals: int = 4
    low: int = 0
    high: int = 50
    seconds: float = 2.3
    bounce: bool = True


# --- Schema and state ------------------------------------------------------

@router.get("/api/parameters")
async def parameters():
    """Every parameter with its range, kind and options. Build a UI from this."""
    return SCHEMA


@router.get("/api/status")
async def status():
    return {
        "connected": amp.is_online(),
        "port": controls.is_connected(),
        "parameters": len(amp.cache),
    }


@router.post("/api/refresh")
async def refresh():
    async with amp.lock:
        values = await amp.call(amp.refresh, read=True)
    await amp.broadcast(amp.state_message())
    return values


# --- Channels and stored patches -------------------------------------------

@router.get("/api/channels")
async def channels():
    """The selectable channels, and the names of the stored patches."""
    async with amp.lock:
        try:
            names = await amp.call(controls.get_patch_names, read=True)
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
            written = await amp.call(controls.save_to_patch, number)
            names = await amp.call(controls.get_patch_names, read=True)
        except KatanaError as exc:
            raise HTTPException(503, str(exc))
    await amp.broadcast({"type": "patches", "names": names})
    return {"patch": number, "bytes": written, "names": names}


# --- Wah gestures ----------------------------------------------------------

async def _wah_moved(position):
    """After a server-side wah gesture: the pedal is on, at `position`."""
    amp.cache["wah_position"] = position
    amp.cache["pedal_switch"] = 1
    await amp.broadcast({"type": "parameter", "name": "wah_position", "value": position})
    await amp.broadcast({"type": "parameter", "name": "pedal_switch", "value": 1})


@router.post("/api/wah/rock")
async def wah_rock(body: Rock = Rock()):
    """Rock the treadle repeatedly - "4 intervals of 0 to 50 in 2.3 seconds".

    Driven server-side for the whole gesture, like /api/wah/sweep: this is
    hundreds of MIDI writes and stepping it from the browser would mean an
    HTTP round-trip each.

    The lock is held for the duration, so a long gesture blocks other amp
    writes until it finishes. That is deliberate - interleaving another
    parameter change mid-sweep is how the amp ends up in a state neither
    side expects.
    """
    if not 1 <= body.intervals <= 32:
        raise HTTPException(422, "intervals must be 1-32")
    if not 0 <= body.low <= 100 or not 0 <= body.high <= 100:
        raise HTTPException(422, "low and high must be 0-100")
    if body.low == body.high:
        raise HTTPException(422, "low and high must differ")
    # An upper bound on total time: the lock is held throughout, and a
    # mistyped 600 would wedge the amp for ten minutes.
    if not 0.05 <= body.seconds <= 30:
        raise HTTPException(422, "seconds must be 0.05-30")
    if body.intervals * body.seconds > 120:
        raise HTTPException(422, "total gesture must be under 120 s")

    async with amp.lock:
        try:
            final = await amp.call(
                controls.rock_wah,
                body.intervals, body.low, body.high, body.seconds, body.bounce,
            )
        except KatanaError as exc:
            raise HTTPException(503, str(exc))

    await _wah_moved(final)
    return {"position": final, "intervals": body.intervals,
            "seconds": body.seconds, "total": round(body.intervals * body.seconds, 2)}


@router.post("/api/wah/sweep")
async def wah_sweep(body: Sweep = Sweep()):
    """Sweep the wah treadle. One request - the amp is driven server-side.

    Animating this from the browser would mean one HTTP round-trip per
    step for a single MIDI byte, which floods both the port and the log.
    """
    async with amp.lock:
        try:
            final = await amp.call(
                controls.sweep_wah, body.start, body.end, body.steps, body.delay
            )
        except KatanaError as exc:
            raise HTTPException(503, str(exc))

    await _wah_moved(final)
    return {"position": final}


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
            await amp.call(controls.send_cc, control, body.value)
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
                "settings": {p.value: settings[p] for p in preview if p in settings},
            }
            eq = [settings[p] for p in EQ_BANDS if p in settings]
            if len(eq) == len(EQ_BANDS):
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
    await amp.broadcast(
        {"type": "patch", "name": patches[index].name, "values": values}
    )
    return {"name": patches[index].name, "applied": applied, "skipped": skipped}

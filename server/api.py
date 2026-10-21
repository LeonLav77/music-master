import asyncio
import contextlib
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from katana_amp import controls
from katana_amp import tsl
from katana_amp.katana import CHANNELS, KatanaError
from katana_amp.params import EQ_BANDS, Param, describe_parameters

# Tone Studio patch files live here, next to the project root.
ROOT = Path(__file__).resolve().parent.parent
PATCH_DIR = ROOT / "patches"

router = APIRouter()

SCHEMA = describe_parameters()

_lock = asyncio.Lock()
_cache = {}
_clients = set()
_amp_online = False
_reconnect = asyncio.Event()
RECONNECT_INTERVAL = 2.0


class Value(BaseModel):
    value: int


async def _broadcast(message, skip=None):
    if not _clients:
        return
    payload = json.dumps(message)
    for client in list(_clients):
        if client is skip:
            continue
        try:
            await client.send_text(payload)
        except Exception:
            _clients.discard(client)


async def _amp_call(fn, *args, read=False):
    """Run a blocking amp call in a thread. A failure means the amp is gone.

    Only a read proves the amp is there: writes get no answer, so they
    succeed even with the amp switched off. Pass read=True for those.
    """
    try:
        result = await asyncio.to_thread(fn, *args)
    except KatanaError:
        controls.disconnect()
        _reconnect.set()
        await _set_online(False)
        raise
    if read:
        await _set_online(True)
    return result


async def _set_online(online):
    """Record whether the amp is answering, and tell clients when it flips.

    Only changes are broadcast, not every call that confirms the same state.
    """
    global _amp_online
    if _amp_online == online:
        return
    _amp_online = online
    await _broadcast({"type": "amp", "connected": online})


def _probe():
    """Open the port if needed and prove the amp is really there.

    A port opens fine when the amp is switched off, so opening is not
    enough. One read of a parameter the amp always answers for is the
    cheapest thing that actually settles it.
    """
    amp = controls.connect()
    amp.read(amp._encode_address(Param.GAIN.address()), 1, attempts=1)


def _refresh():
    """Re-read everything the amp will answer for, into the cache.

    Reads contiguous runs in one query each rather than 154 separate ones -
    the amp answers a block as fast as a single byte, and a parameter it
    will not answer for costs a full timeout plus retries.
    """
    amp = controls.connect()

    # Group the single-byte settings into runs of consecutive addresses.
    singles = sorted((p for p in Param if p.size() == 1), key=lambda p: p.address())
    runs = []
    for param in singles:
        if runs and param.address() == runs[-1][0] + len(runs[-1][1]):
            runs[-1][1].append(param)
        else:
            runs.append((param.address(), [param]))

    found = {}
    for start, params in runs:
        try:
            # One attempt: a block the amp will not answer for is a normal
            # outcome here (effect blocks stay silent unless loaded), and
            # retrying every one of them dominates the refresh.
            data = amp.read(amp._encode_address(start), len(params), attempts=1)
        except KatanaError:
            continue
        for offset, param in enumerate(params):
            if offset < len(data):
                found[param.value] = param.decode([data[offset]])

    # The two-byte ones (delay times), each on its own.
    for param in Param:
        if param.size() == 2:
            try:
                found[param.value] = amp.get_parameter(param)
            except KatanaError:
                continue

    # Individual blocks going silent is normal - effect blocks stay quiet
    # until they are loaded. Every single block going silent is not: that is
    # an amp that has been switched off or unplugged, and the cache must not
    # be wiped to empty on the strength of it.
    if not found:
        raise KatanaError("The amp stopped answering")

    _cache.clear()
    _cache.update(found)
    return found


# --- Schema and state ------------------------------------------------------

@router.get("/api/parameters")
async def parameters():
    """Every parameter with its range, kind and options. Build a UI from this."""
    return SCHEMA


@router.get("/api/status")
async def status():
    """Is the amp there? Cheap enough for a health check to hit repeatedly.

    Answers from the last known state rather than touching the port, so it
    stays fast and never contends with a slider for the lock.
    """
    return {
        "connected": _amp_online,
        "port": controls.is_connected(),
        "parameters": len(_cache),
    }


@router.post("/api/refresh")
async def refresh():
    """Re-read the amp into the cache. Use after someone turns a knob."""
    async with _lock:
        values = await _amp_call(_refresh, read=True)
    await _broadcast({"type": "state", "values": values})
    return values


# --- Parameters ------------------------------------------------------------

async def _apply_parameter(name, value, origin=None):
    """Validate and write one parameter, then tell everyone else.

    `name` arrives from the browser as a string, e.g. "gain".
    """
    try:
        param = Param(name)               # like Laravel's Param::from("gain")
    except ValueError:
        raise KatanaError(f"Unknown parameter {name!r}")
    if not param.is_writable():
        raise KatanaError(f"{name} is read-only on this amp")
    low, high = param.range()
    if not low <= value <= high:
        raise KatanaError(f"{name} must be between {low} and {high}")

    async with _lock:
        await _amp_call(controls.set_parameter, param, value)

    _cache[name] = value
    await _broadcast(
        {"type": "parameter", "name": name, "value": value}, skip=origin
    )
    return value


# --- Channels --------------------------------------------------------------

@router.get("/api/channels")
async def channels():
    """The selectable channels, and the names of the stored patches."""
    async with _lock:
        try:
            names = await _amp_call(controls.get_patch_names, read=True)
        except KatanaError as exc:
            raise HTTPException(503, str(exc))
    return {"channels": CHANNELS, "patches": names}


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


async def _wah_moved(position):
    """After a server-side wah gesture: the pedal is on, at `position`."""
    _cache["wah_position"] = position
    _cache["pedal_switch"] = 1
    await _broadcast({"type": "parameter", "name": "wah_position", "value": position})
    await _broadcast({"type": "parameter", "name": "pedal_switch", "value": 1})


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

    async with _lock:
        try:
            final = await _amp_call(
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
    async with _lock:
        try:
            final = await _amp_call(
                controls.sweep_wah, body.start, body.end, body.steps, body.delay
            )
        except KatanaError as exc:
            raise HTTPException(503, str(exc))

    await _wah_moved(final)
    return {"position": final}


async def _select_channel(name, origin=None):
    """Switch channel and re-read."""
    if not isinstance(name, str) or name.lower() not in CHANNELS:
        raise KatanaError(f"Unknown channel {name!r}")

    async with _lock:
        # Re-selecting the channel the amp is already on does nothing,
        # so bounce via another one to force a reload from memory.
        other = "a2" if name.lower() != "a2" else "a1"
        await _amp_call(controls.select_channel, other)
        await asyncio.sleep(0.5)
        await _amp_call(controls.select_channel, name)
        await asyncio.sleep(1.2)
        values = await _amp_call(_refresh, read=True)

    # Everyone needs this, including whoever asked - it is a whole new state.
    await _broadcast({"type": "channel", "channel": name, "values": values})
    return values


@router.post("/api/patch/{number}")
async def save_patch(number: int):
    """Copy the live sound into stored channel 1-9. Overwrites it permanently."""
    if not 1 <= number <= 9:
        raise HTTPException(422, "Patch number must be 1-9")
    async with _lock:
        try:
            written = await _amp_call(controls.save_to_patch, number)
            names = await _amp_call(controls.get_patch_names, read=True)
        except KatanaError as exc:
            raise HTTPException(503, str(exc))
    await _broadcast({"type": "patches", "names": names})
    return {"patch": number, "bytes": written, "names": names}


@router.post("/api/cc/{control}")
async def send_cc(control: int, body: Value):
    """Send a raw Control Change - the footswitch messages the amp documents."""
    if not 0 <= control <= 127:
        raise HTTPException(422, "CC number must be 0-127")
    if not 0 <= body.value <= 127:
        raise HTTPException(422, "CC value must be 0-127")
    async with _lock:
        try:
            await _amp_call(controls.send_cc, control, body.value)
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

    async with _lock:
        try:
            applied, skipped = await _amp_call(patches[index].apply)
            values = await _amp_call(_refresh, read=True)
        except KatanaError as exc:
            raise HTTPException(503, str(exc))
    await _broadcast(
        {"type": "patch", "name": patches[index].name, "values": values}
    )
    return {"name": patches[index].name, "applied": applied, "skipped": skipped}


# --- Live updates ----------------------------------------------------------

@router.websocket("/ws")
async def websocket(client: WebSocket):
    """The live connection: every change to the amp goes through here.

    Sends on connect, then whenever something changes:
      {"type": "amp",       "connected": true}
      {"type": "state",     "values": {...}}
      {"type": "parameter", "name": "gain", "value": 75}
      {"type": "channel",   "channel": "a1", "values": {...}}
      {"type": "patch",     "name": "...", "values": {...}}
      {"type": "patches",   "names": {"1": "...", ...}}
      {"type": "error",     "detail": "..."}

    Accepts:
      {"type": "set",     "name": "gain", "value": 75}
      {"type": "channel", "name": "b2"}
    """
    await client.accept()
    _clients.add(client)
    try:
        if not _cache:
            async with _lock:
                # No amp yet is not a reason to refuse the socket: the
                # reconnect loop will push the state the moment it appears,
                # and a client that stays connected sees that happen.
                with contextlib.suppress(KatanaError):
                    await _amp_call(_refresh, read=True)
        await client.send_text(
            json.dumps({"type": "amp", "connected": _amp_online})
        )
        await client.send_text(json.dumps({"type": "state", "values": _cache}))

        while True:
            raw = await client.receive_text()
            try:
                message = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(message, dict):
                continue

            kind = message.get("type")

            if kind == "channel":
                try:
                    await _select_channel(message["name"], origin=client)
                except (KatanaError, KeyError) as exc:
                    await client.send_text(
                        json.dumps({"type": "error", "detail": str(exc)})
                    )
                continue

            if kind == "set":
                try:
                    await _apply_parameter(
                        message["name"], int(message["value"]), origin=client
                    )
                except (KatanaError, KeyError, TypeError, ValueError) as exc:
                    await client.send_text(
                        json.dumps({"type": "error", "detail": str(exc)})
                    )
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(client)


async def _reconnect_loop():
    """Keep trying to reach the amp whenever it is not answering.

    This is what makes the server survive being switched on before the amp,
    and the amp being power-cycled underneath it. It idles on the event
    while the amp is fine, so a healthy server does no polling at all.
    """
    while True:
        await _reconnect.wait()

        names = None
        try:
            async with _lock:
                await _amp_call(_probe, read=True)
                # It may have come back on a different channel: re-read it.
                values = await _amp_call(_refresh, read=True)
                # And the patch names, which a page that loaded while the
                # amp was missing never got.
                with contextlib.suppress(KatanaError):
                    names = await _amp_call(controls.get_patch_names, read=True)
        except Exception:
            # Not there yet - or something unexpected, which must not kill
            # the loop either. (A shutdown's CancelledError is not an
            # Exception, so it still stops the loop.)
            await asyncio.sleep(RECONNECT_INTERVAL)
            continue

        _reconnect.clear()
        await _broadcast({"type": "state", "values": values})
        if names:
            await _broadcast({"type": "patches", "names": names})


@contextlib.asynccontextmanager
async def lifespan(app):
    """Run the reconnect loop for as long as the server is up.

    A missing amp at boot is the normal case on a Pi that powers up with the
    rig, so it is the loop's problem rather than a startup failure.
    """
    _reconnect.set()
    task = asyncio.create_task(_reconnect_loop())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        controls.disconnect()

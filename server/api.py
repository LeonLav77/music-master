"""HTTP + WebSocket API for the Katana.

This module is the amp and nothing else: it owns the MIDI port, the cache
and the reconnect loop, and exposes them as a router. It does not know
whether a UI is being served alongside it, which is what keeps it usable on
its own - a footswitch script, curl, or a headless Pi.

Mount it with `server.app`, or on your own FastAPI:

    app.include_router(api.router)
    app.router.lifespan_context = api.lifespan

The amp is a single serial device, so every access goes through one lock
and reads are served from a cache. State changes are pushed to WebSocket
clients so a UI can follow the amp instead of polling it.
"""

import asyncio
import contextlib
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from katana_amp import controls
from katana_amp import tsl
from katana_amp.katana import (
    CHANNELS,
    EQ_BANDS_ORDER,
    PARAMETERS,
    WIDE_PARAMETERS,
    KatanaError,
    describe_parameters,
)

# Tone Studio patch files live here, next to the project root.
ROOT = Path(__file__).resolve().parent.parent
PATCH_DIR = ROOT / "patches"

router = APIRouter()

SCHEMA = describe_parameters()
SCHEMA_BY_NAME = {entry["name"]: entry for entry in SCHEMA}

# One MIDI port, one lock. Everything that touches the amp holds it.
_lock = asyncio.Lock()

# Last known value of every parameter, so reads do not hit the amp.
_cache = {}

# Connected WebSocket clients.
_clients = set()

# Whether the amp answered the last time we tried to talk to it. This is not
# the same as "a MIDI port is open": the port survives the amp being switched
# off, and writes to it succeed silently. Only a read proves the amp is there.
_amp_online = False

# Set while the reconnect loop should be probing. Cleared once the amp
# answers, set again the moment anything sees it fail.
_reconnect = asyncio.Event()

# How long between probes while the amp is missing. Fast enough that
# switching the amp back on feels immediate, slow enough that a Pi with no
# amp attached is not spinning on failed port opens.
RECONNECT_INTERVAL = 2.0


class Value(BaseModel):
    value: int


async def broadcast(message):
    """Send a message to every connected client.

    The public form of `_broadcast`, for other routers mounted alongside
    this one: `server.audio` pushes transport state through here rather
    than opening a second WebSocket. Nothing in this module calls it, and
    this module still knows nothing about what the messages mean.
    """
    await _broadcast(message)


async def _broadcast(message, skip=None):
    """Send to every connected client, dropping any that have gone.

    `skip` is the client that caused the change - it already moved its own
    control, and echoing back would fight the user mid-drag.
    """
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


def _to_display(name, value):
    """Convert a stored value to the units the API exposes."""
    entry = SCHEMA_BY_NAME.get(name)
    if entry and entry.get("unit") == "dB":
        return value - 24
    return value


def _to_stored(name, value):
    entry = SCHEMA_BY_NAME.get(name)
    if entry and entry.get("unit") == "dB":
        return value + 24
    return value


async def _amp_call(fn, *args):
    """Run a blocking amp operation, tracking what it says about the link.

    Every path to the amp goes through here so that connection state is a
    consequence of real traffic rather than something each handler has to
    remember to update. A failure drops the port and wakes the reconnect
    loop; the next call opens a fresh one.
    """
    try:
        result = await asyncio.to_thread(fn, *args)
    except KatanaError:
        controls.disconnect()
        _reconnect.set()
        await _set_online(False)
        raise
    await _set_online(True)
    return result


async def _set_online(online):
    """Record whether the amp is answering, and tell clients when it flips.

    Only edges are broadcast - a probe every two seconds must not turn into
    a message every two seconds.
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
    amp.read(amp._encode_address(PARAMETERS["gain"][0]), 1, attempts=1)


def _read(name):
    """Read one parameter straight from the amp."""
    amp = controls.connect()
    if name in WIDE_PARAMETERS:
        return amp.get_wide_parameter(name)
    return amp.get_parameter(name)


def _write(name, value):
    amp = controls.connect()
    if name in WIDE_PARAMETERS:
        amp.set_wide_parameter(name, value)
    else:
        amp.set_parameter(name, value)


def _refresh():
    """Re-read everything the amp will answer for, into the cache.

    Reads contiguous runs in one query each rather than 154 separate ones -
    the amp answers a block as fast as a single byte, and a parameter it
    will not answer for costs a full timeout plus retries.
    """
    amp = controls.connect()

    # Group the single-byte parameters into runs of consecutive addresses.
    singles = sorted(
        (address, name) for name, (address, _, _) in PARAMETERS.items()
    )
    runs = []
    for address, name in singles:
        if runs and address == runs[-1][0] + len(runs[-1][1]):
            runs[-1][1].append(name)
        else:
            runs.append((address, [name]))

    found = {}
    for start, names in runs:
        try:
            # One attempt: a block the amp will not answer for is a normal
            # outcome here (effect blocks stay silent unless loaded), and
            # retrying every one of them dominates the refresh.
            data = amp.read(amp._encode_address(start), len(names), attempts=1)
        except KatanaError:
            continue
        for offset, name in enumerate(names):
            if offset < len(data):
                found[name] = _to_display(name, data[offset])

    for name, (address, _, _) in WIDE_PARAMETERS.items():
        try:
            high, low = amp.read(amp._encode_address(address), 2, attempts=1)
            found[name] = high * 128 + low
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


@router.get("/api/state")
async def state():
    """Current value of everything, from cache.

    A cold cache with no amp is not an error - it is a rig that has not been
    switched on yet. Answer with what we have and let the caller see
    `connected` rather than failing the request; the reconnect loop is
    already working on it.
    """
    if not _cache:
        async with _lock:
            with contextlib.suppress(KatanaError):
                await _amp_call(_refresh)
    return _cache


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
        values = await _amp_call(_refresh)
    await _broadcast({"type": "state", "values": values})
    return values


# --- Parameters ------------------------------------------------------------

async def _apply_parameter(name, value, origin=None):
    """Validate and write one parameter, then tell everyone. Shared by REST
    and the WebSocket so both behave identically."""
    entry = SCHEMA_BY_NAME.get(name)
    if entry is None:
        raise KatanaError(f"Unknown parameter {name!r}")
    if not entry["writable"]:
        raise KatanaError(f"{name} is read-only on this amp")
    if not entry["min"] <= value <= entry["max"]:
        raise KatanaError(
            f"{name} must be between {entry['min']} and {entry['max']}"
        )

    async with _lock:
        await _amp_call(_write, name, _to_stored(name, value))

    _cache[name] = value
    await _broadcast(
        {"type": "parameter", "name": name, "value": value}, skip=origin
    )
    return value


@router.get("/api/parameter/{name}")
async def get_parameter(name: str):
    if name not in SCHEMA_BY_NAME:
        raise HTTPException(404, f"Unknown parameter {name!r}")
    async with _lock:
        try:
            value = _to_display(name, await _amp_call(_read, name))
        except KatanaError as exc:
            raise HTTPException(503, str(exc))
    _cache[name] = value
    return {"name": name, "value": value}


@router.put("/api/parameter/{name}")
async def set_parameter(name: str, body: Value):
    """Set one parameter. Fine for one-off changes; for a slider being
    dragged, send over the WebSocket instead - see /ws."""
    entry = SCHEMA_BY_NAME.get(name)
    if entry is None:
        raise HTTPException(404, f"Unknown parameter {name!r}")
    if not entry["writable"]:
        raise HTTPException(409, f"{name} is read-only on this amp")
    if not entry["min"] <= body.value <= entry["max"]:
        raise HTTPException(
            422, f"{name} must be between {entry['min']} and {entry['max']}"
        )
    try:
        await _apply_parameter(name, body.value)
    except KatanaError as exc:
        raise HTTPException(503, str(exc))
    return {"name": name, "value": body.value}


# --- Channels --------------------------------------------------------------

@router.get("/api/channels")
async def channels():
    """The selectable channels, and the names of the stored patches."""
    async with _lock:
        names = await _amp_call(controls.get_patch_names)
    return {"channels": CHANNELS, "patches": names}


class Sweep(BaseModel):
    start: int = 0
    end: int = 100
    steps: int = 25
    delay: float = 0.04


class Rock(BaseModel):
    """A repeating wah gesture: `intervals` sweeps, `seconds` each."""

    intervals: int = 4
    low: int = 0
    high: int = 50
    seconds: float = 2.3
    bounce: bool = True


@router.post("/api/wah/rock")
async def wah_rock(body: Rock = Rock()):
    """Rock the treadle repeatedly - "4 intervals of 0 to 50 in 2.3 seconds".

    Held server-side for the whole gesture, like /api/wah/sweep: this is
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
            await _amp_call(
                controls.rock_wah,
                body.intervals, body.low, body.high, body.seconds, body.bounce,
            )
            final = await _amp_call(_read, "wah_position")
        except KatanaError as exc:
            raise HTTPException(503, str(exc))

    _cache["wah_position"] = final
    _cache["pedal_switch"] = 1
    await _broadcast({"type": "parameter", "name": "wah_position", "value": final})
    await _broadcast({"type": "parameter", "name": "pedal_switch", "value": 1})
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
            await _amp_call(
                controls.sweep_wah, body.start, body.end, body.steps, body.delay
            )
            final = await _amp_call(_read, "wah_position")
        except KatanaError as exc:
            raise HTTPException(503, str(exc))

    _cache["wah_position"] = final
    _cache["pedal_switch"] = 1
    await _broadcast({"type": "parameter", "name": "wah_position", "value": final})
    await _broadcast({"type": "parameter", "name": "pedal_switch", "value": 1})
    return {"position": final}


async def _select_channel(name, origin=None):
    """Switch channel and re-read. Shared by REST and the WebSocket."""
    if name.lower() not in CHANNELS:
        raise KatanaError(f"Unknown channel {name!r}")

    async with _lock:
        # Re-selecting the channel the amp is already on does nothing,
        # so bounce via another one to force a reload from memory.
        other = "a2" if name.lower() != "a2" else "a1"
        await _amp_call(controls.select_channel, other)
        await asyncio.sleep(0.5)
        await _amp_call(controls.select_channel, name)
        await asyncio.sleep(1.2)
        values = await _amp_call(_refresh)

    # Everyone needs this, including whoever asked - it is a whole new state.
    await _broadcast({"type": "channel", "channel": name, "values": values})
    return values


@router.post("/api/channel/{name}")
async def select_channel(name: str):
    try:
        values = await _select_channel(name)
    except KatanaError as exc:
        raise HTTPException(404 if "Unknown channel" in str(exc) else 503, str(exc))
    return {"channel": name, "values": values}


@router.post("/api/patch/{number}")
async def save_patch(number: int):
    """Copy the live sound into stored channel 1-9. Overwrites it permanently."""
    if not 1 <= number <= 9:
        raise HTTPException(422, "Patch number must be 1-9")
    async with _lock:
        try:
            written = await _amp_call(controls.save_to_patch, number)
            names = await _amp_call(controls.get_patch_names)
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
        preview_keys = (
            "amp_type", "gain", "volume", "bass", "middle", "treble",
            "presence", "boost_switch", "boost_type", "boost_drive",
            "delay_switch", "delay_type", "delay_time",
            "reverb_switch", "reverb_type", "reverb_level",
            "fx1_switch", "fx1_type", "fx2_switch", "fx2_type",
            "noise_suppressor_switch",
        )
        entries = []
        for index, patch in enumerate(patches):
            settings = patch.settings()
            entry = {
                "index": index,
                "name": patch.name,
                "settings": {
                    key: settings[key] for key in preview_keys if key in settings
                },
            }
            eq = [
                settings[key] - 24
                for key in EQ_BANDS_ORDER
                if key in settings
            ]
            if len(eq) == len(EQ_BANDS_ORDER):
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
        applied, skipped = await _amp_call(patches[index].apply)
        values = await _amp_call(_refresh)
    await _broadcast(
        {"type": "patch", "name": patches[index].name, "values": values}
    )
    return {"name": patches[index].name, "applied": applied, "skipped": skipped}


# --- Live updates ----------------------------------------------------------

@router.websocket("/ws")
async def websocket(client: WebSocket):
    """Push state changes as they happen.

    Sends the whole state on connect, then one message per change:
      {"type": "state",     "values": {...}}
      {"type": "parameter", "name": "gain", "value": 75}
      {"type": "channel",   "channel": "a1", "values": {...}}

    Accepts changes too, which is the right way to drive a slider - no
    per-message HTTP overhead, and nothing echoed back to the sender:
      {"type": "set", "name": "gain", "value": 75}
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
                    await _amp_call(_refresh)
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
                await _amp_call(_probe)
                # Reaching the amp says nothing about what changed while it
                # was away - it may have come back on a different channel.
                values = await _amp_call(_refresh)
                # The patch names too. A client that loaded while the amp
                # was missing got nothing from /api/channels - that endpoint
                # reads the amp directly and simply fails with none - and it
                # never asks again, so without this the rail keeps showing
                # the placeholder names from the schema for the whole
                # session. Which is exactly the case this loop exists for:
                # the Pi powered up before the amp.
                with contextlib.suppress(KatanaError):
                    names = await _amp_call(controls.get_patch_names)
        except KatanaError:
            await asyncio.sleep(RECONNECT_INTERVAL)
            continue
        except asyncio.CancelledError:
            raise
        except Exception:
            # An unexpected failure must not kill the loop - that would
            # leave the server permanently unable to find the amp again.
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

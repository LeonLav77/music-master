"""HTTP + WebSocket API for the Katana.

    ./run-server

Then http://localhost:8000 for the test page, or /docs for the
interactive API.

The amp is a single serial device, so every access goes through one lock
and reads are served from a cache. State changes are pushed to WebSocket
clients so a UI can follow the amp instead of polling it.
"""

import asyncio
import contextlib
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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

# The interface is a TanStack Start app, which builds to its own Node
# server rather than a static bundle - so this API does not serve it.
# Run the two side by side; the UI finds this one through VITE_API_URL.
WEB_DIR = ROOT / "interface" / ".output" / "public"

app = FastAPI(title="Katana MkII", version="1.0")

# The client is served from somewhere else during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SCHEMA = describe_parameters()
SCHEMA_BY_NAME = {entry["name"]: entry for entry in SCHEMA}

# One MIDI port, one lock. Everything that touches the amp holds it.
_lock = asyncio.Lock()

# Last known value of every parameter, so reads do not hit the amp.
_cache = {}

# Connected WebSocket clients.
_clients = set()


class Value(BaseModel):
    value: int


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

    _cache.clear()
    _cache.update(found)
    return found


# --- Schema and state ------------------------------------------------------

@app.get("/api/parameters")
async def parameters():
    """Every parameter with its range, kind and options. Build a UI from this."""
    return SCHEMA


@app.get("/api/state")
async def state():
    """Current value of everything, from cache."""
    if not _cache:
        async with _lock:
            await asyncio.to_thread(_refresh)
    return _cache


@app.post("/api/refresh")
async def refresh():
    """Re-read the amp into the cache. Use after someone turns a knob."""
    async with _lock:
        values = await asyncio.to_thread(_refresh)
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
        await asyncio.to_thread(_write, name, _to_stored(name, value))

    _cache[name] = value
    await _broadcast(
        {"type": "parameter", "name": name, "value": value}, skip=origin
    )
    return value


@app.get("/api/parameter/{name}")
async def get_parameter(name: str):
    if name not in SCHEMA_BY_NAME:
        raise HTTPException(404, f"Unknown parameter {name!r}")
    async with _lock:
        try:
            value = _to_display(name, await asyncio.to_thread(_read, name))
        except KatanaError as exc:
            raise HTTPException(503, str(exc))
    _cache[name] = value
    return {"name": name, "value": value}


@app.put("/api/parameter/{name}")
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

@app.get("/api/channels")
async def channels():
    """The selectable channels, and the names of the stored patches."""
    async with _lock:
        names = await asyncio.to_thread(controls.get_patch_names)
    return {"channels": CHANNELS, "patches": names}


class Sweep(BaseModel):
    start: int = 0
    end: int = 100
    steps: int = 25
    delay: float = 0.04


@app.post("/api/wah/sweep")
async def wah_sweep(body: Sweep = Sweep()):
    """Sweep the wah treadle. One request - the amp is driven server-side.

    Animating this from the browser would mean one HTTP round-trip per
    step for a single MIDI byte, which floods both the port and the log.
    """
    async with _lock:
        try:
            await asyncio.to_thread(
                controls.sweep_wah, body.start, body.end, body.steps, body.delay
            )
            final = await asyncio.to_thread(_read, "wah_position")
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
        await asyncio.to_thread(controls.select_channel, other)
        await asyncio.sleep(0.5)
        await asyncio.to_thread(controls.select_channel, name)
        await asyncio.sleep(1.2)
        values = await asyncio.to_thread(_refresh)

    # Everyone needs this, including whoever asked - it is a whole new state.
    await _broadcast({"type": "channel", "channel": name, "values": values})
    return values


@app.post("/api/channel/{name}")
async def select_channel(name: str):
    try:
        values = await _select_channel(name)
    except KatanaError as exc:
        raise HTTPException(404 if "Unknown channel" in str(exc) else 503, str(exc))
    return {"channel": name, "values": values}


@app.post("/api/patch/{number}")
async def save_patch(number: int):
    """Copy the live sound into stored channel 1-9. Overwrites it permanently."""
    if not 1 <= number <= 9:
        raise HTTPException(422, "Patch number must be 1-9")
    async with _lock:
        try:
            written = await asyncio.to_thread(controls.save_to_patch, number)
            names = await asyncio.to_thread(controls.get_patch_names)
        except KatanaError as exc:
            raise HTTPException(503, str(exc))
    await _broadcast({"type": "patches", "names": names})
    return {"patch": number, "bytes": written, "names": names}


@app.post("/api/cc/{control}")
async def send_cc(control: int, body: Value):
    """Send a raw Control Change - the footswitch messages the amp documents."""
    if not 0 <= control <= 127:
        raise HTTPException(422, "CC number must be 0-127")
    if not 0 <= body.value <= 127:
        raise HTTPException(422, "CC value must be 0-127")
    async with _lock:
        try:
            await asyncio.to_thread(controls.send_cc, control, body.value)
        except KatanaError as exc:
            raise HTTPException(503, str(exc))
    return {"cc": control, "value": body.value}


# --- Tone Studio patches ---------------------------------------------------

@app.get("/api/tsl")
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


@app.post("/api/tsl/{filename}/{index}")
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
        applied, skipped = await asyncio.to_thread(patches[index].apply)
        values = await asyncio.to_thread(_refresh)
    await _broadcast(
        {"type": "patch", "name": patches[index].name, "values": values}
    )
    return {"name": patches[index].name, "applied": applied, "skipped": skipped}


# --- Live updates ----------------------------------------------------------

@app.websocket("/ws")
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
                await asyncio.to_thread(_refresh)
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


@app.get("/")
async def index():
    """Where to find things. The interface runs as its own server."""
    return {
        "api": "/docs",
        "interface": "cd interface && bun run dev  (or bun run start after a build)",
        "note": "the UI reaches this server through VITE_API_URL",
    }


@app.on_event("startup")
async def startup():
    with contextlib.suppress(KatanaError):
        await asyncio.to_thread(_refresh)


if __name__ == "__main__":
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="Katana MkII control API.")
    # 0.0.0.0 so another machine on the network can reach it.
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)

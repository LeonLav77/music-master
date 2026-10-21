"""The WebSocket: the live connection every browser keeps open.

Knob changes and channel switches come in here; every change to the amp
goes back out to the other browsers. Everything goes through the shared
amp link in amp.py.
"""

import asyncio
import contextlib
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from katana_amp import controls
from katana_amp.katana import CHANNELS, KatanaError
from katana_amp.params import Param
from server import amp

router = APIRouter()


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

    async with amp.lock:
        await amp.call(controls.set_parameter, param, value)

    amp.cache[name] = value
    await amp.broadcast(
        {"type": "parameter", "name": name, "value": value}, skip=origin
    )
    return value


async def _select_channel(name, origin=None):
    """Switch channel and re-read."""
    if not isinstance(name, str) or name.lower() not in CHANNELS:
        raise KatanaError(f"Unknown channel {name!r}")

    async with amp.lock:
        # Re-selecting the channel the amp is already on does nothing,
        # so bounce via another one to force a reload from memory.
        other = "a2" if name.lower() != "a2" else "a1"
        await amp.call(controls.select_channel, other)
        await asyncio.sleep(0.5)
        await amp.call(controls.select_channel, name)
        await asyncio.sleep(1.2)
        values = await amp.call(amp.refresh, read=True)

    # Everyone needs this, including whoever asked - it is a whole new state.
    await amp.broadcast({"type": "channel", "channel": name, "values": values})
    return values


@router.websocket("/ws")
async def websocket(client: WebSocket):
    """The live connection: every change to the amp goes through here.

    Sends on connect, then whenever something changes:
      {"type": "amp",       "connected": true}
      {"type": "state",     "values": {...}, "channel": "b3"}
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
    amp.clients.add(client)
    try:
        if not amp.cache:
            async with amp.lock:
                # No amp yet is not a reason to refuse the socket: the
                # reconnect loop will push the state the moment it appears,
                # and a client that stays connected sees that happen.
                with contextlib.suppress(KatanaError):
                    await amp.call(amp.refresh, read=True)
        await client.send_text(
            json.dumps({"type": "amp", "connected": amp.is_online()})
        )
        await client.send_text(json.dumps(amp.state_message()))

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
        amp.clients.discard(client)

"""The WebSocket: the live connection every browser keeps open.

Knob changes and channel switches come in here; every change to the amp
goes back out to the other browsers. Everything goes through the shared
amp link in amp.py.
"""

import asyncio
import contextlib
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from katana_amp.katana import CHANNELS, Katana, KatanaError
from katana_amp.param import Param
from server import amp, browsers

router = APIRouter()


async def _apply_parameter(name, value, origin=None):
    try:
        param = Param(name)
    except ValueError:
        raise KatanaError(f"Unknown parameter {name!r}")
    if not param.is_writable():
        raise KatanaError(f"{name} is read-only on this amp")
    
    low, high = param.range()
    if not low <= value <= high:
        raise KatanaError(f"{name} must be between {low} and {high}")

    async with amp.lock:
        await amp.call(Katana.set_parameter, param, value)

    amp.cache[name] = value
    await browsers.broadcast(
        {"type": "parameter", "name": name, "value": value}, skip=origin
    )
    return value


async def _select_channel(name):
    """Switch channel and re-read."""
    if not isinstance(name, str) or name.lower() not in CHANNELS:
        raise KatanaError(f"Unknown channel {name!r}")
    name = name.lower()

    async with amp.lock:
        current = await amp.call(Katana.read_channel, read=True)
        if current == name:
            detour = "a2" if name != "a2" else "a1"
            await amp.call(Katana.select_channel, detour)
            await asyncio.sleep(0.5)

        await amp.call(Katana.select_channel, name)
        await asyncio.sleep(1.2)
        values = await amp.call(amp.refresh, read=True)

    # Everyone needs this, including whoever asked - it is a whole new state.
    await browsers.broadcast({"type": "channel", "channel": name, "values": values})
    return values


@router.websocket("/ws")
async def websocket(client: WebSocket):
    await client.accept()
    browsers.connected.add(client)

    try:
        if not amp.cache:
            async with amp.lock:
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

            message_type = message.get("type")

            if message_type == "channel":
                try:
                    await _select_channel(message["name"])
                except (KatanaError, KeyError) as exc:
                    await client.send_text(
                        json.dumps({"type": "error", "detail": str(exc)})
                    )
                continue

            if message_type == "set":
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
        browsers.connected.discard(client)

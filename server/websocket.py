"""The WebSocket: the live connection every browser keeps open.

Knob changes and channel switches come in here; every change to the amp
goes back out to the other browsers. Everything goes through the shared
amp link in amp.py.
"""

import asyncio
import contextlib
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from katana_amp.katana import CHANNELS, PANEL_BUTTONS, Katana, KatanaError
from katana_amp.param import Param
from capture import RecorderError
from playback import PlaybackError, TrackError
from server import amp, audio, browsers, recorder, tuner, wifi

router = APIRouter()

# Which delay time each TAP sets, and how long after the last tap to read
# it back - the amp only knows the tempo once you stop tapping.
TAPS = {"delay_tap": Param.DELAY_TIME, "delay2_tap": Param.DELAY2_TIME}
TAP_SETTLE = 1.5
_tap_readback = None


async def _refresh_everyone():
    """Re-read the whole amp and send it to every browser. For changes that
    move many settings at once (a colour switch loads another effect)."""
    await asyncio.sleep(0.3)
    values = await amp.call(amp.refresh, read=True)
    await browsers.broadcast(amp.state_message())
    return values


async def _read_tap(param):
    """After the taps stop, read the delay time they set."""
    await asyncio.sleep(TAP_SETTLE)
    try:
        async with amp.lock:
            value = await amp.call(Katana.get_parameter, param, read=True)
    except KatanaError:
        return  # the amp went away; the reconnect loop re-reads everything
    amp.cache[param.value] = value
    await browsers.broadcast({"type": "parameter", "name": param.value, "value": value})


async def _press(button):
    global _tap_readback
    if button not in PANEL_BUTTONS:
        raise KatanaError(f"Unknown button {button!r}")
    if button in TAPS:
        # No re-read between taps: it would hold the line and spoil the
        # timing. Each tap restarts the countdown to one read at the end.
        async with amp.lock:
            await amp.call(Katana.press, button)
        if _tap_readback is not None:
            _tap_readback.cancel()
        _tap_readback = asyncio.create_task(_read_tap(TAPS[button]))
        return
    async with amp.lock:
        await amp.call(Katana.press, button)
        await _refresh_everyone()


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
        if name.startswith("color_select_"):
            # Switching colour loads that colour's effect and its settings,
            # so everything in the block has just changed.
            await _refresh_everyone()
            return value

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
        await client.send_text(json.dumps(audio.state_message()))
        await client.send_text(json.dumps(audio.tracks_message()))
        await client.send_text(json.dumps(tuner.state_message()))
        await client.send_text(json.dumps(recorder.state_message()))
        await client.send_text(json.dumps(recorder.recordings_message()))
        await client.send_text(json.dumps(wifi.state_message()))

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

            if message_type in ("metronome", "track"):
                try:
                    await audio.handle(message)
                except (PlaybackError, TrackError, KeyError, TypeError, ValueError) as exc:
                    await client.send_text(
                        json.dumps({"type": "error", "detail": str(exc)})
                    )
                continue

            if message_type == "recorder":
                try:
                    await recorder.handle(message)
                except (RecorderError, KeyError, ValueError) as exc:
                    await client.send_text(
                        json.dumps({"type": "error", "detail": str(exc)})
                    )
                continue

            if message_type == "press":
                try:
                    await _press(message["button"])
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

import asyncio
import contextlib

from katana_amp import controls
from katana_amp.katana import KatanaError
from katana_amp.param import Param
from server import browsers

lock = asyncio.Lock()
cache = {}
_online = False
_channel = None
_reconnect = asyncio.Event()
RECONNECT_INTERVAL = 2.0


def is_online():
    return _online


def current_channel():
    return _channel


def state_message():
    return {"type": "state", "values": cache, "channel": _channel}


async def call(fn, *args, read=False):
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
    global _online

    if _online == online:
        return
    _online = online
    await browsers.broadcast({"type": "amp", "connected": online})


def probe():
    amp = controls.connect()
    amp.read(amp._encode_address(Param.GAIN.address()), 1, attempts=1)


def refresh():
    amp = controls.connect()

    # Group the single-byte settings into runs of consecutive addresses.
    singles = sorted(
        (param for param in Param if param.size() == 1),
        key=lambda param: param.address(),
    )
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

    if not found:
        raise KatanaError("The amp stopped answering")

    cache.clear()
    cache.update(found)

    global _channel
    with contextlib.suppress(KatanaError):
        _channel = amp.read_channel()
    return found


async def _reconnect_loop():
    while True:
        await _reconnect.wait()

        names = None
        try:
            async with lock:
                await call(probe, read=True)
                values = await call(refresh, read=True)
                with contextlib.suppress(KatanaError):
                    names = await call(controls.get_patch_names, read=True)
        except Exception:
            await asyncio.sleep(RECONNECT_INTERVAL)
            continue

        _reconnect.clear()
        await browsers.broadcast(state_message())
        if names:
            await browsers.broadcast({"type": "patches", "names": names})


@contextlib.asynccontextmanager
async def lifespan(app):
    _reconnect.set()
    task = asyncio.create_task(_reconnect_loop())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        controls.disconnect()

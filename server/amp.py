"""The server's link to the amp, and to the browsers watching it.

Everything the routes share lives here: the lock that keeps one
conversation with the amp at a time, the cache of its last known values,
the connected browsers, and the loop that finds the amp again when it goes
away. The HTTP routes (routes.py) and the WebSocket (live.py) both use
this; it uses neither.
"""

import asyncio
import contextlib
import json

from katana_amp import controls
from katana_amp.katana import KatanaError
from katana_amp.params import Param

# One MIDI port, one conversation at a time. Everything that touches the
# amp holds this.
lock = asyncio.Lock()

# Last known value of every setting, so a page that connects gets the state
# without the amp being asked.
cache = {}

# The browsers connected over the WebSocket.
clients = set()

# Whether the amp answered the last time we tried. Read it with is_online():
# a `from server.amp import _online` would copy the value once and never see
# it change.
_online = False

# The channel the amp was on at the last refresh ("b3"), or None if unknown.
# Read it with current_channel(), for the same reason as is_online().
_channel = None

# Set while the reconnect loop should be trying to reach the amp.
_reconnect = asyncio.Event()
RECONNECT_INTERVAL = 2.0


def is_online():
    """True if the amp answered the last time it was asked."""
    return _online


def current_channel():
    """The channel the amp was on at the last refresh, or None."""
    return _channel


def state_message():
    """The full state for the browsers: every value, and the channel."""
    return {"type": "state", "values": cache, "channel": _channel}


async def broadcast(message, skip=None):
    """Send a message to every connected browser except `skip`, dropping
    any that have gone away."""
    if not clients:
        return
    payload = json.dumps(message)
    for client in list(clients):
        if client is skip:
            continue
        try:
            await client.send_text(payload)
        except Exception:
            clients.discard(client)


async def call(fn, *args, read=False):
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
    global _online
    if _online == online:
        return
    _online = online
    await broadcast({"type": "amp", "connected": online})


def probe():
    """Open the port if needed and prove the amp is really there.

    A port opens fine when the amp is switched off, so opening is not
    enough. One read of a parameter the amp always answers for is the
    cheapest thing that actually settles it.
    """
    amp = controls.connect()
    amp.read(amp._encode_address(Param.GAIN.address()), 1, attempts=1)


def refresh():
    """Re-read everything the amp will answer for, into the cache.

    Reads contiguous runs in one query each rather than 154 separate ones -
    the amp answers a block as fast as a single byte, and a parameter it
    will not answer for costs a full timeout plus retries.
    """
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

    # Individual blocks going silent is normal - effect blocks stay quiet
    # until they are loaded. Every single block going silent is not: that is
    # an amp that has been switched off or unplugged, and the cache must not
    # be wiped to empty on the strength of it.
    if not found:
        raise KatanaError("The amp stopped answering")

    cache.clear()
    cache.update(found)

    # Which channel this is. A refresh is exactly when the channel may have
    # changed under us - the amp was off, or someone pressed a CH button.
    global _channel
    with contextlib.suppress(KatanaError):
        _channel = amp.read_channel()
    return found


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
            async with lock:
                await call(probe, read=True)
                # It may have come back on a different channel: re-read it.
                values = await call(refresh, read=True)
                # And the patch names, which a page that loaded while the
                # amp was missing never got.
                with contextlib.suppress(KatanaError):
                    names = await call(controls.get_patch_names, read=True)
        except Exception:
            # Not there yet - or something unexpected, which must not kill
            # the loop either. (A shutdown's CancelledError is not an
            # Exception, so it still stops the loop.)
            await asyncio.sleep(RECONNECT_INTERVAL)
            continue

        _reconnect.clear()
        await broadcast(state_message())
        if names:
            await broadcast({"type": "patches", "names": names})


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

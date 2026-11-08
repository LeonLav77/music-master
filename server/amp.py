import asyncio
import contextlib

from katana_amp import katana
from katana_amp.katana import LIVE_BASE, NAME_LENGTH, PATCH_BLOCKS, Katana, KatanaError, advance, decode_name
from katana_amp.param import Param
from server import browsers

lock = asyncio.Lock()
cache = {}
# {patch number 1-9: name}, from the last time the names were read.
patch_names = {}
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
    # Runs fn(connection, *args) in a thread, so the slow MIDI work never
    # blocks the server: e.g. call(Katana.select_channel, "b2").
    def run():
        return fn(katana.connect(), *args)

    try:
        result = await asyncio.to_thread(run)
    except KatanaError:
        katana.disconnect()
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


def read_patch_names(connection):
    """Read the nine stored names, and remember them for channel switches."""
    names = connection.read_patch_names()
    patch_names.clear()
    patch_names.update(names)
    return names


def live_name(connection):
    """The live patch's name, or None if the amp did not answer this time.

    Catches its own error: a missed reply while polling is normal, and
    letting it reach call() would count as the amp having gone away.
    """
    try:
        return decode_name(connection.read(connection._encode_address(LIVE_BASE), NAME_LENGTH, attempts=1))
    except KatanaError:
        return None


def probe(connection):
    connection.read(connection._encode_address(Param.GAIN.address()), 1, attempts=1)


MAX_READ = 128  # bytes per request; Tone Studio's own limit (SYSEX_MAXLEN)


def _plan_reads():
    """The requests a refresh makes: (address, length, is_system) each.

    Patch settings are read the way BOSS Tone Studio reads them: whole
    blocks from Roland's list, up to 128 bytes at a time - about 15
    requests, two-byte values included, instead of one per run of
    settings. Amp-wide (system area) settings are read as runs of
    consecutive addresses; there are only a few.
    """
    reads = []
    for offset, length in PATCH_BLOCKS.values():
        start = LIVE_BASE + offset
        end = advance(start, length)
        if not any(start <= param.address() < end for param in Param):
            continue
        for chunk in range(0, length, MAX_READ):
            reads.append((advance(start, chunk), min(MAX_READ, length - chunk), False))

    system = sorted((param for param in Param if param.address() < LIVE_BASE), key=lambda param: param.address())
    for param in system:
        last = reads[-1] if reads and reads[-1][2] else None
        if last and param.address() == advance(last[0], last[1]):
            reads[-1] = (last[0], last[1] + param.size(), True)
        else:
            reads.append((param.address(), param.size(), True))
    return reads


READS = _plan_reads()


def refresh(connection, include_system=True):
    """Re-read the amp into the cache and return all the values it holds.

    A channel switch passes include_system=False: amp-wide settings do not
    change with the channel, so their cached values are kept.
    """
    image = {}
    for start, length, is_system in READS:
        if is_system and not include_system:
            continue
        try:
            # One attempt: retrying every block that does not answer would
            # dominate the refresh. A missing block stays "unknown".
            data = connection.read(connection._encode_address(start), length, attempts=1)
        except KatanaError:
            continue
        for index, byte in enumerate(data):
            image[advance(start, index)] = byte

    found = {}
    for param in Param:
        data = [image.get(advance(param.address(), index)) for index in range(param.size())]
        if None not in data:
            found[param.value] = param.decode(data)

    if not found:
        raise KatanaError("The amp stopped answering")

    if include_system:
        cache.clear()
    cache.update(found)

    global _channel
    with contextlib.suppress(KatanaError):
        _channel = connection.read_channel()
    return dict(cache)


async def _reconnect_loop():
    while True:
        await _reconnect.wait()

        names = None
        try:
            async with lock:
                await call(probe, read=True)
                values = await call(refresh, read=True)
                with contextlib.suppress(KatanaError):
                    names = await call(read_patch_names, read=True)
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
        katana.disconnect()

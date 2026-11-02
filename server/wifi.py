import asyncio
import contextlib
import logging
import re
import shutil

from server import browsers

DEVICE = "wlan0"
HOTSPOT = "katana-ap"      # the hotspot's profile name in NetworkManager
HOTSPOT_SSID = "Katana"    # what phones see; open, no password
HOTSPOT_ADDRESS = "10.42.0.1"   # NetworkManager's own choice for a shared network
WIFI = "802-11-wireless"   # NetworkManager's name for the Wi-Fi profile type

CHECK_INTERVAL = 10        # seconds between looks at wlan0
OFFLINE_LIMIT = 120        # seconds without a network before the hotspot goes up
JOIN_TIMEOUT = 20          # seconds one saved network gets to answer

log = logging.getLogger("uvicorn.error")

available = shutil.which("nmcli") is not None

# "online", "offline", "hotspot" or "connecting" - connecting while
# connect() is trying the saved networks.
mode = "offline"
network = None             # the network's name while online
_connecting = None         # the running connect() task


class WifiError(Exception):
    pass


# --- nmcli ------------------------------------------------------------------

async def _nmcli(*arguments):
    process = await asyncio.create_subprocess_exec(
        "nmcli", "--terse", *arguments,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    output, errors = await process.communicate()
    if process.returncode != 0:
        message = errors.decode(errors="replace").strip()
        raise WifiError(message.removeprefix("Error: ") or f"nmcli {arguments[0]} failed")
    return output.decode(errors="replace")


def _rows(output):
    for line in output.splitlines():
        fields = re.split(r"(?<!\\):", line)
        yield [field.replace("\\:", ":").replace("\\\\", "\\") for field in fields]


async def _device():
    for name, state, profile in _rows(await _nmcli("-f", "DEVICE,STATE,CONNECTION", "device")):
        if name == DEVICE:
            return state, profile
    return "unavailable", ""


async def _ssid(uuid):
    output = await _nmcli("-g", f"{WIFI}.ssid", "connection", "show", "uuid", uuid)
    return next(_rows(output), [""])[0]


# --- Saved networks ---------------------------------------------------------

async def saved():
    networks = []
    output = await _nmcli("-f", "NAME,UUID,TYPE,ACTIVE", "connection", "show")
    for name, uuid, kind, active in _rows(output):
        if kind != WIFI or name == HOTSPOT:
            continue
        networks.append({"uuid": uuid, "ssid": await _ssid(uuid), "active": active == "yes"})
    return networks


async def nearby(rescan="auto"):
    if mode == "hotspot":
        return []
    try:
        output = await _nmcli("-f", "SSID,SIGNAL", "device", "wifi", "list", "ifname", DEVICE, "--rescan", rescan)
    except WifiError:
        return []
    signals = {}
    for ssid, signal in _rows(output):
        if ssid:
            signals[ssid] = max(signals.get(ssid, 0), int(signal or 0))
    return sorted(signals, key=signals.get, reverse=True)


async def add(ssid, password):
    if not 1 <= len(ssid.encode()) <= 32:
        raise WifiError("A network name is 1-32 characters")
    if password and not 8 <= len(password) <= 63:
        raise WifiError("A Wi-Fi password is 8-63 characters")

    for known in await saved():
        if known["ssid"] == ssid:
            await _nmcli("connection", "delete", "uuid", known["uuid"])

    arguments = ["connection", "add", "type", "wifi", "ifname", DEVICE,
                 "con-name", ssid, "ssid", ssid]
    if password:
        arguments += ["wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password]
    await _nmcli(*arguments)


async def forget(uuid):
    if not any(known["uuid"] == uuid for known in await saved()):
        raise WifiError("No such saved network")
    await _nmcli("connection", "delete", "uuid", uuid)


# --- The hotspot ------------------------------------------------------------

async def _start_hotspot():
    try:
        await _nmcli("connection", "show", HOTSPOT)
    except WifiError:
        # "shared": the Pi takes 10.42.0.1 and hands out addresses itself.
        # No autoconnect, so at boot the saved networks are tried first.
        await _nmcli(
            "connection", "add", "type", "wifi", "ifname", DEVICE,
            "con-name", HOTSPOT, "ssid", HOTSPOT_SSID,
            f"{WIFI}.mode", "ap", f"{WIFI}.band", "bg",
            "ipv4.method", "shared", "connection.autoconnect", "no",
        )
    await _nmcli("--wait", str(JOIN_TIMEOUT), "connection", "up", HOTSPOT)
    log.info("Wi-Fi: no network, hotspot %s is on", HOTSPOT_SSID)
    await _set("hotspot")


async def _try_saved():
    # Rescan: the last scan is from before the hotspot, when the radio could not look.
    in_range = set(await nearby(rescan="yes"))
    for known in await saved():
        if known["ssid"] not in in_range:
            continue
        try:
            await _nmcli("--wait", str(JOIN_TIMEOUT), "connection", "up", "uuid", known["uuid"])
            return True
        except WifiError as exc:
            log.info("Wi-Fi: %s did not answer: %s", known["ssid"], exc)
    return False


async def _connect():
    await _set("connecting")
    try:
        with contextlib.suppress(WifiError):
            await _nmcli("connection", "down", HOTSPOT)
        if await _try_saved():
            await _look()
            return
        log.info("Wi-Fi: none of the saved networks answered, back to the hotspot")
        await _start_hotspot()
    except WifiError as exc:
        # Nobody is waiting for an answer, so it goes to the log; the
        # watcher brings the hotspot back if the radio was left with nothing.
        log.warning("Wi-Fi: %s", exc)
        await _set("offline")


def connect():
    global _connecting
    if not available:
        raise WifiError("No Wi-Fi control on this machine")
    if _connecting and not _connecting.done():
        raise WifiError("Already trying the saved networks")
    _connecting = asyncio.create_task(_connect())


# --- State, the watcher and the lifespan -----------------------------------

def state_message():
    return {
        "type": "wifi",
        "available": available,
        "mode": mode,
        "network": network,
        "hotspot": {"ssid": HOTSPOT_SSID, "address": HOTSPOT_ADDRESS},
    }


async def _set(new_mode, new_network=None):
    global mode, network
    if (new_mode, new_network) == (mode, network):
        return
    mode, network = new_mode, new_network
    await browsers.broadcast(state_message())


async def _look():
    state, profile = await _device()
    if profile == HOTSPOT:
        await _set("hotspot")
    elif state == "connected":
        active = [known["ssid"] for known in await saved() if known["active"]]
        await _set("online", active[0] if active else profile)
    else:
        await _set("offline")


async def _watch():
    if not available:
        return
    offline_for = 0
    while True:
        # While connect() runs it owns the radio - the watcher stays out.
        if mode != "connecting":
            try:
                await _look()
                offline_for = offline_for + CHECK_INTERVAL if mode == "offline" else 0
                if offline_for >= OFFLINE_LIMIT:
                    offline_for = 0
                    await _start_hotspot()
            except WifiError as exc:
                log.warning("Wi-Fi: %s", exc)
        await asyncio.sleep(CHECK_INTERVAL)


@contextlib.asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(_watch())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

"""Joining wifi networks from the control surface.

The Pi travels, so the networks it should join are not knowable in advance.
This is what makes that configurable without a keyboard: connect to the amp's
own access point, open the page, and add the network you are standing in.

Everything here shells out to nmcli rather than talking to NetworkManager
over D-Bus. It is a handful of one-shot commands, and a subprocess is far
easier to read - and to run by hand when something is wrong - than a D-Bus
client would be.

Nothing here trusts its input: an SSID is whatever a stranger typed into a
form on an open network, so it reaches nmcli as an argument in a list, never
inside a shell string.
"""

import asyncio
import shutil
import subprocess

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/wifi")

# The AP's own profile, which must never be offered as something to forget:
# deleting it from a phone connected through it would cut the branch off.
AP_CONNECTION = "katana-ap"

# nmcli can block for a long time on a bad password or a busy radio. These
# are per-command ceilings, chosen so a request fails rather than hangs.
SCAN_TIMEOUT = 25
CONNECT_TIMEOUT = 45


class Network(BaseModel):
    ssid: str = Field(min_length=1, max_length=32)
    # Open networks exist, so a password is optional rather than required.
    password: str | None = Field(default=None, max_length=63)
    # Hidden networks do not answer a scan and need telling.
    hidden: bool = False


def _nmcli(*args, timeout=15):
    """Run one nmcli command and return stdout, raising on failure."""
    if shutil.which("nmcli") is None:
        raise HTTPException(503, "NetworkManager is not available on this host")
    try:
        result = subprocess.run(
            ["nmcli", *args], capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "the network manager did not answer in time")
    if result.returncode != 0:
        # nmcli's own message names the actual problem - a bad password, a
        # network out of range - far better than anything generic here.
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise HTTPException(400, detail[-1] if detail else "nmcli failed")
    return result.stdout


def _split(line):
    r"""Split one -t line, honouring nmcli's backslash escaping.

    An SSID may contain a colon, which is also the field separator, so a
    plain split() corrupts exactly the networks that are hardest to type in
    by hand. nmcli escapes those as \:, and this undoes it.
    """
    fields, current, escaped = [], "", False
    for char in line:
        if escaped:
            current += char
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append(current)
            current = ""
        else:
            current += char
    fields.append(current)
    return fields


@router.get("/scan")
async def scan():
    """Networks in range, strongest first.

    The amp's own access point is filtered out: it is not something you join
    from the page you are reading over it.
    """
    out = await asyncio.to_thread(
        _nmcli, "-t", "-f", "SSID,SIGNAL,SECURITY,IN-USE",
        "dev", "wifi", "list", "--rescan", "yes", timeout=SCAN_TIMEOUT,
    )

    seen, networks = set(), []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = _split(line)
        if len(parts) < 3:
            continue
        ssid, signal, security = parts[0], parts[1], parts[2]
        in_use = len(parts) > 3 and parts[3] == "*"

        # A hidden network scans as an empty SSID; it cannot be joined by
        # tapping it, so there is nothing to show.
        if not ssid or ssid in seen:
            continue
        seen.add(ssid)

        networks.append({
            "ssid": ssid,
            "signal": int(signal) if signal.isdigit() else 0,
            "secure": bool(security and security != "--"),
            "active": in_use,
        })

    networks.sort(key=lambda n: n["signal"], reverse=True)
    return {"networks": networks}


@router.get("/saved")
async def saved():
    """Networks the Pi will join by itself, and which one it is on now."""
    out = await asyncio.to_thread(
        _nmcli, "-t", "-f", "NAME,TYPE,DEVICE", "con", "show"
    )
    active = {
        _split(line)[0]
        for line in (await asyncio.to_thread(
            _nmcli, "-t", "-f", "NAME", "con", "show", "--active")).splitlines()
        if line.strip()
    }

    saved_networks = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = _split(line)
        if len(parts) < 2 or "wireless" not in parts[1]:
            continue
        name = parts[0]
        if name == AP_CONNECTION:
            continue
        saved_networks.append({"name": name, "active": name in active})

    return {"saved": saved_networks}


@router.post("/join")
async def join(body: Network):
    """Join a network and remember it for next time.

    The connection is added rather than used once, so the Pi rejoins it on
    its own the next time it is in range - which is the whole point: you
    configure a venue's wifi once, standing there, and never again.
    """
    args = ["dev", "wifi", "connect", body.ssid]
    if body.password:
        args += ["password", body.password]
    if body.hidden:
        args += ["hidden", "yes"]

    # ifname: join on the radio's real interface, never on the AP's virtual
    # one. Without this nmcli may pick ap0 and take the access point down -
    # disconnecting the phone that asked for the change.
    args += ["ifname", "wlan0"]

    await asyncio.to_thread(_nmcli, *args, timeout=CONNECT_TIMEOUT)
    return {"joined": body.ssid}


@router.delete("/saved/{name}")
async def forget(name: str):
    """Forget a saved network."""
    if name == AP_CONNECTION:
        raise HTTPException(
            400, "that is the amp's own network - forgetting it would "
                 "disconnect you"
        )
    await asyncio.to_thread(_nmcli, "con", "delete", name)
    return {"forgot": name}


@router.get("/status")
async def status():
    """What the Pi is connected to, and how to reach it.

    Both halves matter: the access point is how you are probably reading
    this, and the client connection is what gives it a route to the outside
    world - and an address on the house network worth telling you about.
    """
    out = await asyncio.to_thread(
        _nmcli, "-t", "-f", "NAME,DEVICE,TYPE", "con", "show", "--active"
    )

    ap, client = None, None
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = _split(line)
        if len(parts) < 3 or "wireless" not in parts[2]:
            continue
        name, device = parts[0], parts[1]
        entry = {"name": name, "device": device}
        try:
            addr = await asyncio.to_thread(
                _nmcli, "-g", "IP4.ADDRESS", "con", "show", name)
            entry["address"] = addr.strip().split("/")[0].split("\n")[0] or None
        except HTTPException:
            entry["address"] = None
        if name == AP_CONNECTION:
            ap = entry
        else:
            client = entry

    return {"ap": ap, "client": client}

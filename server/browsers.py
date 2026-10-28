"""The browsers connected over the WebSocket, and sending to all of them.

websocket.py adds a browser here when it connects and removes it when it
leaves; anything that changes the amp's state calls broadcast() so every
open page stays in step.
"""

import json

# Every browser with the page open right now.
connected = set()


async def broadcast(message, skip=None):
    """Send a message to every connected browser except `skip`, dropping
    any that have gone away."""
    if not connected:
        return
    payload = json.dumps(message)
    for browser in list(connected):
        if browser is skip:
            continue
        try:
            await browser.send_text(payload)
        except Exception:
            connected.discard(browser)

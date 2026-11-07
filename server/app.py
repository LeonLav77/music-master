import contextlib
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from server import amp, audio, hotplug, monitor, recorder, routes, tuner, websocket, wifi

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@contextlib.asynccontextmanager
async def lifespan(app):
    # The recorder and the monitor use what audio and the tuner opened, so
    # they come after them; hotplug reopens all of these, so it comes last
    # of all. Wi-Fi needs none of them.
    async with (amp.lifespan(app), audio.lifespan(app), tuner.lifespan(app),
                recorder.lifespan(app), monitor.lifespan(app), hotplug.lifespan(app),
                wifi.lifespan(app)):
        yield


app = FastAPI(title="Katana MkII", lifespan=lifespan)
app.include_router(routes.router)   # HTTP endpoints
app.include_router(websocket.router)  # the WebSocket

app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="ui")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

import contextlib
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from server import amp, audio, recorder, routes, tuner, websocket

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@contextlib.asynccontextmanager
async def lifespan(app):
    # The recorder uses what audio and the tuner opened, so it comes last.
    async with amp.lifespan(app), audio.lifespan(app), tuner.lifespan(app), recorder.lifespan(app):
        yield


app = FastAPI(title="Katana MkII", lifespan=lifespan)
app.include_router(routes.router)   # HTTP endpoints
app.include_router(websocket.router)  # the WebSocket

app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="ui")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

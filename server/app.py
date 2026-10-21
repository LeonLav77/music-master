import contextlib
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from server import amp, live, meter, routes

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@contextlib.asynccontextmanager
async def lifespan(app):
    """What runs while the server is up: the loop that finds the amp, and
    the input meter listening to its audio."""
    async with amp.lifespan(app), meter.lifespan(app):
        yield


app = FastAPI(title="Katana MkII", lifespan=lifespan)
app.include_router(routes.router)   # HTTP endpoints
app.include_router(live.router)     # the WebSocket

# Mounted last: "/" matches every URL, so it would hide the API if it came
# first.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="ui")

if __name__ == "__main__":
    # 0.0.0.0 means every network interface, so a phone can reach it too.
    uvicorn.run(app, host="0.0.0.0", port=8000)

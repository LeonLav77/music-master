from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from server import amp, routes, websocket

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Katana MkII", lifespan=amp.lifespan)
app.include_router(routes.router)   # HTTP endpoints
app.include_router(websocket.router)  # the WebSocket

app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="ui")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

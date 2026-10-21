"""The server: the amp API and the web page, on port 8000.

    ./run

Open http://<this machine's address>:8000 from any device on the network.
"""

from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from server import api

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Katana MkII", lifespan=api.lifespan)
app.include_router(api.router)

# Mounted last: "/" matches every URL, so it would hide the API if it came
# first.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="ui")

if __name__ == "__main__":
    # 0.0.0.0 means every network interface, so a phone can reach it too.
    uvicorn.run(app, host="0.0.0.0", port=8000)

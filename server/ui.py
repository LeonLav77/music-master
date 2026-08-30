"""Serving the control surface in web/.

The UI is static files with no build step, so this is a mount and nothing
more. It is kept separate from the API for the same reason it used to be a
separate process: the two are different things, and the API has to stay
usable on its own.

What changed is only how the separation is enforced. Two processes on two
ports meant the page had to guess where the API lived - it appended a
hardcoded :8000 to its own hostname, so moving the API port silently broke
the UI. Mounting both on one port makes them same-origin: the page just
uses relative URLs, there is no CORS, and one service starts the whole
thing on a Pi that boots unattended.
"""

from pathlib import Path

from fastapi.staticfiles import StaticFiles

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def mount(app, directory=WEB_DIR):
    """Serve `directory` at the root, index.html included.

    Mounted last so it never shadows the API: a mount at "/" matches
    everything, and routes registered before it still win.
    """
    if not directory.is_dir():
        raise RuntimeError(f"No web directory at {directory}")
    app.mount("/", StaticFiles(directory=directory, html=True), name="ui")
    return app

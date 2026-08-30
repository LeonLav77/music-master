"""The server: the amp API, with the control surface on the same port.

    ./run-server                 API + UI on :8000
    ./run-server --no-ui         API only
    ./run-server --port 9000     both, somewhere else

One process, one port. The UI is same-origin with the API, so the page uses
relative URLs and there is nothing to configure - which is what makes
`--port` actually work, and what makes this a single systemd unit on a Pi.

The two halves stay separable in the code rather than in the deployment:
`server.api` is the amp and knows nothing about a UI, `server.ui` is a
static mount and knows nothing about the amp. This module is the only place
that knows about both.
"""

from fastapi import FastAPI

from server import api, ui


def create_app(serve_ui=True):
    """Build the application. Set serve_ui=False for the API on its own."""
    app = FastAPI(title="Katana MkII", version="1.0", lifespan=api.lifespan)

    app.include_router(api.router)

    # Last: the UI mounts at "/" and would otherwise shadow the API.
    # A missing web/ is a broken checkout, not something to paper over -
    # silently serving no UI would look identical to a UI that fails to
    # load, which is a miserable thing to debug on a Pi with no screen.
    if serve_ui:
        ui.mount(app)

    return app


app = create_app()


def main():
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="Katana MkII control server.")
    # 0.0.0.0 so a phone on the same network can reach it.
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--no-ui",
        action="store_true",
        help="serve the API only, without the control surface",
    )
    args = parser.parse_args()

    uvicorn.run(
        create_app(serve_ui=not args.no_ui), host=args.host, port=args.port
    )


if __name__ == "__main__":
    main()

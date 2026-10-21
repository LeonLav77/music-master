# Katana MkII control surface — no build step

Plain HTML, hand-written CSS and ES modules, with [Alpine](https://alpinejs.dev)
for reactivity. No TypeScript, no bundler, no `node_modules`. Edit a file,
reload the page.

## Running it

The server serves this directory itself, so there is nothing separate to
start:

    ./run

Then open `http://<host>:8000` — from a phone on the same network too. The
API is on the same origin as the page, so the UI talks to whatever address
you opened it at, with no configuration and no CORS.

To serve the page from somewhere else (any static file server will do — it
only needs HTTP, since ES modules do not load from `file://`), point it at
the API with:

    <script>window.KATANA_API_URL = "http://gitra.local:8000"</script>

placed before `js/app.js` in `index.html`.

## Layout

| File | What it is |
| --- | --- |
| `index.html` | The whole surface. Alpine directives, no templating language. |
| `app.css` | Design tokens, cabinet materials, layout. Hand-written. |
| `vendor/alpine.min.js` | Vendored, so the panel works with no internet. |
| `js/schema.js` | Parameter tables, fetched from `/api/parameters` at startup. |
| `js/transport.js` | HTTP + WebSocket seam. Nothing else knows about the wire. |
| `js/store.js` | The Alpine global store: amp state and the operations on it. |
| `js/controls.js` | Pointer drag, knob geometry, EQ curve maths. |
| `js/components.js` | `x-data` factories for knob, dial, treadle, EQ, rail. |
| `js/blocks.js` | Which parameters each editor panel shows. |
| `js/app.js` | Registers everything on `alpine:init`, then loads Alpine. |

## The schema

`js/schema.js` fetches the parameter tables from the server rather than
keeping its own copy, so the UI and the amp cannot disagree about ranges or
enum numbering. Change a parameter in `katana.py`, restart the server, and
the UI picks it up on the next reload.

## Notes

- **Reactivity.** Alpine's proxies are per-property, so dragging one knob
  only re-renders bindings that read that knob. There is no provider and no
  memoisation to keep in sync.
- **Held controls.** While a control is being dragged its key is in
  `store._held`, and incoming amp state for that key is dropped — otherwise a
  push would yank the control out from under a finger.
- **No `<template x-for>` inside `<svg>`.** SVG has no `<template>` element, so
  the parser mis-nests it and `importNode` throws. Static SVG geometry (the
  knob tick marks) is written out literally.
- **The treadle slab is tilted in 3D**, which projects it below its own box.
  Its label and buttons need an explicit `z-index` and reserved space or the
  slab swallows their clicks.

# Doc Scan MVP — Relay Server

Minimal Express + `ws` server used to pair a desktop viewer with a phone uploader.
See the [top-level MVP README](../README.md) for the full flow.

## Scripts

- `npm run dev` — start the server with auto-reload (`tsx watch`).
- `npm run start` — start the server once.
- `npm run build` — type-check and compile to `dist/`.

## Configuration

- `PORT` — port to listen on (defaults to `4000`).

## Endpoints

- `POST /api/sessions` — creates a new session and returns `{ sessionId, expiresInMs }`.
- `POST /api/sessions/:id/photos` — accepts `{ dataUrl }` and relays it to the desktop
  paired with that session over WebSocket.
- `GET /ws?sessionId=<id>` (WebSocket) — the desktop viewer connects here to receive
  relayed photos for the given session.

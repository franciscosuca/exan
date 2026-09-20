# Doc Scan MVP — Phone-to-Desktop Scanning

This is a small, standalone **proof-of-concept** app that lets you take a photo with
your phone and have it show up instantly on a desktop browser. It's kept intentionally
simple: no persistence, no auth, no integration with the rest of Exan. It exists as a
reference implementation for the "QR-paired web uploader" option described in
[`docs/scanning/SCANNING_INTEGRATION_OPTIONS.md`](../docs/scanning/SCANNING_INTEGRATION_OPTIONS.md),
tracked by [issue #24](https://github.com/franciscosuca/exan/issues/24).

## How it works

1. **Desktop**: open the app, choose "I'm on the desktop". It requests a short-lived
   session code from the relay server, opens a WebSocket to it, and renders a QR code
   that encodes a link back to this same app with the session code pre-filled.
2. **Phone**: scan the QR code (or open the app and type the code manually), choose
   "I'm on the phone", then tap the photo button. The phone's camera/file picker
   opens (`<input type="file" capture="environment">`), and the chosen photo is
   uploaded to the relay server as a data URL over a plain `fetch` POST.
3. **Relay server**: a minimal Express + `ws` server keeps an in-memory map of
   session codes to the desktop's WebSocket connection. When a photo is POSTed for a
   session, the server pushes it straight to the paired desktop socket. Sessions
   expire automatically after 30 minutes.

There's no image storage: photos only exist in memory on the phone until uploaded,
and are relayed directly to the desktop without being written to disk.

## Project layout

```
mvp/
├── server/   # Express + ws relay server (session pairing + photo relay)
└── client/   # Vite + React app (desktop viewer and phone uploader)
```

## Running locally

You'll need two terminals — one for the relay server, one for the client.

```bash
# Terminal 1: relay server (defaults to http://localhost:4000)
cd mvp/server
npm install
npm run dev

# Terminal 2: client app (defaults to http://localhost:5173)
cd mvp/client
npm install
npm run dev
```

Open the client URL on your desktop and choose "I'm on the desktop". To test the
phone side from the same machine, open the same URL in a second browser tab/window
and choose "I'm on the phone", or scan the QR code with an actual phone **that is on
the same network** as your computer (you'll need to set `VITE_SERVER_URL` in
`mvp/client` to your computer's LAN IP so the phone can reach the relay server, e.g.
`VITE_SERVER_URL=http://192.168.1.20:4000 npm run dev`).

## Limitations (by design, since this is an MVP)

- Single desktop viewer per session — no multi-device fan-out.
- No authentication or rate limiting on the relay server.
- Sessions and photos live only in memory; restarting the server clears everything.
- No HTTPS setup included; phone camera capture (`capture="environment"`) generally
  requires HTTPS or `localhost` in production browsers.

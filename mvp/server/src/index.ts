import { createServer } from "node:http";
import { randomBytes } from "node:crypto";
import express from "express";
import cors from "cors";
import { WebSocketServer, type WebSocket } from "ws";

const PORT = Number(process.env.PORT ?? 4000);
const SESSION_TTL_MS = 30 * 60 * 1000; // 30 minutes
const MAX_PHOTO_BYTES = 8 * 1024 * 1024; // 8 MB, generous for a phone photo data URL

// Only allow raster image formats. SVG is intentionally excluded because it can embed
// scripts, and this data URL is later rendered directly in an <img> on the desktop.
const SAFE_IMAGE_DATA_URL = /^data:image\/(png|jpe?g|webp|gif);base64,[A-Za-z0-9+/]+=*$/;

interface Session {
  id: string;
  createdAt: number;
  desktopSocket: WebSocket | null;
}

const sessions = new Map<string, Session>();

function generateSessionId(): string {
  // 6 uppercase alphanumeric characters, easy to type on a phone if the QR scan fails.
  return randomBytes(4).toString("hex").slice(0, 6).toUpperCase();
}

function pruneExpiredSessions() {
  const now = Date.now();
  for (const [id, session] of sessions) {
    if (now - session.createdAt > SESSION_TTL_MS) {
      session.desktopSocket?.close();
      sessions.delete(id);
    }
  }
}

setInterval(pruneExpiredSessions, 60 * 1000).unref();

const app = express();
app.use(cors());
app.use(express.json({ limit: "10mb" }));

app.post("/api/sessions", (_req, res) => {
  let id = generateSessionId();
  while (sessions.has(id)) {
    id = generateSessionId();
  }
  sessions.set(id, { id, createdAt: Date.now(), desktopSocket: null });
  res.status(201).json({ sessionId: id, expiresInMs: SESSION_TTL_MS });
});

app.post("/api/sessions/:id/photos", (req, res) => {
  const session = sessions.get(req.params.id);
  if (!session) {
    res.status(404).json({ error: "Session not found or expired" });
    return;
  }

  const { dataUrl } = req.body ?? {};
  if (typeof dataUrl !== "string" || !SAFE_IMAGE_DATA_URL.test(dataUrl)) {
    res.status(400).json({ error: "dataUrl must be a PNG, JPEG, WEBP, or GIF image data URL" });
    return;
  }
  if (dataUrl.length > MAX_PHOTO_BYTES) {
    res.status(413).json({ error: "Photo is too large" });
    return;
  }

  if (session.desktopSocket && session.desktopSocket.readyState === session.desktopSocket.OPEN) {
    session.desktopSocket.send(
      JSON.stringify({ type: "photo", dataUrl, receivedAt: Date.now() }),
    );
    res.status(202).json({ delivered: true });
  } else {
    res.status(409).json({ error: "No desktop is currently paired with this session" });
  }
});

const server = createServer(app);
const wss = new WebSocketServer({ server, path: "/ws" });

wss.on("connection", (socket, request) => {
  const url = new URL(request.url ?? "", "http://localhost");
  const sessionId = url.searchParams.get("sessionId");
  const session = sessionId ? sessions.get(sessionId) : undefined;

  if (!session) {
    socket.close(4004, "Unknown or expired session");
    return;
  }

  session.desktopSocket = socket;
  socket.send(JSON.stringify({ type: "paired", sessionId: session.id }));

  socket.on("close", () => {
    if (session.desktopSocket === socket) {
      session.desktopSocket = null;
    }
  });
});

server.listen(PORT, () => {
  console.log(`MVP relay server listening on http://localhost:${PORT}`);
});

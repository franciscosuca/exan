import express, { type NextFunction, type Request, type Response } from "express";
import { connectToDatabase } from "../db/connection.js";
import { ensureIndexes } from "./lib/user.model.js";
import { authRoutes } from "./routes/auth.routes.js";
import { authMiddleware } from "./middleware/auth.middleware.js";

const PORT = process.env.PORT || 3001;

function getSafeErrorPayload(payload: unknown): Record<string, string> | string | undefined {
  if (typeof payload === "string") {
    return payload;
  }

  if (typeof payload !== "object" || payload === null) {
    return undefined;
  }

  const responsePayload = payload as Record<string, unknown>;
  const safePayload: Record<string, string> = {};

  for (const key of ["error", "detail"]) {
    if (typeof responsePayload[key] === "string") {
      safePayload[key] = responsePayload[key];
    }
  }

  return Object.keys(safePayload).length > 0 ? safePayload : undefined;
}

function logFailedJsonResponses(req: Request, res: Response, next: NextFunction): void {
  const originalJson = res.json.bind(res);

  res.json = ((payload: unknown) => {
    if (res.statusCode >= 400) {
      console.error("Auth HTTP error", {
        method: req.method,
        path: req.path,
        status: res.statusCode,
        errorPayload: getSafeErrorPayload(payload),
      });
    }

    return originalJson(payload);
  }) as Response["json"];

  next();
}

async function main() {
  const db = await connectToDatabase();
  await ensureIndexes(db);

  const app = express();

  app.use(express.json());

  // CORS for local frontend development
  app.use((_req, res, next) => {
    res.header("Access-Control-Allow-Origin", "*");
    res.header("Access-Control-Allow-Headers", "Content-Type, Authorization");
    res.header("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    if (_req.method === "OPTIONS") {
      res.sendStatus(204);
      return;
    }
    next();
  });

  app.use(logFailedJsonResponses);

  app.use("/api/auth", authRoutes(db));

  // Example protected route
  app.get("/api/me", authMiddleware, (req, res) => {
    res.json({ user: (req as any).user });
  });

  app.use((err: unknown, req: Request, res: Response, next: NextFunction) => {
    console.error("Unhandled auth error", {
      method: req.method,
      path: req.path,
      error: err instanceof Error ? err.stack || err.message : String(err),
    });

    if (res.headersSent) {
      next(err);
      return;
    }

    res.status(500).json({ error: "Internal server error" });
  });

  app.listen(PORT, () => {
    console.log(`Auth server running on http://localhost:${PORT}`);
  });
}

main().catch(console.error);

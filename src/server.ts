import express from "express";
import { connectToDatabase } from "../db/connection.js";
import { ensureIndexes } from "./auth/user.model.js";
import { authRoutes } from "./routes/auth.routes.js";
import { authMiddleware } from "./middleware/auth.middleware.js";

const PORT = process.env.PORT || 3001;

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

  app.use("/api/auth", authRoutes(db));

  // Example protected route
  app.get("/api/me", authMiddleware, (req, res) => {
    res.json({ user: (req as any).user });
  });

  app.listen(PORT, () => {
    console.log(`Auth server running on http://localhost:${PORT}`);
  });
}

main().catch(console.error);

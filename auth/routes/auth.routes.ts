import { Router, Request, Response } from "express";
import { Db } from "mongodb";
import { verifyUser } from "../lib/user.model.js";
import { generateToken } from "../lib/token.js";

export function authRoutes(db: Db): Router {
  const router = Router();

  router.post("/login", async (req: Request, res: Response) => {
    const { username, password } = req.body;

    if (!username || !password) {
      res.status(400).json({ error: "Username and password are required" });
      return;
    }

    try {
      const user = await verifyUser(db, username, password);
      const token = generateToken({
        userId: user._id!.toString(),
        username: user.username,
      });

      res.json({ token, username: user.username });
    } catch {
      res.status(401).json({ error: "Invalid username or password" });
    }
  });

  return router;
}

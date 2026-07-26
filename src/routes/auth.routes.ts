import { Router, Request, Response } from "express";
import { Db } from "mongodb";
import { createUser, verifyUser } from "../auth/user.model.js";
import { generateToken } from "../auth/token.js";

export function authRoutes(db: Db): Router {
  const router = Router();

  router.post("/register", async (req: Request, res: Response) => {
    const { username, password, repeatPassword } = req.body;

    if (!username || !password || !repeatPassword) {
      res.status(400).json({ error: "All fields are required" });
      return;
    }

    if (password !== repeatPassword) {
      res.status(400).json({ error: "Passwords do not match" });
      return;
    }

    if (username.length < 3) {
      res.status(400).json({ error: "Username must be at least 3 characters" });
      return;
    }

    if (password.length < 6) {
      res.status(400).json({ error: "Password must be at least 6 characters" });
      return;
    }

    try {
      const user = await createUser(db, username, password);
      const token = generateToken({
        userId: user._id!.toString(),
        username: user.username,
      });

      res.status(201).json({ token, username: user.username });
    } catch (err: any) {
      if (err.message === "Username already exists") {
        res.status(409).json({ error: err.message });
        return;
      }
      res.status(500).json({ error: "Registration failed" });
    }
  });

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

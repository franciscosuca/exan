import { Collection, Db } from "mongodb";
import bcrypt from "bcrypt";

export interface User {
  _id?: string;
  username: string;
  passwordHash: string;
  createdAt: Date;
}

function getUsersCollection(db: Db): Collection<User> {
  return db.collection<User>("users");
}

export async function verifyUser(
  db: Db,
  username: string,
  password: string
): Promise<User> {
  const collection = getUsersCollection(db);

  const user = await collection.findOne({ username });
  if (!user) {
    throw new Error("Invalid username or password");
  }

  const isValid = await bcrypt.compare(password, user.passwordHash);
  if (!isValid) {
    throw new Error("Invalid username or password");
  }

  return user;
}

export async function ensureIndexes(db: Db): Promise<void> {
  const collection = getUsersCollection(db);
  await collection.createIndex({ username: 1 }, { unique: true });
}

import { MongoClient, Db } from "mongodb";

const MONGO_URI =
  process.env.MONGO_URI ||
  "mongodb://exan_app:exan_app_password@localhost:27017/exan?authSource=exan";

let client: MongoClient | null = null;
let db: Db | null = null;

export async function connectToDatabase(): Promise<Db> {
  if (db) return db;

  client = new MongoClient(MONGO_URI);
  await client.connect();
  db = client.db();

  console.log(`Connected to MongoDB: ${db.databaseName}`);
  return db;
}

export async function disconnectFromDatabase(): Promise<void> {
  if (client) {
    await client.close();
    client = null;
    db = null;
  }
}

export function getDatabase(): Db {
  if (!db) {
    throw new Error(
      "Database not connected. Call connectToDatabase() first."
    );
  }
  return db;
}

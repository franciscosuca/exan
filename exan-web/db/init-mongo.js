// Creates the application database and a dedicated app user with readWrite access.
// This script runs automatically on first container startup via docker-entrypoint-initdb.d.

const dbName = process.env.MONGO_INITDB_DATABASE || "exan";

const db = db.getSiblingDB(dbName);

db.createUser({
  user: "exan_app",
  pwd: "exan_app_password",
  roles: [{ role: "readWrite", db: dbName }],
});

db.createCollection("app_metadata");
db.app_metadata.insertOne({
  _id: "init",
  createdAt: new Date(),
  description: "Database initialized successfully",
});

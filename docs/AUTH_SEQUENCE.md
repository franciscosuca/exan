# Authentication Service Sequence Diagram

This diagram shows how the `server`, `auth.routes`, `auth.middleware`, `token`, and `user.model` modules interact with **MongoDB** and the **Frontend** during registration, login, and protected-route access.

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant SRV as Auth Server<br/>(server.ts)
    participant DB as MongoDB
    participant RT as Auth Routes<br/>(auth.routes.ts)
    participant UM as User Model<br/>(user.model.ts)
    participant TK as Token Module<br/>(token.ts)
    participant MW as Auth Middleware<br/>(auth.middleware.ts)

    %% Server startup
    SRV->>DB: connectToDatabase()
    DB-->>SRV: Db instance
    SRV->>UM: ensureIndexes(db)
    UM->>DB: createIndex(username, unique)
    DB-->>UM: index created
    UM-->>SRV: indexes ready
    SRV->>SRV: app.use("/api/auth", authRoutes(db))
    SRV->>SRV: app.get("/api/me", authMiddleware, handler)
    SRV->>SRV: listen(PORT)

    %% Registration
    FE->>RT: POST /api/auth/register<br/>{username, password, repeatPassword}
    RT->>RT: Validate input
    RT->>UM: createUser(db, username, password)
    UM->>DB: findOne({username})
    DB-->>UM: null
    UM->>UM: bcrypt.hash(password, 12)
    UM->>DB: insertOne({username, passwordHash, createdAt})
    DB-->>UM: new user
    UM-->>RT: User
    RT->>TK: generateToken({userId, username})
    TK-->>RT: JWT
    RT-->>FE: 201 {token, username}
    FE->>FE: saveToken(token)

    %% Login
    FE->>RT: POST /api/auth/login<br/>{username, password}
    RT->>UM: verifyUser(db, username, password)
    UM->>DB: findOne({username})
    DB-->>UM: user document
    UM->>UM: bcrypt.compare(password, passwordHash)
    UM-->>RT: User
    RT->>TK: generateToken({userId, username})
    TK-->>RT: JWT
    RT-->>FE: 200 {token, username}
    FE->>FE: saveToken(token)

    %% Protected route access
    FE->>MW: GET /api/me<br/>Authorization: Bearer <token>
    MW->>MW: Extract token from header
    MW->>TK: verifyToken(token)
    TK-->>MW: TokenPayload {userId, username}
    MW->>MW: req.user = payload
    MW->>SRV: next() → call route handler
    SRV-->>FE: 200 {user: {userId, username}}

    %% Invalid token case
    FE->>MW: GET /api/me<br/>Authorization: Bearer <invalid>
    MW->>MW: Extract token from header
    MW->>TK: verifyToken(token)
    TK--xMW: throws (invalid/expired)
    MW-->>FE: 401 {error: "Invalid or expired token"}
```

## Flow Summary

1. **Server startup** (`server.ts`)
   - Connects to MongoDB via `connectToDatabase()`.
   - Calls `ensureIndexes(db)` to create a unique index on `username`.
   - Mounts `/api/auth` routes from `auth.routes.ts`.
   - Registers the protected `/api/me` route with `authMiddleware`.

2. **Registration** (`POST /api/auth/register`)
   - The frontend sends `{username, password, repeatPassword}`.
   - `auth.routes.ts` validates input length and password match.
   - `user.model.ts` checks for existing usernames and inserts a new document with a bcrypt hash (12 rounds).
   - `token.ts` generates a signed JWT (24-hour expiry).
   - The frontend receives `{token, username}` and stores the token.

3. **Login** (`POST /api/auth/login`)
   - The frontend sends `{username, password}`.
   - `user.model.ts` fetches the user and verifies the password with bcrypt.
   - `token.ts` generates a signed JWT.
   - The frontend receives `{token, username}` and stores the token.

4. **Protected route access** (`GET /api/me`)
   - The frontend includes the token in the `Authorization: Bearer <token>` header.
   - `auth.middleware.ts` extracts the token and calls `verifyToken()`.
   - On success, the decoded payload is attached to `req.user` and the request proceeds.
   - On failure, a `401 Unauthorized` response is returned immediately.

## Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `server.ts` | Bootstraps Express, connects to MongoDB, mounts routes, and starts listening. |
| `auth.routes.ts` | Defines `/register` and `/login` endpoints and orchestrates model + token calls. |
| `auth.middleware.ts` | Validates the `Authorization` header and attaches the decoded user to `req.user`. |
| `token.ts` | Signs and verifies JWT tokens with `JWT_SECRET` and a 24-hour expiry. |
| `user.model.ts` | Handles MongoDB user queries, bcrypt hashing, and password verification. |
| `db/connection.ts` | Manages the MongoDB client lifecycle and provides the `Db` instance. |

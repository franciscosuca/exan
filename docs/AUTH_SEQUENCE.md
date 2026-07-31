# Authentication Service Sequence Diagram

This diagram shows how the webapp proxy, `server`, `auth.routes`, `auth.middleware`, `token`, and `user.model` modules interact with **MongoDB** and the **Frontend** during registration, login, and protected-route access.

```mermaid
sequenceDiagram
    participant FE as Frontend
   participant PX as Webapp Proxy<br/>(nginx / Vite)
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

   %% Same-origin proxy routing
   Note over FE,PX: Browser requests stay on the webapp origin

    %% Registration
   FE->>PX: POST /api/auth/register<br/>{username, password, repeatPassword}
   PX->>SRV: Forward /api/auth/register<br/>to auth-server:3001
   SRV->>RT: Dispatch /register
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
   RT-->>SRV: 201 {token, username}
   SRV-->>PX: 201 {token, username}
   PX-->>FE: 201 {token, username}
    FE->>FE: saveToken(token)

    %% Login
   FE->>PX: POST /api/auth/login<br/>{username, password}
   PX->>SRV: Forward /api/auth/login<br/>to auth-server:3001
   SRV->>RT: Dispatch /login
    RT->>UM: verifyUser(db, username, password)
    UM->>DB: findOne({username})
    DB-->>UM: user document
    UM->>UM: bcrypt.compare(password, passwordHash)
    UM-->>RT: User
    RT->>TK: generateToken({userId, username})
    TK-->>RT: JWT
   RT-->>SRV: 200 {token, username}
   SRV-->>PX: 200 {token, username}
   PX-->>FE: 200 {token, username}
    FE->>FE: saveToken(token)

   %% Protected route access through the auth server directly
   Note over FE,SRV: /api/me is not currently forwarded by the webapp proxy
   FE->>SRV: GET /api/me<br/>Authorization: Bearer <token>
   SRV->>MW: Run authMiddleware
    MW->>MW: Extract token from header
    MW->>TK: verifyToken(token)
    TK-->>MW: TokenPayload {userId, username}
    MW->>MW: req.user = payload
    MW->>SRV: next() → call route handler
    SRV-->>FE: 200 {user: {userId, username}}

    %% Invalid token case
   FE->>SRV: GET /api/me<br/>Authorization: Bearer <invalid>
   SRV->>MW: Run authMiddleware
    MW->>MW: Extract token from header
    MW->>TK: verifyToken(token)
    TK--xMW: throws (invalid/expired)
    MW-->>FE: 401 {error: "Invalid or expired token"}
```

## Flow Summary

1. **Webapp proxy routing**
   - The frontend uses relative `/api/auth/*` URLs, so browser requests stay on the webapp origin and do not require CORS.
   - In the Docker/Codespaces build, `webapp/nginx.conf` forwards `/api/auth/` to `http://auth-server:3001/api/auth/` using Docker service discovery.
   - During `npm run dev`, `webapp/vite.config.ts` forwards `/api/auth` to `http://localhost:3001`.
   - Nginx sends remaining `/api/` requests to the inference service at `http://inference:8000`.

2. **Server startup** (`server.ts`)
   - Connects to MongoDB via `connectToDatabase()`.
   - Calls `ensureIndexes(db)` to create a unique index on `username`.
   - Mounts `/api/auth` routes from `auth.routes.ts`.
   - Registers the protected `/api/me` route with `authMiddleware`.

3. **Registration** (`POST /api/auth/register`)
   - The frontend sends `{username, password, repeatPassword}`.
   - `auth.routes.ts` validates input length and password match.
   - `user.model.ts` checks for existing usernames and inserts a new document with a bcrypt hash (12 rounds).
   - `token.ts` generates a signed JWT (24-hour expiry).
   - The frontend receives `{token, username}` and stores the token.

4. **Login** (`POST /api/auth/login`)
   - The frontend sends `{username, password}`.
   - `user.model.ts` fetches the user and verifies the password with bcrypt.
   - `token.ts` generates a signed JWT.
   - The frontend receives `{token, username}` and stores the token.

5. **Protected route access** (`GET /api/me`)
   - The frontend includes the token in the `Authorization: Bearer <token>` header.
   - `auth.middleware.ts` extracts the token and calls `verifyToken()`.
   - On success, the decoded payload is attached to `req.user` and the request proceeds.
   - On failure, a `401 Unauthorized` response is returned immediately.
   - The auth server exposes this route, but the current webapp nginx and Vite proxies do not forward `/api/me`; browser access through the webapp origin requires an additional proxy rule.

## Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `webapp/nginx.conf` | Proxies containerized `/api/auth/` requests to `auth-server:3001` and other `/api/` requests to `inference:8000`. |
| `webapp/vite.config.ts` | Proxies local-development `/api/auth` requests to `localhost:3001`. |
| `server.ts` | Bootstraps Express, connects to MongoDB, mounts routes, and starts listening. |
| `auth.routes.ts` | Defines `/register` and `/login` endpoints and orchestrates model + token calls. |
| `auth.middleware.ts` | Validates the `Authorization` header and attaches the decoded user to `req.user`. |
| `token.ts` | Signs and verifies JWT tokens with `JWT_SECRET` and a 24-hour expiry. |
| `user.model.ts` | Handles MongoDB user queries, bcrypt hashing, and password verification. |
| `db/connection.ts` | Manages the MongoDB client lifecycle and provides the `Db` instance. |

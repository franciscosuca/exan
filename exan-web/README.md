# Exan Web — cloud product

The browser-delivered Exan stack: multi-user, MongoDB-backed, deployed to Google Cloud Run.

| Service | Path | Stack |
|---|---|---|
| Web app | [`webapp/`](webapp/) | React SPA (Vite + Tailwind) served by nginx |
| Auth server | [`auth/`](auth/) | Express + JWT |
| Inference | [`inference/`](inference/) | FastAPI (Gemini / LM Studio / Ollama / other OpenAI-compatible providers) |
| Database | [`db/`](db/) | MongoDB init + connection |
| Infra | [`terraform/`](terraform/) | Google Cloud Run infrastructure |
| Compose | [`docker-compose.yml`](docker-compose.yml) | local run (mongo + inference + auth + webapp) |

## Local development

From this folder:

```bash
cp .env.example .env          # set MONGO_URI, JWT_SECRET, …
bun install                   # root deps (auth)
cd webapp && bun install      # webapp deps
npm run ...                   # the scripts below (npm scripts at this folder's package.json)
```

- `npm run dev:webapp`, `npm run dev:inference`, `npm run dev:auth`
- `npm run db:start` / `db:stop` / `db:reset` (Docker Compose Mongo)
- `cd webapp && bun run dev` — the SPA on http://localhost:5173

Production build is orchestrated by GitHub Actions (`.github/workflows/`) with the Dockerfiles in each service folder. See [`docs/deployment/`](docs/deployment/) for the Cloud Run guide and secret setup.
# Exan

AI-powered exam scanning and grading. Exan ships the same product through two delivery channels, each a self-contained folder at the root:

- **[`exan-web/`](exan-web/README.md)** — the cloud stack: a React SPA, an Express + JWT auth server, a FastAPI inference service, MongoDB, and Terraform/Cloud Run deployment. Multi-user.
- **[`exan-desktop/`](exan-desktop/README.md)** — a single local Tauri desktop app (macOS + Windows) that bundles its own Python engine and a small on-device reading model. No accounts, no database; photos never leave the computer.

Change the code once and ship for web, macOS, and Windows. Cross-cutting docs (architecture, ADRs/preferences, provider runtime notes) live in [`docs/`](docs/); shared test fixtures in [`test/`](test/).

## Repository layout

```
/                      repo root
├── exan-web/          cloud product (webapp, auth, inference, db, terraform, docker-compose, deployment docs)
├── exan-desktop/      desktop product (one Tauri app: React UI, Rust shell, Python sidecar; macOS + Windows)
├── docs/              cross-cutting docs (strategy, architecture, ADRs/preferences, provider runtime)
├── test/              shared test fixtures
├── .github/           CI/CD workflows (test-pipeline, build-and-release, deploy-cloud-run)
├── README.md · CHANGELOG.md · .releaserc.json
```

Each product folder is self-contained: run the web stack or build a desktop app without touching the other. Follow the product README for the exact commands.

## Docs

- [ADRs / design decisions](docs/adr/)
- [Architecture](docs/ARCHITECTURE.md)
- [Provider runtime](docs/PROVIDER_RUNTIME.md)
- [Deployment (cloud)](exan-web/docs/deployment/)
- [Desktop apps overview](exan-desktop/docs/DESKTOP_APPS.md) · [Desktop options](exan-desktop/docs/DESKTOP_OPTIONS.md)
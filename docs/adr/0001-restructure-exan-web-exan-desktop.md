# 0001 — Split the repository into `exan-web` and `exan-desktop` product folders

- **Status:** Accepted
- **Date:** 2026-11-24
- **Deciders:** Francisco Susana (owner), with pi Grill Me interview
- **Related:** PR #50 (`copilot/create-native-apps-for-windows-macos`), [Desktop options](../desktop/DESKTOP_OPTIONS.md), [Deployment options](../deployment/DEPLOYMENT_OPTIONS.md)

## Context

Exan ships two delivery channels for one product:

1. **Cloud stack** (at repo root today): `webapp/` (React SPA + nginx), `auth/` (Express + JWT), `inference/` (FastAPI), `db/`, `terraform/`, `docker-compose.yml`, deployment docs, CI. Multi-user, MongoDB, providers Gemini/LM Studio.
2. **Desktop apps** (introduced in PR #50): two **duplicated** Tauri projects, `exan-macos/` and `exan-windows/`. Each has its own React UI, its own Python sidecar (bundling llama.cpp), and differs mainly in bundle ID, icons, sidecar target triple, and installer config. Single user, no accounts/database, in-memory session, CSV export.

The owner's goal is "change the code once and ship for web, macOS, and Windows". Tauri covers desktop targets (including both OSes from one app); the browser product still needs the served cloud stack. The immediate, lowest-risk improvement is to eliminate the desktop duplication and give each delivery channel a self-contained folder, before the two desktop UI copies drift further.

Constraints and expectations:

- No behavior change is intended by the move itself; CI must be updated in the same change so it can go green.
- Documentation must make it easy to tell which install/run/package guide applies to macOS vs Windows.
- The owner runs post-restructure validation ("I will make sure everything runs afterwards").

## Decision

**Restructure the repository so the root contains exactly two product folders — `exan-web/` (cloud) and `exan-desktop/` (desktop, merged) — with shared assets at the root.**

Target layout:

```
/                      repo root
├── exan-web/          cloud product
│   ├── webapp/        React SPA + nginx
│   ├── auth/          Express + JWT auth server
│   ├── inference/     FastAPI inference service
│   ├── db/            Mongo init
│   ├── terraform/     Cloud Run infrastructure
│   ├── docker-compose.yml, Dockerfile.auth
│   └── docs/          deployment guides (moved from docs/deployment)
├── exan-desktop/      desktop product (macOS + Windows, one app)
│   ├── src/           merged React UI (single copy)
│   ├── src-tauri/     one Tauri shell, two build targets
│   ├── sidecar/       one Python engine (bundling llama.cpp)
│   ├── scripts/       sidecar/runtime build tooling
│   ├── package-macos.sh, package-windows.ps1
│   └── docs/          macOS vs Windows install/run/package guides
├── docs/              cross-cutting docs (strategy, architecture, ADRs)
├── test/              shared test fixtures
├── .github/           CI/CD workflows (paths updated)
├── README.md, CHANGELOG.md, .releaserc.json
```

Sub-decisions:

- **Desktop internals merge (now):** `exan-desktop` is *one* Tauri app — one React UI, one sidecar, two build targets (`aarch64-apple-darwin`, `x86_64-pc-windows-msvc`). The `exan-macos/` copy is the merge base for the sidecar/UI; Windows-only deltas (target triple, NSIS/MSI config, bundle ID, icons) move into target-specific config in the single `src-tauri/`.
- **Per-OS guides (now):** `exan-desktop` docs clearly separate macOS and Windows install/execute/package instructions, anchored by the existing `package-macos.sh` / `package-windows.ps1` scripts.
- **Shared UI package (deferred):** extracting a React UI package consumed by both `exan-web/webapp` and `exan-desktop` is a later phase.
- **Backend contract unification (deferred):** aligning the desktop sidecar API with the `inference/` API (long-term single backend with cloud/local profiles) is a later phase.
- **Branch strategy:** the restructure runs on a **fresh branch off `main` after PR #50 merges**, as its own reviewable PR. It is not stacked onto PR #50.
- **Validation ownership:** the owner validates that everything runs after the restructure; the implementation plan includes the CI path updates (test-pipeline, build-and-release, deploy-cloud-run, `.releaserc`) needed for CI to go green.

## Options Considered

| Option | Assessment |
| --- | --- |
| **A. Two product folders, desktop merged (chosen)** | Self-contained per platform, kills desktop duplication immediately, moderate CI churn. |
| B. Status quo (root + `exan-macos/` + `exan-windows/`) | No migration cost, but duplicated UI/sidecar keep drifting; does not serve the write-once goal. |
| C. Products-only move (move `webapp/` + Tauri; `auth/`/`inference/`/`terraform/` stay root) | Less moving, but `exan-web` is not self-contained and root stays cluttered with product code. |
| D. Everything nested (docs and CI duplicated per product) | Maximum self-containment, but duplicates CI and docs maintenance. |
| E. Shared UI package from day one | Closest to "write once", but the biggest upfront abstraction risk; chosen as the deferred follow-up instead. |

## Consequences

**Positive**

- One desktop UI and one engine to maintain instead of two near-copies.
- Each product folder is self-contained; the root reads as "web | desktop | shared".
- Clear per-OS guides follow naturally from per-product docs folders.
- Deferred items are explicit follow-up phases rather than forgotten.

**Negative / risks**

- Large pure-move diff: CI workflows (`test-pipeline.yml`, `build-and-release.yml`, `deploy-cloud-run.yml`) and `.releaserc.json` must be rewritten to the new paths; a missed path in the deploy workflow only breaks at release time.
- Terraform and deployment docs reference root-relative paths (e.g., `MONGO_URI` secrets docs) that must be repointed into `exan-web/`.
- Merging the two desktop UIs may hide small per-OS drift (e.g., HEIC support notes are macOS-only).
- Windows packaging still requires a Windows machine or a new CI matrix job (desktop has no CI today).
- Web/desktop UI sharing remains duplicated until the deferred phase lands.

## Follow-ups

1. Merge PR #50 → create fresh branch → execute the restructure implementation plan.
2. Update CI workflow paths and verify green on the restructure PR.
3. Later phase: shared React UI package for `exan-web` + `exan-desktop`.
4. Later phase: unify sidecar ≈ inference API contract; optional cloud/local backend profiles.
5. Optional: desktop CI matrix job (macOS runner, Windows runner) for automated installer builds.

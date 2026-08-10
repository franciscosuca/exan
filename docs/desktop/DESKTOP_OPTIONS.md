# Local and Desktop Distribution Options

This document evaluates how to turn Exan from a hosted web application into a **local application for macOS and Windows that runs inference against an LLM on the user's own machine**, and records the recommendation, the trade-offs of each shell (PWA, Electron, Tauri, native), the packaging decision for the Python inference service, and the migration steps.

It is the local-first counterpart to [First release deployment options](../deployment/DEPLOYMENT_OPTIONS.md). That document decides *where to host* Exan for beta testers; this one decides *how to ship* Exan onto a machine. They are two distribution channels for one codebase, not alternatives — the hosted beta keeps serving cloud providers while the desktop build serves privacy-sensitive and offline users.

## Table of Contents

- [Summary](#summary)
- [What "Local" Has to Mean Here](#what-local-has-to-mean-here)
- [Why a Hosted Page Cannot Drive a Local LLM](#why-a-hosted-page-cannot-drive-a-local-llm)
- [Shell Options](#shell-options)
  - [Option 1: PWA over a locally served Exan (recommended first step)](#option-1-pwa-over-a-locally-served-exan-recommended-first-step)
  - [Option 2: PWA on a public origin calling the local LLM from the browser](#option-2-pwa-on-a-public-origin-calling-the-local-llm-from-the-browser)
  - [Option 3: Electron desktop app](#option-3-electron-desktop-app)
  - [Option 4: Tauri v2 desktop app (recommended target)](#option-4-tauri-v2-desktop-app-recommended-target)
  - [Option 5: Native app per platform](#option-5-native-app-per-platform)
  - [Option 6: Installer that wraps Docker Desktop](#option-6-installer-that-wraps-docker-desktop)
- [Comparison Table](#comparison-table)
- [Is Electron "Basically a Rewrite"?](#is-electron-basically-a-rewrite)
- [Packaging the Python Inference Service](#packaging-the-python-inference-service)
- [Fastest Stack vs. Most Optimal Stack](#fastest-stack-vs-most-optimal-stack)
- [Recommended Roadmap](#recommended-roadmap)
- [Cross-Cutting Concerns](#cross-cutting-concerns)
- [Cloud Blockers, Inverted](#cloud-blockers-inverted)
- [Risks and Open Questions](#risks-and-open-questions)
- [Rollout Checklist](#rollout-checklist)

## Summary

**Recommendation: ship in two stages — first make the existing stack installable as a PWA over a *locally served* origin, then build a Tauri v2 shell around the same React code with the FastAPI service bundled as a sidecar process.**

- **The local LLM constraint decides everything.** Ollama (`:11434`) and LM Studio (`:1234`) listen on the *user's* loopback interface. Whatever calls them must run on the user's machine. Inside a Cloud Run container, `localhost` is the container — not the teacher's laptop — so no amount of hosted-frontend work reaches a local model.
- **The PWA is the fastest deliverable, but only over a local origin.** Installed from `http://localhost:3000`, the PWA is same-origin with a local `inference` service and needs no browser exceptions at all. Installed from a public HTTPS origin and pointed at `http://localhost:11434`, it depends on three moving browser policies (mixed content, local network access permissions, and the provider's own CORS allowlist) for the product's core promise. That is a bad foundation, so **Option 2 is not the primary path**.
- **Electron is not a rewrite.** `webapp/` is a plain Vite SPA and loads unchanged in either shell. The real work — supervising the Python process, replacing `auth/` + MongoDB with local identity, packaging, signing, and auto-update — is roughly 80–90 % of the effort and is *shell-agnostic*. That makes the Electron-vs-Tauri decision cheap and reversible, which is why it should not block starting.
- **Fastest desktop stack:** Electron + `electron-vite` + `electron-builder`, with `inference/` frozen by PyInstaller. One JavaScript toolchain, no new language, and the most heavily documented notarization and auto-update path.
- **Most optimal desktop stack:** Tauri v2 + `@tauri-apps/cli` + the *same* PyInstaller binary as a sidecar. Roughly an order of magnitude smaller shell, lower idle memory, a capability-scoped IPC surface, and one codebase producing macOS (Apple silicon and Intel), Windows, and Linux artifacts.
- **One codebase for every desktop platform is achievable with either shell.** Both build from a single `desktop/` project plus the shared `webapp/` UI. Options that fail this requirement (SwiftUI + WinUI, or any framework that discards React) are rejected in [Option 5](#option-5-native-app-per-platform).
- **The long-term prize is deleting Python from the client.** Porting `inference/` document processing and provider calls to TypeScript would remove the sidecar, the freeze step, and most of the installer size, leaving one language and one artifact. It is a significant piece of work and is explicitly **not** required for v1 — see [Phase 4](#phase-4-optional-remove-the-python-sidecar).

## What "Local" Has to Mean Here

Today's runtime is four containers from `docker-compose.yml`. A desktop build must decide the fate of each one, because "install the app" cannot mean "install four servers and a database".

| Service today | Role in the hosted stack | Fate in a desktop build |
|---------------|--------------------------|-------------------------|
| `webapp` (nginx + Vite build) | Serves the SPA and reverse-proxies `/api/*` | nginx disappears. The shell loads the built assets directly and the proxy becomes a base-URL setting. |
| `inference` (FastAPI) | Document processing, provider registry, grading | **Stays, and becomes the hard part.** Ships as a bundled binary started and supervised by the shell, bound to `127.0.0.1` on an ephemeral port. |
| `auth-server` (Express + JWT) | Multi-user login | **Removed for v1.** A single-user desktop app has no accounts to separate; identity becomes an OS-level profile and secrets move to the OS keychain. |
| `mongodb` | User storage | **Removed for v1.** Bundling `mongod` costs hundreds of megabytes to persist a username. Use a local file or SQLite if durable history is ever needed. |

Two properties of the current code make this easier than it looks, and both are consequences of decisions already recorded in [ARCHITECTURE.md](../ARCHITECTURE.md):

- `ExamRepository` keeps workflow state in process memory. On a server that is [Blocker 1](../deployment/DEPLOYMENT_OPTIONS.md#blockers-to-resolve-before-the-beta); on a single-user desktop app it is simply correct.
- Every provider already implements the same `BaseProvider` contract, and `get_available_providers()` already probes Ollama and LM Studio over HTTP. Local inference is not a new feature — it is an existing feature that the hosted topology cannot expose.

Three properties actively block packaging and must be changed:

- `webapp/src/lib/api.ts` and `webapp/src/auth.api.ts` hard-code `const API_BASE = '/api'`, which only resolves when something serves the SPA and the API on one origin.
- `inference/app/main.py` allows exactly one CORS origin, `http://localhost:5173`. A desktop shell loads the UI from a custom scheme or a loopback port, so this must become configurable.
- `inference/app/utils/run_logging.py` resolves `LOG_ROOT` relative to the source tree. Inside a signed macOS bundle or `C:\Program Files`, that path is read-only; logs must move to the per-user application-data directory.

## Why a Hosted Page Cannot Drive a Local LLM

```
  HOSTED (today)                              LOCAL (required for a local LLM)

  Browser ─── HTTPS ──▶ Firebase/Cloud Run    Shell/Browser ──▶ inference (127.0.0.1)
                             │                                        │
                             ▼                                        ▼
                        localhost = the container            localhost = the user's machine
                             ✗                                        │
                        Ollama / LM Studio                   Ollama :11434 / LM Studio :1234
                        are on the user's machine                     ✓
```

There are exactly two ways to close that gap:

1. **Move the caller onto the user's machine** — a local `inference` process (Options 1, 3, 4, 6). The browser or shell keeps talking to one local origin, and the existing Python providers reach the model over loopback exactly as they already do in development.
2. **Make the browser itself call the model** (Option 2). This bypasses `inference/` entirely, which also means bypassing PDF rendering, `.docx` extraction, prompt construction, and response parsing — all of which live in Python today.

Option 1 preserves the codebase. Option 2 requires re-implementing the inference pipeline in TypeScript *and* winning three browser-policy arguments. That asymmetry is the core finding of this document.

## Shell Options

### Option 1: PWA over a locally served Exan (recommended first step)

**Shape:** Add a web app manifest and a service worker to `webapp/` (via `vite-plugin-pwa`). The user runs the stack locally — `docker compose up` today, a one-click installer later — opens `http://localhost:3000`, and installs it from the browser. The installed window is same-origin with nginx, which proxies to the local `inference` container, which reaches Ollama or LM Studio over loopback.

**Pros**

- **Smallest possible change.** No new language, no new build target, no packaging pipeline, no signing. The PWA additions are confined to `webapp/`, and the browser build is unaffected.
- **No browser-policy exposure.** Same-origin `fetch` to `/api/*` over `http://localhost` avoids mixed content, local network access prompts, and provider CORS configuration entirely.
- **Real app affordances:** dedicated window, dock/taskbar icon, own launch surface, and offline caching of the SPA shell.
- **One artifact for every platform**, including Linux and tablets, with zero per-platform build work.
- **It is a stepping stone, not a detour.** Everything it forces — a configurable API base URL, provider settings in the UI, an offline-capable build — is required by the desktop shells too.

**Cons**

- **It does not solve distribution.** The user still has to install and start the backend. Without Phase 2's installer this only helps people who already run Docker or the dev toolchain, which is not the target audience of the issue.
- Service worker caching must exclude `/api/*`; caching a grading response would be a correctness bug.
- An installed PWA cannot spawn or supervise the Python process, manage models, or read files outside the picker — the capabilities that make a desktop build worth doing.
- Desktop install support is uneven across browsers (Chromium-based browsers are the reliable target), and installed-PWA behaviour on macOS is comparatively recent.
- Offline caching of the shell does not make the app work offline; that depends on the local model being present.

**Verdict:** the fastest way to give users something installable, and a prerequisite for everything else. Ship it, but do not present it as the answer to "install Exan and connect it to my LLM".

### Option 2: PWA on a public origin calling the local LLM from the browser

**Shape:** Keep the SPA on the hosted origin from [DEPLOYMENT_OPTIONS.md](../deployment/DEPLOYMENT_OPTIONS.md), and have the installed PWA call `http://localhost:11434` (Ollama) or `http://localhost:1234/v1` (LM Studio) directly from JavaScript.

**Pros**

- Zero installation of Exan itself; the user installs only the model runtime.
- Updates ship instantly from the web, with no signing, notarization, or release binaries.
- Inference data never leaves the machine even though the app is hosted.

**Cons**

- **Three browser policies stand in the way, and none of them are ours.** A secure page requesting an insecure URL is subject to mixed-content rules that treat loopback inconsistently across engines; Chromium is adding explicit local network access restrictions with a user permission prompt for exactly this pattern; and the request is cross-origin, so it also needs the model server's consent.
- **The user must reconfigure their model runtime.** Ollama only accepts browser origins listed in `OLLAMA_ORIGINS`, so every user must set an environment variable and restart the service before the product works. LM Studio requires its equivalent CORS toggle. "Install the app and it just works" is not achievable.
- **It abandons `inference/`.** PDF-to-image rendering (PyMuPDF), `.docx` extraction, prompt templates, JSON repair, and run logging would have to be re-implemented in TypeScript before a single exam could be graded this way — the same rewrite as [Phase 4](#phase-4-optional-remove-the-python-sidecar), but with none of the packaging benefits and with the browser's memory limits applied to multi-page PDF rasterisation.
- **No fallback.** If a browser tightens loopback access, the product breaks for everyone at once, remotely, with no version pinning.
- Cloud providers still need a key path, so the hosted backend does not actually go away.

**Verdict:** **not recommended as the product's local-LLM story.** It is a legitimate *convenience* feature to add later (a "connect to my local model" toggle for advanced users who accept configuring `OLLAMA_ORIGINS`), but building the desktop strategy on browser policies that are actively being tightened is a poor bet.

### Option 3: Electron desktop app

**Shape:** A `desktop/` workspace using `electron-vite` for the main/preload/renderer build and `electron-builder` for packaging. The renderer loads the existing `webapp/` build. The main process spawns the frozen `inference` binary on an ephemeral loopback port, injects the port into the renderer through a context-isolated preload bridge, and terminates the child on quit.

**Pros**

- **One language and one toolchain.** Everything is TypeScript, which matches the repo's existing `tsx`/Vite/Bun setup; no third language enters the build.
- **Deterministic rendering.** Chromium is bundled, so the Tailwind 4 UI renders identically on both platforms and on old OS versions, and there is a single browser target to test against.
- **The most mature packaging ecosystem:** `electron-builder` handles DMG/NSIS/AppImage, macOS notarization, Windows signing, and delta auto-updates via `electron-updater` with well-trodden recipes.
- Full Node.js in the main process — child process supervision, file system access, `safeStorage` for API keys, and native dialogs are all first-party.
- Largest hiring/knowledge pool and the most StackOverflow answers per problem, which matters for a one-maintainer project.

**Cons**

- **Ships an entire browser.** A minimal Electron app is on the order of 100 MB before the Python sidecar; idle memory is measured in hundreds of megabytes.
- **Security posture is opt-in.** `nodeIntegration`, `contextIsolation`, `sandbox`, CSP, and `will-navigate`/`setWindowOpenHandler` guards must all be configured correctly; the defaults have historically been permissive.
- Chromium and Node upgrades arrive on Electron's fast release cadence, and staying current is ongoing maintenance rather than a one-off.
- Ships a second JavaScript runtime alongside the Python one, so the installer carries two interpreters for an app whose UI is a three-step form.

**Verdict:** the **fastest credible desktop delivery**, and a perfectly defensible permanent choice. Pick it if the priority is a signed installer in testers' hands with the least new knowledge required.

### Option 4: Tauri v2 desktop app (recommended target)

**Shape:** A `desktop/` project built with `@tauri-apps/cli`. The window renders the same `webapp/` build in the platform WebView (WebView2 on Windows, WKWebView on macOS, WebKitGTK on Linux). The frozen `inference` binary is declared as a Tauri **sidecar**, so the CLI copies it into the bundle per target triple and the app spawns it under a capability-scoped permission.

**Pros**

- **Dramatically smaller and lighter shell.** The WebView is the operating system's, so the shell itself is single-digit megabytes rather than ~100 MB, and idle memory is a fraction of Electron's. With a multi-gigabyte model on disk this is not the decisive argument, but it is real for download, update, and disk footprint.
- **Security by construction.** The frontend has no Node, no filesystem, and no process API unless a capability explicitly grants it; the IPC surface is an allowlist rather than an opt-out.
- **First-class sidecar support** — exactly the primitive this architecture needs — plus official plugins for the updater, dialogs, filesystem, shell, and secure storage.
- Cross-compilation targets and CI recipes for macOS (Apple silicon and Intel, including universal binaries), Windows, and Linux from one project.
- Rust exposure stays small: the sidecar spawn, a couple of commands, and configuration. It is not a Rust application with a React skin.

**Cons**

- **A third language in the repository.** Rust and `cargo` must be installed locally and in CI, and any native dependency issue is debugged in a language nobody here writes daily.
- **Two rendering engines to support.** WKWebView on macOS tracks the OS's WebKit version, so a user on an old, unpatched macOS can get a different — and with Tailwind CSS 4's modern-baseline features, potentially broken — UI. Chromium-only assumptions in the current CSS have to be validated on Safari's engine.
- Windows requires the WebView2 runtime; it is present on current Windows 11 and widely deployed on Windows 10, but the installer should still carry the evergreen bootstrapper.
- Smaller ecosystem and fewer worked examples than Electron; plugin gaps are solved by writing Rust.
- Slower first build (`cargo` compilation) and an extra cache to manage in CI.

**Verdict:** **the recommended end state.** It produces the leanest single-codebase artifact for macOS, Windows, and Linux, and its permission model is the right default for an app that handles student work. The Rust surface is small enough for a project that already spans TypeScript and Python, and the sidecar primitive matches the architecture exactly.

### Option 5: Native app per platform

**Shape:** SwiftUI on macOS and WinUI/WPF on Windows, sharing only the Python service — or a rewrite into Flutter, .NET MAUI, or Qt.

**Pros**

- Best-in-class platform integration, smallest binaries, native file pickers and menus.
- No WebView dependency and no bundled browser.

**Cons**

- **Fails the stated requirement outright.** SwiftUI + WinUI is two UI codebases plus the web one — three implementations of the same three-step workflow.
- Flutter, MAUI, and Qt do satisfy "one codebase", but only by **discarding `webapp/` entirely**: every component, the Tailwind design system in [`.github/DESIGN.md`](../../.github/DESIGN.md), the i18n layer, and the Vitest suite would be rewritten in Dart, C#, or C++/QML, and the hosted web build would then diverge from the desktop build forever.

**Verdict:** rejected. Any option that does not reuse `webapp/` pays for the desktop app by creating a second product to maintain.

### Option 6: Installer that wraps Docker Desktop

**Shape:** Ship a small launcher that installs Docker Desktop, runs the existing `docker-compose.yml`, and opens a browser window at `http://localhost:3000`.

**Pros**

- Truly zero application changes — the compose file, nginx, and all four services run exactly as they do today.
- Could be prototyped in a day, and is a reasonable *internal* distribution for technical pilot users.

**Cons**

- Docker Desktop requires administrator rights, is licensed for commercial use above a company-size threshold, and consumes gigabytes of disk and a persistent VM's worth of RAM before Exan starts.
- Container start-up is far too slow for a double-click app, and a failed pull or an occupied port surfaces as a Docker error to a teacher.
- It is not "an application" in any sense the user recognises: no icon, no updates, no uninstall story, and `mongodb` and `auth-server` are still running for no benefit.

**Verdict:** rejected as a product. Keep `docker-compose.yml` as the developer and self-hosting path, which is what [DEPLOYMENT_OPTIONS.md](../deployment/DEPLOYMENT_OPTIONS.md) already assumes.

## Comparison Table

| Criterion | 1. Local PWA | 2. Hosted PWA → local LLM | 3. Electron | 4. Tauri v2 | 5. Native | 6. Docker wrapper |
|-----------|--------------|---------------------------|-------------|-------------|-----------|-------------------|
| Reuses `webapp/` unchanged | Yes | Yes (UI only) | Yes | Yes | No | Yes |
| Reuses `inference/` unchanged | Yes | **No — full port** | Yes (bundled) | Yes (bundled) | Yes | Yes |
| One codebase, all desktops | Yes | Yes | Yes | Yes | **No / rewrite** | Yes |
| User installs a real app | Partly | Partly | Yes | Yes | Yes | No |
| Backend installed for the user | **No** | N/A | Yes | Yes | Yes | Via Docker |
| Depends on browser policy | No | **Yes, heavily** | No | No | No | No |
| Needs `OLLAMA_ORIGINS` set by user | No | **Yes** | No | No | No | No |
| Shell footprint | ~0 | ~0 | ~100 MB | Single-digit MB | Smallest | GBs |
| New language required | None | None | None | Rust (small) | Swift/C#/Dart | None |
| Code signing required | No | No | Yes | Yes | Yes | Yes |
| Auto-update story | Browser | Browser | `electron-updater` | Updater plugin | Per platform | None |
| Relative effort | **Days** | Weeks + rewrite | Weeks | Weeks + toolchain | Months | Days |
| **Verdict** | **Phase 1** | Later opt-in only | Fast fallback | **Recommended** | Rejected | Dev only |

## Is Electron "Basically a Rewrite"?

No — and this is the most expensive misconception to carry into planning.

`webapp/` is a standard Vite SPA with no server-side rendering and no Node-specific code. Both Electron and Tauri load a built SPA from disk. The renderer keeps React 19, Tailwind 4, `lucide-react`, `react-dropzone`, the i18n layer, and the existing Vitest suite untouched.

What genuinely has to be built, in either shell:

| Work item | Where | Shell-specific? |
|-----------|-------|-----------------|
| Configurable API base URL instead of `const API_BASE = '/api'` | `webapp/src/lib/api.ts`, `webapp/src/auth.api.ts` | No |
| Settings UI for provider, base URLs, model, and API keys | `webapp/src/components/` | No |
| Remove or bypass the login gate in `App.tsx` when running locally | `webapp/src/App.tsx` | No |
| Freeze `inference/` into a self-contained binary | `inference/` + build script | No |
| Bind the service to `127.0.0.1` on an ephemeral port with a per-launch token | `inference/app/main.py` | No |
| Make CORS origins configurable | `inference/app/main.py` | No |
| Move `LOG_ROOT` to the OS application-data directory | `inference/app/utils/run_logging.py` | No |
| Store API keys in the OS keychain instead of `.env` | `inference/app/config.py` + shell | Partly |
| Spawn, health-check, and terminate the sidecar | `desktop/` | **Yes** |
| Window, menus, deep links, native dialogs | `desktop/` | **Yes** |
| Installer, signing, notarization, auto-update, CI matrix | `desktop/` + `.github/workflows/` | Partly |

Only three rows are genuinely shell-specific, and they are the smallest ones. **The shell choice is roughly 10–20 % of the work and is reversible**, which is precisely why it should not delay Phase 1 — and why "start with Electron, move to Tauri later" is a legitimate strategy rather than wasted effort.

## Packaging the Python Inference Service

This is the real cost of the desktop build, and it is identical for Electron and Tauri. The service depends on PyMuPDF, Pillow, `python-docx`, `httpx`, `uvicorn`, and the Gemini, Anthropic, and OpenAI SDKs — all of which must land on a machine that has no Python.

| Approach | How it works | Pros | Cons | Fit |
|----------|--------------|------|------|-----|
| **PyInstaller** (recommended) | Freezes `app/` plus dependencies into a one-folder or one-file bundle per platform | Mature, handles native wheels, well-documented signing workflow, ships a plain executable that both shells can spawn | Hidden-import and data-file tuning for native packages; must build on each target OS; one-file mode extracts to a temp dir at start-up and is slower | **Yes** |
| **Standalone CPython** (`uv python install` / python-build-standalone) | Ship a relocatable interpreter plus a virtual environment | Simple, no freezing magic, closest to the development environment, easy to debug | Larger and more files; needs careful relocation and hardened-runtime handling on macOS | Good fallback |
| **Nuitka** | Compiles to C and then to a native binary | Fastest start-up, hardest to trivially inspect | Longest builds, more packaging edge cases with native extensions | If start-up becomes a problem |
| **Require Python on the user's machine** | Call the system interpreter | Trivial build | Unacceptable for teachers; version and dependency drift | No |
| **Port `inference/` to TypeScript** | Delete the sidecar entirely | One language, one artifact, smallest install, no freeze step | Re-implements PDF rasterisation, `.docx` extraction, prompts, and parsing; loses the Python AI SDK ecosystem | [Phase 4](#phase-4-optional-remove-the-python-sidecar) |

Regardless of approach, the sidecar contract should be:

- **Bind to `127.0.0.1` on port `0`** and report the chosen port to the shell on stdout. Never listen on `0.0.0.0`; a desktop app that exposes an unauthenticated grading API to the local network is a security bug, and it is the same mistake as the published ports flagged in [Blocker 4](../deployment/DEPLOYMENT_OPTIONS.md#blockers-to-resolve-before-the-beta).
- **Require a per-launch shared secret** in an `Authorization` header, generated by the shell and passed to the child through its environment, so other local processes and any browser page cannot drive it.
- **Be supervised**: health-checked on start-up, restarted on crash with a visible error state, and killed on quit — including on force-quit, so no orphan uvicorn survives.
- **Write logs and temporary files to the OS application-data directory**, never next to the executable.

Expect the frozen service, not the shell, to dominate the installer. Measure it early: the exact figure decides whether the download is "a big app" or "an unreasonable download", and it is the main input into whether [Phase 4](#phase-4-optional-remove-the-python-sidecar) is worth doing.

## Fastest Stack vs. Most Optimal Stack

The issue asks for both. They are different answers, and the gap between them is small enough that starting with the fast one is not a trap.

**Fastest to deliver**

1. **Days:** [Option 1](#option-1-pwa-over-a-locally-served-exan-recommended-first-step) — `vite-plugin-pwa` in `webapp/`, a manifest, an installable local origin. Delivers "download the app from the browser" for anyone already running the stack.
2. **Weeks:** [Option 3](#option-3-electron-desktop-app) — Electron + `electron-vite` + `electron-builder` + PyInstaller. No new language, the best-documented signing and update path, and the shortest distance from the current repo to a signed `.dmg` and `.exe`.

**Most optimal**

[Option 4](#option-4-tauri-v2-desktop-app-recommended-target) — Tauri v2 + `@tauri-apps/cli` + the same PyInstaller binary as a sidecar. Best installer size, lowest memory, strictest default security model, and one project producing every desktop target. The cost is a Rust toolchain in CI and validating the UI on WKWebView as well as Chromium.

**How to choose**

- If a signed build must be in testers' hands within a month and nobody wants to touch Rust → **Electron**, and revisit later. Because the sidecar, settings, keychain, and CI work all carry over, switching costs weeks, not months.
- If the desktop app is a long-lived product surface and a few days of toolchain setup are acceptable → **Tauri v2** directly, and skip the migration.
- **In both cases, do Phase 1 first.** It is cheap, it de-risks the API-base-URL and settings work that both shells need, and it ships something to users immediately.

## Recommended Roadmap

### Phase 0: Make local inference first-class in the current app

*Prerequisite for every option; useful on its own.*

1. Replace `const API_BASE = '/api'` in `webapp/src/lib/api.ts` and `webapp/src/auth.api.ts` with a resolved base URL (build-time default, runtime override).
2. Add a settings surface for provider selection, Ollama/LM Studio base URLs, model name, and cloud API keys, instead of requiring edits to `inference/.env`.
3. Make `inference/app/main.py` CORS origins configurable through settings.
4. Move `LOG_ROOT` in `inference/app/utils/run_logging.py` to a configurable, per-user writable directory.
5. Surface local-provider availability and a clear "Ollama not detected" state in `ProviderSelector`, using the probe that `get_available_providers()` already performs.

### Phase 1: Installable PWA over the local origin

1. Add `vite-plugin-pwa` to `webapp/`, with a manifest, icons, and a theme colour aligned to `.github/DESIGN.md`.
2. Precache the app shell; explicitly exclude `/api/*` from runtime caching.
3. Document the install flow and the local-LLM setup in `README.md`.
4. Add a component test asserting the manifest link and that API routes are not cached.

### Phase 2: Package `inference/` as a standalone binary

1. Add a PyInstaller spec and a build script producing a binary per target triple.
2. Add the `--host 127.0.0.1 --port 0` + port-reporting + shared-secret start-up contract.
3. Verify PyMuPDF, Pillow, and `python-docx` work from the frozen bundle on macOS and Windows, with the existing `pytest` suite run against the packaged binary.
4. Record the resulting size and cold-start time; both feed the Phase 4 decision.

### Phase 3: Desktop shell

1. Create `desktop/` with the chosen shell (Tauri v2 recommended; Electron if speed dominates).
2. Load the `webapp/` build, spawn and supervise the sidecar, and pass the port and secret to the renderer through the shell's secure bridge.
3. Replace the login gate with a local profile; store cloud API keys in the OS keychain.
4. Add a GitHub Actions matrix (macOS arm64 + x64, Windows x64) that builds, signs, notarizes, and publishes artifacts, extending the existing `build-and-release.yml` release flow rather than replacing it.
5. Ship the updater, an "offline mode" indicator, and a first-run check that detects Ollama or LM Studio and links to their installers.

### Phase 4 (optional): Remove the Python sidecar

Only if Phase 2 shows the installer is unacceptably large or the frozen build proves fragile. Port `file_processing`, `prompts`, the provider adapters, and the workflow services to TypeScript, using `pdf.js` for rasterisation and the official JavaScript SDKs for the cloud providers. The result is one language, a single small artifact, and a shell whose size is measured in megabytes — at the cost of losing the Python AI ecosystem and maintaining two implementations during the transition.

## Cross-Cutting Concerns

| Concern | What it means for Exan |
|---------|------------------------|
| **Code signing** | macOS distribution outside the App Store needs a paid Apple Developer account, a Developer ID certificate, hardened runtime, and notarization — bundled interpreters are exactly what notarization scrutinises. Windows needs a code-signing certificate whose key lives in hardware or a cloud signing service; unsigned installers trigger SmartScreen warnings that a teacher will not click through. Budget for both before promising a release date. |
| **Auto-update** | Both shells have first-party updaters backed by signed release feeds. Do this in Phase 3, not later: an un-updatable desktop app strands users on a broken build. |
| **CI** | Desktop artifacts must be built on their own OS. Add a matrix job on macOS (Apple silicon and Intel runners) and Windows alongside the current `webapp-tests` and `inference-tests` jobs, and keep signing secrets out of pull-request builds. |
| **Security** | The desktop threat model replaces "authenticate every HTTP request" with "do not expose anything beyond loopback". Bind to `127.0.0.1`, require the per-launch secret, keep `contextIsolation`/capabilities strict, set a CSP that only permits the local API and configured provider hosts, and keep API keys in the OS keychain rather than a `.env` file next to the binary. |
| **Model management** | Exan should detect Ollama/LM Studio and guide installation rather than bundle a runtime: a vision-capable model is a multi-gigabyte download and bundling one would dwarf the app. Show model presence, RAM guidance, and a link to pull the model. |
| **Hardware reality** | Local vision models need substantial RAM, and grading is far slower on a laptop than on a hosted API. Set expectations in the UI, keep cloud providers available as the fast path, and make long-running grading cancellable. |
| **Licensing** | Confirm the licence and redistribution terms of anything shipped in the installer — the frozen Python dependencies in particular — before publishing binaries. |
| **The hosted build stays** | Nothing here removes the cloud path. `webapp/` serves both, and the desktop build is a second consumer of the same UI and the same inference service. |

## Cloud Blockers, Inverted

The desktop target neutralises most of the [beta blockers](../deployment/DEPLOYMENT_OPTIONS.md#blockers-to-resolve-before-the-beta) — and replaces them with a different, smaller set.

| Cloud blocker | On desktop |
|---------------|------------|
| 1. In-memory workflow state | **Resolved.** One user, one process; `ExamRepository` is the right design. |
| 2. 32 MiB upload limit | **Resolved.** No platform request limit on loopback. |
| 3. Unauthenticated inference endpoints | **Changed.** Replaced by loopback binding plus a per-launch secret. |
| 4. Published ports | **Critical.** The sidecar must never listen beyond `127.0.0.1`. |
| 5. Long grading requests | **Resolved.** No 60-second proxy ceiling; local inference is simply slow and must be cancellable. |
| 6. Secrets | **Changed.** No `JWT_SECRET` or Mongo credentials at all; provider keys move to the OS keychain. |
| 7. Logs | **Changed.** Must write to the user's application-data directory, not the app bundle. |
| 8. Local providers unreachable | **Inverted.** They become the point of the product. |
| — | **New:** code signing, notarization, auto-update, per-OS CI, installer size, and support for machines that cannot run a vision model. |

## Risks and Open Questions

- **Frozen-bundle size and start-up time are unknown** until Phase 2 measures them; they determine whether Phase 4 is optional or necessary.
- **PyMuPDF and Pillow under PyInstaller** are the most likely packaging friction points and should be spiked before committing to a date.
- **WKWebView compatibility** with the Tailwind 4 CSS baseline needs verification on the oldest macOS version we intend to support; this is the main technical reason to choose Electron instead.
- **Signing cost and lead time** (Apple enrolment, Windows certificate issuance and identity validation) are calendar risks, not engineering ones. Start them in parallel with Phase 2.
- **Which auth model survives on desktop** is a product decision: fully local single-user, or optional sign-in that syncs settings with the hosted deployment.
- **Support burden** shifts from a server we control to laptops we do not; add opt-in diagnostics before the first public build.

## Rollout Checklist

- [ ] Confirm the target OS versions for macOS and Windows, and whether Linux is in scope.
- [ ] Complete Phase 0 so the hosted app, the PWA, and the desktop shell share one configuration path.
- [ ] Ship the installable PWA and document the local-LLM setup.
- [ ] Spike PyInstaller on macOS and Windows; record binary size, cold-start time, and any native-dependency workarounds.
- [ ] Decide Electron vs. Tauri from that spike plus the WKWebView check, and record the decision here.
- [ ] Start Apple Developer enrolment and Windows code-signing certificate procurement.
- [ ] Build the `desktop/` shell with sidecar supervision, loopback binding, and the per-launch secret.
- [ ] Replace the login gate with a local profile and move provider keys to the OS keychain.
- [ ] Add the signed, notarized release matrix to CI and verify auto-update end to end.
- [ ] Smoke-test the full workflow (template, answer key, grading, batch evaluation) against Ollama and LM Studio on a clean macOS and a clean Windows machine.

> Browser policies for loopback access, platform signing requirements, and framework version support all change frequently. Re-verify the constraints in [Option 2](#option-2-pwa-on-a-public-origin-calling-the-local-llm-from-the-browser) and [Cross-Cutting Concerns](#cross-cutting-concerns) against current vendor documentation before committing to a plan.

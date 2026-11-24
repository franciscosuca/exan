# Exan for macOS and Windows

Correct exams locally, without a server, account, or database. You photograph or scan the answer key and the participants' answer sheets. A small OCR or vision model that runs **on your computer** reads the answers, and Exan grades every participant against the key. Photos never leave the computer, except when you choose to send them from your phone to the computer over your own Wi‑Fi.

**Exan Desktop is one Tauri app with two build targets:** the same React UI, the same Rust shell and the same Python engine ship as `Exan.app` (macOS) and `Exan_*_x64-setup.exe`/`.msi` (Windows). The two OSes differ only in bundle configuration (`src-tauri/tauri.*.conf.json`), installer art (`src-tauri/windows/`), packaging scripts and two UI strings.

| | macOS | Windows |
|---|---|---|
| Install/run/package guide | [docs/MACOS.md](docs/MACOS.md) | [docs/WINDOWS.md](docs/WINDOWS.md) |
| Packaging script | `./package-macos.sh` | `.\package-windows.ps1` |
| Build targets | `.app` + `.dmg` | NSIS `-setup.exe` + `.msi` |
| WebView | WKWebView | WebView2 |

## How it works

```
┌──────────── Exan ──────────────────────────────────┐
│ Tauri v2 shell (Rust)                              │
│  ├─ React UI: Key → Participants → Results         │
│  └─ starts/stops the engine (exan-sidecar)         │
│        Python + FastAPI, 127.0.0.1:<random port>,  │
│        random secret per start, data in memory     │
│          └─ starts llama-server (bundled llama.cpp │
│             runtime), 127.0.0.1 only               │
└───────────────┬────────────────────────────────────┘
                │ or: Ollama (:11434) / LM Studio (:1234)
     model files in the OS application-data directory (com.exan.desktop/models)
```

- **No accounts and no database.** One correction session lives in memory. *New correction* clears it. CSV export is the only file Exan writes, apart from settings and logs.
- **One feature:** compare the answer key with each participant's answers. You can fix any recognised answer by hand or override a verdict before exporting.
- **Photos** come from a file picker / drag and drop, or **from your phone**: the app shows a QR code, the phone opens a small upload page served by your computer on the local network, and the photos appear immediately. Supported formats: JPG, PNG, WEBP, TIFF and PDF; HEIC is macOS-only.

## Models

No model is part of the installer, so it stays small. The recommended model (Granite‑Docling 258M, IBM) is preselected; nothing is downloaded until you tick the consent box. Each file is pinned to a Hugging Face repository revision and checked with SHA‑256 (`sidecar/exan_sidecar/engine/models.json`). The built-in runtime is a pinned [llama.cpp](https://github.com/ggml-org/llama.cpp) build (`scripts/runtime.lock.json`, SHA‑256 checked on fetch). [Ollama](https://ollama.com/download) and [LM Studio](https://lmstudio.ai) remain an alternative under Settings → Local model runtime.

| Built-in model | Download | RAM | Licence | Reads |
|---|---|---|---|---|
| Granite‑Docling 258M (IBM) ★ recommended | 0.28 GB | 4 GB | Apache‑2.0 | printed and typed text; often misses short handwritten answers |
| PaddleOCR‑VL 1.6 (0.9B) | 1.8 GB | 6 GB | Apache‑2.0 | printed text and handwriting, copies exactly what is written |
| Qwen2.5‑VL 3B | 2.8 GB | 8 GB | Qwen Research Licence (research/evaluation only) | general vision model; also ticked or circled options |

On the macOS build the model is chosen on the app's first start (a DMG has no installer pages); the Windows installer asks during installation (`npm run installer:models` regenerates that page).

## Quick start (both platforms)

**Prerequisites:** Node.js 22+, Python 3.12, Rust. macOS also needs the Xcode command-line tools (`xcode-select --install`); Windows needs the Visual Studio Build Tools (workload *Desktop development with C++*). Ollama is optional — `npm run setup` fetches the built-in llama.cpp runtime and the app downloads a model on first start.

```bash
cd exan-desktop
npm ci
npm run setup    # once: Python venv + engine binary + llama.cpp runtime
npm start        # tauri dev (the first run compiles Rust, a few minutes)
```

For the fastest UI loop without Rust, run `npm run dev:engine` in one terminal and `npm run dev:browser` in another (see `.env.browser`).

For the full install/run/package and troubleshooting checklists, follow the per-OS guide: [macOS](docs/MACOS.md) or [Windows](docs/WINDOWS.md). `npm run check` runs every lint and test (UI + engine).

## Development

| Command | What it does |
|---|---|
| `npm run setup` | Creates `sidecar/.venv` (Python 3.11+), builds the engine binary for this machine and fetches the llama.cpp runtime |
| `npm start` | Rebuilds the engine if its sources changed, then runs `tauri dev` with hot reload |
| `npm run package` | Builds the engine and the platform artifacts (app + DMG, or NSIS + MSI; with the runtime, without models) |
| `npm run fetch:runtime` | Downloads the llama.cpp build pinned in `scripts/runtime.lock.json` (SHA‑256 checked) into `src-tauri/runtime/` |
| `npm run installer:models` | Regenerates the Windows installer's model page from `models.json`; `npm run check` fails when it is stale |
| `npm run check` | Type-check, lint and unit tests for UI and engine |
| `npm run dev:engine` + `npm run dev:browser` | Engine on `127.0.0.1:8765` and the UI in a normal browser (values in `.env.browser`) |

Layout:

```
exan-desktop/
├─ src/                React 19 + Tailwind 4 UI (lib/ = API client, store, i18n; components/ = screens)
├─ src-tauri/          Rust shell: engine supervisor (sidecar.rs), commands (lib.rs), capabilities
│                      Info.plist + Entitlements.plist (macOS), windows/ (NSIS installer files)
│                      runtime/ (llama-server + libraries, fetched, not committed)
│                      tauri.conf.json + tauri.macos.conf.json + tauri.windows.conf.json (per-OS bundle config)
├─ sidecar/            Python engine: FastAPI API, grading, parsing, image handling, built-in runtime
│                      (engine/llamacpp.py, model_store.py, models.json), Ollama/OpenAI clients,
│                      model downloads, phone upload page, PyInstaller spec, pytest suite
└─ scripts/            build-sidecar.mjs (PyInstaller → src-tauri/binaries), fetch-runtime.mjs + runtime.lock.json
                       (llama.cpp → src-tauri/runtime), installer-models.mjs (Windows), sidecar-task.mjs (venv tasks)
```

Security: the engine listens on `127.0.0.1` only. Every API call needs the random secret the shell creates on each start. The phone page is only served on the local network after you start it from the QR dialog; it accepts private-network addresses only, needs an unguessable token in the URL, and stops after inactivity or when you click *End connection*.

## License

MIT
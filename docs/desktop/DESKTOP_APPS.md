# Exan Desktop: macOS and Windows

Two standalone, local-only desktop apps: `exan-macos/` and `exan-windows/`. Both have the same layout and code. They differ only in:

- bundle config (`src-tauri/tauri.conf.json`)
- macOS-only `Info.plist` and `Entitlements.plist`
- CI workflow, README and package metadata
- two UI texts (firewall hint, HEIC support)

More detail: [macOS README](../../exan-macos/README.md) · [Windows README](../../exan-windows/README.md) · [Design decision](DESKTOP_OPTIONS.md)

## Folder structure

```
exan-macos/                         # exan-windows/ has the same layout
├── .github/workflows/build.yml     # CI: checks + installers
├── README.md
├── package.json                    # npm scripts: setup · start · check · package
├── index.html · vite.config.ts · tsconfig*.json
├── .env.browser                    # engine URL/token for browser dev mode
├── scripts/
│   ├── build-sidecar.mjs           # PyInstaller → src-tauri/binaries/
│   ├── sidecar-task.mjs            # Python venv tasks: setup · dev · test · lint
│   └── lib.mjs
├── src/                            # React UI
│   ├── App.tsx · main.tsx · index.css
│   ├── components/                 # KeyStep · ParticipantsStep · ParticipantDetail · ResultsStep
│   │                               # SettingsPanel · PhoneDialog · Dropzone · ui
│   ├── lib/                        # api · bridge (Tauri IPC) · store · i18n · types (+ tests)
│   └── test/setup.ts
├── src-tauri/                      # Rust desktop shell
│   ├── src/                        # main.rs · lib.rs (commands) · sidecar.rs (starts/stops engine)
│   ├── binaries/                   # exan-sidecar-<target> (generated, git-ignored)
│   ├── capabilities/ · icons/
│   ├── Cargo.toml · build.rs · tauri.conf.json
│   └── Info.plist · Entitlements.plist      # macOS only
└── sidecar/                        # Python engine (local API)
    ├── exan_sidecar/
    │   ├── api.py · session.py · state.py · config.py · __main__.py
    │   ├── extraction.py · parsing.py · grading.py · export.py
    │   ├── images.py · uploads.py · phone.py · phone_page.py · netutil.py · errors.py
    │   └── engine/                 # ollama · openai_compat · catalog · prompts · base
    ├── tests/                      # pytest
    └── pyproject.toml · exan-sidecar.spec · sidecar_entry.py
```

## Stack

| Layer   | macOS                                   | Windows                     |
|---------|-----------------------------------------|-----------------------------|
| Shell   | Tauri 2 (Rust) · WKWebView              | Tauri 2 (Rust) · WebView2   |
| UI      | React 19 · TypeScript 7 · Vite 8 · Tailwind 4 · Vitest · oxlint | same |
| Engine  | Python 3.12 · FastAPI/Uvicorn · Pillow · pypdfium2 · segno · httpx, frozen into one file by PyInstaller | same |
| Models  | Ollama (default) or an OpenAI-compatible server (LM Studio): `qwen2.5vl:3b`, `qwen3-vl:4b`, `granite3.2-vision:2b`, … | same |
| Package | `.app` + `.dmg` (macOS 13+)             | NSIS `-setup.exe` + `.msi`  |

## Run locally (dev mode)

**Prerequisites**

- macOS: `xcode-select --install`
- Windows: Visual Studio 2022 Build Tools → "Desktop development with C++"
- Both: Rust (rustup.rs), Node 22+, Python 3.12, Ollama (`ollama pull qwen2.5vl:3b`, or download a model in the app under Settings)

**Desktop window (hot reload)**, from the repository root:

```bash
cd exan-macos          # on Windows: cd exan-windows
npm ci
npm run setup          # once: Python venv + engine binary
npm start              # tauri dev (the first run compiles Rust, a few minutes)
```

**UI in the browser (no Rust needed, fastest loop)**

```bash
npm run dev:engine     # terminal 1 → engine on http://127.0.0.1:8765
npm run dev:browser    # terminal 2 → open http://localhost:1420
```

**Notes**

- `npm run check` runs every lint and test (UI + engine).
- Run one project at a time: both use ports 1420 and 8765.
- After editing the Python engine: `npm start` rebuilds the engine binary on its next start; in browser mode, restart `dev:engine`.

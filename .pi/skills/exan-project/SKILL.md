---
name: exan-project
description: Compact project map and guardrails for the Exan desktop apps. Use for the Python engine, built-in OCR models, React UI, Tauri packaging, Windows installer, or project tests.
disable-model-invocation: true
---

# Exan project context

Load this skill explicitly with `/skill:exan-project` when working on Exan. It is intentionally on-demand to keep unrelated Pi prompts small. This is a project map, not a substitute for checking the current code: start with `git status`, then inspect only the relevant README and files.

## Layout and architecture

- `exan-macos/` and `exan-windows/` are parallel Tauri 2 desktop apps. Keep shared source changes mirrored; preserve platform-specific configuration, i18n text, README and workflows.
- UI: `src/` (React/Vite). Setup and model management: `src/components/SetupWizard.tsx`, `SettingsPanel.tsx`, `models.tsx`; API types/client: `src/lib/types.ts`, `api.ts`.
- Shell: `src-tauri/src/` (Rust supervises the Python sidecar). The sidecar passes `EXAN_RUNTIME_DIR` and `EXAN_MODELS_DIR` to the engine.
- Engine: `sidecar/exan_sidecar/` (FastAPI, grading, OCR parsing). Built-in runtime: `engine/llamacpp.py` and `model_store.py`; pinned model catalog and Hugging Face SHA-256 values: `engine/models.json`.
- Runtime binaries are fetched, checksum-verified build artifacts in `src-tauri/runtime/`; do not commit runtime binaries or model weights. Model downloads require explicit consent and are resumable. Ollama and OpenAI-compatible servers remain optional alternatives.
- Cross-platform overview: `docs/desktop/DESKTOP_APPS.md`; detailed setup and troubleshooting: each app's `README.md`.

## Model caveat (current owner decision pending)

The smallest model, Granite-Docling 258M, is currently recommended because the owner requested the smallest option. On four project sample sheets it read at most 10/24 answers; PaddleOCR-VL 1.6 read 24/24, and Qwen2.5-VL 3B read 23/24 but once inferred the correct answer instead of faithfully transcribing the student's wrong one. Do not silently change the recommendation; ask the owner whether to prefer PaddleOCR-VL's tested accuracy. Qwen's source model uses the Qwen Research License (research/evaluation only), not Apache-2.0.

## Platform-specific packaging

- macOS uses a DMG, so model choice and consent happen in the app's first-start wizard. llama.cpp requires macOS 13.3+.
- Windows NSIS asks for model choice and consent during installation; `/S` or `/P` skips pages, while `/MODEL=<id>` selects/downloads a model for managed installs. MSI falls back to the first-start wizard. `src-tauri/windows/installer.nsi` is based on Tauri CLI 2.12.1; preserve its two `EXAN` insertion points when upgrading the CLI. Regenerate `models.nsh` from the catalog with `npm run installer:models`.
- Windows has not been runtime-tested on a Windows machine. Do not claim otherwise.

## Checks

From either app directory (Node 22+, Python 3.11+, Rust; platform native build tools required):

```sh
npm ci
npm run setup
npm run check
npm start       # Tauri dev app
npm run package # installer/bundle
```

`npm run check` covers TypeScript, oxlint, Vitest, Ruff, and pytest. Also use `(cd src-tauri && cargo fmt --check && cargo clippy --all-targets --locked -- -D warnings && cargo test --locked)` for Rust changes. Windows additionally checks the generated installer model list. `npm run setup` fetches the platform llama.cpp runtime; `npm run fetch:runtime` refreshes it.

Keep loopback services on `127.0.0.1`, keep runtime API keys out of command-line arguments, never bundle model weights, and test shared engine/UI changes in both app folders.

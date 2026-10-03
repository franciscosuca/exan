# Exan for macOS

Correct exams on your Mac without a server, account, or database. You photograph or scan the answer key and the participants' answer sheets. A small OCR or vision model that runs **on your Mac** reads the answers, and Exan grades every participant against the key. Photos never leave the computer, except when you choose to send them from your phone to the Mac over your own Wi‑Fi.

| | |
|---|---|
| Platforms | macOS 13.3 Ventura or newer, Apple Silicon (recommended) or Intel |
| Memory | 4 GB RAM for the smallest model, 8 GB for the 3B model (see [Models](#models)) |
| Reading model | **Built in**: Exan ships [llama.cpp](https://github.com/ggml-org/llama.cpp) and downloads the model you pick on the first start, after you agree. [Ollama](https://ollama.com/download) or [LM Studio](https://lmstudio.ai) still work (Settings) |
| Output | `Exan.app` and `Exan_<version>_<arch>.dmg` (about 40 MB; no model inside) |

## How it works

```
┌──────────── Exan.app ───────────────────────────────┐
│ Tauri v2 shell (Rust, WKWebView)                    │
│  ├─ React UI: Key → Participants → Results          │
│  └─ starts/stops the engine (exan-sidecar)          │
│        Python + FastAPI, 127.0.0.1:<random port>,   │
│        random secret per start, data in memory      │
│          └─ starts llama-server (bundled llama.cpp) │
│             for the chosen model, 127.0.0.1 only    │
└───────────────┬─────────────────────────────────────┘
                │ or: Ollama (:11434) / LM Studio (:1234)
     model files in ~/Library/Application Support/com.exan.desktop/models
```

- **No accounts and no database.** One correction session lives in memory. *New correction* clears it. CSV export is the only file Exan writes, apart from settings and logs.
- **One feature:** compare the answer key with each participant's answers. You can fix any recognised answer by hand or override a verdict before exporting.
- **Photos** come from Finder (drag and drop or a file picker; JPG, PNG, HEIC, WebP, TIFF and PDF) or **from your phone**. The app shows a QR code, the phone opens a small upload page served by the Mac on your local network, and the photos appear immediately.

## Models

No model is part of the app, so the download stays small. On the first start Exan shows **Choose a reading model**: the smallest model is preselected, every entry shows its download size, memory needs and licence, and nothing is downloaded until you tick *I agree that Exan downloads … from Hugging Face (huggingface.co)*. The models come from Hugging Face's overview of open OCR models (<https://huggingface.co/blog/ocr-open-models>); each file is pinned to a repository revision and checked with SHA‑256 (`sidecar/exan_sidecar/engine/models.json`):

| Built-in model | Download | RAM | Licence | Reads |
|---|---|---|---|---|
| Granite‑Docling 258M (IBM) ★ recommended | 0.28 GB | 4 GB | Apache‑2.0 | printed and typed text; often misses short handwritten answers |
| PaddleOCR‑VL 1.6 (0.9B) | 1.8 GB | 6 GB | Apache‑2.0 | printed text and handwriting, copies exactly what is written |
| Qwen2.5‑VL 3B | 2.8 GB | 8 GB | Qwen Research Licence (research/evaluation only) | general vision model; also ticked or circled options |

Measured on this project's four sample sheets (answer key plus three handwriting-style answer sheets, 24 answers) on an M5 Max: PaddleOCR‑VL read 24/24 answers (about 1.5 s per page), Qwen2.5‑VL 23/24 (about 3 s per page; it once wrote the correct answer instead of the participant's), Granite‑Docling at most 10/24 (fast, but it drops short handwritten answers and sometimes repeats itself). OCR models transcribe the page and Exan finds the answers next to the question numbers or labels such as *Antwort:*; Qwen returns JSON.

Why on the first start: Mac apps are installed by dragging them from the DMG into *Applications*, which has no installer pages, so the first start completes the installation (the Windows installer asks during installation).

Downloads resume where they stopped. **Settings → Built-in models** downloads more models (after the same consent), switches between them and removes them. **Ollama** or **LM Studio** (OpenAI‑compatible) can still be selected under Settings → Local model runtime, with the models listed there.

---

## ✅ What you need to do locally (checklist)

The code was written and tested in a Linux sandbox. The engine, the UI and the Rust shell compile there, and the engine runs there as the same frozen binary that ships in the app. **Building, signing and running the `.app` needs a real Mac**, so the following steps are still open:

1. **Install the tools (once):**
   ```bash
   xcode-select --install                                           # Apple command-line tools (clang, codesign, otool)
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh   # Rust (stable)
   brew install node@22 python@3.12                                 # or the installers from nodejs.org / python.org
   ```
   Ollama is optional now; the reading model runs in the bundled llama.cpp runtime.
2. **Get the code:** move this `exan-macos/` folder into its own repository (or `cd` into it), then:
   ```bash
   npm ci
   npm run setup        # creates sidecar/.venv, installs the engine, builds src-tauri/binaries/exan-sidecar-<arch>-apple-darwin
                        # and fetches the pinned llama.cpp build into src-tauri/runtime/
   ```
3. **Run it:** `npm start`. The first Rust build takes a few minutes. Then check that:
   - the window opens and the status changes from *Engine is starting…* to **Choose a reading model**;
   - after ticking the consent box, the recommended model downloads with a progress bar and the key step appears;
   - you can upload a key photo and a participant photo, read them, and see **Results**;
   - **CSV export** opens the save dialog and the file opens in Numbers/Excel with correct umlauts.
4. **Test the phone upload:** click **Take photos with your phone**, scan the QR code with a phone on the same Wi‑Fi, and send a photo. The first time, macOS asks *"Allow Exan to find devices on your local network?"* — click **Allow**. If the phone cannot connect, check **System Settings → Network → Firewall** (allow Exan) and make sure the Wi‑Fi has no "client isolation" (common on guest networks).
5. **Build the installer:** `npm run package` creates `src-tauri/target/release/bundle/macos/Exan.app` and `bundle/dmg/Exan_0.1.0_<arch>.dmg`. Install the DMG on a **second Mac that has never seen the project** to test the real first‑run experience.
6. **Build for both chip types:** the engine is a native binary and PyInstaller cannot cross‑compile. Run `npm run package` once on Apple Silicon (→ `aarch64`) and once on an Intel Mac (→ `x86_64`), or let the CI workflow below do it.
7. **Decide on distribution** (needs your Apple account; I cannot do this for you):
   - **Without an Apple Developer account (free):** the app is signed *ad hoc*. On other Macs, users must right‑click → **Open** the first time, or run `xattr -dr com.apple.quarantine /Applications/Exan.app`. This is fine for testing and for a few colleagues.
   - **For normal distribution:** join the Apple Developer Program (99 USD/year), create a **Developer ID Application** certificate, and then:
     1. in `src-tauri/tauri.conf.json` set `"hardenedRuntime": true` and replace `"signingIdentity": "-"` with your identity (or set `APPLE_SIGNING_IDENTITY`);
     2. export `APPLE_ID`, `APPLE_PASSWORD` (an app‑specific password) and `APPLE_TEAM_ID` before `npm run package` — Tauri then notarizes and staples the app;
     3. keep `src-tauri/Entitlements.plist`, which the frozen Python engine needs under the hardened runtime.
8. **Enable CI in the new repository:** `.github/workflows/build.yml` builds and tests both architectures and uploads the DMGs. It only runs once this folder is the root of its own repository. For signed builds, add the secrets listed in the workflow file.
9. **Optional:** replace the placeholder icons with `npx tauri icon path/to/icon-1024.png`, and change `identifier` (`com.exan.desktop`) to a reverse domain you own before the first public release, because changing it later moves the settings folder.

Please send me any error output from steps 2–5 (and `~/Library/Logs/com.exan.desktop/sidecar.log`) and I will fix it.

---

## Using the app

1. **Answer key:** upload photos of the solution sheet, or paste the solutions as text (`1. B`, `2) A, C`, `3: true`, …). Check the table and correct anything that was misread.
2. **Participants:** choose how files become people:
   - *one file = one person*: a multi‑page PDF is one person;
   - *one page = one person*: a PDF with one scanned sheet per page;
   - *all photos = one person*: the pages of one exam taken as separate photos.

   Then click **Read**. Open a card to see the photo next to the recognised answers, fix answers, or override a verdict.
3. **Results:** points, percentages and per‑question statistics. Export a summary or a detailed CSV (UTF‑8 with BOM; `;` as separator in German and `,` in English, so Excel and Numbers open it correctly).

Settings (runtime, model, reading mode, image size, timeout and language) are stored in `~/Library/Application Support/com.exan.desktop/settings.json`, downloaded models in `models/` next to it. Logs (`sidecar.log`, `runtime.log`) are in `~/Library/Logs/com.exan.desktop/`.

## Development

| Command | What it does |
|---|---|
| `npm run setup` | Creates `sidecar/.venv` (Python 3.11+), builds the engine binary for this Mac and fetches the llama.cpp runtime |
| `npm start` | Rebuilds the engine if its sources changed, then runs `tauri dev` with hot reload |
| `npm run package` | Builds the engine and the signed `.app` + `.dmg` (with the runtime, without models) |
| `npm run fetch:runtime` | Downloads the llama.cpp build pinned in `scripts/runtime.lock.json` (SHA‑256 checked) into `src-tauri/runtime/` |
| `npm run check` | Type-check, lint and unit tests for UI and engine |
| `npm run dev:engine` + `npm run dev:browser` | Engine on `127.0.0.1:8765` and the UI in a normal browser (values in `.env.browser`) |

Layout:

```
exan-macos/
├─ src/                React 19 + Tailwind 4 UI (lib/ = API client, store, i18n; components/ = screens)
├─ src-tauri/          Rust shell: engine supervisor (sidecar.rs), commands (lib.rs), bundle config,
│                      Info.plist (local-network prompt), Entitlements.plist (hardened runtime),
│                      runtime/ (llama-server + libraries, fetched, not committed)
├─ sidecar/            Python engine: FastAPI API, grading, parsing, image handling, built-in runtime
│                      (engine/llamacpp.py, model_store.py, models.json), Ollama/OpenAI clients,
│                      model downloads, phone upload page, PyInstaller spec, pytest suite
└─ scripts/            build-sidecar.mjs (PyInstaller → src-tauri/binaries), fetch-runtime.mjs + runtime.lock.json
                       (llama.cpp → src-tauri/runtime), sidecar-task.mjs (venv tasks)
```

Security: the engine listens on `127.0.0.1` only. Every API call needs the random secret that the shell creates on each start. The phone page is only served on the local network after you start it from the QR dialog. It accepts private-network addresses only, needs an unguessable token in the URL, and stops after inactivity or when you click *End connection*.

## Troubleshooting

| Problem | Fix |
|---|---|
| *"Exan" cannot be opened because the developer cannot be verified* | Right‑click → Open, or `xattr -dr com.apple.quarantine /Applications/Exan.app` (see step 7) |
| Engine stays at *starting* / *could not be started* | Click **Restart**; check `~/Library/Logs/com.exan.desktop/sidecar.log`; run `src-tauri/binaries/exan-sidecar-* --version` |
| *The built-in model runtime is missing* | Reinstall Exan; in development run `npm run fetch:runtime` |
| The model download fails | Exan needs `https://huggingface.co` (files are served from Hugging Face's CDN). Proxy settings (`HTTPS_PROXY`) are used. Click the download again: it continues where it stopped |
| *The built-in runtime stopped …* | See `~/Library/Logs/com.exan.desktop/runtime.log`; usually not enough memory for the model: pick a smaller one |
| *Ollama is not reachable* | Only when Ollama is selected: start the Ollama app (menu bar icon) or run `ollama serve`; the URL must be `http://127.0.0.1:11434` |
| Reading is slow | Use a smaller model and close other memory‑heavy apps. `EXAN_RUNTIME_ARGS` passes extra flags to llama-server (for example `--device none` to read on the CPU only) |
| Phone cannot open the page | Same Wi‑Fi, allow *Local Network* for Exan in **System Settings → Privacy & Security → Local Network**, and allow Exan in the firewall |
| `npm run setup` cannot find Python | `brew install python@3.12` (or `uv python install 3.12`), or `EXAN_PYTHON=/path/to/python3.12 npm run setup` |
| `npm run package` stops at `bundle_dmg.sh` with *Finder got an error: AppleEvent timed out* or *Not authorized to send Apple events to Finder* | The DMG step asks Finder to arrange the DMG window. Allow your terminal under **System Settings → Privacy & Security → Automation → Finder** (macOS asks once). Without a GUI session (for example over SSH), run `CI=true npm run package`, which skips the window layout. `Exan.app` is already built at this point. |

## Why there is no iOS/iPadOS version (yet)

This app cannot be turned into an iOS app by changing the build target:

- **iOS does not allow apps to start other processes.** The whole engine is a Python program that the shell starts as a separate process (`exan-sidecar`). Tauri's iOS target has no sidecar support, and there is no Python runtime on iOS.
- **There is no Ollama or LM Studio on iOS** that other apps can call on `127.0.0.1`. The vision model would have to run inside the app itself.
- **App Store distribution** needs an Apple Developer account, review, and an app smaller than iPhone memory limits (a 3B model needs about 2–3 GB of RAM while running).

An iOS/iPadOS version would be a **separate native app**:

1. SwiftUI app with `PhotosPicker`/`VNDocumentCameraViewController` for photos, and `Vision` (`VNRecognizeTextRequest`, on‑device) for printed text and checkboxes.
2. For handwriting: an on-device vision-language model, either MLX Swift (`mlx-swift-examples`, for example Qwen2.5‑VL 3B 4‑bit) or Core ML. This means iPhone 15 Pro / iPad with M‑chip or newer.
3. The grading and parsing logic from `sidecar/exan_sidecar/grading.py` and `parsing.py`, ported to Swift (about 830 lines of Python with a pytest suite that can be translated).
4. Xcode on a Mac, an Apple Developer account, and TestFlight for testing.

A lighter alternative already works today: the **phone upload** in this app lets you take the photos with the iPhone camera while the Mac does the reading.

## License

MIT

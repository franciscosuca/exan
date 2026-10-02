# Exan for macOS

Correct exams on your Mac without a server, account, or database. You photograph or scan the answer key and the participants' answer sheets. A small vision model that runs **on your Mac** reads the answers, and Exan grades every participant against the key. Photos never leave the computer, except when you choose to send them from your phone to the Mac over your own Wi‑Fi.

| | |
|---|---|
| Platforms | macOS 13 Ventura or newer, Apple Silicon (recommended) or Intel |
| Memory | 8 GB RAM for the 3–4B models, 16 GB for the 7B models |
| Local model | [Ollama](https://ollama.com/download) (recommended) or any OpenAI‑compatible local server such as [LM Studio](https://lmstudio.ai) |
| Output | `Exan.app` and `Exan_<version>_<arch>.dmg` |

## How it works

```
┌──────────── Exan.app ───────────────────────────────┐
│ Tauri v2 shell (Rust, WKWebView)                    │
│  ├─ React UI: Key → Participants → Results          │
│  └─ starts/stops the engine (exan-sidecar)          │
│        Python + FastAPI, 127.0.0.1:<random port>,   │
│        random secret per start, data in memory      │
└───────────────┬─────────────────────────────────────┘
                │ http://127.0.0.1:11434 (Ollama) or :1234 (LM Studio)
          small vision model (Qwen2.5‑VL 3B, …)
```

- **No accounts and no database.** One correction session lives in memory. *New correction* clears it. CSV export is the only file Exan writes, apart from settings and logs.
- **One feature:** compare the answer key with each participant's answers. You can fix any recognised answer by hand or override a verdict before exporting.
- **Photos** come from Finder (drag and drop or a file picker; JPG, PNG, HEIC, WebP, TIFF and PDF) or **from your phone**. The app shows a QR code, the phone opens a small upload page served by the Mac on your local network, and the photos appear immediately.

## Models

All suggestions run locally. They were chosen from Hugging Face's overview of open OCR models (<https://huggingface.co/blog/ocr-open-models>) and filtered to sizes that run on ordinary Macs:

| Model (Ollama name) | Download | RAM | Notes |
|---|---|---|---|
| `qwen2.5vl:3b` ★ | 3.2 GB | 8 GB | Best balance for handwriting and checkboxes |
| `qwen3-vl:4b` | 3.3 GB | 8 GB | Newer and often more accurate; needs a recent Ollama |
| `granite3.2-vision:2b` | 2.4 GB | 6 GB | Smallest; good for printed sheets |
| `gemma3:4b` | 3.3 GB | 8 GB | General vision model |
| `qwen2.5vl:7b` | 6.0 GB | 16 GB | More accurate, slower |
| `deepseek-ocr:3b` | 6.7 GB | 16 GB | Pure OCR mode (text first, then parsed) |

You can download a model from **Settings → Download** inside the app, or with `ollama pull qwen2.5vl:3b`. With LM Studio, load any vision model (for example an MLX build of Qwen2.5‑VL 3B), start its local server, and pick **OpenAI‑compatible** in Settings.

---

## ✅ What you need to do locally (checklist)

The code was written and tested in a Linux sandbox. The engine, the UI and the Rust shell compile there, and the engine runs there as the same frozen binary that ships in the app. **Building, signing and running the `.app` needs a real Mac**, so the following steps are still open:

1. **Install the tools (once):**
   ```bash
   xcode-select --install                                           # Apple command-line tools (clang, codesign)
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh   # Rust (stable)
   brew install node@22 python@3.12                                 # or the installers from nodejs.org / python.org
   brew install --cask ollama                                       # or https://ollama.com/download
   ```
2. **Get the code:** move this `exan-macos/` folder into its own repository (or `cd` into it), then:
   ```bash
   npm ci
   npm run setup        # creates sidecar/.venv, installs the engine, builds src-tauri/binaries/exan-sidecar-<arch>-apple-darwin
   ```
3. **Run it:** `npm start`. The first Rust build takes a few minutes. Then check that:
   - the window opens and the status changes from *Engine is starting…* to the key step;
   - **Settings** shows Ollama as reachable, and you can download/select `qwen2.5vl:3b`;
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

Settings (runtime URL, model, reading mode, image size, timeout and language) are stored in `~/Library/Application Support/com.exan.desktop/settings.json`. Logs are in `~/Library/Logs/com.exan.desktop/`.

## Development

| Command | What it does |
|---|---|
| `npm run setup` | Creates `sidecar/.venv` (Python 3.11+) and builds the engine binary for this Mac |
| `npm start` | Rebuilds the engine if its sources changed, then runs `tauri dev` with hot reload |
| `npm run package` | Builds the engine and the signed `.app` + `.dmg` |
| `npm run check` | Type-check, lint and unit tests for UI and engine |
| `npm run dev:engine` + `npm run dev:browser` | Engine on `127.0.0.1:8765` and the UI in a normal browser (values in `.env.browser`) |

Layout:

```
exan-macos/
├─ src/                React 19 + Tailwind 4 UI (lib/ = API client, store, i18n; components/ = screens)
├─ src-tauri/          Rust shell: engine supervisor (sidecar.rs), commands (lib.rs), bundle config,
│                      Info.plist (local-network prompt), Entitlements.plist (hardened runtime)
├─ sidecar/            Python engine: FastAPI API, grading, parsing, image handling, Ollama/OpenAI clients,
│                      phone upload page, PyInstaller spec, pytest suite
└─ scripts/            build-sidecar.mjs (PyInstaller → src-tauri/binaries), sidecar-task.mjs (venv tasks)
```

Security: the engine listens on `127.0.0.1` only. Every API call needs the random secret that the shell creates on each start. The phone page is only served on the local network after you start it from the QR dialog. It accepts private-network addresses only, needs an unguessable token in the URL, and stops after inactivity or when you click *End connection*.

## Troubleshooting

| Problem | Fix |
|---|---|
| *"Exan" cannot be opened because the developer cannot be verified* | Right‑click → Open, or `xattr -dr com.apple.quarantine /Applications/Exan.app` (see step 7) |
| Engine stays at *starting* / *could not be started* | Click **Restart**; check `~/Library/Logs/com.exan.desktop/sidecar.log`; run `src-tauri/binaries/exan-sidecar-* --version` |
| *Ollama is not reachable* | Start the Ollama app (menu bar icon) or run `ollama serve`; the URL must be `http://127.0.0.1:11434` |
| Reading is slow | Use a 3–4B model, lower *Max. image size* to 1280, and close other memory‑heavy apps |
| Phone cannot open the page | Same Wi‑Fi, allow *Local Network* for Exan in **System Settings → Privacy & Security → Local Network**, and allow Exan in the firewall |
| `npm run setup` cannot find Python | `brew install python@3.12` or `EXAN_PYTHON=/path/to/python3.12 npm run setup` |

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

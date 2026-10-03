# Exan for Windows

Correct exams on your PC without a server, account, or database. You photograph or scan the answer key and the participants' answer sheets. A small OCR or vision model that runs **on your PC** reads the answers, and Exan grades every participant against the key. Photos never leave the computer, except when you choose to send them from your phone to the PC over your own Wi‑Fi.

| | |
|---|---|
| Platforms | Windows 10 (version 1809 or newer) and Windows 11, x64 |
| Memory | 4 GB RAM for the smallest model, 8 GB for the 3B model (see [Models](#models)); a GPU with Vulkan drivers (NVIDIA, AMD, Intel) makes reading faster but is optional |
| Reading model | **Built in**: Exan ships [llama.cpp](https://github.com/ggml-org/llama.cpp); the installer lets you pick a model and downloads it after you agree. [Ollama](https://ollama.com/download) or [LM Studio](https://lmstudio.ai) still work (Settings) |
| Output | `Exan_<version>_x64-setup.exe` (NSIS, per-user, no admin rights, no model inside) and `Exan_<version>_x64_en-US.msi` |

## How it works

```
┌──────────── Exan.exe ───────────────────────────────┐
│ Tauri v2 shell (Rust, WebView2)                     │
│  ├─ React UI: Key → Participants → Results          │
│  └─ starts/stops the engine (exan-sidecar.exe)      │
│        Python + FastAPI, 127.0.0.1:<random port>,   │
│        random secret per start, data in memory      │
│          └─ starts llama-server.exe (bundled        │
│             llama.cpp, Vulkan/CPU), 127.0.0.1 only  │
└───────────────┬─────────────────────────────────────┘
                │ or: Ollama (:11434) / LM Studio (:1234)
     model files in %LOCALAPPDATA%\com.exan.desktop\models
```

- **No accounts and no database.** One correction session lives in memory. *New correction* clears it. CSV export is the only file Exan writes, apart from settings and logs.
- **One feature:** compare the answer key with each participant's answers. You can fix any recognised answer by hand or override a verdict before exporting.
- **Photos** come from Explorer (drag and drop or a file picker; JPG, PNG, WebP, TIFF and PDF; HEIC only on macOS) or **from your phone**. The app shows a QR code, the phone opens a small upload page served by the PC on your local network, and the photos appear immediately. iPhones send JPEG when uploading through the browser.

## Models

No model is part of the installer, so it stays small. After the folder page, the installer shows **Reading model**: the smallest model is preselected, each entry shows its size, and the download only starts when you tick *I agree that Exan downloads the selected model from Hugging Face (huggingface.co)*. The model is downloaded on the installation page (progress lines in the details list). *Do not download now* skips it; Exan then asks on its first start. If the download fails (for example offline), Exan offers the same model again on its first start. The models come from Hugging Face's overview of open OCR models (<https://huggingface.co/blog/ocr-open-models>); each file is pinned to a repository revision and checked with SHA‑256 (`sidecar/exan_sidecar/engine/models.json`):

| Built-in model | Download | RAM | Licence | Reads |
|---|---|---|---|---|
| Granite‑Docling 258M (IBM) ★ recommended | 0.28 GB | 4 GB | Apache‑2.0 | printed and typed text; often misses short handwritten answers |
| PaddleOCR‑VL 1.6 (0.9B) | 1.8 GB | 6 GB | Apache‑2.0 | printed text and handwriting, copies exactly what is written |
| Qwen2.5‑VL 3B | 2.8 GB | 8 GB | Qwen Research Licence (research/evaluation only) | general vision model; also ticked or circled options |

Measured on this project's four sample sheets (answer key plus three handwriting-style answer sheets, 24 answers) on a Mac: PaddleOCR‑VL read 24/24 answers, Qwen2.5‑VL 23/24 (it once wrote the correct answer instead of the participant's), Granite‑Docling at most 10/24 (fast, but it drops short handwritten answers and sometimes repeats itself). OCR models transcribe the page and Exan finds the answers next to the question numbers or labels such as *Antwort:*; Qwen returns JSON.

Downloads resume where they stopped. **Settings → Built-in models** downloads more models (after the same consent), switches between them and removes them. **Ollama** or **LM Studio** (OpenAI‑compatible) can still be selected under Settings → Local model runtime.

**Unattended installs** (`/S` or `/P`) show no pages and download nothing, unless IT staff pass a model: `Exan_0.1.0_x64-setup.exe /S /MODEL=granite-docling-258m` (passing it counts as consent). Uninstalling with *Delete the application data* also removes the downloaded models.

---

## ✅ What you need to do locally (checklist)

The code was written and tested in a Linux sandbox: the engine, the UI and the Rust shell compile there, and the frozen engine runs there. **Building the Windows installer needs a Windows PC**:

1. **Install the tools (once):**
   - [Visual Studio 2022 Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with the workload **Desktop development with C++**
   - [Rust](https://rustup.rs) (`rustup-init.exe`, default MSVC toolchain)
   - [Node.js 22 LTS](https://nodejs.org) and [Python 3.12](https://www.python.org/downloads/windows/) (tick *Add python.exe to PATH*; the `py` launcher is used automatically)
   - Ollama is optional now; the reading model runs in the bundled llama.cpp runtime
2. **Get the code:** move this `exan-windows/` folder into its own repository (or `cd` into it), then in PowerShell:
   ```powershell
   npm ci
   npm run setup        # creates sidecar\.venv, installs the engine, builds src-tauri\binaries\exan-sidecar-x86_64-pc-windows-msvc.exe
                        # and fetches the pinned llama.cpp build (Vulkan) into src-tauri\runtime\
   ```
3. **Run it:** `npm start`. The first Rust build takes a few minutes. Then check that:
   - the window opens and the status changes from *Engine is starting…* to **Choose a reading model**, with **no console window** (also not when a page is read: `llama-server.exe` runs hidden);
   - after ticking the consent box, the recommended model downloads with a progress bar and the key step appears;
   - you can upload a key photo and a participant photo, read them, and see **Results**;
   - **CSV export** opens the save dialog and the file opens in Excel with correct umlauts.
4. **Test the phone upload:** click **Take photos with your phone**, scan the QR code with a phone on the same Wi‑Fi, and send a photo. When Windows Firewall asks, allow Exan on **private networks**. Your Wi‑Fi must be set to *Private* in Windows network settings, and guest networks with "client isolation" will not work.
5. **Build the installers:** `npm run package` creates `src-tauri\target\release\bundle\nsis\Exan_0.1.0_x64-setup.exe` and `bundle\msi\Exan_0.1.0_x64_en-US.msi`. Install the `-setup.exe` on a **second PC** that has never seen the project, to test the real first run (WebView2 is installed automatically if missing): the **Reading model** page, the consent check (*Next* with a model but without consent must show a hint), the download in the details list, and that Exan opens with the model ready. The `.msi` has no model page; Exan asks on its first start.
6. **Decide on code signing** (needs a certificate; I cannot do this for you): unsigned installers show *"Windows protected your PC"* → **More info → Run anyway**, and some antivirus tools are suspicious of unsigned PyInstaller programs. For wider distribution, sign with an OV/EV code-signing certificate or [Azure Trusted Signing](https://learn.microsoft.com/azure/trusted-signing/) (see the Tauri guide *Windows Code Signing*).
7. **Enable CI in the new repository:** `.github/workflows/build.yml` builds, tests and uploads the installers. It only runs once this folder is the root of its own repository.
8. **Optional:** replace the placeholder icons with `npx tauri icon path\to\icon-1024.png`, and change `identifier` (`com.exan.desktop`) to a reverse domain you own before the first public release.

Please send me any error output from steps 2–5 (and `%LOCALAPPDATA%\com.exan.desktop\logs\sidecar.log`) and I will fix it.

---

## Using the app

1. **Answer key:** upload photos of the solution sheet, or paste the solutions as text (`1. B`, `2) A, C`, `3: true`, …). Check the table and correct anything that was misread.
2. **Participants:** choose how files become people:
   - *one file = one person*: a multi‑page PDF is one person;
   - *one page = one person*: a PDF with one scanned sheet per page;
   - *all photos = one person*: the pages of one exam taken as separate photos.

   Then click **Read**. Open a card to see the photo next to the recognised answers, fix answers, or override a verdict.
3. **Results:** points, percentages and per‑question statistics. Export a summary or a detailed CSV (UTF‑8 with BOM; `;` as separator in German and `,` in English, so Excel and Numbers open it correctly).

Settings (runtime, model, reading mode, image size, timeout and language) are stored in `%APPDATA%\com.exan.desktop\settings.json`; downloaded models in `%LOCALAPPDATA%\com.exan.desktop\models\` (not roaming). Logs (`sidecar.log`, `runtime.log`) are in `%LOCALAPPDATA%\com.exan.desktop\logs\`.

## Development

| Command | What it does |
|---|---|
| `npm run setup` | Creates `sidecar/.venv` (Python 3.11+), builds the engine binary for this PC and fetches the llama.cpp runtime |
| `npm start` | Rebuilds the engine if its sources changed, then runs `tauri dev` with hot reload |
| `npm run package` | Builds the engine and the installers (`-setup.exe` and `.msi`; with the runtime, without models) |
| `npm run fetch:runtime` | Downloads the llama.cpp build pinned in `scripts/runtime.lock.json` (SHA‑256 checked) into `src-tauri/runtime/` |
| `npm run installer:models` | Regenerates the installer's model page (`src-tauri/windows/models.nsh`) from `models.json`; `npm run check` fails when it is stale |
| `npm run check` | Type-check, lint and unit tests for UI and engine |
| `npm run dev:engine` + `npm run dev:browser` | Engine on `127.0.0.1:8765` and the UI in a normal browser (values in `.env.browser`) |

Layout:

```
exan-windows/
├─ src/                React 19 + Tailwind 4 UI (lib/ = API client, store, i18n; components/ = screens)
├─ src-tauri/          Rust shell: engine supervisor (sidecar.rs), commands (lib.rs), bundle config (NSIS + MSI),
│                      runtime/ (llama-server.exe + DLLs, fetched, not committed),
│                      windows/ (installer.nsi = Tauri's template + 2 marked lines, hooks.nsh = model page
│                      and download, models.nsh = generated model list)
├─ sidecar/            Python engine: FastAPI API, grading, parsing, image handling, built-in runtime
│                      (engine/llamacpp.py, model_store.py, models.json), Ollama/OpenAI clients,
│                      model downloads (also `exan-sidecar models download`), phone upload page, pytest suite
└─ scripts/            build-sidecar.mjs (PyInstaller → src-tauri/binaries), fetch-runtime.mjs + runtime.lock.json
                       (llama.cpp → src-tauri/runtime), installer-models.mjs, sidecar-task.mjs (venv tasks)
```

Security: the engine listens on `127.0.0.1` only. Every API call needs the random secret that the shell creates on each start. The phone page is only served on the local network after you start it from the QR dialog. It accepts private-network addresses only, needs an unguessable token in the URL, and stops after inactivity or when you click *End connection*.

## Troubleshooting

| Problem | Fix |
|---|---|
| *Windows protected your PC* | **More info → Run anyway** (see step 6) |
| Engine stays at *starting* / *could not be started* | Click **Restart**; check `%LOCALAPPDATA%\com.exan.desktop\logs\sidecar.log`; run `src-tauri\binaries\exan-sidecar-x86_64-pc-windows-msvc.exe --version`; check whether your antivirus quarantined `exan-sidecar.exe` |
| *The built-in model runtime is missing* | Reinstall Exan; in development run `npm run fetch:runtime` |
| The model download fails (installer or app) | Exan needs `https://huggingface.co` (files are served from Hugging Face's CDN). Proxy settings (`HTTPS_PROXY`) are used. Start the download again in Exan: it continues where it stopped |
| *The built-in runtime stopped …* | See `%LOCALAPPDATA%\com.exan.desktop\logs\runtime.log`; usually not enough memory for the model (pick a smaller one) or a GPU driver problem: set `EXAN_RUNTIME_ARGS=--device none` to read on the CPU only |
| *Ollama is not reachable* | Only when Ollama is selected: start Ollama from the Start menu (tray icon) or run `ollama serve`; the URL must be `http://127.0.0.1:11434` |
| Reading is slow | Use a smaller model, update the graphics driver (Vulkan), and close other memory‑heavy apps |
| Upgrading `@tauri-apps/cli` | `src-tauri/windows/installer.nsi` is Tauri's NSIS template with two lines marked `EXAN`: copy the new upstream template and add them again |
| Phone cannot open the page | Same Wi‑Fi, network profile *Private*, and allow Exan in **Windows Security → Firewall & network protection → Allow an app through firewall** |
| `npm run setup` cannot find Python | Install Python 3.12 from python.org or set `$env:EXAN_PYTHON="C:\Path\to\python.exe"` |
| `link.exe` not found during `npm start` | Install the Visual Studio Build Tools with *Desktop development with C++* and open a new terminal |

## License

MIT

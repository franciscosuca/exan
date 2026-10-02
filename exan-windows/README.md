# Exan for Windows

Correct exams on your PC without a server, account, or database. You photograph or scan the answer key and the participants' answer sheets. A small vision model that runs **on your PC** reads the answers, and Exan grades every participant against the key. Photos never leave the computer, except when you choose to send them from your phone to the PC over your own Wi‑Fi.

| | |
|---|---|
| Platforms | Windows 10 (version 1809 or newer) and Windows 11, x64 |
| Memory | 8 GB RAM for the 3–4B models, 16 GB for the 7B models; an NVIDIA/AMD GPU makes reading much faster but is optional |
| Local model | [Ollama](https://ollama.com/download) (recommended) or any OpenAI‑compatible local server such as [LM Studio](https://lmstudio.ai) |
| Output | `Exan_<version>_x64-setup.exe` (NSIS, per-user, no admin rights) and `Exan_<version>_x64_en-US.msi` |

## How it works

```
┌──────────── Exan.exe ───────────────────────────────┐
│ Tauri v2 shell (Rust, WebView2)                     │
│  ├─ React UI: Key → Participants → Results          │
│  └─ starts/stops the engine (exan-sidecar.exe)      │
│        Python + FastAPI, 127.0.0.1:<random port>,   │
│        random secret per start, data in memory      │
└───────────────┬─────────────────────────────────────┘
                │ http://127.0.0.1:11434 (Ollama) or :1234 (LM Studio)
          small vision model (Qwen2.5‑VL 3B, …)
```

- **No accounts and no database.** One correction session lives in memory. *New correction* clears it. CSV export is the only file Exan writes, apart from settings and logs.
- **One feature:** compare the answer key with each participant's answers. You can fix any recognised answer by hand or override a verdict before exporting.
- **Photos** come from Explorer (drag and drop or a file picker; JPG, PNG, WebP, TIFF and PDF; HEIC only on macOS) or **from your phone**. The app shows a QR code, the phone opens a small upload page served by the PC on your local network, and the photos appear immediately. iPhones send JPEG when uploading through the browser.

## Models

All suggestions run locally. They were chosen from Hugging Face's overview of open OCR models (<https://huggingface.co/blog/ocr-open-models>) and filtered to sizes that run on ordinary PCs:

| Model (Ollama name) | Download | RAM | Notes |
|---|---|---|---|
| `qwen2.5vl:3b` ★ | 3.2 GB | 8 GB | Best balance for handwriting and checkboxes |
| `qwen3-vl:4b` | 3.3 GB | 8 GB | Newer and often more accurate; needs a recent Ollama |
| `granite3.2-vision:2b` | 2.4 GB | 6 GB | Smallest; good for printed sheets |
| `gemma3:4b` | 3.3 GB | 8 GB | General vision model |
| `qwen2.5vl:7b` | 6.0 GB | 16 GB | More accurate, slower |
| `deepseek-ocr:3b` | 6.7 GB | 16 GB | Pure OCR mode (text first, then parsed) |

You can download a model from **Settings → Download** inside the app, or with `ollama pull qwen2.5vl:3b`. With LM Studio, load any vision model (for example a GGUF build of Qwen2.5‑VL 3B), start its local server, and pick **OpenAI‑compatible** in Settings.

---

## ✅ What you need to do locally (checklist)

The code was written and tested in a Linux sandbox: the engine, the UI and the Rust shell compile there, and the frozen engine runs there. **Building the Windows installer needs a Windows PC**:

1. **Install the tools (once):**
   - [Visual Studio 2022 Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with the workload **Desktop development with C++**
   - [Rust](https://rustup.rs) (`rustup-init.exe`, default MSVC toolchain)
   - [Node.js 22 LTS](https://nodejs.org) and [Python 3.12](https://www.python.org/downloads/windows/) (tick *Add python.exe to PATH*; the `py` launcher is used automatically)
   - [Ollama for Windows](https://ollama.com/download)
2. **Get the code:** move this `exan-windows/` folder into its own repository (or `cd` into it), then in PowerShell:
   ```powershell
   npm ci
   npm run setup        # creates sidecar\.venv, installs the engine, builds src-tauri\binaries\exan-sidecar-x86_64-pc-windows-msvc.exe
   ```
3. **Run it:** `npm start`. The first Rust build takes a few minutes. Then check that:
   - the window opens and the status changes from *Engine is starting…* to the key step, with **no console window**;
   - **Settings** shows Ollama as reachable, and you can download/select `qwen2.5vl:3b`;
   - you can upload a key photo and a participant photo, read them, and see **Results**;
   - **CSV export** opens the save dialog and the file opens in Excel with correct umlauts.
4. **Test the phone upload:** click **Take photos with your phone**, scan the QR code with a phone on the same Wi‑Fi, and send a photo. When Windows Firewall asks, allow Exan on **private networks**. Your Wi‑Fi must be set to *Private* in Windows network settings, and guest networks with "client isolation" will not work.
5. **Build the installers:** `npm run package` creates `src-tauri\target\release\bundle\nsis\Exan_0.1.0_x64-setup.exe` and `bundle\msi\Exan_0.1.0_x64_en-US.msi`. Install the `-setup.exe` on a **second PC** that has never seen the project, to test the real first run (WebView2 is installed automatically if missing).
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

Settings (runtime URL, model, reading mode, image size, timeout and language) are stored in `%APPDATA%\com.exan.desktop\settings.json`. Logs are in `%LOCALAPPDATA%\com.exan.desktop\logs\`.

## Development

| Command | What it does |
|---|---|
| `npm run setup` | Creates `sidecar/.venv` (Python 3.11+) and builds the engine binary for this PC |
| `npm start` | Rebuilds the engine if its sources changed, then runs `tauri dev` with hot reload |
| `npm run package` | Builds the engine and the installers (`-setup.exe` and `.msi`) |
| `npm run check` | Type-check, lint and unit tests for UI and engine |
| `npm run dev:engine` + `npm run dev:browser` | Engine on `127.0.0.1:8765` and the UI in a normal browser (values in `.env.browser`) |

Layout:

```
exan-windows/
├─ src/                React 19 + Tailwind 4 UI (lib/ = API client, store, i18n; components/ = screens)
├─ src-tauri/          Rust shell: engine supervisor (sidecar.rs), commands (lib.rs), bundle config (NSIS + MSI)
├─ sidecar/            Python engine: FastAPI API, grading, parsing, image handling, Ollama/OpenAI clients,
│                      phone upload page, PyInstaller spec, pytest suite
└─ scripts/            build-sidecar.mjs (PyInstaller → src-tauri/binaries), sidecar-task.mjs (venv tasks)
```

Security: the engine listens on `127.0.0.1` only. Every API call needs the random secret that the shell creates on each start. The phone page is only served on the local network after you start it from the QR dialog. It accepts private-network addresses only, needs an unguessable token in the URL, and stops after inactivity or when you click *End connection*.

## Troubleshooting

| Problem | Fix |
|---|---|
| *Windows protected your PC* | **More info → Run anyway** (see step 6) |
| Engine stays at *starting* / *could not be started* | Click **Restart**; check `%LOCALAPPDATA%\com.exan.desktop\logs\sidecar.log`; run `src-tauri\binaries\exan-sidecar-x86_64-pc-windows-msvc.exe --version`; check whether your antivirus quarantined `exan-sidecar.exe` |
| *Ollama is not reachable* | Start Ollama from the Start menu (tray icon) or run `ollama serve`; the URL must be `http://127.0.0.1:11434` |
| Reading is slow | Use a 3–4B model, lower *Max. image size* to 1280, and close other memory‑heavy apps |
| Phone cannot open the page | Same Wi‑Fi, network profile *Private*, and allow Exan in **Windows Security → Firewall & network protection → Allow an app through firewall** |
| `npm run setup` cannot find Python | Install Python 3.12 from python.org or set `$env:EXAN_PYTHON="C:\Path\to\python.exe"` |
| `link.exe` not found during `npm start` | Install the Visual Studio Build Tools with *Desktop development with C++* and open a new terminal |

## License

MIT

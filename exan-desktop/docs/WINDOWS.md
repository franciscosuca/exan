# Exan for Windows — install, run, and package

See the [top-level README](../README.md) for the unified overview.

## ✅ Checklist

**Building the Windows installer needs a Windows PC.**

1. **Install the tools (once):**
   - [Visual Studio 2022 Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with workload **Desktop development with C++**
   - [Rust](https://rustup.rs) (`rustup-init.exe`, default MSVC toolchain)
   - [Node.js 22 LTS](https://nodejs.org) and [Python 3.12](https://www.python.org/downloads/windows/) (tick *Add python.exe to PATH*)
2. **Get the code:**
   ```powershell
   cd exan-desktop
   npm ci
   npm run setup
   ```
3. **Run it:** `npm start`. The first Rust build takes a few minutes. Check that:
   - the window opens and the status changes from *Engine is starting…* to **Choose a reading model**, with **no console window**;
   - after ticking the consent box, the recommended model downloads with a progress bar and the key step appears;
   - you can upload a key photo and a participant photo, read them, and see **Results**;
   - **CSV export** opens the save dialog and the file opens in Excel with correct umlauts.
4. **Test the phone upload:** click **Take photos with your phone**, scan the QR code. When Windows Firewall asks, allow Exan on **private networks**. Your Wi‑Fi must be set to *Private* in Windows network settings.
5. **Build the installers:** `npm run package` creates `src-tauri\target\release\bundle\nsis\Exan_0.1.0_x64-setup.exe` and `bundle\msi\Exan_0.1.0_x64_en-US.msi`. Install the `-setup.exe` on a **second PC**: test the **Reading model** page, the consent check, and the model download.
6. **Decide on code signing:** unsigned installers show *"Windows protected your PC"* → **More info → Run anyway**. For wider distribution, sign with an OV/EV code-signing certificate or [Azure Trusted Signing](https://learn.microsoft.com/azure/trusted-signing/).
7. **Enable CI** (once this folder is its own repository): `.github/workflows/build.yml` builds and uploads the installers.

## Unattended installs

Pass `/S` or `/P` to skip all pages and download nothing. IT staff can pass a model:
```
Exan_0.1.0_x64-setup.exe /S /MODEL=granite-docling-258m
```
Passing `/MODEL` counts as consent. Uninstalling with *Delete the application data* also removes downloaded models.

## Troubleshooting

| Problem | Fix |
|---|---|
| *Windows protected your PC* | **More info → Run anyway** (see step 6) |
| Engine stays at *starting* / *could not be started* | Click **Restart**; check `%LOCALAPPDATA%\com.exan.desktop\logs\sidecar.log`; run `src-tauri\binaries\exan-sidecar-x86_64-pc-windows-msvc.exe --version`; check antivirus |
| *The built-in model runtime is missing* | Reinstall Exan; in development run `npm run fetch:runtime` |
| The model download fails | Exan needs `https://huggingface.co`. Proxy settings (`HTTPS_PROXY`) are used. Start the download again: it continues where it stopped |
| *The built-in runtime stopped …* | See `%LOCALAPPDATA%\com.exan.desktop\logs\runtime.log`; not enough RAM → pick a smaller model; GPU driver → `EXAN_RUNTIME_ARGS=--device none` (CPU only) |
| *Ollama is not reachable* | Only when Ollama is selected: start Ollama (tray icon) or run `ollama serve`; URL must be `http://127.0.0.1:11434` |
| Phone cannot open the page | Same Wi‑Fi, network profile *Private*, allow Exan in **Windows Security → Firewall & network protection → Allow an app through firewall** |
| `npm run setup` cannot find Python | Install Python 3.12 from python.org or `$env:EXAN_PYTHON="C:\Path\to\python.exe"` |
| `link.exe` not found during `npm start` | Install Visual Studio Build Tools with *Desktop development with C++* and open a new terminal |
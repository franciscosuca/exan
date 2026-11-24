# Exan for macOS — install, run, and package

See the [top-level README](../README.md) for the unified overview.

## ✅ Checklist

The engine, the UI and the Rust shell compile in a Linux sandbox and the engine runs there as the same frozen binary that ships in the app. **Building, signing and running the `.app` needs a real Mac.**

1. **Install the tools (once):**
   ```bash
   xcode-select --install
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   brew install node@22 python@3.12
   ```
2. **Get the code:**
   ```bash
   cd exan-desktop
   npm ci
   npm run setup
   ```
3. **Run it:** `npm start`. Check that:
   - the window opens and the status changes from *Engine is starting…* to **Choose a reading model**;
   - after ticking the consent box, the recommended model downloads with a progress bar and the key step appears;
   - you can upload a key photo and a participant photo, read them, and see **Results**;
   - **CSV export** opens the save dialog and the file opens in Numbers/Excel with correct umlauts.
4. **Test the phone upload:** click **Take photos with your phone**, scan the QR code with a phone on the same Wi‑Fi. The first time, macOS asks *"Allow Exan to find devices on your local network?"* — click **Allow**.
5. **Build the installer:** `npm run package` creates `src-tauri/target/release/bundle/macos/Exan.app` and `bundle/dmg/Exan_0.1.0_<arch>.dmg`.
6. **Build for both chip types:** the engine is a native binary and PyInstaller cannot cross‑compile. Run `npm run package` once on Apple Silicon and once on Intel.
7. **Decide on distribution:**
   - *Without an Apple Developer account (free):* the app is signed ad hoc. Users right‑click → **Open** or run `xattr -dr com.apple.quarantine /Applications/Exan.app`.
   - *For normal distribution:* Apple Developer Program ($99/year), a Developer ID Application certificate, hardened runtime, and notarization.
8. **Enable CI** (once this folder is its own repository): `.github/workflows/build.yml` builds both architectures.

## Troubleshooting

| Problem | Fix |
|---|---|
| *"Exan" cannot be opened because the developer cannot be verified* | Right‑click → Open, or `xattr -dr com.apple.quarantine /Applications/Exan.app` |
| Engine stays at *starting* / *could not be started* | Click **Restart**; check `~/Library/Logs/com.exan.desktop/sidecar.log`; run `src-tauri/binaries/exan-sidecar-* --version` |
| *The built-in model runtime is missing* | Reinstall Exan; in development run `npm run fetch:runtime` |
| The model download fails | Exan needs `https://huggingface.co`. Proxy settings (`HTTPS_PROXY`) are used. Click the download again: it continues where it stopped |
| *The built-in runtime stopped …* | See `~/Library/Logs/com.exan.desktop/runtime.log`; usually not enough memory for the model: pick a smaller one |
| *Ollama is not reachable* | Only when Ollama is selected: start the Ollama app or run `ollama serve`; the URL must be `http://127.0.0.1:11434` |
| Phone cannot open the page | Same Wi‑Fi, allow *Local Network* in **System Settings → Privacy & Security → Local Network**, and allow Exan in the firewall |
| `npm run setup` cannot find Python | `brew install python@3.12` or `EXAN_PYTHON=/path/to/python3.12 npm run setup` |
| `npm run package` stops at *Finder got an error: AppleEvent timed out* | Allow your terminal under **System Settings → Privacy & Security → Automation → Finder**. Without a GUI session, run `CI=true npm run package`
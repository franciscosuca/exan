#!/usr/bin/env node
// Runs engine tasks inside sidecar/.venv (created on first use):
//   setup   create the venv and install the engine with dev + build extras
//   test    pytest
//   lint    ruff check + ruff format --check
//   dev     run the engine on http://127.0.0.1:8765 for UI work in a normal browser (`npm run dev:browser`),
//           with the bundled model runtime and the desktop app's model folder
import process from "node:process";
import { join } from "node:path";
import { desktopModelsDir, ensureVenv, fail, root, run, venvBin } from "./lib.mjs";

const task = process.argv[2];
const extra = process.argv.slice(3);

switch (task) {
  case "setup":
    ensureVenv({ force: true });
    break;
  case "test":
    ensureVenv();
    run(venvBin("python"), ["-m", "pytest", ...extra]);
    break;
  case "lint":
    ensureVenv();
    run(venvBin("ruff"), ["check", "."]);
    run(venvBin("ruff"), ["format", "--check", "."]);
    break;
  case "dev":
    ensureVenv();
    // Fixed values for browser development only; the desktop app generates a random secret on every start.
    run(venvBin("python"), ["-m", "exan_sidecar"], {
      env: {
        ...process.env,
        EXAN_SECRET: process.env.EXAN_SECRET ?? "dev-secret-change-me-0123456789",
        EXAN_PORT: process.env.EXAN_PORT ?? "8765",
        // Same runtime (npm run fetch:runtime) and model folder as the desktop app.
        EXAN_RUNTIME_DIR: process.env.EXAN_RUNTIME_DIR ?? join(root, "src-tauri", "runtime"),
        EXAN_MODELS_DIR: process.env.EXAN_MODELS_DIR ?? desktopModelsDir(),
      },
    });
    break;
  default:
    fail("Usage: node scripts/sidecar-task.mjs <setup|test|lint|dev>");
}

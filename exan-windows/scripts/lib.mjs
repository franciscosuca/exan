// Shared helpers for the build scripts. Plain Node (no dependencies) so they run on macOS and Windows.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

export const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
export const sidecarDir = join(root, "sidecar");
export const isWindows = process.platform === "win32";
export const venvDir = join(sidecarDir, ".venv");
export const venvBin = (name) => join(venvDir, isWindows ? "Scripts" : "bin", isWindows ? `${name}.exe` : name);

export function fail(message) {
  console.error(`\n✖ ${message}`);
  process.exit(1);
}

export function run(command, args, options = {}) {
  console.log(`> ${command} ${args.join(" ")}`);
  const result = spawnSync(command, args, { stdio: "inherit", cwd: sidecarDir, ...options });
  if (result.error) fail(`${command} could not be started: ${result.error.message}`);
  if (result.status !== 0) fail(`${command} exited with code ${result.status}`);
}

export function capture(command, args) {
  const result = spawnSync(command, args, { encoding: "utf8" });
  return result.status === 0 ? result.stdout.trim() : null;
}

function pythonVersion(command, args) {
  const out = capture(command, [...args, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"]);
  if (!out) return null;
  const [major, minor] = out.split(".").map(Number);
  return major === 3 && minor >= 11 ? out : null;
}

/** Finds a Python 3.11+ interpreter: EXAN_PYTHON, then the usual names (the `py` launcher on Windows). */
export function findPython() {
  const candidates = process.env.EXAN_PYTHON
    ? [[process.env.EXAN_PYTHON]]
    : isWindows
      ? [["py", "-3.12"], ["py", "-3.13"], ["py", "-3.11"], ["python"]]
      : [["python3.12"], ["python3.13"], ["python3.11"], ["python3"]];
  for (const [command, ...args] of candidates) {
    const version = pythonVersion(command, args);
    if (version) return { command, args, version };
  }
  return fail(
    "Python 3.11 or newer was not found. Install Python 3.12 from https://www.python.org/downloads/ " +
      "(or `brew install python@3.12` on macOS) or point EXAN_PYTHON to it.",
  );
}

/** Creates sidecar/.venv on first use and installs the engine with its dev and build extras. */
export function ensureVenv({ force = false } = {}) {
  const python = venvBin("python");
  if (!existsSync(python)) {
    const found = findPython();
    console.log(`Using Python ${found.version} (${[found.command, ...found.args].join(" ")})`);
    run(found.command, [...found.args, "-m", "venv", venvDir]);
    force = true;
  }
  if (force) {
    run(python, ["-m", "pip", "install", "--upgrade", "pip"]);
    run(python, ["-m", "pip", "install", "-e", ".[dev,build]"]);
  }
  return python;
}

/** The Rust target triple Tauri expects as suffix of the engine binary. */
export function targetTriple(explicit) {
  const triple = explicit || process.env.TAURI_ENV_TARGET_TRIPLE;
  if (triple) return triple;
  const info = capture("rustc", ["-vV"]);
  const host = info?.split("\n").find((line) => line.startsWith("host:"));
  if (!host) fail("rustc was not found. Install Rust from https://rustup.rs and open a new terminal.");
  return host.slice("host:".length).trim();
}

/** Models folder of the desktop app (Tauri app_local_data_dir/models), shared with browser dev mode. */
export function desktopModelsDir() {
  const id = "com.exan.desktop";
  if (isWindows) return join(process.env.LOCALAPPDATA || join(homedir(), "AppData", "Local"), id, "models");
  if (process.platform === "darwin") return join(homedir(), "Library", "Application Support", id, "models");
  return join(process.env.XDG_DATA_HOME || join(homedir(), ".local", "share"), id, "models");
}

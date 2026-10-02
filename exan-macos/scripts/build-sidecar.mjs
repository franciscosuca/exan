#!/usr/bin/env node
// Freezes the Python engine with PyInstaller and copies it to src-tauri/binaries/exan-sidecar-<triple>,
// which is where Tauri looks for `externalBin` sidecars.
//
//   node scripts/build-sidecar.mjs              build for this machine
//   node scripts/build-sidecar.mjs --if-needed  skip when the binary is newer than the engine sources
//   node scripts/build-sidecar.mjs --target aarch64-apple-darwin
//
// PyInstaller cannot cross-compile: build Apple Silicon and Intel binaries on matching machines
// (or with `arch -x86_64` and an x86_64/universal2 Python on Apple Silicon).
import { chmodSync, copyFileSync, existsSync, mkdirSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import process from "node:process";
import { capture, ensureVenv, fail, isWindows, root, run, sidecarDir, targetTriple } from "./lib.mjs";

const args = process.argv.slice(2);
const option = (name) => {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : undefined;
};

const triple = targetTriple(option("--target"));
const exe = triple.includes("windows") ? ".exe" : "";
const binariesDir = join(root, "src-tauri", "binaries");
const destination = join(binariesDir, `exan-sidecar-${triple}${exe}`);

function newestSource(dir) {
  let newest = 0;
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "__pycache__") continue;
    const path = join(dir, entry.name);
    newest = Math.max(newest, entry.isDirectory() ? newestSource(path) : statSync(path).mtimeMs);
  }
  return newest;
}

if (args.includes("--if-needed") && existsSync(destination)) {
  const sources = Math.max(
    newestSource(join(sidecarDir, "exan_sidecar")),
    ...["pyproject.toml", "exan-sidecar.spec", "sidecar_entry.py"].map((f) => statSync(join(sidecarDir, f)).mtimeMs),
  );
  if (statSync(destination).mtimeMs >= sources) {
    console.log(`Engine is up to date: ${destination}`);
    process.exit(0);
  }
}

const python = ensureVenv();
const hostArch = capture(python, ["-c", "import platform; print(platform.machine())"]) ?? "";
const wantsArm = triple.startsWith("aarch64");
if (/^(arm64|aarch64)$/i.test(hostArch) !== wantsArm && !process.env.EXAN_SKIP_ARCH_CHECK) {
  fail(
    `This Python builds ${hostArch} binaries but the target is ${triple}. ` +
      "Build on a matching machine, or set EXAN_SKIP_ARCH_CHECK=1 if your Python is universal2.",
  );
}

run(python, ["-m", "PyInstaller", "--noconfirm", "--clean", "--log-level", "WARN", "exan-sidecar.spec"]);

const built = join(sidecarDir, "dist", `exan-sidecar${isWindows ? ".exe" : ""}`);
if (!existsSync(built)) fail(`PyInstaller did not produce ${built}`);
mkdirSync(binariesDir, { recursive: true });
copyFileSync(built, destination);
if (!isWindows) chmodSync(destination, 0o755);

const version = capture(destination, ["--version"]);
if (!version) fail(`The built engine does not start: ${destination}`);
console.log(`\n✔ Engine ${version} → ${destination}`);

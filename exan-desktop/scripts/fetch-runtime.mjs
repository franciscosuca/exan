#!/usr/bin/env node
// Downloads the pinned llama.cpp build (scripts/runtime.lock.json), checks its SHA-256 and copies
// llama-server with the libraries it needs to src-tauri/runtime/, which Tauri bundles as a resource.
//
//   node scripts/fetch-runtime.mjs              fetch for this machine
//   node scripts/fetch-runtime.mjs --if-needed  skip when src-tauri/runtime already has this build
//   node scripts/fetch-runtime.mjs --target x86_64-apple-darwin
import { createHash } from "node:crypto";
import { chmodSync, copyFileSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join } from "node:path";
import process from "node:process";
import { capture, fail, root, run, targetTriple } from "./lib.mjs";

const args = process.argv.slice(2);
const option = (name) => {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : undefined;
};

const lock = JSON.parse(readFileSync(join(root, "scripts", "runtime.lock.json"), "utf8"));
const triple = targetTriple(option("--target"));
const asset = lock.targets[triple];
if (!asset) fail(`No llama.cpp runtime is configured for ${triple} (see scripts/runtime.lock.json).`);
const isWindowsTarget = triple.includes("windows");
const serverName = isWindowsTarget ? "llama-server.exe" : "llama-server";
const runtimeDir = join(root, "src-tauri", "runtime");
const stamp = `${lock.build} ${triple}`;
const versionFile = join(runtimeDir, "VERSION");

if (args.includes("--if-needed") && existsSync(join(runtimeDir, serverName)) && existsSync(versionFile)) {
  if (readFileSync(versionFile, "utf8").trim() === stamp) {
    console.log(`Runtime is up to date: llama.cpp ${stamp}`);
    process.exit(0);
  }
}

// 1. Download (cached in .cache/runtime) and verify.
const cacheDir = join(root, ".cache", "runtime");
mkdirSync(cacheDir, { recursive: true });
const archive = join(cacheDir, basename(new URL(asset.url).pathname));
const sha256 = (path) => createHash("sha256").update(readFileSync(path)).digest("hex");
if (!existsSync(archive) || sha256(archive) !== asset.sha256) {
  console.log(`> download ${asset.url}`);
  const response = await fetch(asset.url, { redirect: "follow" });
  if (!response.ok) fail(`Download failed: HTTP ${response.status} for ${asset.url}`);
  writeFileSync(archive, Buffer.from(await response.arrayBuffer()));
}
const actual = sha256(archive);
if (actual !== asset.sha256) {
  rmSync(archive, { force: true });
  fail(`Checksum mismatch for ${basename(archive)}: expected ${asset.sha256}, got ${actual}`);
}

// 2. Unpack with the system tar (bsdtar reads .zip as well, also on Windows 10+).
const work = mkdtempSync(join(tmpdir(), "exan-runtime-"));
try {
  run("tar", ["-xf", archive, "-C", work], { cwd: root });
  const find = (dir) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const path = join(dir, entry.name);
      if (entry.isDirectory()) {
        const found = find(path);
        if (found) return found;
      } else if (entry.name === serverName) {
        return path;
      }
    }
    return null;
  };
  const server = find(work);
  if (!server) fail(`${serverName} was not found in ${basename(archive)}`);
  const source = dirname(server);

  // 3. Pick llama-server and only the libraries it loads.
  const files = isWindowsTarget ? windowsFiles(source) : macosFiles(source, server);
  rmSync(runtimeDir, { recursive: true, force: true });
  mkdirSync(runtimeDir, { recursive: true });
  writeFileSync(join(runtimeDir, ".gitkeep"), "");
  let bytes = 0;
  for (const [from, name] of files) {
    copyFileSync(from, join(runtimeDir, name)); // copyFileSync follows symlinks: every library becomes a plain file
    if (!isWindowsTarget) chmodSync(join(runtimeDir, name), 0o755);
    bytes += statSync(join(runtimeDir, name)).size;
  }
  // llama.cpp is MIT licensed; the Windows archive does not include the licence, so a copy is kept here.
  copyFileSync(join(root, "scripts", "licenses", "LICENSE-llama.cpp.txt"), join(runtimeDir, "LICENSE-llama.cpp.txt"));
  for (const license of readdirSync(source).filter((name) => /^LICENSE./i.test(name))) {
    copyFileSync(join(source, license), join(runtimeDir, `${license.replace(/\.txt$/i, "")}.txt`));
  }
  writeFileSync(versionFile, `${stamp}\n`);

  if (!isWindowsTarget && process.platform === "darwin") {
    const version = capture(join(runtimeDir, serverName), ["--version"]);
    if (version === null) fail(`The bundled ${serverName} does not start.`);
  }
  console.log(`\n✔ llama.cpp ${stamp}: ${files.length} files, ${(bytes / 1e6).toFixed(1)} MB → ${runtimeDir}`);
} finally {
  rmSync(work, { recursive: true, force: true });
}

/** Windows: llama-server.exe plus the shared DLLs (ggml backends are loaded at run time). */
function windowsFiles(source) {
  return readdirSync(source)
    .filter((name) => name === "llama-server.exe" || (/\.dll$/i.test(name) && (!/-impl\.dll$/i.test(name) || name === "llama-server-impl.dll")))
    .map((name) => [join(source, name), name]);
}

/** macOS: llama-server plus every @rpath library it (transitively) links, under the referenced names. */
function macosFiles(source, server) {
  const wanted = new Map([[serverName, server]]);
  const queue = [server];
  while (queue.length) {
    const binary = queue.shift();
    const listing = capture("otool", ["-L", binary]);
    if (listing === null) fail("otool was not found. Install the Xcode command line tools: xcode-select --install");
    for (const match of listing.matchAll(/@rpath\/([^\s]+)/g)) {
      const name = match[1];
      if (wanted.has(name)) continue;
      const path = join(source, name);
      if (!existsSync(path)) fail(`${basename(binary)} needs ${name}, which is missing from the archive.`);
      wanted.set(name, path);
      queue.push(path);
    }
  }
  return [...wanted].map(([name, path]) => [path, name]);
}

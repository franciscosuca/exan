# Package Exan for Windows into a self-contained installer.
#
# Run once on a Windows 10/11 x64 PC that has the build tools installed:
#   - Node.js 22 LTS          https://nodejs.org
#   - Python 3.12             https://www.python.org/downloads/windows/ (tick "Add python.exe to PATH")
#   - Rust (MSVC toolchain)   https://rustup.rs
#   - VS 2022 Build Tools with workload "Desktop development with C++"
#
# Usage:  powershell -ExecutionPolicy Bypass -File .\package-windows.ps1
# Result: src-tauri\target\release\bundle\nsis\Exan_<version>_x64-setup.exe   <- copy this file to any PC
#         src-tauri\target\release\bundle\msi\Exan_<version>_x64_en-US.msi
#
# The installer bundles the UI, the Python engine (exan-sidecar.exe) and the
# llama.cpp runtime. No model is inside; it is downloaded during installation
# or on the app's first start. No admin rights needed on the target PC.

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

function Require($command, $hint) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        Write-Error "Missing '$command'. $hint"
    }
}

Require node   "Install Node.js 22 LTS from https://nodejs.org"
Require npm    "npm ships with Node.js"
Require python "Install Python 3.12 from https://www.python.org/downloads/windows/ (tick Add to PATH)"
Require cargo  "Install Rust (default MSVC toolchain) from https://rustup.rs"

Write-Host "==> npm ci (install UI dependencies)"
npm ci

Write-Host "==> npm run setup (build engine binary + fetch pinned llama.cpp runtime, first run takes minutes)"
npm run setup

Write-Host "==> npm run package (build UI, engine and installers)"
npm run package

Write-Host ""
Write-Host "Installers ready - copy ONE of these files to another Windows PC and double-click it:"
Get-ChildItem -Recurse -Path "src-tauri\target\release\bundle" -Include "*-setup.exe", "*.msi" |
    ForEach-Object { Write-Host "  $($_.FullName)" }

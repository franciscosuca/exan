#!/usr/bin/env bash
# Package Exan for macOS into a self-contained app + DMG.
#
# Run once on a Mac (Apple Silicon or Intel) that has the build tools installed:
#   - Xcode command-line tools:  xcode-select --install
#   - Node.js 22 LTS             https://nodejs.org (or: brew install node@22)
#   - Python 3.12                https://www.python.org/downloads/macos/ (or: brew install python@3.12)
#   - Rust                       https://rustup.rs
#
# Usage:  ./package-macos.sh
# Result: src-tauri/target/release/bundle/macos/Exan.app
#         src-tauri/target/release/bundle/dmg/Exan_<version>_<arch>.dmg
#
# The app bundles the UI, the Python engine (exan-sidecar) and the llama.cpp
# runtime. No model is inside; the model is downloaded on the app's first start.
#
# The build is ad-hoc signed (no Apple Developer account needed). On another Mac
# the first launch needs a right-click -> Open, or:
#   xattr -dr com.apple.quarantine /Applications/Exan.app
# For notarized builds set APPLE_ID, APPLE_PASSWORD and APPLE_TEAM_ID before
# running this script (requires the paid Apple Developer Program).

set -euo pipefail
cd "$(dirname "$0")"

require() {
    command -v "$1" >/dev/null 2>&1 || { echo "Missing '$1'. $2" >&2; exit 1; }
}

if ! xcode-select -p >/dev/null 2>&1; then
    echo "Xcode command-line tools missing. Run:  xcode-select --install" >&2
    exit 1
fi

require node    "Install Node.js 22 LTS from https://nodejs.org"
require npm     "npm ships with Node.js"
require python3 "Install Python 3.12 from https://www.python.org/downloads/macos/ (or: brew install python@3.12)"
require cargo   "Install Rust from https://rustup.rs"

echo "==> npm ci (install UI dependencies)"
npm ci

echo "==> npm run setup (build engine binary + fetch pinned llama.cpp runtime, first run takes minutes)"
npm run setup

echo "==> npm run package (build UI, engine, Exan.app and DMG)"
npm run package

echo ""
echo "Artifacts ready - copy the DMG to another Mac, open it and drag Exan.app to Applications:"
find src-tauri/target/release/bundle -name "Exan.app" -o -name "*.dmg" | while read -r artifact; do
    echo "  $artifact"
done

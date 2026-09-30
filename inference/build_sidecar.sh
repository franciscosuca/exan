#!/usr/bin/env sh
set -eu

pyinstaller --clean --noconfirm exan.spec

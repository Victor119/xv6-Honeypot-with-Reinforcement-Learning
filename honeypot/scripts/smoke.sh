#!/usr/bin/env bash
# smoke.sh - build, then run the headless boot + honeypot round-trip test.
# Intended to run inside the Docker toolchain container from the repo root.
# Build a dedicated fault-injection image, then run the guest acceptance suite.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

HP_TESTING=1 bash "$DIR/build.sh"

echo "== headless boot + round-trip smoke test =="
python3 "$DIR/smoke.py"

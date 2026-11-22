#!/usr/bin/env bash
# Disposable, single-CPU console session; disk writes vanish when QEMU exits.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
exec "${QEMU:-qemu-system-i386}" -accel tcg -smp 1 -m 256 -nic none \
  -nographic -snapshot \
  -drive file=fs.img,index=1,media=disk,format=raw \
  -drive file=xv6.img,index=0,media=disk,format=raw

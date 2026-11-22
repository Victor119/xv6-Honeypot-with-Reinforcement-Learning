#!/usr/bin/env bash
# build.sh - clean build of xv6 + honeypot inside the Docker toolchain.
# May be called from any directory, including a WSL2 Linux checkout.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "== cleaning =="
make TOOLPREFIX= QEMU=qemu-system-i386 clean

echo "== building kernel + user programs =="
# TOOLPREFIX is empty because the Debian toolchain builds elf32-i386 natively
# with -m32; QEMU is qemu-system-i386.
make TOOLPREFIX= QEMU=qemu-system-i386 HP_TESTING="${HP_TESTING:-0}" xv6.img fs.img

echo "== build artifacts =="
ls -l kernel xv6.img fs.img
mkdir -p honeypot/artifacts
{
  date -u '+Built at %Y-%m-%dT%H:%M:%SZ'
  printf 'HP_TESTING=%s\n' "${HP_TESTING:-0}"
  gcc --version | head -n 1
  ld --version | head -n 1
  make --version | head -n 1
  if command -v qemu-system-i386 >/dev/null; then
    qemu-system-i386 --version | head -n 1
  fi
  sha256sum kernel xv6.img fs.img
} > honeypot/artifacts/build-manifest.txt
echo "OK: build complete"

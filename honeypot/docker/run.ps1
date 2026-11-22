# run.ps1 - Windows/PowerShell entry point for the Docker-based xv6 honeypot
# toolchain. Run from the repository root.
#
#   .\honeypot\docker\run.ps1 image   # build the toolchain Docker image (once)
#   .\honeypot\docker\run.ps1 build   # compile kernel + user programs
#   .\honeypot\docker\run.ps1 smoke   # build + headless boot + M1 round-trip test
#   .\honeypot\docker\run.ps1 run     # build + interactive xv6 in QEMU (Ctrl-a x to quit)
#   .\honeypot\docker\run.ps1 shell   # open a shell in the container
#
# Requires Docker Desktop installed and running.

param(
  [Parameter(Position = 0)]
  [ValidateSet('image', 'build', 'smoke', 'run', 'shell')]
  [string]$Command = 'smoke'
)

$ErrorActionPreference = 'Stop'
$Image = 'xv6-honeypot'

# Repo root = two levels up from this script (honeypot\docker\run.ps1).
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Mount = "${RepoRoot}:/xv6"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Error "docker not found. Install Docker Desktop and ensure it is running."
}

switch ($Command) {
  'image' {
    docker build -t $Image (Join-Path $PSScriptRoot '.')
  }
  'build' {
    docker run --rm -v $Mount $Image bash honeypot/scripts/build.sh
  }
  'smoke' {
    docker run --rm -v $Mount $Image bash honeypot/scripts/smoke.sh
  }
  'run' {
    docker run --rm -it -v $Mount $Image bash -lc `
      "honeypot/scripts/build.sh && bash honeypot/scripts/run.sh"
  }
  'shell' {
    docker run --rm -it -v $Mount $Image bash
  }
}

# Native command failures do not obey ErrorActionPreference in Windows
# PowerShell 5.1. Preserve Docker's exit status for callers and CI.
exit $LASTEXITCODE

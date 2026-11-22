# Milestone 1: foundation

This milestone establishes the xv6 x86 baseline and demonstrates communication
between the kernel and one trusted native user-space test agent. Real syscall
mediation, controlled execution and trained-policy inference are later milestones.

## Baseline and status

- Upstream: https://github.com/mit-pdos/xv6-public
- Base revision: `eeb7b415dbcb12cc362d0783e41c3d1f44066b17`.
- xv6 uses syscall vector `0x40`; the diagram's `0x80` is adapted to this kernel.
- The implementation now uses two actual shared pages, rather than syscall
  copies of events and replies.
- Runtime verification results are recorded in `M1-validation.md` after testing.
- Client confirmation of the proposed scope and training interface remains open;
  see `M1-scope-and-policy.md`. Implementing an interface is not client acceptance.

## Build and run

Use a Linux checkout under Ubuntu 24.04 in WSL2, or the Docker environment.
Keep WSL2 source under the Linux filesystem, such as `~/src/xv6-honeypot`.

```sh
sudo apt-get update
sudo apt-get install build-essential gcc-multilib qemu-system-x86 perl python3
bash honeypot/scripts/build.sh
bash honeypot/scripts/run.sh
```

On Windows with Docker Desktop available:

```powershell
.\honeypot\docker\run.ps1 image
.\honeypot\docker\run.ps1 build
.\honeypot\docker\run.ps1 run
.\honeypot\docker\run.ps1 smoke
```

If local PowerShell script execution is disabled, run the reviewed launcher in
a single process without changing the machine's execution policy:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\honeypot\docker\run.ps1 smoke
```

The build explicitly generates both `xv6.img` and `fs.img`. Scripts propagate
errors and produce a version/hash manifest under `honeypot/artifacts/`.
The Docker base is a Debian bullseye tag, not a digest-pinned toolchain; the
manifest records actual versions. WSL2 and Docker commands require validation
on their respective hosts before claiming environment-specific reproducibility.

The guest build disables floating-point/SIMD code generation because xv6 does
not enable or preserve that CPU state. It also disables automatic GNU property
notes when the assembler supports that option: a note placed at a host linker's
default address can make the raw `initcode` payload enormous. Compiler warnings
remain errors. Numeric physical/virtual address conversion and an explicit
non-returning shell executor allow the code to compile with GCC 13.

The launcher uses QEMU TCG, one CPU, 256 MiB, no guest networking and snapshot
writes. Quitting and relaunching resets guest filesystem changes to the built
images. There are no host shared folders or forwarding rules in this guest.
Use Ctrl-a x to quit the interactive launcher.

## Trusted agent startup

`init` uses `hp_start()` once, before starting the shell. The kernel accepts
that call only from the original init process, and marks only its new child
as a bootstrap candidate. Ordinary forks do not inherit this marker.

The candidate gains authorization only after successful exec of `/hpagent`.
This relies on the packaged boot image being trusted and the shell not having
started yet. Process names, a manually executed copy and a caller-selected PID
cannot grant authority. The agent registers, maps its pages, and signals init
through a startup pipe before the shell is launched.

Successful subsequent exec or exit revokes authority and wakes a waiting
requester. Failed exec preserves the current image and its authority. Forked
children have neither the authority nor the shared mappings. The process-table
slot can be reused without inheriting the role. Agent recovery in M1 is a reboot;
there is no automatic reassignment to a new process.

## Two-page interface: ABI version 1

| Page | User address | Agent permission | Other processes |
|---|---|---|---|
| Event | `0x7fffe000` | Read only | Unmapped |
| Decision | `0x7ffff000` | Read/write | Unmapped |

Both physical pages belong to the kernel for the full boot. The kernel uses
its own aliases to publish and validate data. The addresses are reserved above
normal process memory; heap growth cannot reach them, and ordinary syscall
buffer arguments cannot alias them. Fork copies only normal process memory.
Exec/exit/page-table cleanup removes aliases without freeing kernel storage.

`honeypot.h` defines the exact structures. The event contains an ABI version,
readiness flag, request ID, synthetic syscall number, PID and three integer
argument slots. The decision contains version, request ID, action and readiness.
The agent publishes fields before setting readiness and calling `hp_decide()`.
The kernel checks a snapshot under its lock. A flag alone is never a lock.

| Syscall | Purpose |
|---|---|
| `hp_start()` | Init-only, single-use fork of the bootstrap candidate |
| `hp_register()` | Authorized agent only; map pages; idempotent |
| `hp_next()` | Agent sleeps until an event is available in its event page |
| `hp_decide()` | Validate and accept a decision from its decision page |
| `hp_trigger(nr, arg0)` | M1 synthetic injector; returns action or transport error |

Action IDs are **BLOCK=0, ALLOW=1, RESTRICT=2**. This replaces the provisional
mapping in the initial commits. No trained policy has been integrated against
the old mapping. Preserve these IDs in the eventual policy handoff.

Only one request can be outstanding. A second caller receives `HP_ERR_BUSY`.
The requester sleeps, allowing the agent and kernel to run. The deadline is
100 timer ticks, approximately one second; ticks are the authoritative unit.
Replies at or after the deadline, mismatched IDs, duplicates, invalid actions,
wrong versions and unset readiness are rejected. IDs never repeat within a
boot: after unsigned wraparound the channel returns an exhaustion error.

| Result | Value |
|---|---|
| Invalid caller/reply | -1 |
| No registered agent | -2 |
| Busy | -3 |
| Timeout | -4 |
| Interrupted requester | -5 |
| Request-ID exhaustion | -6 |

These are transport outcomes, not policy BLOCK decisions. Future M2 enforcement
must convert failed exchanges to the conservative BLOCK fallback and log the
reason separately. Today `hp_trigger` only returns a code; it does not execute
or block an actual filesystem operation.

## Demo and acceptance suite

Init launches the fixed-policy agent automatically. In the guest:

```text
hptrigger 0       # ALLOW
hptrigger 3       # BLOCK
hptrigger 4       # RESTRICT
hpagent          # registration denied for a manually launched copy
hptest basic     # real user/kernel isolation and basic decision tests
hptest stress    # 1,000 exchanges
```

The rule is a deterministic communication test, not a danger classifier or RL
model. Zero allows, positive odd numbers block, positive even numbers restrict.

```sh
bash honeypot/scripts/smoke.sh
```

This builds a dedicated `HP_TESTING=1` image and runs `smoke.py`. It checks
1000 exchanges; unauthorized registration/fetch/reply; unmapped pages; reserved
heap addresses; agent fork; failed and successful exec; agent exit; event-page
write protection; stale/invalid/duplicate/late replies; busy requests; timeout;
killed requester recovery; and process-slot reuse. Fault modes exist only in
the acceptance build and use synthetic request numbers from `honeypot_test.h`.

The runner starts fresh disposable VMs for destructive lifecycle cases, fails
on missing output/EOF/timeouts/panics/test failures, and saves serial logs and a
JSON report under `honeypot/artifacts/`. User page faults during isolation tests
are expected; a kernel panic is a failure. `--cpus 2` is an additional robustness
check; the supported M1 configuration remains one CPU.

Reports include UTC start/end timestamps, elapsed time, tool versions and image
hashes. These describe actual test runs independently of Git commit timestamps.

For an already built image, `python3 honeypot/scripts/smoke.py --basic-only`
runs checks without fault injection. A custom QEMU executable can be supplied
with `--qemu`. Run `build.sh` again after acceptance testing to restore a normal
image without test-only agent controls.

After restoring the normal image, also check the upstream OS behavior:

```sh
python3 honeypot/scripts/smoke.py --basic-only --upstream
```

This adds `forktest`, the complete upstream `usertests` program, and another
basic channel check after those tests. Each upstream command has a 300-second
limit; lowercase failure messages from child tests also fail the run. The
filesystem changes made by these tests are discarded with the QEMU snapshot.

## Remaining kernel work and milestone boundaries

- **M2:** collect command context and mediate selected real syscall handlers,
  validate/capture arguments, match real requests, and bypass the trusted agent
  path to avoid recursive approval. Remove or gate the synthetic injector.
- **M3:** enforce protected resources and restricted real execution, collect
  event/result logs, and validate controlled damage and scenario resets.
- **M4:** import the supplied policy, implement native C inference, and verify
  Python/C action parity. Offline training is outside the base implementation.
- M1 page isolation does not make unmodified xv6 a production security boundary.
  Essential file and process protections, including blocking unauthorized agent
  termination during attacker sessions, remain M3 work.

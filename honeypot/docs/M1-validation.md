# M1 validation status

Validated on 30 September 2026. Clean builds, xv6 boot and the implemented M1
guest acceptance checks now pass. Final milestone acceptance remains open for
client confirmation of the scope, scenarios and policy interface. Git commit
timestamps are not evidence of test execution or implementation duration.

## Recorded results

| Check | Result |
|---|---|
| Clean `HP_TESTING=1` build | Passed; kernel and both disk images generated |
| Clean normal build | Passed; test-only agent controls excluded |
| One-CPU guest acceptance | 13/13 checks passed; 10.888 seconds |
| Two-CPU guest acceptance | 13/13 checks passed; 10.924 seconds |
| Normal-image regression | 5/5 checks passed; 73.939 seconds |
| Upstream xv6 tests | `forktest` passed; `usertests` printed `ALL TESTS PASSED` |
| Channel after upstream tests | Basic isolation and decision checks passed |
| Disposable sessions | All three runs preserved the baseline image hashes |
| Host runner unit tests | 5 passed |
| Git whitespace checks | Passed |

The 13 acceptance checks cover basic decisions and 1,000 exchanges; unauthorized
agent APIs; unmapped control pages and the reserved heap boundary; process-slot
reuse; invalid, stale, duplicate and late replies; timeouts, busy requests and
interrupted requesters; agent fork and failed exec; successful exec, exit and
event-page write faults; and unavailable-agent behavior after revocation.

Expected user-mode page faults are part of the isolation tests. No kernel panic
occurred in the passing runs. The one-CPU configuration remains the M1 baseline;
the two-CPU run is an additional concurrency check. These checks do not establish
production isolation or implement real syscall mediation.

## Evidence and environment

The checked-in [evidence directory](evidence/2026-09-30/) contains unmodified JSON
reports, build manifests, source revisions, source hashes and serial-log hashes:

- [One-CPU acceptance](evidence/2026-09-30/results-acceptance-1cpu.json)
- [Two-CPU acceptance](evidence/2026-09-30/results-acceptance-2cpu.json)
- [Normal-image regression](evidence/2026-09-30/results-basic-upstream-1cpu.json)
- [Build and source context](evidence/2026-09-30/validation-context.json)

Builds ran in a temporary Alpine x86 VM using GCC 13.2.1, GNU binutils 2.42 and
GNU Make 4.4.1. Packages and a source snapshot were supplied on read-only media;
the builder ran without a network adapter. Both builds used the repository's
`build.sh`, including its clean step. Source inputs were compared with the
working tree before recording the revisions in the evidence.

The resulting xv6 images ran directly under Windows QEMU TCG version
`10.1.94 (v10.2.0-rc4-12104-gb2a6201393)`, with 256 MiB RAM, no guest networking
and disposable snapshot writes. The test runs occurred at 23:41-23:42 UTC.
Docker and WSL2 execution have **not** been validated on this host.

Full build logs, serial logs, both image variants and manifests are retained in
the ignored `honeypot/artifacts/` directory and its local
`M1-validation-2026-09-30.zip` evidence bundle. The repository root has been
restored to the normal image. Earlier host-only Bash/PowerShell syntax checks
and the mocked Docker failure-propagation check remain recorded from 29 September;
they do not substitute for running Docker or WSL2.

## Issues found and fixed during validation

- GCC 13 rejected pointer-based physical-address translation and the shell's
  undeclared non-returning recursion. Address conversion now uses unsigned
  arithmetic, and the shell executor has an explicit `noreturn` declaration.
- Automatic GNU property notes expanded the 44-byte raw startup program to
  about 128 MiB. The Makefile probes and disables that assembler behavior.
- Host compiler defaults generated SSE instructions in early kernel startup,
  causing an invalid opcode and triple fault. Guest builds now disable
  floating-point/SIMD code generation, which xv6 does not enable or preserve.
- Concurrent console messages split a successful test marker. Test status and
  shell prompt writes are now atomic at the console, and init quietly reaps
  background children. Both acceptance configurations passed after this fix.

Compiler warnings remain errors. The inherited linker warnings about RWX load
segments remain; changing xv6's executable memory layout is outside this M1 fix.

## Reproduce on a configured Linux host

```sh
python3 honeypot/scripts/test_smoke_runner.py
bash honeypot/scripts/smoke.sh
cp honeypot/artifacts/build-manifest.txt honeypot/artifacts/build-manifest-acceptance.txt
python3 honeypot/scripts/smoke.py --cpus 2
bash honeypot/scripts/build.sh
python3 honeypot/scripts/smoke.py --basic-only --upstream
```

On Windows, an already built image can be checked with the same Python runner
and `--qemu C:\path\to\qemu-system-i386.exe`. Keep the matching `kernel`,
`xv6.img` and `fs.img` together. Restore the normal build after testing the
acceptance image; its fault-injection controls are intended only for tests.

## Still open for M1 closure

- Client confirmation of the proposed scope, acceptance scenarios and policy
  feature/export contract in [M1-scope-and-policy.md](M1-scope-and-policy.md).
- Verify the selected WSL2 or Docker workflow before claiming reproducibility
  on that specific environment; the recorded runtime evidence uses Alpine and
  native Windows QEMU.
- Client review of the demonstration and recorded evidence.

Actual syscall enforcement, protected-resource/controlled-damage behavior and
trained-policy inference remain M2-M4 work. The current agent applies a fixed
test policy to synthetic requests.

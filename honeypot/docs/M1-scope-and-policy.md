# M1 scope and policy interface: confirmation draft

This records the implementation baseline and a concrete proposal for the
remaining client decisions. It does not record client approval that has not
been received. Confirm the feature specification before training starts.

## Baseline implemented

- xv6 x86 at upstream revision `eeb7b415dbcb12cc362d0783e41c3d1f44066b17`.
- One attacker console session; one request at a time; QEMU TCG, one CPU.
- Native guest agent, init-controlled bootstrap, two actual shared pages.
- ABI version 1, action IDs BLOCK=0, ALLOW=1, RESTRICT=2.
- 100-tick deadline; negative transport statuses; conservative BLOCK fallback
  for future enforcement; reboot-only agent recovery.
- Python may be used offline. No Python runtime or model training in the guest.
- WSL2 Linux checkout is the planned development workflow; Docker is provided
  as an alternative. Current-host validation is recorded separately.

## Proposed attacker surface for M2/M3

| Area | Proposed scope |
|---|---|
| Commands | `ls`, `cat`, `echo`, `cd`, `mkdir`, `rm`, a bounded file writer |
| Shell syntax | Simple commands and basic redirection |
| Kernel operations | Selected `exec`, `open`, `read`, `write`, `unlink`, `mkdir`, `chdir`; agree precise coverage before M2 |
| Disposable state | Files under a dedicated `/research` directory |
| Protected state | Boot/agent binaries, agreed essential utilities, control pages, agent/control processes |
| Restrictions | Bounded real writes and mutations confined to disposable targets; no fabricated success |
| Exclusions | Pipes/background jobs as acceptance requirements, scripts, networking, SSH, Linux binary compatibility, multiple attacker sessions |

The shell provides command context, but enforcement must also cover selected
syscalls made directly by supported programs. Resolve the actual target and
check mandatory protections before allowing a mutation. Exact allowed flags,
path handling, file sizes and operation bounds need client confirmation.

## Proposed tabular policy handoff

The transport ABI is implemented; the model feature contract below is a draft
for review and has no effect on the current synthetic test policy.

A compact integer Q-table avoids floating-point inference inside xv6. Proposed
state features, in order:

1. Operation class: metadata=0, read=1, write=2, delete=3, exec=4, other=5.
2. Resolved target class: unknown=0, disposable=1, essential=2, agent/control=3,
   outside permitted scope=4.
3. Requested byte count: none/not applicable=0, 1..4096=1, above 4096=2.
4. Session history: no prior damage/protection attempts=0, permitted damage=1,
   any protected-resource attempt=2. Protected attempts take precedence.
5. Remaining permitted mutation budget: exhausted=0, 1..4096 bytes=1, above
   4096 bytes=2. Initial budget is a scenario parameter to confirm.

With ranges (6, 5, 3, 3, 3), there are 810 states. Row index is
`((((operation * 5 + target) * 3 + bytes) * 3 + history) * 3 + budget)`.
Each row contains three signed 32-bit scores in BLOCK/ALLOW/RESTRICT order:
9,720 bytes of raw scores. Conversion and C inference are M4 work.

Use the maximum score; ties choose the lowest action ID. Reject invalid feature
values rather than wrapping indices. A missing/invalid policy must trigger a
logged conservative fallback. Mandatory kernel restrictions may override the
policy and must be logged separately.

Proposed export: versioned metadata plus CSV rows
`state_id,q_block,q_allow,q_restrict`. The handoff must contain all 810 rows,
feature definitions/preprocessing, action IDs, policy version, scaling rules,
Python reference inference, test vectors including ties and boundary cases,
and checksums. Agree any different representation before training.

Client-owned training remains the base arrangement. A trained policy is needed
before M4, not for the M1 communication demo. Developer-owned training is a
separate optional milestone under the existing proposal.

## Scenarios for confirmation

- Benign read/list operation: allowed, with context/action/result recorded.
- Disposable file mutation: changes real guest state within the agreed bound.
- Protected mutation: denied even when the shell is bypassed.
- Agent failure: bounded fallback, stale reply rejection and reboot recovery.
- Agent isolation: no role takeover or unauthorized event/decision access.
- Policy parity: identical Python/C actions, including ties and invalid input.
- Reset/evaluation: fixed initial filesystem and repeatable scenario inputs.

These span the full project. Only the synthetic channel, lifecycle/isolation
foundation and boot/build evidence are M1 implementation acceptance checks.
Actual operation enforcement and policy parity are later milestone checks.

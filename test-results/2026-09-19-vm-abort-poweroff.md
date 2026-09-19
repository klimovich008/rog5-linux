# ARM64 VM abort cleanup reaches normal poweroff — 2026-09-19

**The corrected failure path passed on the retained ARM64 VM.** An actual busy
RAM executable overlay was detached, its shared9P alias released, the induced
service failure124 preserved, and packaged systemd powered off without a panic.
This does not close the earlier full Denial session timeout or any phone result.

Evidence-producing source `19eadb8c44e24c3bd968d86ed18769c3dc0a3f4c`, tree
`8dc62ef0912df887d8c4418a9b39037b73ba7db7`. Production cleanup fix remains `f5c8acfd`.
No production script changed in this turn; no kernel, Flutter, Denial or GTK
rebuild. Existing compiled generic ARM64 init and kernel were reused by exact
hash. Both new initramfs archives are private VM fixtures with no boot authority.

## Executed experiment

The root is the existing immutable mapped-file Arch runtime over read-only9P.
Before executing packaged systemd as PID1, the fixture installs the same
original-bin alias and RAM executable overlay as production. A live sleep process
holds the overlay as its cwd. Ordinary unmount returns32. A real one-second
`timeout` then invokes the actual sourced production EXIT cleanup. Both mounts
must disappear while the same holder is still alive; return124 is checked and
passed to systemd. The service's OnFailure triggers normal poweroff.

The minimal target omits full sysinit/PAM/logind/Denial/UI startup. It isolates
mount teardown and packaged PID1 shutdown; it does not model a completed session.
Rootless container limits:1GiB/no-swap,2CPU,64pids; guest512MiB,1vCPU;90s host
deadline and8MiB log cap. Network disabled; no host GPU exposed. Runtime, kernel,
initramfs and empty payload mounts are read-only. Only guest RAM is writable.

| Attempt | Result | Runtime |
|---|---|---:|
| r1: overlay incorrectly installed after systemd | FAIL before cleanup markers; service127, symlink loop, later PID1 panic | 23.768s |
| r2: production-matching pre-PID1 staging | PASS scoped abort cleanup and normal poweroff; service124 retained | 25.696s |

R1 also used an invalid `StandardOutput=console` value. R2 uses `tty`,
`TTYPath=/dev/console`, and inherited stderr without requiring journald. The
post-PID1 setup difference and recursive paths suggest mount propagation as the
r1 cause; no before/after mount propagation trace was captured, so that causal
explanation remains a hypothesis. R1 was not a valid failed treatment of the
production fix. Its files, raw log and failed result remain unchanged.

R2 requires ordered, unique markers for busy status32, detached mounts with live
holder/status124, and returning124; the real systemd service exit log must agree.
It also requires normal `reboot: Power down`, no panic, stable input/output
hashes, successful owned-container cleanup and container absence. QEMU0 alone
is insufficient. All checks passed.13 inputs and8 outputs per attempt were
rehashed afterward; both containers are absent.

R2 initramfs SHA256:
`01d6aa51dff402c3f956ee59f4d7d9ceeeb0057e638725a92e5c00c2bb62d0cc`.
The paired JSON contains both attempts' commands, scripts, source/artifact
identities, preparation steps, timings, marker excerpts and cleanup receipts.
Raw evidence is private under `rog5-vm-abort-guest-20260919-r1` and `-r2`.

## Qualification boundaries and next work

The previous108-suite active pass atf5c8acfd is reused: all production tools and
host scripts remain identical. It was not rerun for private fixture/evidence
publication. The actual new VM test above is separate runtime evidence. Earlier
full-session FAIL, Mousepad137 investigations, standard300s failure and the
low-caret interaction PASS are preserved; no historical result is overwritten.

The low-caret run's retained host capture mtimes span54.965s, including28.296s
from first home capture to Mousepad-launched capture. These intervals include
actions, waits and image writes, and cannot be combined with guest clock values
or treated as per-function timings. Its existing service-start stage took23s.
Next inspect and instrument those startup intervals before repeating the full
session; retain all current app/user/PAM deadlines. No repeat of proven low-caret
typing is needed merely to qualify abort cleanup.

Phone OLED/touch/Adreno, ordinary starts,60-minute use, screen-off/wake and
installed integration remain NOT RUN. S06/R01 remain FAIL. No phone/USB,
signing, admission, claim, protected-storage operation or new phone candidate.

## Run improvement

A reduced VM fixture must preserve lifecycle setup order, including mounts made
before PID1. The first setup mismatch obscured the intended test; matching
production produced an answer in26s without another400s UI run. Keep source
function proofs, isolated mount tests, minimal VM shutdown and complete-session
qualification separate. This turn is progress; the full phone goal remains open.

Publication checks:8mobile-status cases PASS(0.021s);548-set artifact inventory,
generated status and whitespace PASS. All547 previous sets and existing artifact
pointers remain semantically unchanged. No integrated tier was repeated.

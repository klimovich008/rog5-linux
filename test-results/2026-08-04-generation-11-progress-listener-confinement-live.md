# Generation-11 progress-listener confinement — live result

Date: 2026-08-04

Result: **REJECTED safely before PREPARE — the sole RAM-only Generation-11
recovery boot reached exact recovery ACM/NCM, but the privileged
`serve-progress-deferred` host path rejected its newly started TCP 8081
collector as not uniquely confined before publishing the bundle-server ready
marker. No bundle transfer, recovery PREPARE, COMMIT intent, kexec target, NFS
handoff, or target SSH occurred. Exact Alpine fallback and host cleanup passed.**

## Published prerequisite

The lifecycle ran from clean pushed commit
`04132f039669f437589078e9522b0751512c5bd2`. Its connected-preflight evidence
and publication checkpoints passed independent review, complete local CI, and
exact-head GitHub Actions. Run `30921533485` passed recovery-core in 4m30s and
QEMU in 34s.

The final same-head connected preflight passed immediately before the cycle.
There was exactly one same physical `lahaina` fastboot device, the Generation-11
claim paths were absent, ModemManager was inactive, TCP 8081 was free after a
bounded stop of SteamOS's socket, and the repository was clean and synchronized
with its origin branch.

## One-shot execution

The fixed claim consumer irreversibly entered the exact private
`BOOT_CLAIMED` record before device inspection. Its public SHA-256 is
`0f082a8e6ca6b1ae23a928ddacb21a7b1782b3bc2aa9ead190b927fbcbe983bf`;
the record itself remains outside Git. Fastboot sent the 100,663,296-byte AVB
image once and reported `OKAY`; the boot completed in 12.788 seconds. The live
gate then proved the shell-free stable-recovery archive and observed exact
recovery ACM at `/dev/ttyACM1` plus recovery NCM.

The target diagnostic collector armed first. The privileged bundle controller
then started the fixed receive-only progress collector, which emitted:

```text
READY receive-only recovery progress collector on 169.254.77.1:8081 via enp4s0f3u1u2
FAIL recovery progress listener is not uniquely confined
PASS recovery progress capture result=PARTIAL reason=NO_ADMISSION records=0 authority=NONE
INFO recovery bundle host network state removed
```

The private progress record contains zero records, zero wire bytes,
`phases=none`, `result=PARTIAL`, `reason=NO_ADMISSION`, and
`authority=NONE`. Because the controller exited before the exact TCP 8080
bundle-server ready marker reached the lifecycle, recovery control was never
started. Therefore there was no request/session admission, bundle transfer,
PREPARE, durable COMMIT intent, NFS service, or target execution.

The already-armed diagnostic collector later rejected at its own preflight
because exact diagnostic ACM never became stable before its fixed deadline. It
recorded zero target frames and zero dropped USB events. That independent
failure is consistent with no target execution; it is not used to infer a
later device-side stage.

## Fallback and cleanup

The lifecycle classified the failure as pre-COMMIT, proved the exact Alpine
fallback profile was restored, and passed strict key-pinned fallback SSH on the
same recovery USB path. The fixed host cleanup proof passed. Final checks found
the fallback NetworkManager profile connected, no fastboot device, no project
lifecycle process, and a clean Git worktree. SteamOS's previously active TCP
8081 socket was restored to active/listening with one listener.

No flash, erase, wipe, slot operation, factory reset, phone-storage mount, or
intentional project storage write occurred. The fallback reads retain only the
already accepted bounded BusyBox-history and read-induced ext4-atime effects.
Private serial, session, request, credentials, and raw evidence remain outside
Git. The host interface name reproduced above is public evidence.

## Consumption and integrity chain

Generation 11 is permanently consumed regardless of this pre-COMMIT result.
Its policy row is removed, its exact inventory role begins with `consumed`, and
the permanent private claim independently prevents reuse. Exact-basis
readmission now fails closed before host inspection.

- temporary-boot policy:
  `1f3de8269d986c94c0c0c223a059b9953a04a05ae2895c611710b53e5ddfadea`;
- artifact manifest:
  `5f6669d8d82a71c4c318dcf3f348f03d973ef6e65a6c88be1a7f2e0cbe5dd1cc`;
- minimal profile:
  `8c3a41a4e55b607f91c5eb0b31bb51a37e419cd18308ba41036ac2fe25bae3bd`;
- source/DT outer:
  `3b4e6ef4af08d06f3fc1df7d796f0076b4c29536384a95690d7ee77872d8bc05`.

This result identifies the next amplification-first boundary: reproduce and
fix the production TCP 8081 ownership/PID check offline before issuing any
distinct successor. It authorizes no Generation-11 retry and makes no target,
kernel, storage, sensor, or normal-SSH acceptance claim.

## Publication

Independent spec and standards reviewers found and resolved stale current
ranges, historical-checkpoint tense, one overclaim about listener ownership,
and evidence wording/formatting issues. Two complete local Linux `ci` runs
passed, including one final unchanged-tree run after every review fix. Commit
`3cee3f177ba0b7ae758f0f661cc8fcdaa30b7c40` published the consumed transition;
exact-head GitHub Actions run `30926911113` passed recovery-core in 3m59s and
QEMU in 35s.

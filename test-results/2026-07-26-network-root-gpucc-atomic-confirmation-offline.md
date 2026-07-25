# Network-root v17 atomic GPUCC confirmation — offline acceptance

Date: 2026-07-26

Result: **offline acceptance passed; one attended RAM-only target attempt is
eligible; no new GPUCC or acceleration claim**. Nothing was flashed.

V16 never entered the Linux 7.1 target. Its staging recovery loaded the exact
trace-free payload, but a 284-second operator gap after load exceeded the
independent 180-second staging watchdog. Both later execute invocations failed
before serial transmission, and fallback/host cleanup passed. The
[v16 staging-only report](2026-07-26-network-root-gpucc-confirmation-live.md)
records that boundary.

V17 changes only the host control plane. It combines the already reviewed
trace-free load and execute actions in one process, removing the operator gap
while preserving every v15 artifact and v16 target-side gate.

## Unchanged kernel, package, and target contract

V17 introduces no kernel, module, DTB, initramfs, wrapper, package, firmware,
baseline, disarm, or probe change. The exact bundle verifier invokes the
complete v15 nested artifact verifier and the v16 semantic, mutation,
pre-disarm baseline, and guarded-probe tests.

| Identity | SHA-256 |
|---|---|
| Linux 7.1.4 Image | `d30df38804750ded48607135a7d23d4f95e0947c49b68395a8f6818c4a27c54b` |
| matching module archive | `9350e5a010c0af11fe4bde48527d056701c83a0072be4ad29cce2565a75204a1` |
| external `gpucc-sm8350.ko` | `9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a` |
| GPUCC-only DTB | `e6f86c3022f58a765351b5b761c8bc815b093209517adb4678107d542ff5bcb5` |
| target initramfs | `4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac` |
| staging initramfs | `68b8729c5aef7f9a3eacba07685fe952f4df6cac29eb8c35d9559fda98722fab` |
| temporary-boot AVB image | `bb4a6e34c98475f991a9575defe57c52ac732da0cea96a10585ee0bb92ae7730` |
| fourteen-file manifest | `a739f975f87ac30918625178007b4cd7302449ae96c26e5c42185e9e1a0425cc` |

The target still requires all three built-in core trace parameters at
command-line count zero, mode `0400`, and value `N`. The hash-pinned read-only
baseline must pass with the original 900-second target watchdog still armed.
Only then may the existing disarm helper atomically replace it with the
75-second independent probe watchdog. The required post-load settle interval
remains 30 seconds.

## Atomic transport

The ACM helper exposes one compound mode, `confirm-gpucc`, with the immutable
sequence:

1. `load-gpucc-confirmation`;
2. `execute`.

The load command contains diagnostic systemd masks and
`ROG5_RECOVERY_TIMEOUT=900`, but no Qualcomm, CCF, or RCG2 core trace flag.
The execute command remains exactly `kexec -e`.

Both `ALLOW_NETWORK_ROOT_ACM=1` and `ALLOW_ATTENDED_KEXEC=1` are required
before host checks or device discovery. The sequence has no sleep, retry loop,
exception handler, mutable command, or user-supplied payload.

The existing load-marker race behavior remains unchanged: a missing marker
may cause exactly one rediscovery and replay of the identical idempotent load
action. A load failure exits before execute. Execute still uses the existing
non-retryable path: after its one serial call, every error propagates without
replay.

## Test-first evidence

The new unit expectations failed before implementation because
`SEQUENCES`, `run_fixed_sequence()`, and the compound CLI mode did not exist.
The exact v17 bundle test likewise failed before its verifier existed.

After implementation:

- all 12 ACM unit/pseudoterminal tests pass;
- the sequence calls trace-free load and execute in exact order;
- a synthetic load failure proves execute is unreachable;
- the kexec guard fails before device discovery;
- the existing real-PTY identical-load replay remains bounded to one;
- the existing execute-disconnect and never-retry tests pass;
- semantic verification rejects an operator delay or altered guard;
- mutations reversing the sequence, duplicating execute, selecting the traced
  load, adding delay, weakening the guard, making execute retryable, or
  deleting the failure-order test are rejected;
- the complete v15 artifact/AVB/zero-storage verifier passes;
- all v16 trace-free target semantic, mutation, baseline, and probe tests
  pass; and
- the exact v17 nested bundle verifier passes.

The pinned procedure sources are:

| Procedure source | SHA-256 |
|---|---|
| atomic ACM helper | `105bc5f7ca91693b0ed42c70686162c93fe84a56c6a9643189e43a49c2759176` |
| ACM unit/pseudoterminal tests | `08aee76f4505d9e27dc435eac25d080584c175116f0ae3f6d93f36e520ef8e6d` |
| temporary-boot operator guidance | `2c4e95537bf796a942f9e73e2a5eb3db71abf8e5bf9aae1f0617ecb08e9290ca` |
| atomic semantic verifier | `435c84b7ed990aaa6f27b959977cebbc0fc978dad928063af5ed6a1644964bce` |
| atomic mutation test | `23311b66521a18fbb1645dfd7cb9ae91b7fdefa2df486c96882a94db44844095` |
| pre-disarm target baseline | `cbbbce7149ea35c67cfefac6b312c86a88ecf81dc34b0f77d124d6d0007267a6` |
| pre-disarm baseline source test | `b745eabbfdd7a19d49f178b9100b6b12bc47e73f07eef26da6f965bd6c731a5b` |
| guarded target probe | `7fbc01a2308ea258c51e2f88c01346bd8397dcb545f8f7cab7e13b6f23fba33e` |
| exact v17 bundle verifier | `fba4600d287421dd1be4938fe5fc32e9839a278a578a5d906ef21b1d9633b18f` |
| v17 bundle source test | `cfbacfeb996072dae4d8192568ae824081d654f16ab72432e39c40ff49319d53` |

No binary artifact, credential, private identifier, or personal data is
committed.

## One-shot live gate

V16 must not be rerun. One v17 cycle may use the exact same non-flashing AVB
image. The compound action must run immediately after temporary boot, without
an intervening task boundary. After strict target SSH appears:

1. run the hash-pinned read-only baseline before disarming the 900-second
   target watchdog;
2. stage only the exact module, disarm helper, and probe helper in target
   tmpfs;
3. verify hashes, ownership, modes, zero storage, disabled consumers, clean
   logs, systemd, USB, NFS, and thermals;
4. atomically disarm the initial watchdog and run confirmation mode with the
   75-second independent watchdog and 30-second settle;
5. accept only eight outer markers through `registration-complete ret=0`,
   returned module load, exactly one bound GPUCC device, and every post-load
   gate; and
6. normally reboot to exact fallback after PASS, or let the watchdog restore
   fallback after any non-returning operation.

There is no live retry. A v17 PASS accepts only the GPUCC/CCF foundation.
Power domains, regulators, IOMMU, GMU, firmware, DRM/MSM, render nodes, and
accelerated desktop remain separate tiers.

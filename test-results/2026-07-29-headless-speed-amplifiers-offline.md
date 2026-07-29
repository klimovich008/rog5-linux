# Headless speed amplifiers — offline result

Date: 2026-07-29

Result: **PASS offline; no phone authority granted**

## Scope

This checkpoint shortened the development loop before further subsystem
bring-up:

- added a read-only pstore/ramoops snapshot after rollback-watchdog arming;
- exported bounded postmortem metadata through every framed recovery
  response;
- added a hardware-free repository test tier and GitHub Actions workflow;
- added a board-neutral full-system ARM64 QEMU kernel-to-PID-1 smoke test;
- rewrote the active plan around a minimal headless server and froze
  desktop, browser, Vulkan, and GPU work.

No phone command, fastboot action, partition write, production credential, or
external service setup occurred.

## Tests

The following passed:

```text
reference protocol/model:                         48 tests
native responder and fault injection:             55 tests
recovery init policy:                              6 tests
aggregate unprivileged repository Linux ci tier:  PASS
QEMU ARM64 kernel-to-initramfs handoff:            PASS
stable recovery initramfs, two clean builds:       byte-identical
ASUS 5.4 wrapper, two clean builds:                byte-identical
raw boot-v3 and test-only AVB packaging:           byte-identical
```

The aggregate tier was run in an unprivileged disposable Ubuntu 24.04
environment because the host does not have Clang installed. The full-system
smoke built exact upstream Linux commit
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` and reached the marker:

```text
PASS qemu-system arm64 initramfs boot
```

QEMU proves only the generic ARM64 kernel/initramfs handoff. It does not
emulate or attest ASUS/Qualcomm hardware.

## Final reproducible identities

```text
recovery init source:
2f3357f70606a3de52b30a0c8e6f4bc34021b9ae5622cd03253f319433783568

stable recovery initramfs:
7b02c4227db7db299287395d4a2fbeb89b9e9451a96c2447aa6f7dc6e8f90c17

ASUS 5.4 wrapper Image:
f9fa8affe011e22163a55f5b4cea214062d0bdd57e6a7a70cdcdac5a4974bf29

raw Android boot-v3 image:
8d23b48dd016b1a546d72e76243cc64f6eccbb35bde3598bcd05aefe854c4e37

test-only unsigned-AVB image:
cfd6e7ea2321a9ad625aa0971426f738bc55e75f9236389c884083a3783cc940

generic QEMU ARM64 Image:
9c6cc7db9aa24a6a6f8a87cbd479694615c9d7000a47d4d80eeaa2d55a9447a4
```

The recovery integration generated an ephemeral Ed25519 test key inside its
temporary pipeline. No production private key was created or retained. The
images above remain ignored compile-only artifacts and are not present in
`manifests/temporary-boot-images.tsv`.

## Review status

Local source review moved postmortem collection after watchdog arming,
enforced a read-only pstore mount, and rejected zero-length present records
before the final rebuild.

A requested read-only Claude Opus review was attempted with plan-only
permissions. The CLI produced no report for five minutes and ended with
`Execution error` when stopped. It made no repository changes and is not
counted as approval.

## Remaining boundary

GitHub Actions must turn green after this source is pushed. A separately
approved production public trust root and staging-only live promotion are
still required before the new recovery can become boot authority. The first
live objective is to determine whether ramoops survives the target →
bootloader → recovery path; it is not to resume desktop or GPU work.

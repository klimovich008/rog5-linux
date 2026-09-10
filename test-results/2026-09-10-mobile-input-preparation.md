# Mobile input preparation

The user clarified the destination as a native, touch-first Arch Linux phone
with cellular excluded, inspired by the Denial demonstration. The
[roadmap](../ROADMAP.md) now includes display, touch, GPU and the remaining
non-cellular hardware. Buttons and a default-off indicator are the first
bounded milestone. Existing shutdown and recovery failures remain open.

## Exact-kernel input payload

The prepared current-kernel LED modules are `led-class-multicolor`, `qcom-pbs`
and `leds-qcom-lpg`, for `7.1.4-gf17befd4ef17`. Twin builds and BTF/vermagic/
export dependency checks passed in 11.31 seconds. An isolated module tree's
`depmod` and dry-run `modprobe` resolved both dependencies before LPG in
0.066 seconds. Neither command loaded anything on the host or phone.

The [new composer](../scripts/device/build-buttons-indicator-trial-initramfs.py)
preserves all existing archive members except the fresh trial descriptor,
integrity catalog and explicitly paired corrected shutdown helper. It adds
one directory containing the three exact modules
and the existing reproducible static AArch64 indicator. The existing boot
path carries those files into `/run`; the modules remain unloaded and the
daemon inactive until a separately guarded runtime test.

Seven [focused test methods](../scripts/device/test-buttons-indicator-trial-initramfs.py)
pass in normal and optimized Python. They cover deterministic composition,
preservation of startup/storage/radio contents, corrupted or missing payload,
wrong kernel and trial identity, integrity catalog drift, existing payload,
unsafe metadata, symlinks, hard links, FIFO and oversized inputs.
Shutdown pairing rejects an unknown retained helper or changed correction.
The pure [physical-key evidence parser](../scripts/device/rog5_physical_key_events.py)
also passes 13 test methods in normal and optimized Python. It handles split
AArch64 records and IRQ deltas but supplies no device access or admission.
The existing 42-test native-Wi-Fi boot suite also passes in 9.32 seconds.
Its first sparse-worktree run lacked two fixture files; restoring the tracked
fixtures resolved those infrastructure errors without production changes.

The first current-base unsigned twins passed at 7.05 and 7.06 seconds. Their
package check exposed the deliberately retained old shutdown helper: current
source requires the already-tested relocated-mount correction. Revised twins
include that correction explicitly. The current signed local artifacts are
not published or admitted:

```text
base_sha256=26a093275bd0fe910d5f3c439e58f801096ff89f13778627bafa8627cc92a842
target_sha256=5146e22fb147134bf8f079512dd51cdecd40d8e86818ab6a3d7bfe3bbf14f9b7
target_bytes=55701804
prepared_dtb_sha256=eca5c2c343fc4cd5511490be0c17501d69f4027941e268ff3f95da4672c214f4
proposed_bundle=headless-server-selector-v9
registered=true
signed=true
booted=false
```

The current Image, Arch root and recovery wrapper were not rebuilt. The DTB
preserves the accepted current base except four added nodes and seven changed
properties. The corrected package passed the sealed signature/selector and
current-source startup pairing checks; strict power/UFS module classification
then refused the extra inert modules. Both refusals remain preserved. The
corrected classification verifies the entire exact payload before separating
its deferred hardware-load evidence from the existing power/UFS checks. All
44 rescue-root composition tests passed in normal and optimized Python
(2.34 and 2.06 seconds), including rejection of partial or altered payloads.

Read-only package re-verification at clean source `458cb42a3fd500445de86f061f11701f3999f64a`
passed in 6.13 seconds. It reused the existing signed twins without signing
again, verified them with the sealed recovery verifier, reproduced the selector,
checked current shutdown/startup pairing and passed strict core module closure.
The three indicator hardware-load rows remain explicitly NOT RUN. Private
evidence is retained in `buttons-package-verify-r3/result.json` alongside the
earlier failed receipts.

```text
manifest_sha256=5e1b9e7f2413e00a1e85d9a131fa4ab80c3e16bf62dc9d138298487508dd78cf
selector_sha256=a9b6b3ed9e3808147cc8082049fc244c826e1cc7d64bdcf361f077296de46723
```

Full root/runtime composition and runtime admission
remain pending. Offline PASS does not establish physical
key events, visible LED color, brightness cleanup or successful probe.

The follow-up active-tier run passed its documentation link/context check but
was interrupted with exit 130 when available host disk space fell below the
3 GiB reserve (2,870,116,352 bytes observed after termination). Its retained
log is `buttons-roadmap-active-check-r1.log`; it is not an active-tier PASS.
The reserve was subsequently restored by making two completed, clean review
worktrees sparse. Their tracked artifact copies remain recoverable from the
retained Git objects; untracked evidence was preserved. The operation recovered
5,926,719,488 bytes, leaving 10,167,574,528 bytes available at completion.
Private evidence is `buttons-host-reserve-restoration-r1.json`.

The single canonical registry now binds V9 to the already verified manifest,
selector, fresh trial ID, unchanged recovery wrapper and V11 fallback, with
verification source `458cb42a`. Every pre-existing record is byte-identical.
All 20 exact-claim tests passed in normal and optimized Python (0.277 and
0.273 seconds), including altered-record and permanent one-use rejection.
Registration created no claim file and performed no phone operation. Full
frozen-source integration validation remains pending.

The first full integration attempt stopped because the unprivileged artifact
namespace remapped root-owned host tools to UID 65534; the collector correctly
refused `fuser`. The affected 27-test suite passed on the ordinary host. A
second attempt exposed a missing ignored boot-tool cache in the new checkout;
restoring that cache made all 44 composition tests pass. The third attempt
was deliberately interrupted before source changes when static review found
that A01 could never clear the new indicator modules from its pending list.
These runs remain failures/incomplete evidence, not integration PASS.

A01 now includes all three exact indicator modules in the VM's ordered
`insmod`/`initstate=live` checks, using the shared strict metadata and dependency
validator. It clears their software-load rows only after the complete VM proof
passes. Physical probe, emitted light and brightness cleanup remain explicitly
NOT RUN. The updated 46-test composition suite passes in normal and optimized
Python. Actual signed-payload metadata and dependency validation passes in
0.99 seconds. Final VM composition runs before the next full integration
checkpoint so an offline integration defect is found before repeating CI.

A fresh authenticated readback still passes on V8 boot
`159aa8ca-a7d5-425c-87c8-481e9484ff22`. Read-only D-Bus inspection also confirms
the server inhibitor holds `sleep:handle-power-key` in block mode. Inputs and
LED class devices are absent on that accepted DT; no physical trial occurred.

## Hub automation observation

The connected `214b:7260` hub advertises ganged power switching
(`wHubCharacteristic=0x00e0`). The phone occupies port 2 and a microSD reader
shares port 1. No switch was operated. This is not a verified phone-only VBUS
disconnect method. Logical USB disconnection can test link loss, but cannot
establish the electrical conditions of an unplugged shutdown test.

## Next evidence

Finish full root/runtime composition and current local-root runtime bindings, then use
one controlled button/LED trial with the exact current power-key inhibitor,
storage/power guards and recovery observation. The old physical-key gate's
read-only-NFS assumptions are incompatible with the current local-UFS server.
Display/touch/GPU work follows the clarified mobile roadmap.

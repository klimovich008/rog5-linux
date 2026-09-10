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
registered=false
signed=true
booted=false
```

The current Image, Arch root and recovery wrapper were not rebuilt. The DTB
preserves the accepted current base except four added nodes and seven changed
properties. The corrected package passed the sealed signature/selector and
current-source startup pairing checks; strict power/UFS module classification
then refused the extra inert modules. Both refusals remain preserved. A narrow
classification must verify the entire payload before separating its deferred
hardware-load evidence from the existing power/UFS checks.

Full root/runtime composition, canonical registration and runtime admission
remain pending. Offline PASS does not establish physical
key events, visible LED color, brightness cleanup or successful probe.

## Hub automation observation

The connected `214b:7260` hub advertises ganged power switching
(`wHubCharacteristic=0x00e0`). The phone occupies port 2 and a microSD reader
shares port 1. No switch was operated. This is not a verified phone-only VBUS
disconnect method. Logical USB disconnection can test link loss, but cannot
establish the electrical conditions of an unplugged shutdown test.

## Next evidence

Finish package composition and current local-root runtime bindings, then use
one controlled button/LED trial with the exact current power-key inhibitor,
storage/power guards and recovery observation. The old physical-key gate's
read-only-NFS assumptions are incompatible with the current local-UFS server.
Display/touch/GPU work follows the clarified mobile roadmap.

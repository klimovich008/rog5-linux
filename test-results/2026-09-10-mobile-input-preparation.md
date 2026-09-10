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


## Live component result, 2026-09-10

Current V9 boot `7c945aa5-80d0-4af2-aa76-113d68e23ac5` stayed healthy throughout
the component sessions. The exact frozen source was `4bd1a817`; its complete
boot observation closed at 1380.892 seconds with route, firewall, profile and
address cleanup verified. The raw passive capture remains NOT RUN; the separate
source-bound closure verifier supplies its completed-observation PASS.

| Physical input | Linux code | Recorded pairs | IRQ delta | Result |
|---|---:|---:|---:|---|
| Power | 116 | 1 | 2 | PASS |
| Volume-down | 114 | 1 | 2 | PASS |
| Volume-up | 115 | 1 | 2 | PASS |

The power session's LED journal recorded three natural on/off cycles at 31/511,
with on-to-off journal intervals of 180.143, 179.916 and 180.127 ms. The user
explicitly saw green and confirmed several power presses. This is visible LED
and natural-off component evidence, not an optical timing measurement. The
strict single-pulse validator remains FAIL because it expected only one cycle.
The later volume-only session passed without repeating power, starting an LED
service or modifying modules. Final brightness readback was zero, full health
passed in 1.093 seconds, and its monitor finished, removed its socket and exited.

The aggregate `buttons-hardware-result-r1/result.json` has status
`BUTTONS_AND_LED_COMPONENT_PASS` and SHA-256
`0c7b0deeda132598b0c50eeffbe7971a97e6f1764d3c10c06fc44684fd4db557`. It pins the
raw sessions, explicit user replies, final health/off readbacks and completed
monitor evidence. Original failed receipts remain unchanged.

Three separately proven preparation defects were corrected before acceptance:

* V9 omitted modular `qcom_pon`, which creates the built-in PM8941 key children.
  The unchanged parent source produced identical exact-kernel modules in
  8.633 seconds; a signed-V9-Image VM load/unload check passed in 2.597 seconds.
* This kernel identifies the LED child through its uevent and parent firmware
  node; the original daemon required a nonexistent leaf `of_node` symlink. The
  corrected daemon preserves exact parent/child/driver checks and permits
  input-independent forced-off cleanup. Qualified ARM twins are identical.
* ARM64 `O_LARGEFILE` is octal `0400000`. The local reader's generic architecture
  mask rejected its valid read-only FD. Its corrected mask is `02400000`, and
  the added no-press preflight passed all three real keys in 1.873 seconds with
  zero event bytes and no physical prompt.

An earlier correctly armed recording expired without operator input. Its FAIL
and successful cleanup remain recorded. The replacement workflow waits for a
fresh explicit Ready before any countdown, reuses prepared code and artifacts,
and prompts only at actual reader readiness. Builds, review and no-press checks
finish before the user is asked to be available.

These runtime additions are not a persistent installation. The signed V9
payload and accepted server/rescue baseline were not rewritten. A future image
needs the complete PON/LED closure and an explicit activation path; no release,
shutdown or autonomous fallback qualification is inferred. S06/R01 stay failed.

## Final repository and offline package validation

Frozen integration commit `bc424ae67ddc7ba05528a45139a3c3565eeb42b9` passed
`scripts/host/rog5-dev test ci` in **531.274 seconds**, with a clean checkout
before and after. The retained `buttons-validated-ci-r4/result.json` records the
command and log SHA-256
`4c34ac5c81145dc076b7777717c0fb28fc0de9c47d1e79e5ed9654875d5261df`.
Optional historical-artifact skips remain visible in that log. Earlier attempts
stopped on missing sparse-checkout fixtures or the absent pinned Android boot
tools; their failed receipts are preserved. Restoring the tracked fixtures and
verified cached bootstrap tools resolved those environment failures without
changing the frozen implementation. The affected 46-test composition suite also
passed after bootstrap.

The fresh unsigned offline package contains the corrected daemon and all four
exact-kernel modules. Two compositions took 6.949 seconds each and produced
identical SHA-256
`97de4bd3b2a47fa7c6468cbe1fe0116a7288b043279d028c73d234a3c60b33ee`.
The final archive's complete payload inventory, metadata, AArch64 ELF identities,
ordered dependencies, matching vermagic, integrity catalog and preserved radio
composition passed in 0.623 seconds. Receipts are retained under
`buttons-validated-composition-r1`. The existing kernel and Arch root were reused;
no full image was rebuilt, signed, registered or installed. The artifact remains
inert, and the physical component evidence above applies to the tested RAM
additions on the existing V9 boot.

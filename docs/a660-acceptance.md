# A660 accelerated-desktop acceptance

Status: **offline harness and submit helper complete; no A660 hardware run**

Live authority: **none**

Last reviewed: 2026-07-28

This is the acceptance contract for calling the ROG Phone 5 Adreno 660 stack
usable. It starts only after the incremental GPUCC, SMMU, GMU, firmware, HFI,
and render-node bring-up reaches a candidate that can expose one mainline DRM
render node. It does not authorize the current v10 or v11 candidate, replay a
consumed diagnostic, boot the phone, or promote a root.

The orchestrator is `scripts/device/a660-acceptance.py`. The queue-submit
source is `tools/a660/rog5-vulkan-submit.c`, and its two-build wrapper is
`scripts/device/build-a660-vulkan-submit.sh`. The offline fault suite is
`scripts/device/test-a660-acceptance.py`.

## Why there are two modes

Stable recovery permits a target timeout of at most 600 seconds and a rollback
timeout of at most 900 seconds. A meaningful thermal and battery run needs at
least 30 minutes, so one execution cannot safely do both.

| Mode | Intended environment | Fixed purpose |
|---|---|---|
| `preflight` | Candidate image | Read-only identity, process, driver, and tool checks |
| `staging` | Signed network-root bundle with rollback armed | Bounded render/Mesa/KWin/screen acceptance |
| `soak` | Separately promoted persistent root | 30-minute screen-off submit, memory, thermal, and battery observation |

`staging` has an internal 540-second hard deadline. Its signed bundle must use
`network-root-v1`, `target_timeout=600`, and `rollback_timeout=900`. The
harness requires those exact profile and timeout values in the verified kernel
command line. Before any acceptance command, it pins the armed network-root
watchdog's PID, UID, parent, process start time, pidfd, BusyBox executable, and
write-capable `/dev/kmsg` plus `/proc/sysrq-trigger` descriptors. It also pins
the watchdog's live `sleep` child and requires a root-owned mode-`0400` lease
that binds both process identities, arm time, boottime deadline, and the exact
900-second timeout. At least the 540-second gate plus a 60-second safety margin
must remain. The recovery init now creates that lease atomically before USB
setup; failure enters the existing forced-rollback path. The harness
revalidates the complete lease and confirms no physical block device or
block-backed mount appears throughout the run. It never disarms the watchdog
or reboots.

The recovery-verifier source now binds `rog5.target_timeout`, the A660
command-manifest hash, and the complete `arch-a` lower-tree identity into the
generated kernel command line. The packager, host server, fetcher, and native
verifier agree on the incompatible v2 signed manifest and reject v1. This
remains source-only:
no installed recovery image or trust root was replaced. A future versioned
recovery build must include and re-pin these binaries before an authorized
staging run.

Staging requires exactly one overlay root, the signed NFS lower at
`/.rog5/root-ro` read-only, and a `nodev,nosuid` 2 GiB tmpfs state at
`/.rog5/state`. The active overlay must name the exact lower, upper, and work
paths created by the signed initramfs. The initramfs-resident static AArch64
verifier authenticates the lower tree before OverlayFS or distribution
userspace can run; the later before/after verifier calls are defense in depth.
Before moving those mounts, signed init publishes their stable kernel mount
IDs in a private canonical record. The harness requires the post-move
OverlayFS, visible NFS lower, and tmpfs state IDs to match that record, so a
decoy mount at the expected pathname cannot satisfy provenance. It rejects any
upper-layer replacement or whiteout of `/bin`, `/sbin`, `/lib`, `/lib64`,
`/usr`, or `/etc`.

`soak` refuses all network-root/P2 watchdogs, NFS mounts, and network-root
markers. It requires a signed promoted-profile command line, an exact active
OverlayFS root over the sealed ext4 subtree, a bounded `nodev,nosuid` tmpfs
upper/work layer, an exact read-only ext4 verification mount resolved through
mount major:minor identities, and a private canonical promotion attestation.
Promotion attestation format v2 also binds the active OverlayFS, its exact
sealed lower, and tmpfs state by kernel mount ID across the initramfs mount
moves. The volatile upper may not replace or whiteout trusted
executable/configuration trees. The signed
command line and attestation must agree on the bundle, kernel, root subtree,
tree entry count, tree SHA-256, seal SHA-256, and command-manifest SHA-256.
Before any soak workload, the fixed persistent-root verifier recomputes the
tree through the read-only mount and must produce the exact signed entry count
and tree hash. `soak` is therefore not a substitute for staging and cannot run
before separately approved persistent-root promotion implements that
contract.

## Signed command surface

Every mode requires a root-owned, single-link, mode-`0400` file at
`/etc/rog5/a660-command-manifest`. Its exact canonical order is:

```text
format=rog5-a660-command-manifest-v1
runner_sha256=<sha256>
systemctl_sha256=<sha256>
dmesg_sha256=<sha256>
baseline_sha256=<sha256>
vulkaninfo_sha256=<sha256>
eglinfo_sha256=<sha256>
submit_sha256=<sha256>
gdbus_sha256=<sha256>
vkcube_sha256=<sha256>
screen_sha256=<sha256>
kscreen_sha256=<sha256>
root_verify_sha256=<sha256>
```

The manifest's SHA-256 must equal the signed kernel-command-line value. The
harness opens each fixed root-owned executable without following its final
symlink, checks the signed hash, copies it into a private executable `memfd`,
and applies all four immutable seals before any preflight action. A separate
sealed descriptor-only launcher joins a new delegated cgroup v2 before
dropping to the requested credentials and `fexecve`-ing the target. Every
exit path uses `cgroup.kill`, waits for `populated 0`, and removes the child
cgroup, so a descendant that calls `setsid` cannot escape cleanup. Commands
run in sanitized environments; pathname replacement after startup cannot
change the executed bytes. Output is streamed through a 4 MiB cap and every
action has a deadline.

The command manifest and executable installation are versioned-rootfs inputs,
not files installed by this checkpoint. They must be generated from the final
AArch64 root and carried by the future signed A660 runtime profile.

## Fixed acceptance sequence

Both active modes require:

- the exact caller-supplied kernel release;
- PID 1 and systemd in the running state;
- exactly one `/dev/dri/renderD*`, named `renderD128`, bound to `msm`;
- no `/dev/kgsl-3d0`, preventing reuse of the known-poisoned vendor KGSL path;
- exactly one running `kwin_wayland` session with bounded, validated Wayland
  and D-Bus environment values, pinned by UID, process name, start time, and
  pidfd for the full run;
- one hardware A660 renderer and no llvmpipe, lavapipe, softpipe, or software
  rasterizer.

The bounded staging sequence then:

1. captures private baseline metrics and the kernel log, rejecting fatal GPU
   signatures already present at boot;
2. opens and closes the same render-node inode 100 times;
3. runs `vulkaninfo --summary` ten consecutive times and requires Turnip plus
   `Adreno 660`/`FD660`;
4. requires hardware A660 output from EGL and KWin support information;
5. performs ten real empty-command-buffer Vulkan submissions, each with a
   five-second fence timeout;
6. requires `/usr/bin/vkcube --wsi wayland --c 120` to render and exit
   successfully within the bounded workload deadline;
7. performs five panel off/on cycles, verifies the same KWin process, and
   submits through Vulkan while the panel is off; a lightweight 100 ms worker
   continuously samples the state marker and physical backlight without
   launching processes, while bounded synchronous KScreen DPMS checks run
   around each submit and metrics sample;
8. leaves the panel off, captures final memory, independently inventories
   every selected Plasma process and `smaps_rollup` PSS, and requires the
   collector's process count and PSS total to match before recording battery,
   temperature, and kernel-log evidence;
9. rejects any new SMMU/IOMMU fault, GMU/HFI error or timeout, Adreno/MSM GPU
   fault or hang, DRM error, external abort, watchdog bite, BUG, Oops, call
   trace, or panic.

The promoted soak leaves the panel off under the same physical-darkness
monitor and bounded DPMS checkpoints and
repeats a real bounded submission plus metrics sampling every 60 seconds for
1,800 seconds. Both modes reject a
temperature above 85 °C, available memory below 512 MiB, a changed render-node
count, KWin exit, systemd failure, or kernel-log rotation that would make the
delta ambiguous.

The passing result is first written under a noncanonical pending name. The
physical monitor must close cleanly and a final KScreen/backlight check must
pass before atomic no-replace hard-link publication creates `result`; any
late wake therefore leaves no canonical passing record.

## Minimal submit helper

The helper accepts only:

```text
rog5-vulkan-submit --require-a660
```

It requires exactly one matching Vulkan physical device whose name contains
`Adreno (TM) 660`, `Adreno 660`, or `FD660`; software-device rejection and the
exact render-node inventory are enforced by the surrounding gate. The helper
chooses one graphics or compute queue, records one primary command buffer,
submits it once, and waits on one fence for at most five seconds. It creates no
window, image, shader, network connection, persistent cache, or device
pathname. It contains no KGSL, fastboot, or storage path.

Build it inside the matching AArch64 userspace/toolchain environment with
Vulkan development headers and loader:

```sh
scripts/device/build-a660-vulkan-submit.sh \
  /build/rog5-vulkan-submit
```

The builder compiles twice with hardened PIE flags, rejects differing output,
requires a canonical caller-owned output directory with no group/other write
bits, pins that directory by descriptor, publishes through an atomic
no-replace hard link, then derives size and SHA-256 from the opened published
inode. A concurrently created output wins and is never overwritten. The
offline suite also links the helper against a test-only Vulkan implementation
and proves success, no-A660, duplicate-A660, no-queue, submit-failure, and
fence-timeout behavior. The resulting AArch64 binary must be installed as
`/usr/local/libexec/rog5-vulkan-submit` in a future versioned rootfs. It is not
present in the immutable successor-v3 root.

## Running a future authorized gate

First run the read-only preflight:

```sh
EXPECTED_KERNEL_RELEASE="$EXPECTED_KERNEL_RELEASE" \
  /usr/local/sbin/rog5-a660-acceptance preflight
```

Only a separately authorized signed staging cycle may set:

```sh
ALLOW_A660_STAGING_ACCEPTANCE=1 \
EXPECTED_KERNEL_RELEASE="$EXPECTED_KERNEL_RELEASE" \
  /usr/local/sbin/rog5-a660-acceptance staging
```

After persistent promotion, a separate soak authorization may set:

```sh
ALLOW_A660_PROMOTED_SOAK=1 \
EXPECTED_KERNEL_RELEASE="$EXPECTED_KERNEL_RELEASE" \
  /usr/local/sbin/rog5-a660-acceptance soak
```

Production has no path, command, count, duration, timeout, temperature, or
memory override. It rejects fixture configurations, labels offline results as
fixtures, and runs only signed, sealed command snapshots in sanitized
environments. Offline tests import the module and drive a separate test
orchestrator; the installed CLI has no runtime test hook.

## Evidence and acceptance

Each active run creates a new caller-owned mode-`0700`
`/run/rog5-a660-acceptance` directory and mode-`0600` files. It never replaces
an earlier run in the same boot. The canonical `result` record contains the
verified runtime profile, bundle, generation, signed command-manifest
identity, complete lower-tree identity, root device when applicable, counts,
kernel release,
thermal/memory/independently matched Plasma/battery values, the
new-kernel-log SHA-256, final screen state, and status. Root verification runs
before and after the workload and is retained as two separate records; any
tree mutation prevents a result. Raw `dmesg`, Vulkan, EGL, and KWin outputs
remain private runtime evidence; redact identifiers before committing any
derived report.

Passing `staging` establishes a bounded accelerated-desktop candidate, not
release acceptance. Passing both modes still leaves refresh-rate power curves,
charging behavior, suspend/resume, 24-hour reachability, KRDP, Chromium, and
longer battery depletion as separate roadmap gates.

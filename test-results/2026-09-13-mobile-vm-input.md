# Denial mobile VM display and pointer observation — 2026-09-13

**The retained ARM64 Denial/engine pair visibly renders the mobile lockscreen
and responds to an OSK reveal swipe, `?123`, and `ABC`.** The final guest records
23 raster frames and 23 page flips without reported rendering errors. These are
synthetic pointer interactions in an ARM64 VirGL VM, not phone GPU/touch evidence.
No text, credentials or authentication response was submitted.

The supplied framebuffer review at `410b6935526a977ca727359f23ee43fc4ebe45b2`
has already been addressed by the strict modifier intersection, Invalid-only
pool branch and stored/exported descriptor validation in Denial patch0001.
This turn inspected that current patch and reused the later
[paired rendering qualification](2026-09-13-render-work.md). No renderer guard,
GBM usage flag, native fence, Denial binary, Flutter engine, AOT shell, package
closure or kernel was changed for this observation.

## Identity and executed evidence

Starting repository commit: `224c53e675f3591fb6d3ec624edd7cacca7fdafe`;
tree: `4b3be3def0a3059176165e53b9a18b436516eb3b`.
Final executed harness commit: `b34aa0e5a0c55a38cd7a7e4fe48c9ab119c45d6d`;
tree: `30ef0eb0d41c2a0fcf6714c3a4323d78ca38d6d8`.
Later evidence-only changes are distinct from these executed source bytes.

Native binary SHA256:
`878ff4c6155279264782523837cf7672273f333a9a45318a7db9cc9fbf7ce19a`,
built from repository source `02796f069819b9df2ad11013f69ce3d1ddf39362`.
Engine SHA256:
`a75c88d8f12d9ec7a24bb107ff9dc0349b6bb2d5b0f18cb4d40b9e54227e9418`,
source `66db5ff08065972bf9cf7e3d2c4b845633170052`.
The generic VM Image remains
`34279d12dee925c4c58de9f49411c5e5f9fe85d016214e3939f80cd2f8b797f9`.
These are offline fixture bytes; installed phone identity was not queried.

The [qualification JSON](2026-09-13-mobile-vm-input-qualification.json) contains
all five exact VM commands, their source commits, durations, statuses and input/
output hashes, all88 integrated test commands/results, screenshot identities,
manual visual findings and retained build references. Its SHA256 is
`844fc6fdf6f6fce04f83a5e2b01d136d8fdceca91d23a3b9320bcd653d34410e`.
Raw logs, lossless PNGs and restoration mappings remain in private state
`/home/deck/.local/state/rog5-vm-visual-input-20260913-r1`.

| Executed check | Result | Seconds |
| --- | --- | ---: |
| R1: capture on first render-audit entry | FAIL:640×480 inactive-output placeholder | 14.929 |
| R2: require real presentation first | FAIL:QMP `no surface`, no pointer sent | 26.046 |
| R3: UNIX VNC capture | Capture/render PASS:10 frames; visual OSK FAIL | 49.000 |
| R4: initialize virtual input | FAIL:udevadm refused custom-init chroot; Denial NOT RUN | 5.139 |
| R5: address guest udev from its chroot | PASS:23 frames/flips; all four captures inspected | 51.785 |
| Observer transport/PNG/state-machine tests | 34 PASS under Python -O | 0.949 integrated process |
| Guest prerequisite/readiness tests | 8 PASS under Python -O | 0.185 integrated process |
| Frozen active tier | 88 PASS;0 FAIL/BLOCKED/SKIPPED;255 NOT_SELECTED | 134.842 |

After updating evidence metadata, the five metadata-checker cases pass in
0.925 seconds and eight mobile-status cases pass in0.079 seconds. Artifact
inventory validation passes in0.076 seconds; generated status validation passes
in0.040 seconds. `git diff --check` passes. Exact commands and durations are
retained in private `metadata-result.json`.

Three declared optional subchecks are SKIPPED, separately from suite counts.
The integrated scope used two workers,1GiB memory/no swap and a600-second bound;
its reported peak was319.2MiB. Existing CI results and previous kernel/engine
builds were not rerun or represented as this turn's executions.

## Demonstrated setup defects and corrections

The old readiness predicate accepted an audit entry containing zero presented
outputs. A failing-before regression now requires positive scheduler presentation
counts, rejects duplicate fields and handles ANSI formatting. The first failed
VM's screenshot corroborates the premature start.

QMP command availability did not establish GL capture support. In upstream
[QEMU8.2.2 console.c](https://github.com/qemu/qemu/blob/v8.2.2/ui/console.c),
`qemu_console_surface()` returns null for non-surface scanout, and
[the QMP handler](https://github.com/qemu/qemu/blob/v8.2.2/ui/ui-qmp-cmds.c)
returns `no surface`. The retained binary produced that exact error. The new
observer uses the existing
[egl-headless readback](https://github.com/qemu/qemu/blob/v8.2.2/ui/egl-headless.c)
and [VNC display listener](https://github.com/qemu/qemu/blob/v8.2.2/ui/vnc.c)
through a fresh0700 UNIX-socket directory. It verifies the unique VM name,
requires true540×1224 dimensions after any initial padded544-pixel width,
accepts bounded complete raw frames and writes lossless PNGs without scaling.
No TCP listener, clipboard, VNC keyboard event or phone endpoint is used.

R3 demonstrated why successful QMP replies and changing image hashes cannot
prove a gesture: all keyboard captures still showed the lockscreen. The custom
PID1 had mounted input nodes without starting udev. R4 and R5 both observed
missing ID_INPUT properties before setup. R5 starts bounded udev discovery,
checks the exact virtual tablet/keyboard properties and observes libinput adding
both devices. Its otherwise unchanged gestures then produce the expected OSK
layers. The known custom-init chroot requires the retained systemd compatibility
setting `SYSTEMD_IGNORE_CHROOT=1` on the three guest udev control operations;
the entry's virtual-kernel marker and virtio checks remain mandatory.

Tests exercise real local QMP/RFB peers, exact RGB decoding, shared deadlines,
malformed messages, incomplete/overlapping frames, capture rejection, lost press
acknowledgements, interruption at every observer stage and overwrite prevention.
The mobile prerequisite test failed against the earlier API; all three udev
inputs are now required before launch. The actual guest provides the udev
integration test; host fixtures do not claim to emulate that daemon.

## Scope, retention and next step

Confirmed/fixed: observation readiness, GL capture transport, virtual input
initialization and mobile OSK pointer interaction. Disproved for R3: accepted
QMP events alone meant a functioning input path. Its visual FAIL remains intact.
A black initial wallpaper followed by its loaded texture is retained in the
captures; background changes are not used as gesture evidence. Status-bar icons
are shell pixels, not modem, battery, charging or Wi-Fi qualification.

NOT RUN: text entry, PAM unlock, launcher/application use, lock-screen security,
phone OLED/A660/touch/multitouch, suspend/wake and charging. Headless S06 and R01
remain FAIL. No phone operation, production signing, candidate creation,
admission/claim operation or protected-storage mutation occurred. All five
owned VM containers were removed and the final virtual pointer was released.

Verified duplicate payload copies recovered300,464,485 bytes. The165 removed
files each have a streaming hash and retained-source restoration mapping;
unique logs, screenshots, initramfs and source/build inputs remain. All495
historical inventory sets and accepted artifact pointers are preserved; one
new fixture records this observation without release authority.

Next authorized experiment: bounded VM OSK text entry and native Wayland app
interaction using the same binaries. The next separate hardware question is
stable scanout/rendering and input on the prepared exact phone kernel; it still
requires hardware authorization and cannot be answered by this VM result.

## Changed files

Implementation and executable coverage:

- `scripts/host/qemu-mobile-observer.py`
- `scripts/host/test-qemu-mobile-observer.py`
- `scripts/host/test-qemu-virtio-drm.py`
- `scripts/host/test-qemu-virtio-drm-prerequisites.py`
- `scripts/host/test-repository-linux.sh`
- `tools/qemu-virtio-drm/guest.sh`
- `configs/repository-tests.json`

Documentation and evidence:

- `docs/development.md`
- `docs/development-lessons.md`
- `docs/current-state.md` (generated header only)
- `configs/project-status.json`
- `manifests/current-artifact.json` (VM observation only)
- `manifests/artifact-sets.json` (one appended fixture)
- `test-results/2026-09-13-mobile-vm-input.md`
- `test-results/2026-09-13-mobile-vm-input-qualification.json`

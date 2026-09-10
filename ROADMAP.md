# ROG5 priorities

The user's clarified destination on 2026-09-10 is a usable native Arch Linux
phone with a touch-first mobile interface and non-cellular hardware support.
Cellular calling, SMS and mobile data are excluded. Display, touch and GPU are
now central work. The existing headless server provides the development and
recovery baseline; completing its matrix alone does not complete this product.

The reference is the [OnePlus 12R Denial demonstration](https://www.reddit.com/r/mobilelinux/comments/1w80kvt/arch_linux_on_a_oneplus_12r_powered_by_the_denial/).
[Denial](https://github.com/denialwm/denial) is the selected compositor for the
native mobile session. Its author's post described the
demonstrated mobile build and Droidloom Android app runner as unreleased at
posting. An Android app compatibility milestone must use available, inspectable
software and have its own tests; it is not established by that demonstration.

1. Preserve the completed buttons/default-off LED component milestone and
   healthy server return. The strict single-pulse trial's extra presses remain
   recorded separately; persistent integration of the RAM fixes is pending.
2. Bring up the OLED display path, FocalTech touch and accelerated Adreno
   rendering through separate, specific hardware questions. Reuse historical
   evidence where inputs match, including the [60 Hz status-screen result](test-results/2026-09-02-display-status-screen-development.md)
   on the separate display kernel. That result does not establish display on
   the current server kernel. Prove scanout, touch coordinates and hardware
   rendering before attempting a full mobile shell.
3. Run an ARM64 Wayland mobile session with launcher, touch navigation,
   on-screen keyboard, settings, screen lock and practical Linux applications.
   Use Denial's public mobile shell and matching ARM64 engine/AOT bundle.
   Track any missing behavior against these requirements.
4. Qualify audio, Bluetooth, sensors/rotation, cameras and remaining useful
   non-cellular hardware as separate milestones. Track working, unsupported
   and untested features explicitly.
5. Make daily operation reliable: charging, battery/thermal behavior, suspend
   and wake, shutdown/startup, networking, updates and recovery. Existing
   failures remain open and must be resolved before calling the phone ready
   for daily use. Preserve the [headless acceptance matrix](docs/release-acceptance.md)
   as evidence for the baseline; do not relabel failed rows.

Use exact-kernel incremental module builds and focused tests. Prefer Rust for
suitable new components and isolated live userspace trials where supported;
eBPF/JIT is for supported runtime diagnostics. DT and early-boot changes still
need a controlled boot. Keep the accepted server/rescue baseline and existing
identity, signing, power, storage and one-use recovery guards at every step.

A kernel change requires a specific unresolved hardware question. Reproduce
host parser, packaging and service-sandbox failures offline first. No stage
requires completing unrelated hardware work before its own bounded test.

The [Denial bring-up record](test-results/2026-09-10-denial-bringup.md) tracks
source pins and the current hardware gap. Completion needs a real-phone touch
session with confirmed GPU acceleration, two usable native Wayland applications
and text entry, three authorized starts, a 60-minute interactive/idle observation,
screen-off/wake, compositor recovery and verified updates/rollback. A successful
build or nested session is preparation, not completion. Other non-cellular
hardware remains on the roadmap with explicit qualification status.

The previous roadmap, including completed migration phases and historical
research, is preserved through the [archive index](docs/archive/README.md).

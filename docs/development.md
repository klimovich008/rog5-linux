# Development loop

Start at [current state](current-state.md). Work on one question and choose the
cheapest artifact that changes its answer. Historical profile names are not
the active server. In particular, `power-usb-active.json` and its generated
lock still describe the older NFS observer track; they are kept for its
regression/publication contract, not current installed-selector identity.

## Retaining historical builds

Retire generated compiler caches when a build stops being an active input.
The 2026-09-13 host audit removed 87.21 GiB of historical objects, temporary
link products and ThinLTO cache files across 57 kernel build directories.
Final artifacts and evidence were retained; 514,051 retained file identities
and 172 final-artifact/configuration hashes passed the post-cleanup check.
This reclaimed space without rebuilding or qualifying any phone artifact.

Before cleanup, serialize with the build coordinator and check current artifact
pointers, tracked files, mounts, open handles and owned jobs. Enumerate exact
regular files with device/inode, size, modification time and hardlink coverage;
revalidate before unlinking and keep a private deletion journal. Skip files
whose other hardlinks are outside the approved set. Inaccessible process or
mount namespaces are a recorded limitation, not proof that nothing uses a path.
Keep source/worktrees, final Image/vmlinux/modules/DTs, configuration, ABI
headers, Module.symvers, build commands, toolchain identity and evidence.
Signed packages, claims, rescue backups and retained root filesystems require
their own reference/retirement audit; an old directory date is insufficient.

Use disk-backed scratch and streaming hashes. Keep active dependency caches
that materially shorten the next build; clearing old objects means that any
later rebuild of those historical trees must regenerate them. Record allocated
inode bytes separately from the filesystem free-space delta, and do not count
hardlinked copies repeatedly. Prefer one measured audit and targeted verification
over repeated whole-home scans or another full build as a cleanup check.

Include nested historical checkouts and archived build directories in the
initial inventory: auditing only the main `repo/build` missed compiler objects
in July/August sibling wrappers. A retired output row does not retire its parent
directory or sibling Images. Do not hardlink duplicate live artifacts: recovery
readers can require a single link and bind device/inode identity. Persist each
deletion intent before unlinking so interruption leaves a durable audit trail.

The next audit found another 10.88 GB of objects in seven completed August
outputs named `kernel-a`, `kernel-b`, `output`, or directly as the state root.
Discover compiler files under the measured historical roots first, then locate
their nearest build configuration; a directory-name shortlist misses these.
A revoked boot policy does not mean an artifact is retired for storage, and
a retired inventory row does not override a remaining recovery consumer.

For unpublished failed filesystem-build scratch, a verified lossless sparse
archive can retain the failure data without keeping its original allocation.
Restore the archive into a fresh disk-backed directory and compare equal logical
sizes plus every byte in the union of both files' data extents; mutual holes are
zero. Record the archive hash, original metadata, verification and restore path
before unlinking the exact originals. Do not report an extent-framed digest as
a whole-file SHA-256. The second September 13 audit used this for two failed
userdata population attempts; successful images and execution records stayed
unchanged. Duplicate hashes alone do not authorize hardlinking signed or sealed
artifacts: inode/link-count guards and historical path consumers still matter.

## Offline qualification and reporting

The public `test-repository-linux.sh` tier commands are preserved. Test execution
policy is declared in `configs/repository-tests.json`; the retained shell
selection is checked against its tier membership during this incremental
migration. Every selected suite has a deadline, required inputs/prerequisites,
resource classification and an explicit Python optimization/source requirement.
Only reviewed isolated suites run concurrently; the default remains two workers,
bounded by CPU affinity/quota and `ROG5_TEST_WORKERS`. Network, namespace,
high-memory and shared-state work runs serially.

The runner writes per-suite logs plus `summary.json` and JUnit `summary.xml` under
`build/test-reports/` (or a fresh `ROG5_TEST_REPORT_DIR`). Missing mandatory inputs,
unexpected skips, failures and deadlines fail the tier. An early failure leaves
unreached selected suites BLOCKED and unrelated suites NOT_SELECTED. Declared
optional subchecks remain visible separately. Cleanup terminates ordinary test
process groups, including background descendants; this is not containment for
arbitrary daemons that deliberately create another session.

Panel identity, exact-base application, affected-driver compilation, executable
lifecycle behavior and physical validation are separate results. Generic ARM64
QEMU covers userspace/initramfs behavior. It cannot prove SM8350 panel, touch,
GPU, charging or PMIC behavior. The exact production board job is selected for
kernel/DT/build changes; unrelated userspace/documentation work does not require
a full phone-kernel rebuild. Build failures and schema diagnostics must remain
visible even when an unsigned Image was produced.

For an actual local Denial session with the document portal, use the separate
`QEMU_KERNEL_PROFILE=virtio-session` profile and a fresh ignored build output.
It adds built-in FUSE to the virtual DRM prerequisites. The retained `virtio-drm`
profile and its evidence remain unchanged. Require a usable `/dev/fuse` and a
real document-portal mount in the VM; a successful modprobe unit is insufficient.
Prepared RAM GTK schema/MIME/input-method caches must be imported into the D-Bus and systemd
user activation environments using the explicit three-variable allowlist before
launch. The GTK module hook is generated in guest RAM and selected with
`GTK_IM_MODULE_FILE`; generation alone is not client protocol qualification.
Cache transfer, service readiness, client lifetime and phone behavior
remain separate checks. The combined VM also runs the packaged ARM64
`fc-cache -s -v` in guest RAM before PAM startup, then checks a mobile-UID
`fc-match` consumer with diagnostic cache records, unchanged cache inventory and
no user fallback. Before warming, restore the shipped default configuration links in RAM using
the packaged `40-fontconfig-config` hook. Preserve existing valid configurations,
reject dangling conflicts, and verify that mobile-UID `fc-conflist` actually
processes each default. The extracted package closure did not execute either
Fontconfig post-transaction hook. Keep font sources, timestamps and the fixture clock
unchanged; retain future-mtime warnings rather than treating them as cache
invalidation. No host-generated cache is transplanted into the VM.
The combined-session Denial log retains a 1 MiB ordinary prefix and a separate
64 KiB reserve for terminal/error records across the full stream. Reserve
overflow fails qualification while the reader continues draining; verbose
frame diagnostics cannot silently discard the final counter or known rendering
errors. Native-client protocol logs keep their existing independent limits.
The readiness probe samples the packaged `lsclocks --time CLOCK_MONOTONIC`
before/after the25-second VM-only start command, then takes one3-second,
64KiB-bounded lifecycle snapshot of the four services and permission store before
cleanup. Snapshot failure never replaces the original start failure. Compare
systemd monotonic microseconds with these same-clock samples; start sample+25s
is a lower bound on timeout cutoff, not the exact instant timeout was armed.
Observer/process launch overhead prevents precise causal claims inside that gap.
The former20-second fixture limit had only0.30s margin at a measured successful
command return. The25-second allowance adds scheduling headroom inside unchanged
outer deadlines; it changes no phone or packaged-service policy. It is not a
root-cause fix for historical timeout124 results, which remain recorded.


For the separate offline Denial DRM probe, build the pinned upstream kernel with
`QEMU_KERNEL_PROFILE=virtio-drm JOBS=2 scripts/host/build-qemu-smoke-kernel.sh
LINUX_SOURCE build/qemu-virtio-drm`. The default `smoke` profile remains for the
existing initramfs checks. Profile identity is part of the locked build inputs;
use a fresh output for a different profile. Both use the exact source check and
verify required symbols after `olddefconfig`.

Run `python3 scripts/host/test-qemu-virtio-drm.py --help` for the explicit kernel,
materialized ARM64 runtime, Denial binary, retained QEMU container ID and fresh
output arguments. This manual integration probe needs those private inputs and
is not implicitly executed by an ordinary repository tier. It mounts runtime
and payload read-only, supplies only virtual GPU/input/RNG/9P devices, and gives
the guest 1 GiB RAM with a bounded container, deadline and serial log. Guest root
is a test fixture, not the mobile privilege model. The default checks virtual
DRM discovery and Denial's CLI. Its bounded KMS diagnostic requires a preexisting
active CRTC, which this blank guest lacks. `--flutter-bundle` selects normal
shell startup with an external 45-second deadline. Even a clean timed exit is
separate from rendered-frame evidence. Software rendering is not Adreno proof.
The pinned Denial starts Xwayland unconditionally: it is a mandatory shell
runtime prerequisite, even for native Wayland applications. The retained
315-package graph omitted it and cannot qualify a full session. A missing
Xwayland now produces BLOCKED before VM launch; retain that historical graph
and qualify an explicit successor with authenticated additional packages.
The runner records the supplied runtime path but does not repeat its package
inventory authentication; bind the run to that separate retained evidence.

The materializer defaults to `--permission-policy owner-only`, which retains
the historical root-fixture permission policy. For a separately authenticated
non-root fixture, explicitly request `--permission-policy package-read` into a
fresh output. It preserves package-provided group/other read and execute bits,
keeps private files private, removes group/other write and privileged mode bits,
and retains owner access for inventory hashing. The enclosing output stays0700
on the host. Do not recursively chmod the retained tree or reuse its old mode
manifest for a new profile. Authentication, extraction confinement, disk reserve,
no-install-script and no-replacement guards apply to both profiles. This option
does not create a mobile account, seat authorization or a non-root VM session;
those need separate qualification, and the existing guest still runs root.

The separate mobile entry `packaging/arch/mobile/denial-mobile-session` delegates
to the pinned upstream `denial-session` only after checking a local active
logind session belonging to the process itself, mobile UID/GID1000, its private
runtime directory and explicit machine-configured KMS/render/output paths.
It selects the mobile shell and logind backend. It neither creates a login nor
installs/enables services, and is not selected by the accepted headless builder.
Its fact-provider fixtures execute the actual shell decisions; they do not
establish real logind TakeDevice access, authentication or phone hardware.
Target composition must also supply upstream denialctl, denial-session.target,
the matching engine/AOT/assets and authenticated package closure. Do not use
automatic fastest-mode selection for the phone: its exact connector and60Hz
output configuration still require matching artifact evidence.

Use `python3 scripts/host/compose-denial-session-payload.py --help` to assemble
the exact qualified Denial/Flutter payload plus the retained ARM64 denialctl,
pinned upstream launcher and user target, and this mobile entry/desktop file.
It consumes the non-root VM's complete payload inventory and the CLI build
receipt; it checks every byte while streaming a deterministic root-owned tar.gz.
Measurement and publication must produce identical compressed bytes. Measurement
uses a hash/count sink, avoiding a second archive copy, and the3GiB host reserve
is checked before and during writing. Inputs are never chmodded or extracted.
The terminal provenance receipt is published only after the archive is complete;
consumers must require the receipt and its matching archive hash. Interrupted
receipt writes and failed synchronization do not leave a success receipt.
Outputs must be fresh and outside immutable source trees.

This is an unsigned session-files payload, not an installable rootfs, package
closure or phone candidate. It does not supply machine-specific device/output
configuration, create accounts, install hooks, enable services or grant admission.
The future rootfs composition must enforce user-ID/home conflicts, original PAM
package permissions, default-off remote services and explicit local logind login.
Ordinary host fixtures test the archive and failure paths. Actual retained-byte
composition, ARM64 CLI execution and logind/graphics VM qualification are separate
manual checks; a host fixture PASS does not imply any of them ran.

The manual `scripts/host/test-qemu-logind.py` runner uses the retained generic
ARM64 kernel and authenticated mapped runtime to test packaged systemd as actual
PID1, the original login PAM profile on an unused virtual tty1, and libseat's
forced logind backend. It requires explicit immutable container IDs, runtime
receipt, kernel and retained Rust dependency paths. Its guests have no network
or host render device; virtual DRM/keyboard devices and RAM-only account changes
are test fixtures. The fixed credential is public synthetic data. No login
manager, Denial lock UI or phone session is qualified by this probe.

The default small init continues to fork and reap its test child. Only the
separate compile option `ROG5_SYSTEMD_PID1` replaces PID1 with the guest setup
script and then packaged systemd. A successful PAM open alone is insufficient:
pam_systemd is optional in the packaged login profile. Require the child's own
active local tty1/seat0 session, UID1000 private runtime, responding user manager,
actual libseat device identities and release, followed by logind scope removal.
Missing kernel sandbox features remain explicit limitations even if those
functional checks pass. A timeout or shutdown without the terminal evidence
is failure. Retain failed attempts and do not infer phone or security proof.

Do not carry the sanitized VM package permissions or NoNewPrivs policy into a
password-authenticated session without qualification. The retained PAM1.7.2-2
archive supplies root:root06755 unix_chkpwd. The actual pinned Denial PAM backend
in an isolated ARM64 guest rejects the correct synthetic password with0755 or
NoNewPrivs=1, and accepts it with06755/NoNewPrivs=0, even with an empty capability
bounding set. Wrong passwords, expired accounts and locked accounts are refused.
The mobile entry checks these known prerequisites; it does not change privilege
state or grant capabilities. Mount nosuid, package identity, PAM policy, a real
login and lock-screen input isolation remain separate prerequisites/qualification.
Retain the existing VM isolation and headless policies.

`scripts/host/build-denial-pam-probe.py --help` describes the explicit Git source,
immutable toolchain image and retained Rust dependency inputs for the small
ARM64 backend probe. It extracts the unmodified authentication backend and
uses `tools/denial-modifier-tests/pam-guest-main.rs` only as a synthetic caller.
The companion `tools/qemu-virtio-drm/pam-boundary.sh` runs with the retained
generic init.c/9P VM fixture, a dedicated rog5.pam_fixture=1 command-line marker,
read-only runtime and RAM-only account/PAM/helper overlays. Never run it on a
target or the host. This exact-source compilation and VM check are manual and
are not silently included in an ordinary active-tier PASS. The dated evidence
retains the exact driver, commands, source/tool/package hashes, bounds and results.

For the explicit mobile UI probe, add `--observe-mobile` to the full-shell
VirGL command. QMP sends pointer events; the private UNIX VNC socket supplies
raw full-frame captures because QEMU 8.2 QMP screendump rejects GL scanouts.
No TCP listener is opened. It selects `DENIA_SHELL_PROFILE=mobile` and a 540×1224 portrait
virtual output, then records four bounded PNG captures around an OSK reveal
swipe and `?123`/`ABC` pointer clicks. It contacts only that fresh VM's QMP and VNC
sockets; it never types credentials or sends power commands. The fixture assumes
scale 1 coordinates and must be checked against the captured UI. QMP input acceptance
and valid PNGs are capture/delivery evidence only: `visual_semantics` stays
NOT RUN until actual screenshots are inspected. Clock/cursor changes cannot
substitute for showing the expected keyboard modes. Synthetic pointer gestures
are not phone multitouch qualification. Failed/incomplete observation fails the
requested probe, and held pointer buttons are released before abort cleanup.
The mobile probe starts bounded guest udev discovery and requires the virtual
keyboard/mouse ID_INPUT properties before Denial; kernel event nodes alone do
not prove libinput discovery. The daemon joins the owned guest cleanup.
The existing default landscape, EGL-comparison and CLI probes remain separate.

For unlocked launcher discovery, use `--observe-mobile-launcher` alongside
`--observe-mobile`, excluding editor autolaunch and native screencopy. It takes
two captures after presentation readiness and sends no pointer input. Inspect
the actual tiles before designing launch/switch gestures; capture success leaves
app launching, switching and visual semantics NOT RUN. The VM prepares RAM-only
Mousepad and Foot desktop overrides with fixed commands, owned process lifetimes
and bounded protocol logs for subsequent interaction. Denial launches desktop
commands with null stdio. Discovery retains the guest console; app interaction
uses the dedicated bounded evidence channel described below. The virtual guest
marker remains mandatory; host tests inject inert sinks.
No package, compositor, engine or shell rebuild is needed for discovery.

For launcher-based native app interaction, use `--observe-mobile-apps` with
`--observe-mobile --launcher-reference PATH`, selecting the previously inspected
540×1224 discovery PNG. This excludes discovery/editor autolaunch modes. Exact
Foot and Mousepad icon regions must match before tile clicks; clock and battery
pixels do not participate. Missing tiles stop input after eight bounded captures.
The owned client parser requires app identity, configure/ack, committed buffer,
fresh keyboard focus and a1.5-second settling period for every capture.
Scheduler audit reports depend on new rendering activity; a stable scene may
never produce another interval report. Retain those reports independently rather
than blocking input on their arrival. Native readiness and pointer delivery do
not prove presentation: terminal frame counts and direct captures remain separate.
Pointer gestures launch Mousepad, pull up to Overview and tap its exposed
background to return home, launch Foot and switch twice;
inspect all captures separately. Protocol-only success is not visual usability,
authentication, phone multitouch or GPU qualification. Client diagnostics and
cleanup retain their existing limits. No new binary is required for this probe.

For native-client text delivery, add `--observe-mobile-editor` alongside
`--observe-mobile`. This explicit mode uses normal unlocked startup, launches
the retained Mousepad with `GDK_BACKEND=wayland` on the sole discovered guest
socket, and opens an empty RAM file. It does not test authentication or launcher
activation. Six captures cover the empty editor, OSK, viewport pan, `test`, deletion to `tes`,
and restoration to `test`. Only pointer events press the OSK; direct keyboard
injection is excluded. The client protocol must show a native toplevel and the
exact key press/release sequence; actual rendered text needs separate image
inspection. The pinned shell initially shifts the whole application upward by
the keyboard height. The probe retains that unpanned capture, then drags its
stationary right-edge viewport strip downward to reveal the top document line
before typing. This tests supported manual panning, not automatic caret tracking.
This mode allows90 seconds of compositor execution within the same
120-second host bound: the retained cold GTK runtime first mapped near guest
t=61 seconds. Mousepad has its own95-second bound and joins cleanup.
The ordinary locked probe retains its45-second guest bound. Before D-Bus starts,
the editor probe generates strict GSettings and MIME databases from the retained
package data in guest RAM, recording both cache hashes. The package root stays
read-only. Mousepad alone writes to an owned, prefixed protocol stream; input
waits for its configured, buffer-backed toplevel and later presentation, not
merely compositor startup. Cache-generation failure stops the probe.

To distinguish native composition from VNC capture, add `--native-screencopy`
with the ARM64 client built by `scripts/host/build-qemu-screencopy.py`. This pairs
initial/final VNC captures with the compositor's `zwlr_screencopy` output. Only
the new private `output/native` directory is writable through the guest's extra
9p mount; the aggregate is limited to8MiB. The client has a5-second deadline,
the host handoff8 seconds. Raw RGB PPM and losslessly encoded PNG identities are
retained. The pairs are sequential observations, not a claim of identical frame
timestamps. Transport PASS still requires separate inspection of visible content.

The authenticated successor graph is
`mobile-package-snapshot-20260912-xwayland.json` (326 packages). The historical
315-package graph remains unchanged. A full-shell run now requires a guest
session bus and positive terminal raster-frame/page-flip counters without
rendering errors; a clean exit alone cannot pass. This is still separate from
visual proof. An explicit `--render-node /dev/dri/renderD128` enables VirGL using
only the Deck render node; it does not expose host display control or phone
devices. Use the retained complete GL container from the current artifact
pointer. Default software mode remains available, but the retained llvmpipe
stack lacks the native-fence extension required by this Denial renderer.
The corrected modifier allocation reaches presented frames in the retained VirGL
VM. At that initial checkpoint, per-frame authorization and EGL cleanup both failed;
see current state for the later cleanup repair. Positive counters do not qualify
the session or the phone. The guest's targeted
TRACE filter needs a diagnostic build: the retained Denial release enables
`release_max_level_info`, which compiles those callsites out.

For the independent EGL cleanup investigation, build
`tools/qemu-virtio-drm/egl-thread-probe.c` with the retained ARM64 cross compiler:
`aarch64-linux-gnu-gcc -std=c11 -D_GNU_SOURCE -O2 -Wall -Wextra -Werror
-pthread tools/qemu-virtio-drm/egl-thread-probe.c -o OUTPUT -lEGL -lGLESv2 -lgbm`.
Use the same VM command with `--egl-thread-probe OUTPUT` instead of `--deniald`,
require `--render-node`, and omit `--flutter-bundle`. No Denial binary or shell
runs in this mode. Three fresh processes compare worker exit, explicit unbind,
and `eglReleaseThread`; each first checks rejection while the worker still owns
the context. The ten-second per-process deadline and existing VM/log bounds
apply. PASS means the comparison completed with valid controls; inspect the
recorded post-join outcome separately. This does not reproduce Denial's full
thread/context lifecycle or qualify phone graphics. Record the source, executable,
compiler container and unchanged VM inputs alongside the result.

Before implementing native render reservation completion, run the manual
exact-source ordering checks with fresh disk-backed outputs:

```sh
python3 -O scripts/host/test-frame-completion-order.py --source "$ENGINE_SOURCE" --output "$ENGINE_ORDER_OUTPUT"
RUSTC="$BOUNDED_RUSTC" python3 -O scripts/host/test-render-reservation-order.py --source "$DENIAL_SOURCE" --output "$BROKER_ORDER_OUTPUT"
```

The engine check executes extracted production queue/animator/raster-dispatch
methods with deterministic scheduling and a draw-result adapter. Its PASS means
the ordering counterexamples and controls were reproduced, not that a completion
protocol works. The broker check asserts desired stale-work isolation properties;
it deliberately returns FAIL while delayed acquisition/cancellation can affect a
replacement reservation. `counterexamples_observed` records reproduction
separately. Neither manual check is silently included in the active tier.
Both reuse the repository runner's process-group cleanup and deadlines. They
execute no GPU, Dart, VM or phone code. A UI or raster queue barrier alone is not
proof that a particular frame's raster work completed.

The work-specific successor is checked separately against the exact source:

```sh
python3 -O scripts/host/test-render-work-engine.py --source "$ENGINE_SOURCE" --output "$ENGINE_WORK_OUTPUT"
RUSTC="$BOUNDED_RUSTC" python3 -O scripts/host/test-render-work-broker.py --source "$PATCHED_DENIAL_SOURCE" --output "$BROKER_WORK_OUTPUT"
```

These checks execute production ownership, admission and queue methods with
explicit graphics/task adapters. They are manual exact-source checks, not an
implicit active-tier PASS. A reservation is owned by one immutable work ID,
including queued and retried frame items; its final owner cancels only that ID.
Admission protects the begin-to-acquire span from expiry and completion cleanup.
A stale task is deferred before allocation; real allocation errors stay errors.
The native extension and engine must be built and qualified together. New public
symbols fail closed when an older engine is loaded. Rebuild every linked object
whose recorded dependencies include a changed engine header, then require real
VM raster/page-flip progress without errors. Host fixtures cannot qualify that
runtime boundary or the phone.

The engine suite also checks delayed UI submission after an old-scene retained
retry. Patch0005 requests a coalesced retained frame for a genuinely newer
pending scene, without another Dart build or accepting expired work. The
20-case suite executes the real Shell/Engine/Animator notification route,
including duplicate, already-drawn, topology and weak-lifetime guards. For the
negative control, add `--without-pending-scene-fix --case
queued-ui-stale-scene-progress` and use a separate output directory: it applies
only patches0001–0004 and must fail the explicit progress obligation after
successful fixture compilation. Native grants and GPU presentation are still
adapters; a passing suite does not establish the observed VM failure cause.

The startup lifetime regression runs separately with
`RUSTC="$BOUNDED_RUSTC" python3 -O scripts/host/test-engine-registration-ownership.py
--source-before "$BEFORE_SOURCE" --source-after "$AFTER_SOURCE"
--output "$REGISTRATION_OUTPUT"`.
The source inputs differ by patch 0007; it verifies that delta and executes both actual
constructor tails with shutdown/registration boundary failures. It must retain
the original registration error and keep callback state alive when shutdown
cannot establish worker termination. This injected failure is separate from
the observed VM reservation errors.

The mobile package graph checker validates metadata by default. The original
`mobile-package-closure.json` remains a historical graph; select the current
snapshot explicitly through the graph reference in `manifests/current-artifact.json`.
To audit cached archives against the September 12 snapshot without downloading
or installing anything:

```sh
python3 -O scripts/host/check-mobile-package-closure.py \
  --graph packaging/arch/mobile-package-snapshot-20260912.json \
  --archive-dir "$PACKAGE_CACHE" --keyring "$RETAINED_PUBLIC_KEYRING" \
  --trusted "$RETAINED_TRUSTED_KEYS" --revoked "$RETAINED_REVOKED_KEYS" \
  --report build/new-mobile-archive-audit.json
```

Use a disk-backed TMPDIR. The output must be new. Archive audit exit codes are
0 for all requested archives verified, 1 for failed verification and 2 for
missing inputs/tools. JSON enumerates every pinned package. PASS covers archive
size/hash, detached signature hash and GPG verification, explicit signer trust
and revocation, and signed `.PKGINFO` name/version/architecture/dependencies/
provides. It grants no installation authority. Newer cached revisions are not
substitutes for missing pins. The retained graph and historical verification
fields are unchanged; archive receipts bind their exact graph and trust inputs.
Keyring observation, repository selection and engine/AOT closure require
separate evidence. `--trusted` is a direct primary package-signer allowlist,
not a GPG web-of-trust evaluator. It accepts full uppercase fingerprints with
`:4:`, `:5:` or `:6:` record syntax; those values do not cause trust-chain
evaluation. Revoked files use one full fingerprint per line. Comments start
with `#`. No host keyring or network key lookup is used.

[Arch Linux ARM's published policy](https://archlinuxarm.org/about/package-signing)
signs packages and intentionally does not sign repository databases. Preserve
raw database hashes and malformed records, validate the selected dependency
graph against signed package metadata and libalpm, and describe HTTPS snapshot
selection separately from package authentication. Missing upstream database
signatures are not an obtainable prerequisite. This does not establish
cryptographic freshness/anti-rollback or grant signed mobile-update authority.
For an isolated ABI test tree, `scripts/host/materialize-mobile-runtime.py`
requires `--graph`, `--cache`, `--keyring`, `--trusted`, `--revoked` and a new
`--output` directory. It repeats authentication, preflights archive paths and
conflicts, then extracts payloads through a network-isolated bubblewrap sandbox.
It retains a 3 GiB disk reserve and records every output file/link in `tree.json`.
Package installation hooks and metadata are excluded; ownership, privileged
permissions and generated caches are not an installed-system guarantee. Files
are made owner-readable and directories owner-traversable for evidence hashing;
setuid/setgid/sticky mode bits are stripped. PASS
means payload assembly only. Test ARM64 loader/ABI behavior separately, with no
physical device nodes, and retain QEMU/software-rendering scope explicitly.

The native package set includes `archlinuxarm-keyring` explicitly as well as
Arch's general keyring. Current signed ARM keyring package files and the upstream
keyring Git files differ; retain their exact identities and use the documented
package-signing fingerprint deliberately. Do not substitute the Git repository's
master-key owner-trust file for a direct package-signer allowlist.
GPG/bsdtar subprocesses have deadlines, output limits and process-group cleanup.
The mandatory metadata/archive suite runs in the active tier, including under
Python optimization. It requires `gpg`, `gpgv`, `gpgconf`, `bsdtar` and `vercmp`;
Ubuntu 24.04 supplies the last tool through
[`makepkg`](https://manpages.ubuntu.com/manpages/noble/en/man8/vercmp.8.html).

Run the unsigned board build with an existing Git object store containing the
pinned Linux commit and a new output directory:

```sh
scripts/host/build-rog5-production-kernel.py \
  --linux-git "$ROG5_LINUX_SOURCE" --output build/rog5-production --jobs 2
```

The command archives verified immutable source instead of modifying that checkout.
Install the declared compiler, module and schema tools first; absence fails the
selected gate. `--prepare-only` records configuration preparation, never a compile
PASS. An optional `--base-archive` must match the pinned full archive hash.

After a production source preparation/build, run the separate exact-source
regressions with the schema environment on PATH:

```sh
ROG5_LINUX_SOURCE="$PWD/build/rog5-production/source" \
  scripts/host/test-repository-linux.sh board
```

This tier requires the source and schema tools and fails if they are missing.
It exercises the real RPMh binding/PM fixtures and compares touch core extracts.
It does not rebuild Image/modules or establish physical qualification.

The board build stages the local disabled-touch binding without replacing any
upstream binding. It exports base-DT labels, then requires ordered
display/GPU/inert-touch composition and the provider contract before PASS.
The same composition check can use existing exact board outputs:

```sh
python3 scripts/device/test-mobile-dt-composition.py \
  --linux-source build/rog5-production/source \
  --base-dtb build/rog5-production/objects/arch/arm64/boot/dts/qcom/sm8350-asus-rog-phone5.dtb \
  --schema build/rog5-production/objects/Documentation/devicetree/bindings/processed-schema.json \
  --output build/new-mobile-dt-check
```

The output must be new. The source/schema must contain the complete production
bindings and local touch binding. This compiles only DTs, records consumed
includes and tools, and validates all bindings; it never creates a phone image.
The cheap active tier checks semantic guards and actual GENI extracts. The board
tier additionally runs the real touch schema fixtures. Keep missing source or
schema prerequisites visible; an individual driver/module build proves neither
an enabled provider nor physical input.

The mobile acceptance contract is separate from the immutable headless baseline.
`check-mobile-status.py --write` updates only the generated current-state header;
old checkpoints remain unchanged. Neither this status file nor an artifact
inventory grants admission, signing or phone-execution authority.

## Qualification-first scope

The 2026-09-10 user clarification expands the product destination to a mobile
Arch phone, excluding cellular; see [priorities](../ROADMAP.md). The current
buttons/LED milestone and subsequent display/touch/GPU work may proceed under
their bounded gates while unrelated baseline qualification failures remain
open. The acceptance matrix below still defines baseline release qualification,
and its failures must not be relabelled as success.

The mandatory matrix in [release acceptance](release-acceptance.md) is the
definition of done. Select the highest-value failing or blocked outcome, state
one question, and work to evidence. Fix newly found defects now only if they
block qualification or materially threaten the release. Put unrelated work in
the existing [backlog](../ROADMAP.md), not another review or state ledger.
Reopen a completed review only when new evidence changes its conclusion.

Use focused reproduction/correction for demonstrated defects. Repeated,
unexplained or cross-component failures warrant explicit systematic debugging;
failed attempts trigger hypothesis reassessment, not an architecture verdict.
Bounded experiments and labelled mitigations are permitted while an original
cause is unknown. An unrelated incident need not block a separately proven fix.

## Feedback after each run

The r77 fallback had root-owned sticky `/run` mode 1777. The unchanged
0755 staging guard correctly refused before creating its namespace. Separate
recovery used the existing protected 0755 tmpfs `/run/initramfs` as parent,
retaining the guard rather than chmodding global `/run`. Five ARM64 cases and
five coordinator cases passed; actual restoration took 10.340 s. Discover the
actual fallback RAM parent as part of preparation and qualify that exact path.
After any early reboot, collect retained reset evidence before another boot;
PSTORE config with no ramoops DT node does not prove a working crash-log backend.

In r77, the prepared terminal entry started immediately on Ready and both
independent sudo reuse checks passed. Keep the same verified controlling terminal
for subsequent sudo work, with bounded refresh only while a job is active.
Successful RAM transfer and early stage packets do not prove target health:
read the authenticated returned bundle/release before interpreting a generic
identity error. Preserve that distinction in the run summary, and retrieve
retained reset evidence before another boot can replace it. A display DT may
exercise built-in MDSS/DSI before any explicit panel-module command.

A healthy overall boot does not prove all PMIC children bound. In r76, a
0.363-second metadata-only query distinguished the SID-5 unbound PMR735B from
five successfully bound PMICs. Trace the exact failed register and probe return
before changing DT nodes; device labels alone do not prove board population.
Thermal-driver config, module availability, loading and actual alarm binding
are separate facts. Keep this diagnosis independent of a frozen prepared test.


For sudo reuse, retain the actual controlling terminal and verify its shell
PID/start, session, foreground process group and host boot. `/dev/tty` reports
its special device number rather than the underlying pts device; compare the
process's tty number and foreground ownership instead. The r75 live terminal
check and ten launcher cases pass. After local authentication, two separately
owned `sudo -n -v` children must succeed before delegating to the trial. Keep
this wrapper outside the frozen kernel/controller so authentication preparation
does not trigger another build or invalidate qualified controller code.


The r74 provenance fixtures now shift a running monotonic clock past their
accelerated capture closure. A fresh 1380-second software recording must be
replayable immediately; never wait for wall time or relax the production
capture deadline to accommodate a fixture. When rebinding qualified components,
preserve historical source maps explicitly and publish the current dependency
identities separately. Eleven unchanged privilege boundaries were compared
before inheriting actual root/deck handoff evidence, avoiding another password
prompt for an unchanged test. Current credential reuse still needs verification.


The r71 missing-RAM failure is now covered by the actual staging receipt and a
fresh read-only pre-claim observation, with the same binding checked at every
admission gate. In r73, 76 focused cases and four full-flow fixtures passed; the
actual phone recheck took 2.883 seconds. Derivative checkouts must retain explicit
paths to unchanged installed-file evidence: a copied selector path caused the
first fixture failure, fixed without copying or rebuilding the selector. Keep
fixture and actual phone results distinct, and preserve failed attempt outputs.


Standing user instruction, 2026-09-10: reserve a brief review after each run and
at the end of every goal turn. Check whether the run advanced the current
priority, what failed repeatedly, and where measured time or resources were
spent without useful new evidence. A successful build can still be the wrong
next task: kernel and hardware qualification currently precede Denial builds.

When a repeated error or bottleneck has an actionable cause, implement one
scoped improvement and verify it with the smallest relevant check. If the cause
is uncertain, choose a bounded measurement that distinguishes hypotheses before
retrying. Preserve failed receipts and original deadlines; do not turn a fix
into a weaker acceptance gate. Carry larger justified changes into the existing
roadmap, and add a development lesson only when it prevents a reusable failure.
No-change reviews need no new file or repetitive user update. Keep this review
proportional so it improves the next run without delaying hardware work.
Before accepting a mocked boundary test as preparation, run a cheap check of
the actual entrypoint and target tool availability. Record the cause, change
and relevant result together in the existing run record; measured improvements
apply only to the work actually measured.

## Commands and tests

Run these from the repository; `scripts/host/rog5-dev` also works from another
directory. Each command delegates to an existing implementation.

```sh
scripts/host/rog5-dev test active
scripts/host/rog5-dev select --event push BASE HEAD
scripts/host/rog5-dev select --development BASE HEAD
scripts/host/rog5-dev build-initramfs --help
scripts/host/rog5-dev package --help
scripts/host/rog5-dev check-target --help
```

- Documentation: link/context checks and active tier.
- Observer/userspace: focused behavior tests and active tier; copy only the
  admitted script if no reboot is needed.
- Module: exact `.ko`, ABI/vermagic/BTF and dependency closure; no full kernel
  build unless built-in code or ABI changes. Unsafe unload requires a short boot.
- DT/initramfs: compose only the affected DTB/archive, then test that composition.
- Kernel/recovery/shared lifecycle/trust/storage: focused checks first, one full
  `test ci` on the frozen tree. Historical matrices run `test nightly`.

Do not rerun full local tests without changed code or a new failure. The runner
prints per-suite duration. It runs at most two explicitly isolated suites by
default, further limited by CPU affinity and inherited CPU quotas.
`ROG5_TEST_WORKERS=1` serializes those suites; values 1–32 request another cap
without exceeding detected CPU capacity. Unknown quota hierarchies serialize
conservatively. Completed suite logs print as slots are reclaimed, and any ready
failure is handled before refilling the queue. Shared-state tests remain sequential. CI uses this same runner. PR head and
merge validation remain separate; main pushes now select from before/head.
Unknown or unavailable diffs broaden validation. Scheduled/manual validation
runs nightly and QEMU. Required job names are retained, with explicit skipped
merge handling for non-PR runs.
The single reviewed current narrative report is documentation in both the
development and CI selectors. Other `test-results` paths remain potentially
executable inputs and select broader checks; mixed critical changes still win.
PR merge checks continue to cover their full relevant branch delta.

Before full CI in a new worktree, materialize the tracked test fixtures; a sparse
checkout prepared for hardware observation may omit required historical inputs.
Provide the pinned Android boot tools and canonical boot-v3 template using the
bootstrap steps in `.github/workflows/offline-smoke.yml`, or reuse local copies
after verifying their exact pinned hashes. These ignored dependencies are not
created by `git worktree add`. Keep temporary checkout copies on disk, preserve
at least 3 GiB free, and restore the sparse checkout after validation if needed.
The active composition suite also uses the pinned Android unpacker, so active
checks need boot-tool bootstrap or verified local copies. Only the canonical
boot-v3 template remains unnecessary for the active tier.

Batch related fixes into one frozen integration checkpoint; record the exact
source/dirty-input identity tested. Run focused checks during edits, one full
local CI for relevant shared changes, then publish with existing exact-head
and merge requirements. Documentation-only follow-up gets its link/active
checks; it does not retroactively change the source covered by earlier CI.
No repeated full CI for unchanged inputs. While remote checks run, do useful
independent work without modifying their frozen inputs or starting a second
device coordinator. This policy changes iteration cadence, not release gates.

### Human-assisted hardware sessions

Complete the builds, focused tests, review, staging and no-press runtime checks
before asking the user to be available. The
[local-root physical-key reader](../scripts/device/observe-local-root-physical-key.sh)
supports `--preflight`: it checks the actual input FD, driver, device tree and
inhibitor, then exits without a READY prompt or event reads. Run the relevant
key preflights before the handoff; keep the existing NFS-specific gate separate.

Prepare the full launch and cleanup recipe in advance. Wait for a fresh explicit
Ready before starting any operator countdown. After the reply, perform only the
brief current-state guards and runtime arming, then immediately present the
actual reader READY prompt. Ask for one short press/release at a time and collect
events automatically; the user should not have to type terminal commands.

If preparation fails or availability expires, close the session and resolve the
problem independently before asking again. Keep partial valid component evidence
and every raw failure; avoid repeating a completed physical step solely because
a later independent validator failed. Explicitly distinguish a strict test-case
FAIL from separately verified component behavior.

### Development-only fast eligibility

`select --development BASE HEAD` emits a JSON **NOT RUN** decision, the exact
commit/tree, selector hash, impact, focused/optimized tests and remaining
requirements. It is not test evidence or admission. Freeze the named checkout
and retain the decision beside the existing run receipt; record actual tested
source, artifacts, toolchain/configuration/environment and durations. A dirty
checkout is not represented by the committed tree and must be recorded and
reclassified before use. No previous run is relabelled and no new result cache
is introduced by this selector.

The first reviewed leaves are the read-only standalone-root observer and
healthd's isolated userspace implementation (plus their tests). Documentation
and the reviewed current narrative report may accompany them; other retained
test reports can be runtime inputs and are not exempt. Any other changed
dependency selects full CI: notably the
deployed verifier, generated service units, lifecycle, admission, charging,
shutdown, watchdog, DT, initramfs, kernel and storage. A small diff does not
override this. Module work still needs exact module/dependency builds,
ABI/vermagic/BTF/firmware closure and final packaged composition. Registration
changes retain all-consumer/canonical-record and altered/consumed-record
rejection checks in normal and optimized Python; they are not a fast-path leaf.

Under standing authority, an eligible **development observation/experiment**
may proceed after its focused normal/optimized tests, active checks and exact
target/payload compatibility checks, without waiting for unrelated remote CI.
Use a fresh dedicated `/run/rog5-dev-experiments` child (host-side for a host
observer). A healthd experiment uses a separate bounded loopback listener and
exact target Python, never the accepted service, port or persistent unit/config.
Record cleanup and a bounded service-level result; failed/missing prerequisites
remain FAIL/BLOCKED, not development success. Do not promote a changed observer
into a boot/power/storage safety gate through this route. The existing exact
device, signatures, power/thermal, storage and fallback checks still apply.

No fast-path decision grants reboot, target execution, signing, flash or release
authority. Critical integration and final release retain relevant full local
and exact-head/merge CI plus the unchanged mandatory physical matrix. Broader
tiers now union active/probe coverage, execute duplicates once, and preserve
the existing isolated/shared-state scheduling. Reuse kernel/module/wrapper
caches only under their existing exact-input contracts.

A test-fixture-only correction may reuse the last successful full local CI for
unchanged production inputs. Bind the original receipt, enumerate and review
the exact test/documentation delta, run the changed tests and active tier, and
retain exact-head remote checks. The publication adapter must reject any other
changed path or altered receipt. Report original and current tested revisions;
never relabel the older full run as testing the newer fixture.

A01 overlaps its initial full retained-root hash with independent read-only
composition checks. That hash must complete before QEMU; a separate post-VM
full hash and pathname/metadata checks remain mandatory. The 120-second limit
is unchanged. This scheduling optimization does not reuse a stale root digest.
Disposable A01 VM archives use deterministic gzip level 1; exact decompressed
CPIO content remains unchanged. Signed release compression is not affected.
On the constrained development host, do not overlap memory-heavy A01/C02 work
with full local CI: a measured C02 deadline failure passed when run separately.
Overlap remote CI and bounded independent preparation instead. Keep the failed
run and original deadline; a successful isolated rerun does not erase it.

A01 and C02's sparse-root checksum still hashes every logical byte. Filesystem-reported
holes contribute their exact zero bytes without reading them from disk; unsupported
sparse seeking falls back to a full read. Invalid extents, I/O errors and changed
inputs are refused. Results record both checksums' read volume and duration;
neither root check nor the 120-second deadline is omitted.

## Packaging without identity-copy scripts

The runtime packager accepts one JSON `--config` containing its non-credential
Configuration fields. Run `package --help` for field names (JSON uses underscores).
All values are strings. Artifact paths resolve relative to the JSON file.
The recipe cannot contain signing-key/output paths, admission authority or
unknown fields; CLI recipe overrides are rejected. Supply the key and a fresh
private output directory separately. The original CLI remains supported.

The packager computes sizes, hashes and the signed manifest from the actual
input bytes and publishes atomically. Do not copy derived hashes into a second
manual signing script. Keep per-cycle private recipes and receipts outside Git.
`build-initramfs` delegates to the qualified base/radio composer; later layer
builders retain their own explicit input contracts.

For a packaging rehearsal, use an ephemeral test key and the retained accepted
Image/DTB/archive. Compare twin outputs and run the native bundle verifier with
that test public key. Such an output is **not trusted by the phone**. Testing
with a test key must never replace production signature verification.

## Exact target filesystem checks

Host QEMU without filesystem isolation previously exposed host `modules.dep`
and hid a real BusyBox failure. The following command extracts the archive into
a disposable root and runs its own BusyBox, using bubblewrap plus static
`qemu-aarch64-static`. No host `/lib`, network or physical device is exposed.

```sh
scripts/host/rog5-dev check-target --release TARGET_RELEASE INITRAMFS -- \
  sh -n /rog5-native-wifi/runtime
scripts/host/rog5-dev check-target --release TARGET_RELEASE \
  --empty-module-index INITRAMFS -- \
  modinfo -F vermagic /rog5-native-wifi/qcom-pon.ko
```

`--empty-module-index` explicitly simulates the trusted pre-switch runtime's
empty mode-0444 index **inside the disposable extraction**. Omit it to test the
original archive. Check expected output as well as status: BusyBox `modinfo`
can exit zero for a missing module. Archive paths precede runtime relocation;
`/rog5-native-wifi` becomes `/run/rog5-native-wifi` during boot. This runner
does not execute init, load modules, emulate hardware or prove systemd behavior.

## Builds, trials and publication

Reuse the retained kernel/DT/modules for host, documentation and userspace
changes. `kernel-build-contract.sh` already enforces locked exact-state
incremental reuse through `INCREMENTAL_BUILD=1`, optional `KBUILD_CCACHE=1`
and bounded `JOBS`. A changed kernel input must invalidate reuse. The existing
ASUS wrapper cache binds actual source, toolchain, config, initramfs and repack
inputs; host docs and target bundle names are not wrapper-kernel inputs.
Keep clean twins when changed recovery/kernel inputs need release reproduction.

Local development path: freeze source; run the appropriate local tests;
compose/package without remote access; validate exact archive, signature,
payload identity and output inventory; retain source SHA and timings. This
path now uses the shared recipe CLI instead of copied scripts requiring a
fresh remote run merely to package unchanged payloads.

Live admission is separate. Existing reviewed device/topology/slot, power,
fallback, artifact and one-use claim checks still apply. This consolidation
does not add a local-CI waiver to a live gate that requires remote evidence.
Publication/release still requires successful CI for the exact commit plus
merge validation where applicable. A shared trust/runtime change receives full
validation. Admission-only generated data need isolated artifact/claim checks,
not another complete run when the already verified source is unchanged.

Do not invoke historical Alpine/NFS live gates for the installed native server.
The native RAM loader and transaction are
`scripts/device/load-native-ram-bundle.sh` and
`scripts/device/execute-native-ram-bundle-transaction.sh`; host admission must
precede them. Neither this command front door nor packaging consumes a claim.
Never retry an ambiguous or post-COMMIT experimental target.

## Experimental execution and stable operation

| Operation | Rule and required evidence |
|---|---|
| Issue an experimental candidate | Exact signed composition and admission first; one execution claim consumed at COMMIT. Packaging never grants authority. |
| Ambiguous experimental execution | Treat as consumed; collect diagnostics and use the independently verified recovery route. Do not resend COMMIT or relabel it an ordinary reboot. |
| Ordinary accepted-release reboot | Repeated boots are required for qualification, each with fresh boot identity, verified installed artifacts, power gates and complete logs. Do not reexecute an experimental RAM claim. Verify the installed loader/release supports the existing normal path first. |
| Automatic fallback / recovery qualification | Exercise the existing verified selector and rollback path with an isolated failed test candidate. Do not corrupt installed payloads. A simulated pass or host-assisted fastboot rescue does not prove autonomous fallback. |

These distinctions document existing boundaries, not a new retry mechanism.
An accepted release is not permanently barred from reboot by experimental
one-use rules. Conversely, current RAM-rescue success does not qualify an old
installed loader. Any selector/claim/rollback mechanism change needs focused
regressions and the applicable full/trust checks before use. Storage/flash
authorization remains separately scoped; no policy wording grants it.

For an installed-release reboot, start `headless-stage-receiver.py` with
`--source-boot-id` set to the freshly authenticated current boot UUID. Use the
same option with `--check`; experimental RAM executors deliberately reject
this capture mode. Authenticate installed bytes, fallback and power separately
before the reboot request. The receiver is passive and grants no authority.
It ignores the old boot, requires an observed USB disconnect, then accepts
only a different boot's frames. Missing disconnect, returning old identity or
mixed boot evidence cannot qualify a reboot. Complete pinned SSH/local-root
verification and host boot-service-absence evidence are still required for S01.
Do not infer bootloader slot-success state from Linux trial-health records.

## Retention and context

Current state owns accepted identities and links to evidence. Active context
is a pointer; lessons contain failure patterns, not another chronological log.
Use [the archive index](archive/README.md) for superseded instructions. Global
skills/configuration are unchanged; the project debugging skill remains
explicit-only and does not require installing its upstream companion skills.

Before reclaiming a build, check references, mounts/processes, cache twins and
recovery dependencies. Archive the exact tree without dereferencing symlinks,
compare archive members with originals, test restoration, and retain the
archive digest and original path privately. Remove only that verified obsolete
tree; preserve source, cache, unique evidence and recovery inputs.

Authentication preparation lesson (2026-09-11): keep password-entry attempts
separate from the one-use hardware execution entry. Preserve each bounded
authentication result, exclude concurrent owners, and refuse incomplete or
unreaped prior attempts. Reserve the hardware entry only after authentication
succeeds, with the original claim and current-state checks still enforced. A
password timeout before phone actions is not evidence of a kernel failure or a
wrong password. Reuse unchanged artifact and timer evidence when only host
authentication bookkeeping changes; verify the full dependency readers before
asking for fresh availability.

Hardware preparation lesson (2026-09-11, OLED r71): host artifact checks and
generic phone health do not establish that the experiment-specific RAM helpers
exist. Before live admission, claim consumption or asking Ready, stage the exact
source helpers with their boot/owner/custody checks, then run the actual generated
read-only source and route preflight on the phone. Retain its authenticated
receipt and require current boot, owner and file identities. Keep the runtime
verification in the observer; an unstaged phone must refuse. Do not consume a
boot claim merely to discover missing preparatory RAM files. Failed/consumed
experiments and their execution source remain immutable evidence.

Sudo reuse preparation (2026-09-11): independent non-TTY command processes may
not share sudo authentication. Keep one verified controlling terminal alive
across related test launches, and verify noninteractive reuse from separate
child processes after fresh authentication. Retain bounded refresh only during
active work. A terminal handle or an old success is not proof of current sudo
credentials; do not open a password window from automatic goal continuation.

Offline fixture lesson (2026-09-12): admission tests must construct unconsumed
and consumed claim states explicitly. The first integrated repair run exposed
a test that read the host's retained claim state and therefore changed outcome
after a historical trial. Guard the canonical claim paths in unit tests and
mock the admission result; never reset a real claim to make a fixture pass.
The failing run is retained and the isolated nine-case fixture passes.

Integrated repair lesson (2026-09-12): preserve failing receipts while repairing
fixture assumptions, then run the final tier on frozen source. The 536.475-second
continuation exposed stale Action-tag expectations and an orphaned watchdog-test
sleeper. Keep original child identities through mock watchdog termination and
wait for owned supervisors; do not loosen the reporter's descendant rejection.
Keep execution metadata beside the reporter directory, whose JSON files are
per-test receipts, rather than mixing an unrelated JSON record into that namespace.

Provenance lesson (2026-09-12): a raw execution record can correctly identify
a dirty starting checkout whose commit omits later inputs. Use the verified
final-source-binding commit/tree for the resulting source identity, and retain
the dirty execution repository separately. An independent final review caught
that labeling error in the public board summary; the correction changes no
build input or artifact byte.

Component qualification lesson (2026-09-12): use read-only external-module
builds when the compiled kernel inputs are unchanged. Touch twins took about
2.9 seconds each; an archive/source comparison and exact DT rebuild took
15.4 seconds, avoiding another 4,457-second cold kernel compile. Reproduce the
old DTB with its actual kernel flags before interpreting a new DT delta.
Keep full schema checks separate from cheap guard changes: an unchanged
schema/driver/DT input binding can retain the 81.4-second result while a stricter
configuration parser receives focused regressions. Record commands before
launch so failed and interrupted builds retain the same provenance as successes.


For the retained x86-64 builder, `scripts/host/generate-denial-arm64-engine-args.py
--source "$LOCKED_FLUTTER_SOURCE" --output "$NEW_EXTERNAL_OUTPUT"` derives
arguments through the pinned Flutter generator. It verifies Flutter/Skia commits,
Dart against that Flutter DEPS file, and tracked cleanliness. Linux ARM64 target,
ARM64 Dart code generation, target embedder inclusion, Fontconfig and release mode
are mandatory; internal toolchain concurrency is one. Prebuilt Dart auto-selection
is disabled so cache contents cannot silently choose another SDK route. The
result is **argument generation only**. GN graph validation, complete dependency/
hook closure, compilation, host gen_snapshot targeting ARM64, engine/ICU and shell
AOT still need separate evidence. The command executes no GN, Ninja, hooks or
package/phone operations, and will not write inside the frozen source or replace
an existing output. Its receipt includes the subsequent GN argument vector; run
that command with the locked checkout’s `engine/src` as the working directory.


Before the real engine GN graph, run a single bounded `vpython3` source script
in the same isolated build environment. This separates interpreter-cache misses
from graph/configuration failures. Provision missing pinned interpreter packages
explicitly; keep the subsequent graph check network-disabled. Use `--threads=1`
while diagnosing dependency closure. The active GN tool path and immutable CIPD
instance are recorded in `manifests/current-artifact.json`; argument generation
alone neither installs that tool nor populates sysroots. Historical intermediate
archives remain outside Git with per-file restoration manifests. The existing
regular-file hash helper rewinds its input; pipe-backed archive verification
requires a non-seeking streaming hash loop.

### Denial Flutter assets at resolved package paths

Use `scripts/host/assemble-denial-flutter-assets.dart` with the pinned
`flutter_tools` package configuration. Its four positional arguments are the
absolute application root, Flutter root, compiled engine output and fresh output
directory. For the isolated ARM64 build layout:

```sh
/flutter/bin/cache/dart-sdk/bin/dart \
  --packages=/flutter/packages/flutter_tools/.dart_tool/package_config.json \
  /repo/scripts/host/assemble-denial-flutter-assets.dart \
  /work/workspace/settings_app /flutter /engine /output
```

Mount the resolved workspace, hosted package cache and matching generated
`sky_engine` root at the paths recorded by the application package configuration.
The helper rejects missing package roots and an existing `flutter_assets` output.
Relocating settings to `/app` changes its relative shell dependency to
`/dart_shell`: Flutter can otherwise emit a valid but incomplete asset manifest.
The real settings startup exposed the missing package logo. The corrected
workspace yields 29 declared assets, including package assets and fonts; the
complete SDK mapping also supplies its license notices. Keep frontend/AOT,
asset assembly, actual startup and physical rendering as separate results.

### GTK implicit-view disposal patch

The local patch
`patches/flutter-d728e61e/0001-linux-preserve-implicit-view-on-dispose.patch`
applies to Flutter base `d728e61e7d835e02c453c70ae9523a40f6c03215`.
That base's embedder forbids removing the implicit view, although its GTK
`ViewDestroy` test expected such a call. The patch leaves implicit-view ownership
with the engine and retains secondary-view removal, correcting the actual test.

Keep qualified source/build artifacts intact. For incremental qualification,
copy the completed output cache, apply the patch to independent copies of its
two affected files, and mount those copies read-only at the original source
paths. Build `flutter_linux_unittests` and `flutter_linux_gtk` in the copied
cache. Record the upstream source revision, patch hash, effective file hashes,
GN arguments and output hashes; an upstream engine version string alone does
not describe patched bytes. Use the corrected test against the original
implementation first, then test secondary removal/error cases and actual
settings disposal with only the new library overlaid. None of these steps
qualifies phone hardware, a Denial backend or a complete Wayland session.

For engine raster-origin diagnostics, use the bounded patch and exact-source
runner documented in `patches/flutter-engine-d728e61e/README.md`. Normal startup
suppresses FML INFO; test the actual Shell threshold and use targeted IMPORTANT
audit messages. Keep call IDs distinct from native reservation IDs and preserve
failed origin collection as failure even when the guest renders frames.


For the exact-source window-command dispatch regression, run
`RUSTC=rustc python3 scripts/host/test-window-command-dispatch.py --source DENIAL_GIT --output NEW_DIRECTORY`.
It extracts the pinned event-loop segment, queue methods and command routing,
then compiles deterministic Rust tests before and after patch 0009. Missing
source/compiler fails the command. This manual source-dependent test is separate
from the active host tier; its PASS does not imply a VM or physical run. The
first dispatch handles at most 64 queued commands before background yields;
ordinary management and engine replacement retain their complete final drain.
The lock boundary still precedes client effects. This repairs the two tested
post-message yields, not every possible event-loop starvation path.


For the unresolved VM focus boundary, `--trace-focus` requires
`--observe-mobile-apps` and stages an explicit guest marker. The guest refuses
an invalid marker and clears an ambient `DENIA_FOCUS_TRACE` setting. Patches
0010/0011 read the exact opt-in value `1`: each emits at most 64 records per
process. Dart records animation lifecycle, commit target, send attempt and
reply/error type; native records accepted enqueue, routed drain and actual focus
before/after activation with grab state. Send/reply is not focus acknowledgement.
No titles, payloads, error contents or credentials are logged. The opt-in changes
diagnostics only; physical qualification and full app-switch acceptance remain
independent. Run `test-shell-focus-trace.py --help` and
`test-native-focus-trace.py --help` for the manual exact-source checks before
building these diagnostic binaries. The host tier alone does not execute them.

For `--observe-mobile-apps`, supply `--evidence-writer PATH` with the matching
ARM64 build of `tools/qemu-virtio-drm/evidence-writer.rs`. Compile using the
pinned native builder's rustc, `--edition=2024 -Dwarnings -O --target
aarch64-unknown-linux-gnu -C linker=/usr/bin/aarch64-linux-gnu-gcc`; no Denial,
engine or kernel rebuild is needed. Execute `test-qemu-evidence-writer.py
--output FRESH_DIRECTORY` with the pinned host RUSTC, then
`test-qemu-launcher-evidence.py --writer HOST_BINARY`.

One guest FIFO collector owns virtual port1 (`rog5.launcher`). Each producer
writes complete records at most4096 bytes in one syscall; clients are capped
at1MiB each and drained after errors. Native output stays on the console; its
forwarder sends the existing terminal boundary to the evidence FIFO before
forwarding that native line. The host reads `protocol/events.log`, capped
at3MiB, independently of serial counters. Truncated records, missing terminal
boundary, writer failure and failed collector drain fail the observation.
Optional global presentation intervals are not forwarded and remain NOT RUN;
the terminal frame counts and inspected captures stay separate evidence.
This isolates observed console-fragment interleaving without accepting arbitrary
embedded client prefixes. It adds no physical device exposure or phone proof.

Add `--observe-mobile-apps-text` to the existing app-interaction command to
exercise the same OSK text/backspace/restoration sequence after returning to
Mousepad, then dismiss the keyboard and switch back to Foot. This requires
`--observe-mobile-apps` and the dedicated evidence writer. The combined probe
checks both the four native focus visits and the exact focused key lifecycle
from the same owned protocol stream; inspected text remains a separate result.
It uses a fixed96-command QMP budget, while other probes retain64. Only allowed
pointer/capture queries are available; no QMP power command is added.

The action clock now honors scheduled100ms steps while keeping idle polling
at200ms and an active10ms floor. The unchanged90-second shell/120-second harness
bounds remain in force. The observer resets the manual viewport pan and drags
the OSK's blank top padding down before the final switch. This tests the current
manual workaround, not automatic caret visibility or physical multitouch.

Keyboard animation changes must preserve a single position across the visible
sheet, translated content and native input regions. The open/closed target is
not a rendered-frame observation. Patch0013 publishes coalesced controller
samples in the scheduler's transient phase, before build and native layout;
post-frame provider writes can otherwise race the input publisher's fresh state
read. Source tests use `test-keyboard-animation-geometry.py` with an explicit
matching source and Dart tool. These adapter tests and a frontend compile do not
qualify actual animation timing or phone touch. Keep exact AOT/runtime and the
current VM proof distinct until a changed-runtime observation is executed.

For the selected Denial userspace, `check-denial-runtime-linkage.py` runs the
actual ARM64 dynamic loader and a small Rust `dlopen(RTLD_NOW)` probe inside a
read-only bubblewrap root, with no host GPU device, network or application startup.
Supply the exact materialized root/tree SHA, bundle, compositor and ARM64 probe;
use a fresh output directory. The committed linkage profile covers the native
binary, Foot/Mousepad, engine/AOT and Mesa EGL/GBM/MSM/Freedreno entry points.
Each library is checked in a fresh process. Loaded package files and driver
JSON descriptors must match the authenticated materialization tree. Missing
libraries, symbols, relocations, architecture, receipts or tools cannot pass.

The probe never invokes a requested symbol, but loading/resolution can run
constructors, IFUNC resolvers and destructors. These tests prove only current
loader closure, not optional later dlopen, driver initialization, hardware
acceleration, firmware availability or phone compatibility. Preserve the real
phone's kernel/module/trial binding separately; a matching userspace closure
cannot authorize substituting a new module cohort into a frozen boot trial.

The confined runtime checker always stops and verifies its owned user service,
even when observation is interrupted. Its client takes no stdin. A nonterminal
service state prevents success; interruption retains its original exception and
any cleanup-error notes in its failure report; interrupted CLI runs exit130.
Client-wait interruption still reaches the independent service stop. Raw output
remains in the newly created log. SIGKILL
cannot execute Python cleanup, so the independent service deadline is still
required. This host machinery does not grant phone execution authority.

For a disk-bounded non-root VM fixture, `prepare-qemu-runtime-view.py` accepts the
retained materialization receipt, matching tree manifest and cached archives.
It rechecks archive and payload hashes, derives package-read modes, and creates
a fresh QEMU `mapped-file` view. Regular bytes are hardlinked; mode metadata and
symlink descriptions are separate host files. Source nlink/ctime change, but
contents, owner/mode and xattrs must not. The view is not a normal host rootfs:
use only `--runtime-security-model mapped-file` with the runner's read-only bind
and read-only9P export. The recorded signature audit is reused, not rerun.

`--non-root-session --observe-mobile-apps --runtime-security-model mapped-file`
selects a separately qualified VM fixture with RAM-only mobile UID/GID1000,
home and account-file bind mounts. Session bus, Denial and app exec paths require
empty supplementary groups, all capabilities empty and NoNewPrivs. Root seatd
owns device mediation; root udev and the bounded supervisor remain. This proves
neither the mobile policy's logind seat handling nor authentication/lock-screen
security. Account conflicts and missing identity records fail. Existing root
observations retain their original default. `--link-payload` may also reuse
regular immutable Denial/Flutter fixture bytes on the same filesystem; it refuses
symlink payloads, changes nlink/ctime and records payload hashes without changing
source permissions. Neither option admits or operates a phone candidate.

The actual logind VM uses512MiB guest RAM inside a1024MiB/no-swap container;
the extra host allowance covers measured QEMU allocations. It preserves the
existing foreground tty1 through `setsid --wait openvt -e`, verifies it is
unowned before and after, and requires successful session/scope enumeration
after PAM logout. The original PAM checks and packaged Permit User Sessions
service remain in the path. A timeout is failure, never cleanup qualification.

The same manual logind runner accepts the complete optional group
`--session-archive`, `--session-receipt`, and `--host-render-node /dev/dri/renderD128`
for a combined Denial VM. It verifies every archive file before RAM extraction,
uses retained VirGL with1024MiB guest/2048MiB host and a300s deadline, and compiles
only the small PAM fixture with coherent longer limits. No Denial/Flutter rebuild
is required. The actual mobile entry runs on the original PAM session and user
bus; both systemd targets, actual frame counters, native client configuration
and logout cleanup must pass. Same-GPU rendering reuses the logind-acquired card0
descriptor; no supplemental render group or device permission change is needed.
The archive and original runtime remain read-only; all installation paths in
this test exist solely in VM RAM. This is not a phone composition or admission.

The combined `test-qemu-logind.py` runner accepts `--observe-editor` only with
its authenticated session archive/receipt and explicit host render fixture.
It closes Foot normally before launching Mousepad, streams the editor's bounded
attributed protocol through a dedicated virtual serial port, and reuses the
pointer-only OSK sequence. The host waits for a committed native editor surface
with stable keyboard focus; a title or configure marker alone is insufficient.
It requires exact focused key press/release order and complete captures, as well
as the existing rendering/PAM/scope cleanup. Visual text still requires separate
image inspection. The normal logind-only and combined configuration tests retain
their behavior. Client65s, user120s, PAM140s and VM300s limits are unchanged.
Only the virtual port becomes guest mobile-owned; no host/phone device permissions
or runtime package files are modified.

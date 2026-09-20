# Draft display-loader ordering repair

`0001-default-dark-probe-ordering.patch` is an offline successor source patch,
not a kernel patch, admitted controller or installable payload. It applies to
`load-display.py` SHA-256
`5c298ba05fe7a6f338471cd178a10b49cd9c03914f4a696ad442e7e0dbc1838d`.
The exact historical source is retained in
`scripts/device/fixtures/display-loader/load-display-before.py`. It contains no
unit serial, USB topology or credential. Do not import this fixture: the test
extracts only the functions under test and substitutes hardware/identity I/O.

During insertion the successor observes the qualified default-zero brightness
property. After both insertion children finish and are reaped, it validates the
framebuffer endpoint and sends one zero command. It requires command success
and a final caller health/monitor check. Failed preparation, DSI errors and
zero-property readback after a failed write remain failures. Independent cleanup
still runs and cannot overwrite the original failure. No insertion retry is added.

Neither framebuffer registration nor insertion completion proves preparation.
The current kernel disables deferred fbcon takeover, but deferred driver probing
is possible; the resulting EPERM remains a conservative failure. Do not add
retries or modesets to turn that result into PASS without reviewing the actual
activation operation. The historical endpoint's framebuffer routine checks the
zero property, not proof of an earlier successful command; a successor must
update its “after blanking” docstring to reflect that distinction.

The old helper/module pins intentionally remain unchanged. They are incompatible
with the current production cohort, and the old panel's default1023 is rejected.
Before this can become a usable controller, bind the default-dark panel and the
complete production dependency closure, qualify insertion order and timing,
update the endpoint and enclosing component contracts, and requalify admission,
one-use ownership, independent cleanup and rescue. Never edit sealed controllers
or reuse a consumed claim. Applying this patch grants no execution authority.

Run `python3 -O scripts/device/test-display-loader-ordering.py` for semantic
coverage. It applies the patch without fuzz, executes the actual loader/child
supervision, and compiles the actual current panel plus pinned DRM/backlight core
extracts. Sysfs, identity, module insertion effects and preparation timing are
fixtures. The test also verifies the previous loader fails with EPERM. No module
is loaded and no phone operation, optical result or physical PASS is implied.

## Current production module input

`scripts/device/build-production-display-modules.py --output /absolute/new.tar`
materializes the fixed REFGEN/GPUCC/panel/MSM symbol dependency closure from the
machine-readable current board qualification. It validates that qualification,
module metadata, dependency-index hashes, actual ARM64 ELF identity/vermagic and
default-dark panel hash before atomically publishing an inert tar with an embedded
manifest. Existing outputs are never replaced. Nothing is loaded or signed.
The manifest binds builder/checker hashes and the exact board inputs. No helper,
service, aliases, modprobe index, firmware or boot image is added. Future archive
consumers must verify the archive hash and its exact members before staging it.

Its order is only a symbol dependency order. REFGEN's DSI-host supply and GPUCC's
GMU/SMMU clock/power relationships come from DT, and MSM can trigger fbcon/panel
preparation automatically. Those activation edges require review in the successor
controller; no insertion commands are generated. Inserting GPUCC can program PLLs,
and opening MSM DRM can load firmware/start the GPU. These are hardware actions.

All14 current modules have empty `.modinfo` firmware fields, but exact A660 source
requests SQE/GMU firmware and the overlay names `qcom/sm8350/a660_zap.mbn`.
Firmware status is explicitly NOT PACKAGED; empty module metadata is not proof of
runtime firmware completeness. The archive is an unsigned host fixture, not a new
phone candidate. Keep the historical loader and consumed claims unchanged.


## Successor archive intake

`scripts/device/stage-production-display-modules.py ARCHIVE --qualification JSON
--qualification-sha256 SHA256 --output /absolute/new-directory` verifies the
pinned offline packaging qualification and materializes its exact archive into a
new private host directory. It accepts canonical builder USTAR records only:
member order/names/types/modes/owners, payload hashes, manifest, padding and end
records must match. It does not call an extraction API or interpret archive paths
as instructions. Hash reads are bounded by the qualified size plus one EOF byte.
Every copied member is hashed again before atomic exclusive publication.

No staging directory is created before full archive validation. Failed copying
or interruption removes only owned temporary files; an existing destination is
never overwritten. A parent-directory fsync error after atomic publication stays
an error while preserving the complete output. Output files are0644 regardless
of host umask; the containing directory is private. This is host-side inert
staging, not target admission or a root-owned phone payload. The future controller
must revalidate its own target identity, ownership, files and one-use guards.
The historical controller and its claims are unchanged.

## Production successor components (offline only)

`load-production-display.py` carries the exact qualified 14-module pins and
preserves the one-shot helper, bounded child supervision and durable-entry
callback. It loads REFGEN and GPUCC first, checks those providers, loads the DRM
helpers and MSM, checks Adreno, and inserts the panel last. Every insertion is
preceded by current identity, health, cleanup-owner and retained firmware checks.
The archive's symbol order deliberately differs from this activation sequence.

`display-providers.py` supplies read-only checkpoints for the exact composed DT:
REFGEN's DSI-host supply, GPUCC/SMMU bindings, reciprocal GPU/GMU group membership,
then Adreno binding and the shared-DRM parameters after MSM is present. It performs
no reprobe, DMA test or DRM open. A missing provider fails; module presence alone
is insufficient. Panel insertion itself can complete component binding and start
GMU/display setup, so independent cleanup ownership precedes that insertion.

`display-firmware.py` retains protected directory/file descriptors for the three
fixed A660 firmware inputs and validates the firmware-class path. It detects root,
mount namespace and pathname changes, with bounded hashing. The kernel uses
`init_task.fs`, not the caller's private root. Matching the caller to PID1 is a
prerequisite only: a future root transition still needs its own qualification.
Do not treat `check()` as firmware import, SCM authentication or execution proof.

The successor constructor takes the qualified endpoint, firmware factory and
read-only checkpoint adapter. The future admitted composition must bind their
source identities and exact device/boot/board identity; no such composition is
issued here. Its durable entry must cover all 14 insertions and the 85-second
component bound. Historical two-module/45-second contracts are incompatible.
The old endpoint's release is rejected. No module is unloaded or retried and no
claim is issued or consumed. This source is not a live entry point.

The final endpoint and zero-command receipts are required, including the actual
two-byte write and zero readback. Zero property alone, `None`, or an unsuccessful
write cannot produce success. Independent cleanup retains its own errors and
runs even after main health or firmware validation fails. No physical darkness,
scanout or hardware acceleration is inferred.

The executable tests use owned inert children and the actual panel/DRM/backlight
callback extracts. Provider/sysfs/ownership/identity effects are explicit host
fixtures. They include firmware-reader integration, early-panel ordering failure,
provider failure, uncertain entry, missing receipts and interruption cleanup.

## Bound endpoint and supervisor draft

`display-endpoint.py` supplies the production endpoint. Its admitted identity
callback must provide boot ID, release, bundle, descriptor hash, current composed
DT hash and owner. The endpoint checks local root/boot/release, exactly one matching
bundle token and the stable protected descriptor, then binds that identity for its
lifetime. The caller still owns exact device/signature/health/recovery admission.
Framebuffer discovery now requires the exact DPU device, driver, DT node and
reciprocal links, not merely a matching-looking fb0 beneath MDSS. Metadata and a
successful zero write do not establish active scanout or physical darkness.

`display-component.py` assembles the four hash-pinned source components, executes
only the verified source bytes and validates all 14 insertion receipts, provider
checkpoints, endpoint identity and zero-command proof. Its entry scope comes from
the same pure `entry_intent()` used by the loader, avoiding a second scope definition.
Importing it performs no device operation; its constructor is not admission.

`0002-production-supervisor.patch` applies to the exact historical backend fixture
SHA256 `840ba5ad5c1bfe2059bfc580fb45da4e8f3fef59f8e6627789cfe5ed38904a0d`.
It routes the worker through the production loader and preserves exclusive durable
entry, matching host acknowledgment and independent cleanup. It validates entry
scope before saving it. Interruption cannot publish a successful terminal result;
cleanup error details survive, with bounded summaries for large payloads.
The draft lifetime is 100 seconds around the 85-second loader; cleanup/reaping
remain separately bounded. Existing 60/78-second host transport contracts are
incompatible and must be adapted and tested before any live composition.

The patch deliberately retains historical source/context pins and entry barriers.
It cannot form a deployable production backend by itself. No candidate, claim or
admission is issued. The legacy entry paths are not renamed to evade consumption.
Tests apply the patch to a private temporary copy of the retained source. Real
pipes and separate processes exercise acknowledgment, interruption, expiry and
cleanup; an assembled case runs the real loader/endpoint and compiled panel/core
callbacks under that supervisor, with all device effects explicitly substituted.
The process-closure repair retains each worker with `waitid(WNOWAIT)` until
all group signaling is finished. It signals the group again at worker exit to
close a setsid/fork race around an earlier forced stop, then reaps and only
observes. A retry after interruption must establish direct-child ownership;
ECHILD refuses all signals. Real inert-process fixtures cover surviving children,
pre-session termination, interruption before/after reap and observation timeout.
The fixture acts as an orphan reaper; production still requires init to reap
orphans within the existing bound. The pinned insertion helper remains in the
worker's group. This is not containment of arbitrary session escape, nor reversal
of module effects or a guarantee that uninterruptible kernel work can terminate.
Outer transport/admission and firmware root-transition assumptions remain
unqualified before any real hardware trial.


## Host duplex contract draft

`0003-production-transport.patch` applies to the exact historical transport source
retained as the non-importable `transport-before.py` fixture (SHA256
`3d6f76bb421bf8f40967ac354d49e152248636b2272a1cf2653f8702e2a1a573`).
Tests extract only the actual protocol functions; historical source loading,
staging and SSH construction are neither imported nor called. The patch preserves
those guarded historical entrypoints and pins, so it remains undeployable.

The host uses `display-component.HostContract` with the separately admitted six-field
production identity. It reads only pinned local source, snapshots the identity,
and shares the actual loader entry scope and component/blank receipt validators.
The existing outer owner still supplies device/signing/health/logger/recovery proof.
No profile, signed descriptor, admission or claim is produced by this constructor.

The exchange accepts the 100-second supervisor and reserves 120 seconds for normal
operation including target cleanup and drainage. Its first failure closes the
lease and starts one independent 18-second collection window; later errors or a
positive terminal cannot reset it or erase the original failure. Two local reap
windows and one second of reserve bring initial admission to 143 seconds. Exact
arithmetic is tested against the current supervisor's constants. Terminal records
use the production status and exact 14-insertion/zero receipts. Local transport
children remain waitable until the repaired group-cleanup routine finishes.

Real duplex fixtures cover handshake refusal in the historical version, the old
78-second deadline using a virtual clock, delayed cleanup lost with the old min
expression, fragmentation, owner loss, interruption, corrupt results, and a full
host/supervisor/loader/endpoint chain with inert insertions and compiled callback
extracts. Timing-fixture acceleration is not a long physical observation.

The session's historical provider handoff, overall logger/recovery reservations,
source admission and firmware root lifetime still need matching composition.
Transport success alone does not qualify those boundaries or any phone hardware.

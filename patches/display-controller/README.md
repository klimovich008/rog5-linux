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

Its order is only a symbol dependency order. REFGEN's DSI-PHY supply and GPUCC's
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

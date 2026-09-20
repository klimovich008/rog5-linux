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


## Enclosing session adaptation (offline only)

`0004-production-session.patch` applies to the exact historical `session.py`
fixture SHA-256 `2a2316564977a2839a31f11fb0435859857b6567f38fc5f0752ca27b5f63fa8c`.
It removes the separate GPUCC provider dispatch because the production loader
owns the complete 14-module cohort. The session binds its immutable entry to
that contract and revalidates it before display dispatch. It preserves the
500-second session bound and reserves 1,800 seconds for fallback on every
owner check, including delayed entry after initial admission.

The 300-second logger closes before the final health observation. A health
snapshot before that wait cannot prove health at session completion. Action
failure or interruption remains FAIL even with successful independent cleanup;
`healthy_target_with_cleanup` additionally requires logger-child closure.
Failure to publish a health diagnostic cannot prevent the existing recovery
owner from running. A failed final result write still raises; no receipt is
claimed when storage cannot publish it.

`test-production-display-session.py` executes the actual session, duplex loop,
supervisor and assembled loader/endpoint fixtures. Logger/loader children and
pipe transport are real; phone I/O, credentials, source admission, health,
staging, module effects and logger time are explicit fixtures. No SSH or sealed
historical import executes. This does not qualify live staging or logging.
The old source pins, health validator, logger and admission closure remain
unchanged and deliberately prevent deployment of this source adaptation.
A matched composition must first qualify those boundaries and firmware-root
lifetime. No new candidate, claim, staging authority or physical PASS is added.


## Production kernel logger (offline only)

`0005-production-kernel-log.patch` applies to the historical `kernel-log.py`
fixture SHA256 `b690ae15bfced9c5cc3c9ab905209dc12dccb909678c31975fe6a32282a18d14`.
The logger snapshots the session's production identity and embeds the exact
verified endpoint source bytes. It calls only the read-only identity method,
then reads `/dev/kmsg`; no display endpoint or device mutation is requested.
Boot, release, a single bundle token and descriptor bytes are checked remotely.
Owner and board hash remain admitted bindings, not newly observed hardware proof.

Input transfer is nonblocking within the existing eight-second readiness budget;
the expanded script is bounded to 32 KiB. Output retains the four-MiB, 64-KiB
frame and 128 kernel-record bounds. Short frame writes fail explicitly.
The local leader stays waitable until the existing supervisor group-stop callback
finishes. PASS requires leader reap and process-group absence, valid complete
logs and no cleanup/publication error. Partial-start interruption cleans owned
resources; each FD is detached before close and each output file is cleaned
independently. Closure retries cannot signal a reaped leader or close a reused
pidfd number. This does not contain descendants that escape their process group.

The session supplies the contract, owner and actual transport stop function and
requires the logger's group proof. Tests execute this connection with local
pipe peers. The remote script's real control flow also runs with explicitly
substituted proc/descriptor reads, kmsg I/O and time; no host or phone kmsg is read.
The historical SSH/source command guards remain unchanged, so this patch does
not make a deployable staging/admission composition. Full-health and staging
integration, firmware-root lifetime and physical qualification remain open.


## Successor full-health protocol (offline only)

`0006-production-health.patch` adapts the existing full-health collector to the
six-field production contract. The inner sealed root/readiness readers retain
their three-field identities; the exact endpoint source verifies the outer
identity before and after collection. Descriptor and current-boot acceptance
receipts must have the same canonical bytes consumed by runtime rollback.
The persistent selection must explicitly be healthy for this trial and bundle,
as well as matching the sealed state hash.

The corrected health helper keeps timers armed. The checker therefore requires
loaded, active waiting/elapsed timers pointing to the guarded rollback services,
quiescent successful services with no additional command hooks, and typed D-Bus
ExecStart values naming only `/run/rog5-native-wifi/runtime rollback`. An active
probe timer running `systemctl reboot` is rejected. This is inspection, not a
service action or containment of an arbitrary privileged process. A service
currently executing is conservatively refused; no retry or timer cancellation
is introduced. The original physical, root, firmware and source-lock guards
remain. The session supplies the same admitted contract/owner to the script and
validator, retaining transport byte hashes, deadline and child-closure checks.

The historical health source is represented by a sanitized fixture. Its only
normalization replaces the private SSH host fingerprint assignment with a
synthetic value; the original source SHA256 is
`738f5d0b6bc6aef9f7b46babd7f53a46103696e8ce9624c21f2454d3de9bcb32`,
and the normalized fixture SHA256 is
`5d8aa3e5e61ebcffdabd3f5b32d90c3c5c5b378866de1df69bff92d7ce5f5940`.
The successor reads the fingerprint from a future private, sealed health input.
Historical private files and input pins are unchanged; this draft cannot be
substituted into their admitted closure. A future composition must bind all new
runtime bytes, exact identity and the required busctl JSON interface. No health
observation, phone contact, candidate or execution authority is produced here.


## Production context and source-only staging (offline only)

Apply `0007-production-context.patch` after0002 to the backend, and
`0008-production-staging.patch` after0003 to the transport. The resulting
backend is SHA256 `e8354b4591d5110224ed5bd4579a82995071d7c98c846567dd387396e2a1a098`.
The fixed cohort is backend, component, endpoint, firmware verifier, provider
verifier and loader source. The historical initializer/provider/query programs
are absent; this stage requests no DRM query or separate GPUCC execution.
The modules, module-once helper and firmware remain independently required
preexisting payload inputs, verified by the loader before one-use entry.

The initial context keeps the root/tmpfs/namespace and consumed-entry checks.
Worker/result/cleanup loading uses the retained canonical manifest binding,
rechecking all six source hashes without treating an already-consumed entry as
permission to skip cleanup. The checked component bytes execute directly; its
pinned dependencies use their existing checked-byte reader. This neither grants
admission nor fabricates observed endpoint identity from manifest fields.

The generated source stager verifies the complete fixed source/manifest input,
RAM parent and actual endpoint identity before writing a new exclusive namespace.
It fsyncs files and rechecks context/identity afterward. Caught failures close
owned descriptors and remove only matching owned inodes; an unknown/replaced
file is preserved. SIGKILL/crash recovery and malicious privileged mutation are
not qualified by these caught-exception fixtures. Existing namespace and evidence
files are never replaced. The caller still owns the host evidence directory.

Host staging preserves the existing worker/SSH credential and source-authority
checks and reserves40 seconds for the35-second command plus forced closure.
The receipt explicitly says Python sources only, modules/firmware not staged,
and no admission granted. The enclosing session supplies its production contract.
No live source closure, health seal, candidate, claim or deployment is issued.
The unchanged historical SOURCE/admission pins remain incompatible until a
separately qualified composition is prepared.

The module archive is3,010,560 bytes; base64 alone would exceed the existing
3MiB transport request bound. This source-only path does not attempt to sneak
that payload through the code channel or enlarge the transfer limit. A future
image/payload composition must bind the already qualified module/firmware inputs.
`test-production-display-context.py` executes the generated script on a temporary
filesystem with explicit root/proc/tmpfs/transport fixtures; it never writes to
actual /run, contacts a phone or loads a kernel module.

## Private caller API repair (offline consumer only)

`0010-private-display-api.patch` applies to the two exact source fixtures
`live-admission-before.py.txt` and `trial-launcher-before.py.txt`, copied under
its `live-admission.py.txt` and `trial-launcher.py.txt` paths. The fixture bytes
contain no unit serial, USB topology, address, credential or boot UUID. They are
source inputs, not admission records; do not import their private top-level
loaders or run their entrypoints. Historical runtime files and pins stay intact.

The patch threads one explicit production contract and owner through ordinary
admission callbacks, health-command policy and session execution. It accepts the
exact ten-path production scope only inside the authenticated input bytes and
recognizes the production session result. Recovery compares the three observed
discovery fields with the contract projection, then separately requires the full
six-field prior health identity. Descriptor, DTB and owner proof are not inferred
from discovery or discarded to make the comparison pass.

Preparation invokes the unchanged source-bound `initialize()` before credentials,
launch entry or claim consumption. Its unreviewed private dependency still refuses.
The historical health seal remains incompatible and cannot be replaced by changing
a consumer hash. Root envelopes, root phase whitelist, one-use guards and fallback
checks are unchanged. This patch is not a cold-boot launcher: an already boot-bound
`HostContract` cannot use a guessed future boot UUID. The authenticated static
artifact/owner producer and its one-time discovered-boot binding remain unqualified.
The omitted boot-health wrapper and controller identity producers need separate
source integration; no execution authority is produced here.

Run `python3 -O scripts/device/test-private-display-api.py`. It assembles the
existing production cohort and applies the caller patch strictly in temporary
ordinary-user directories. It exercises actual caller definitions and composed
session/health functions with explicit inert external effects. All five original
counterexamples are checked before and after the repair. Two named no-effect
initialization fixtures inspect downstream API checks; separate tests execute
the real private-dependency refusal before credentials or claims. The suite is
mandatory in the existing active/CI tiers, with bounded runtime and input checks.
Physical results remain NOT RUN, and the private runtime remains UNBOUND.


## Cold-boot caller and owned publication repair

`0011-production-cold-boot.patch` follows the 0010 caller output and seven
retained downstream source fixtures. The clean-checkout composition and
70-case regression are in `scripts/device/test-production-cold-boot.py`; fixture
normalization and scope are documented in its `fixtures/display-cold-boot/README.md`.
The existing source-cohort assembler remains authoritative.

One static authenticated-input projection binds only after actual discovery of
the intended boot. Discovery is an expectation, not health acceptance. An
exclusive expectation writer retains creation ownership and validates its
closed snapshot. Failed publication can produce an exclusion-only witness for
guarded fallback, never target acceptance. Normal finalization stays inside the
same failure boundary; first cancellation during the final close no longer
escapes before witness/cancellation handling. Original failure and cancellation
remain visible after permitted cleanup/recovery. Uncertain closure, tampering
and consumed recovery phases remain refusals.

This is source integration only. The original runtime, signatures, input locks,
health seals and claims remain untouched. Initialization still refuses the
unqualified private SSH worker before any health or credential operation;
adding a source pin alone cannot qualify its transitive imports.


## Worker source binding and process lifetime

`0012-worker-source-lifetime.patch` composes the reviewed worker/deployed-source
binding, bounded actual Git source-identity observation and pidfd finalization
correction. It applies to the exact sanitized worker fixtures and the existing
assembled session plus public acceptance source. The clean-checkout wrapper is
`scripts/device/test-production-display-worker.py`; its 58 cases and explicit
host prerequisites are described in `scripts/device/fixtures/display-worker/README.md`.

This removes eager unqualified imports from the proposed worker closure, binds
its source reader explicitly and retains a stable group pidfd after leader reap.
The first final-close cancellation propagates after remaining close attempts,
including when the preceding timeout was handled. Uncertain raw descriptor close
is never retried against a reused number. Acceptance compares two bounded actual
Git observations; this is neither an atomic repository snapshot nor a sandbox
for hostile Git repositories.

This remains an offline successor patch. The original source pins, runtime
refusal, signed artifacts, credentials, health seals and claims are unchanged.
Actual private admission and downstream health/capture binding remain UNBOUND.

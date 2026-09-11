# ROG5 current state

Latest r112, 2026-09-11: **GPU fallback observation, state-change callbacks and
authenticated health callbacks pass offline integration**. Previous r111 was
progress. Components are under gpu-live-driver-r1; no live-admission.py or
controller execution directory exists. No phone action, reboot, state/shutdown
write, module load, DRM open or claim consumption ran. Last authenticated phone
health remains r111, same OLED boot at 14754.55 s uptime.

The fallback observer uses the GPU namespace, state records and custody while
preserving the exact 11-file installed V9/V11 inventory and boot_b hash. Its
catalog origin stays bound to the original installed record, independent of the
new trial's OLD state. Eleven ARM64 BusyBox/Rust fixture cases passed in 60.968 s:
pending/healthy observation, completed restoration from both states and negative
boot/readiness/transaction/image/service cases. The observer left selection bytes
unchanged. Physical telemetry and installed-image contents are explicit fixtures.
Thirty-three parser replay cases passed in 0.064 s; legacy V11 readiness remains
honestly unbound when its marker lacks a boot ID. This is not physical fallback.

Seven action callbacks now bind the tested GPU source controls and helper. They
verify the existing consumed RAM-stage preparation and stage receipts with their
actual 0600 metadata, hashes and custody; no duplicate staging or custody copies.
Twenty-seven action/controller cases passed in 7.681 s. Three added custody cases
passed in 0.766 s, rejecting changed preparation, changed stage receipt and writable
receipt before command intent/transport. Source restore, lost reboot reply and
capture-before-recovery ordering retain their original one-use behavior.

Authenticated target/fallback health callbacks use the qualified r111 target
reader and new V11 observer. Twenty-six integration cases passed in 9.986 s,
including stale boot, source mismatch, repeated calls, incomplete capture and
restoration verification. Together: 100 distinct checks. All r110/r111 capture and
health bytes remain unchanged. No build/A01 rerun. Evidence index:
gpu-live-driver-r1/completion-r112.json; keep completed results and consumed claims.

Next adapt the sealed-shell source-abort observer and source-read callbacks, then
complete fastboot/boot and fallback transport routes plus the GPU live driver/
admission. Prepare bounded GPUCC/first DRM open before boot admission. No human
test is ready. Preserve RAM staging; prepare a longer optical window with viewing
instructions before fresh Ready. Optical acceptance remains unobserved.

Latest r111, 2026-09-11: **the GPU capture bridge and target-health component
pass offline qualification**. Previous r110 was progress. Added capture-bridge.py
and capture-root-entry.py under gpu-capture-r1, changing only pinned paths/hashes
from the retained bridge. Ownership, pidfds, cancellation, output bounds and
guardian deadlines remain unchanged. Sixteen bridge/guardian tests passed in
8.343 s; three bridge-plus-supervisor integration tests passed in 4.225 s.
Controller/launcher loss, full output pipes, forced cleanup failure, separate
capture roles and target-to-fallback ordering were exercised with real child
processes. Sudo/root/phone actions remain explicit fixtures.

New gpu-health-r1/successor-health.py binds the GPU identity and custody, with
12 expected runtime files: nine retained health/runtime files and all three A660
firmware files. Exact metadata/content match the final GPU CPIO inventory or
frozen installed-root source plus completed A01. The collector and validator
are byte-identical to the retained implementation. Removed its unreachable
baseline configuration branch; source/V11 health uses separate observers.
Twenty-four health cases passed in 0.465 s, including missing/changed firmware,
unsafe metadata, old OLED identity, stale healthy/ready records, late commit,
unsafe power and writable protected storage. Generated guard shell syntax passes.
These results verify software boundaries, not real GPU initialization.

Fresh authenticated current-source health passed in 1.778 s on unchanged boot
229580f9-ac26-4b18-a0eb-ea9c05bc632f, OLED bundle c371bcc38a6a73fe and
7.1.4-g05941d04803f at 14754.55 s uptime; selection remains b4d203a8...c4d.
This was the only phone action: no mutation, selection/shutdown change, module
load, DRM open or reboot. No build/A01 rerun. All r110 source hashes are unchanged.

Evidence: gpu-health-r1/completion-r111.json; bridge-tests-r1 in gpu-capture-r1;
health tests-r2 and current-source-health-r111 in gpu-health-r1. The complete GPU
live driver/admission and controller execution directory remain absent. Next wire
source-abort/fallback controls and authenticated health callbacks, then prepare
the bounded GPUCC/first-open session before boot admission. Preserve the consumed
RAM staging. No human test is ready; the missed optical window stays unobserved.

Latest r110, 2026-09-11: **GPU boot capture and its controller ordering pass offline
qualification**. Reused the retained r93 continuous-drain fix, with a 1 ms yield
between locked reads so foreground readiness can acquire the pipe lock. The GPU
capture now binds the current OLED source, new GPU target, staged owner/boot,
exact state records and the relay config sealed in the qualified GPU payload.
The controller algorithm is unchanged; only five identity/record constants differ.
Its execution directory has not been created and live boot admission remains false.

72 distinct cases passed: 21 receiver tests in 0.515 s, 22 supervisor tests in
19.355 s, 25 controller-ordering tests in 1.517 s and four GPU-binding tests in
0.716 s. The >1 MiB burst regression passes while the foreground controller is
busy. Real child streams and socket cleanup were exercised; phone transport,
privilege and clocks use explicit fixtures. Receiver tests run with the relay
address and CAP_NET_ADMIN only in a disposable user/network namespace. Success
and late-failure integration cases prove target capture closes before separate
fallback capture. These are not physical reboot/fallback or GPU evidence.

Files: gpu-capture-r1/{capture-common,capture-worker,capture-supervisor,
capture-callbacks,source-read-callbacks}.py and gpu-controller-r1/controller.py.
Evidence index: gpu-capture-r1/completion-r110.json. Preserve these tested bytes.
The worker's operational network-source identity remains frozen f02083f4;
new GPU bindings/controller are separately hash-pinned. Source review and initial
failed fixture logs are retained. Initial failures were incomplete common-engine
bindings and missing namespace network setup; one timing failure preceded the
small drain yield, but its exact cause was not established. The old-relay replay
fixture initially used a wrong path, corrected to the retained payload config.

No phone action ran in r110. Last authenticated phone health remains r109 at
13052.51 s uptime on boot229580f9-ac26-4b18-a0eb-ea9c05bc632f. No claim was
created/consumed, no selection or shutdown write ran, and no reboot occurred.
The r109 RAM-stage entry remains consumed; do not restage it. Host disk had
39 GiB free, RAM 9.2 GiB available, swap 65 MiB used. No large build was repeated.
No human test is prepared or Ready pending. The missed display window remains
UNOBSERVED_OPERATOR_MISSED_WINDOW.

Next connect this capture component to a scoped root bridge and complete the
GPU driver/admission using qualified source controls. Finish exact target-health
bindings and the separately bounded GPUCC/first-open session before consuming
any boot claim. Prepare a longer optical window with viewing instructions before
requesting fresh Ready. The kernel and non-cellular hardware remain the priority.

Latest r109, 2026-09-11: **the GPU state-exchange helper and source controls pass
offline qualification, and their files are now staged in the phone's RAM**.
Previous r108 was progress. Actual RAM staging plus health checks took6.220 s;
the subsequent live read-only source preflight passed in1.127 s. No boot selection,
shutdown installation, helper execution, module load or reboot occurred. The GPU
boot claim remains uncreated/unconsumed; capture/boot orchestration is not admitted.
No human test is prepared, no Ready is pending, and optical acceptance stays
UNOBSERVED_OPERATOR_MISSED_WINDOW.

New helper source is tracked at tools/gpu_state_exchange in
`60fdf9b63049df67d26280375d23804a5050a01d` (gpu-admission-worktree-r1). Its algorithm is
identical to the tested atomic exchange: only exact embedded records, transaction/
intent names and diagnostic labels changed. It uses .gpu-05941-transition and
preserves the kernel/OLED/startup transaction namespaces.16 native cases and
Clippy passed. ARM64 static-PIE twins match at1253144 bytes, SHA
`83bdab961e5bc5bd1456a02a8301b5e904e9806f9091e0da91e0f1dcde3d96cc`.
The ABI checks include rejecting the wrong ARM64 open flags. Six isolated
interoperability scenarios executed17 operations with the retained v1/v2 trial
helpers, including healthy marking, restoration of the original inode and
refusal after lost replies;0.574 s. Builds took1.012/1.029 s, each under512 MiB,
no swap and one CPU. All owned build containers exited and were removed.

The new guards preserve the original power, device, partition, mount and custody
checks and additionally verify the actual four-file startup transaction.38 ARM64
fixture cases plus6 generator refusals passed in121.496 s. Source actions use the
observed OLED service states, including the active/exited healthy service;
21 cases plus4 generator refusals passed in329.853 s. They cover installation,
restoration, lost/partial replies, locks, replacement races and exactly one reboot
request. Seven RAM-stage cases passed in29.373 s, preserving all persistent files
and refusing partial/duplicate staging. These are explicit fixture tests, not
physical reboot/fallback evidence. The existing kernel, wrapper and A01 were reused.

Actual staged namespace:
`/run/initramfs/rog5-gpu-05941-eb7eb2d66a88422790d765655143768d`.
Owner `eb7eb2d66a88422790d765655143768d`; host custody receipt
`94aa13ff7ec74d5ece82f94c1b627601d7b7e23e85898cfc25dfc6e9fb311f2b`.
Host entry gpu-ram-stage-r1/live-stage-r1 and its stage-once.py are consumed;
never rerun them. The staged inventory is state-exchange, shutdown-to-fastboot,
custody and staging-completed. The existing reboot helper is reused. Post-stage
health passed on unchanged boot229580f9-ac26-4b18-a0eb-ea9c05bc632f, current OLED
bundle/kernel and b4d203a8...c4d selection at13052.51 s uptime.
The actual source preflight verifies the staged files, current service states,
shutdown, restart provider, absence of a GPU transaction and fresh file locks.

Evidence index: gpu-state-exchange-r1/completion-r109.json. Source guards live in
gpu-state-guards-r1; source actions in gpu-source-actions-r1; staging evidence in
gpu-ram-stage-r1. Keep the tested bytes and completed cases. Next prepare the
remaining capture/boot/recovery orchestration and fresh target-health bindings,
then the separately bounded GPUCC/first-open session, before consuming any boot
claim or changing the phone's selection/shutdown. No request for operator
availability belongs before all preparation is complete.

Latest r108, 2026-09-11: **GPU-specific boot guards and the exact current-source
transition bytes are prepared and tested offline**. This is progress from r107;
the live controller is still unprepared. No reboot, module load, display command,
selection write or claim consumption ran. The missed optical window remains
UNOBSERVED_OPERATOR_MISSED_WINDOW; no human test is ready and no Ready is pending.

Fresh authenticated health passed in1.777 s on boot
229580f9-ac26-4b18-a0eb-ea9c05bc632f, OLED bundle c371bcc38a6a73fe,
7.1.4-g05941d04803f, uptime11842.52 s. Selection remains b4d203a8...c4d.
The phone's10354-byte shutdown script exactly matches retained
initramfs/persistent-root-shutdown-standalone, SHA fc1ce027...860. Its existing
1600-byte root-owned executable reboot helper matches68d6a69e...785.

Admission worktree: gpu-admission-worktree-r1, clean revision
`25de2ea1bbbd83ba2a9977ca40307e0635fed9cd`. The new verified-gpu-hardware-boot.py binds the
completed6956875b/A01 result, exact GPU profile/image, current source boot and
selection, device/slot and V11 fallback. It uses a distinct gpu-source-05941-r1
expected claim, requires durable consumption before dispatch, and bounds fastboot
to90 s while closing the sealed image on failure/timeout. All228 prior expected
claims remain byte-identical. No actual claim record was created or consumed.
The compiled kernel, completed A01, integration source and current live driver
remain unchanged; this admission worktree is the place for the next controller work.

prepare-gpu-source-transition.py produces exact source/pending/healthy records and
a shutdown variant changing only the final normal reboot dispatch to the existing
bootloader helper. Teardown, relocking, poweroff and emergency-reset bytes stay
unchanged. Pending SHA5c74582a...25d1; healthy813f108a...b4b4; shutdown variant
0ee47fb5...84ca. These files exist only on the host, under
gpu-admission-prep-r1/transition. Do not install them without the complete controller.

46 distinct checks passed:9 boot boundaries (including timeout closure),7 shared
RAM primitive,21 claim lifecycle,5 transition checks and4 ARM64 selector replays.
The installed selector function/helper chose V11 for GPU pending, GPU healthy and
current OLED healthy records without changing those records. Its original V9
healthy case also passed. Replay took0.443 s with explicit storage fixtures;
this proves the decision, not physical fallback boot. No kernel/wrapper/A01 rebuild.
Evidence: gpu-admission-prep-r1/completion-r108.json and source-health/result.json.

Next implement the exact state exchange/custody and source exitrd actions, then
complete bounded capture/recovery orchestration and the separately recorded GPUCC
load/first-open session before boot admission. Reuse the existing verified reboot
helper; do not stage another copy unnecessarily. The old V11-starting controller
is incompatible with the current OLED source, and its consumed run stays retired.
Prepare a longer optical session separately with viewing instructions before Ready.

Latest r107, 2026-09-11: **the GPU candidate passed complete offline A01
composition qualification**. Previous r106 was progress: the verified wrapper
is now integrated with the exact Arch roots and module/runtime checks. No phone
action ran. Optical result remains UNOBSERVED_OPERATOR_MISSED_WINDOW; no human
test is prepared and old Ready replies/consumed launches must not be reused.

Integration source is frozen at
`6956875b0a18dfc51eb651edbf2d4c31c38c1280` in gpu-integration-worktree-r1.
The existing operational OLED controller stays frozen separately at f02083f4.
New composition profile: configs/composition/gpu-05941-v1.json, SHA
`5d8dbaa7a2db9e6084ae9d9230e69496e13aea95619ca686bad00b934e0411e4`.
It binds the r106 wrapper, r105 payload/DT, manifest/signature, module inventories,
fresh descriptor/relay nonce and all ten added firmware/license members. Mixed
old/new artifact tuples refuse. Physical GPU qualification remains explicitly false.

The radio checker previously allowed only the six WCN6855/regulatory firmware
files under the shared directory. It now accepts the registered GPU profile's
three separately sealed A660 members only after exact metadata/content checks;
all other extra firmware still refuses. The Wi-Fi manifest/inventory remains
unchanged and strict. The same profile reaches the QEMU fixture, whose default
radio-firmware copies still use only the six radio files. The new regression
cases cover missing/altered GPU bytes, ownership/link changes, extras, wrong
profile, mixed artifacts, false hardware claims and changed Wi-Fi data.

78 focused cases passed:7 GPU-profile,59 rescue-composition,3 release-composition,
9 existing OLED-profile. Initial failures are preserved: the fresh checkout had
not yet received five ignored, pinned wrapper prerequisites, and one old fixture
incorrectly assumed a historical profile could never have a real claim. Staged
and verified those prerequisites; made that fixture isolate only its in-memory
claim registry and prove the real registry is restored. Production claim checks
remain unchanged. Added the GPU suite to the existing repository test list.

Actual A01 result: gpu-a01-r1/a01/result.json, PASS with a01_qualified=true and
release_qualified=false. All seven checks pass: wrapper, signed target, archive,
root runtime, module load, firmware and timing transport. Result SHA
`d4f569761fafee855e3b404f9942e15a72fae411a2b8257bcf4594364081a193`.
The exact-kernel QEMU run completed and both retained ext4 lower/upper images
remained identical before/after. Source remained clean and unchanged. The GPUCC,
GPI, GENI I2C and touch modules passed software registration only; no ASUS GPU,
DMA/I2C endpoint, touch hardware, firmware authentication or acceleration was
simulated or accepted.

A01 took82.835 s (checker82.426 s), with1.9 GiB reported peak under a3 GiB/no-swap
limit. Sparse logical hashing still covers the entire32 GiB lower and16 GiB upper:
lower25.266/23.227 s and upper11.268/11.076 s before/after. Existing kernel,
modules, wrapper and VM activation fixture were reused. No expensive unchanged
build or unrelated full test suite was repeated.

Evidence index: gpu-integration-qualification-r1/completion-r107.json; focused
results and preserved initial logs live alongside it. Runtime/complete proof is
in gpu-a01-r1. This completes offline composition, not the per-device boot claim
or real-phone GPU acceptance. Next prepare a distinct one-use RAM-boot admission
and capture flow from the current healthy OLED boot, including fallback and the
subsequent GPUCC/first-open session. Prepare a longer optical window separately,
with viewing instructions before requesting Ready. Do not mutate either frozen
source tree or rerun already-completed A01 without changed inputs/new evidence.


Latest r106, 2026-09-11: **the GPU candidate now has matching recovery-wrapper
twins with verified embedded signatures, payload bytes and AVB footers**. Previous
r105 was progress: its exact payload/DT inputs are now packaged. No phone action
ran this turn. Optical outcome remains UNOBSERVED_OPERATOR_MISSED_WINDOW; no
human test is prepared and no older Ready or consumed command may be reused.

Accepted packaging output: gpu-boot-package-r2/result.json, PACKAGING_TWINS_PASS.
Bundle gpu-05941-52181a3157c26029 contains the unchanged exact05941 kernel, the
qualified five-property GPU DTB delta and the r105 firmware-bearing archive.
All bundle files, signatures, recovery archives, raw images and AVB images match
between sides. The existing sealed verifier returned SEALED_PLAN_PASS; both
AVB checks passed. Embedded manifests use Ed25519; the outer AVB footer retains
algorithm NONE. This is offline signature/byte composition, not boot admission,
root-content qualification, secure-boot certification or GPU hardware acceptance.

Recovery archive:80290874 bytes, SHA
`24c5c068e9649528cf3b7ca6667f61afe400ace266df7fdcfab7659be23157ca`.
Raw Android boot image:130797568 bytes, SHA
`5362122fff7e85b5fcd0809589d485f04f2b8d7654d9b9a74c3f06c8e486c99f`.
128 MiB AVB image:134217728 bytes, SHA
`7dce52c48e23f1adfeaa719c199453a9073bb6fe6469a580469445d90697f9d6`.
Manifest SHA:
`2dc065be228fe4cee9a4c791d6d06abd2b17a23d4a8533beb8b70eeecfa8497a`.
Signature SHA:
`6d70117f1faa46bfb852c2ae0646d100610340e286f59034cf5b7ddf305ff760`.
The96 MiB envelope was too small; measured AVB capacity admitted128 MiB.

The first attempt, gpu-boot-package-r1, remains FAIL_SCOPED_MEMCG_OOM. It ended
at9.525 s during repack-a in its512 MiB/no-swap service. Kernel evidence identifies
110166016 anonymous bytes,414613504 file-cache bytes and405987328 dirty-file
bytes at the limit; this was a memory-cgroup OOM, not a system-wide incident.
The first signed bundle, recovery archive and canonical sizing raw were already
complete. Their exact bytes were pinned and verified before reuse. The partial
boot-a.raw.img.tmp was excluded; old failure/source artifacts remain preserved.

The successor in gpu-boot-resume-r1 reuses completed side A and independently
composes side B. It flushes generated files and releases their clean cache pages
between tool stages, avoids rebuilding the canonical raw image a second time,
and verifies extracted kernel/recovery bytes plus all original boot-header and
command-line arguments. It changes no key, root selection, wrapper source or
rollback policy. Eight wrapper-contract cases and seven continuation cases
passed. Initial inspection passed without opening the private key. Resume took
48.865 s; service50.120 s; file writeback accounted for5.775 s. All commands and
cleanup checks passed under the same512 MiB/no-swap cap. Reported peak still
reached512 MiB, so do not claim spare memory headroom or a general OOM cure.
No unchanged kernel, module or payload build was repeated.

Evidence index: gpu-boot-resume-r1/completion-r106.json. Contract/input evidence
is in gpu-boot-package-prep-r1; failed original evidence is preserved there and
in gpu-boot-package-r1. Successful output is exclusively gpu-boot-package-r2.

Next: register the exact new composition profile in an isolated successor and
run root/wrapper/activation composition qualification, preserving all frozen
sources and fallback artifacts. Then prepare the GPUCC and first-open session
with logging/recovery. The wrapper is not ready for phone boot yet. A separate
longer optical session still needs preparation with viewing instructions before
Ready. Retain the missed-window observation and every consumed entry.


Latest r105, 2026-09-11: **a distinct GPU candidate now has reproducible
unsigned initramfs payloads paired with the verified GPU DTB**. Previous r104
was progress: its component is now consumed by actual payload composition.
The user reported **"I missed the display window"** for r103. Optical outcome is
UNOBSERVED_OPERATOR_MISSED_WINDOW, not PASS or evidence of a black screen. The
reply is bound to the visibility receipt in show-r1/operator-observation-r105.json.
All r103 command, cleanup and health evidence remains unchanged. The intervening
Ready was not used to rerun the consumed launch; no new human test is prepared.

The read-only phone check found the current firmware_class search path is
/run/rog5-native-wifi/firmware. Arch has /lib -> /usr/lib, but no /lib/firmware
currently exists. The early-root map from r104 alone would not preserve firmware
through switch_root. Composition therefore uses the existing init source move
/rog5-native-wifi -> /run/rog5-native-wifi and the existing Wi-Fi search-path setup.
The three firmware files are added under rog5-native-wifi/firmware/qcom, with
licenses under rog5-native-wifi/licenses/a660, so both remain in retained RAM.
No init/runtime source or firmware_class setting was changed. This live-path and
matching-source binding supersedes direct use of r104's early-root-only map.

New bundle: `gpu-05941-52181a3157c26029`.
Trial: `52181a3157c2602983ca172999a2f4edc4bb351cb30d4ec5fa9cc6d629a245d4`.
Profile SHA: `585ea829d528dc4340c5051342cf506c76bc43139a6df699e435485a8198526c`.
Twin initramfs size58612856 bytes; SHA
`c253b28aa5db0382fcfe96bb5bf581f1009fff3256c5ba13c589552fc4c489f4`.
Paired GPU DTB SHA
`5ce36eecfe49601034e89cb3d98536e3d558b1399d2576004f5eb1aba713b89b`.
All736 member records match between twins. Six regular files plus four directories
were added. Only the trial descriptor, boot-file catalog and relay configuration
changed among existing members; the descriptor and relay nonce are fresh. Exact
metadata/content preservation and roundtrip checks passed. All32 loose module
copies and the complete nested module archive remain unchanged. The retained DT
validator again proves exactly four dependency status changes and the ZAP name;
all other property bytes and boot/reservation metadata remain intact.

Eight focused tests passed. Compositions took4.811 and7.005 s in separate512 MiB,
no-swap scopes; both exited successfully with336.1 MiB reported peak memory.
420444688 bytes of newly generated scratch were removed only after each blob
matched content retained in the pinned original/candidate archives. Archives,
DTBs, inventories, source files, receipts and profiles remain on disk.

This is unsigned payload composition, not a bootable recovery wrapper or phone
GPU acceptance. GPUCC remains inert for a separately supervised load; enabling
its DT node does not load the module. Next qualify a fresh recovery wrapper and
composition profile, then prepare GPUCC and first-open observation with recovery.
No new kernel build, signature, boot claim, reboot or flash occurred. The only
phone operation was an authenticated read-only path inspection on the unchanged
boot229580f9-ac26-4b18-a0eb-ea9c05bc632f. Last full health is still r103.

Evidence: gpu-successor-payload-r1/twins-result.json, both composition results,
focused-tests.json, firmware-path-transport.json, profile.json and scratch-cleanup.json.
After-run lessons: check firmware visibility on both sides of switch_root, not
just the early-root archive. For the next visible test prepare a longer bounded
window and give all viewing instructions before requesting Ready, so the user
can watch the phone immediately. Prepare and validate that distinct session
fully before asking again; no current readiness or old launch may be reused.


Latest r104, 2026-09-11: **the retained A660 firmware now has a reproducible
component package and an explicit early-root install map**. Previous r103 was
progress: the real-phone timed command sequence, cleanup, log and health passed.
Its actual optical observation remains pending. The r101 display launch remains
consumed; no currently unconsumed human test is prepared. No phone action ran in
r104, and no boot image, current profile or frozen display source was modified.

`gpu-firmware-package-r1/a.tar` and `b.tar` each contain1658880 bytes and have
identical SHA `83fab937d3b02b295ec42ea389fe13f189d8ac619f1c9241b4e674f7e69d1c53`.
The deterministic USTAR component carries all three previously pinned A660
firmware files plus LICENSE.qcom, NOTICE.qcom and WHENCE from linux-firmware
commit b2722d241309a1872446c1d00c2e812bad055f89. Metadata uses root ownership,
0644 files,0755 directories and the existing epoch1681862400. Streaming input
verification and exclusive publication prevent corrupt/partial input or an
existing output from silently becoming an accepted package. Twin creation took
0.028 s; independent tar inventories/extraction hashes and six refusal cases
passed in0.062 s. No download or kernel/DT rebuild was needed.

The0.484-second install-map audit caught a concrete integration issue: the exact
726-member early-root archive has separate real lib and usr/lib directories.
The matching kernel searches /lib/firmware; a usr/lib-only insertion would not
satisfy that lookup. `boot-install-map.json` therefore maps the component's three
usr/lib/firmware members to lib/firmware in the future newc archive. It preserves
the license paths under usr/share/licenses and proves no destination currently
exists. The Wi-Fi probe sets a custom firmware_class path; preserve it, since
standard /lib/firmware fallback remains available. This is a component and merge
recipe, not an already-integrated or deployed image.

GPUCC is already packaged inert with no module dependencies; COMMON_CLK_QCOM,
QCOM_GDSC and QCOM_CLK_RPMH are built in. This does not prove runtime clock/power
readiness. Next compose a distinct successor with the verified firmware map and
retained five-property GPU DT change, review GPUCC activation and qualify the
result before a controlled first GPU open. Firmware authentication, GPU startup,
accelerated Mesa, touch and Denial remain unverified. Continue to preserve stock
slot A, signed fallback and every consumed entry.

Evidence: `gpu-firmware-package-r1/result.json`, `validation.json`,
`boot-install-map.json` and their pinned producer sources. After-run improvement:
inspect the actual early-root library topology before selecting firmware paths;
retain a small verified component and explicit map so future composition reuses
these bytes instead of recovering firmware or rebuilding unchanged kernel inputs.


Latest r103, 2026-09-11: **the prepared visible command sequence, cleanup,
kernel recording and final health passed after a fresh user Ready**. The actual
screen-observation reply is still pending. Do not count command/readback success
as optical acceptance. No further physical action or countdown is running.

**The r101 launch is now consumed. Never rerun prepared-visible-run-r101.json,
show-r1, or the target marker /run/rog5-oled-visible-validation-r1-entered.json.**
Preserve all executed sources, old failures and one-use entries. The r101/r102
waiting and launch instructions below are historical and superseded by r103.
No currently unconsumed visible session is prepared.

Ready-to-visible receipt took 4.926 seconds; the observation prompt was submitted
immediately after that receipt was read. The messaging tool supplies no persisted
delivery timestamp, so exact UI-delivery latency is not independently measured.
All 10653696 framebuffer bytes matched the cached pattern after 11 writes in
1.453 seconds. Brightness32/1023 was commanded for 20.008 seconds with 72 owned
state samples. The component completed in 22.796 seconds. Independent cleanup
restored KD_TEXT and brightness0; both target workers and SSH were reaped.
The complete 90-second kernel log contains zero new records. Full health passed
at 9081.12 seconds uptime on unchanged boot
`229580f9-ac26-4b18-a0eb-ea9c05bc632f`. Total Ready-to-final-health: 94.148 seconds.
No module load, reboot, flash or GPU enablement occurred.

Evidence: `oled-startup-visible-host-r1/show-r1/result.json`, `visible.json`,
`ready.json`, and `oled-startup-experiment-r1/visible-run-summary-r103.json`.
The original frozen coordinator result correctly retains physical_scanout_verified
false. Save the actual operator reply separately, bound to the visible receipt
hash; retain command evidence unchanged. If the report is black/partial/wrong,
use it to choose the next diagnostic before preparing another human test. If the
report confirms the complete upright pattern, record that narrow optical result;
it does not establish GPU acceleration, touch or Denial operation. The offline
GPU input audit from r102 remains valid. The contemplated firmware packaging work
was interrupted before any package was created so fresh Ready could run at once.

After-run improvement: immediate prepared execution worked without new staging,
rendering or builds. Keep that workflow and record its measured latency. Retire
the consumed launch prominently in the authoritative state and checkpoint now,
avoiding accidental reuse of the older waiting paragraphs during handoff.


Latest r102, 2026-09-11: **offline GPU input binding advanced while the
r101 visible test remains fully prepared and unentered**. This continuation
was not a fresh user Ready, so no phone command or physical test ran. On an actual
fresh Ready, immediately follow the r101 launch instructions below; all launch,
source, cache and prepared-record pins remain unchanged.

The current OLED profile pins the same display DTB used by the already-qualified
GPU proposal: base SHA `2ee1ed4b43083bb7e50631269009107efbe0ffed89207acce3c8066f6ba9e4df`.
Rechecking the retained candidate proves exactly four dependency status changes
plus the ZAP firmware name; all other properties and boot/reservation metadata
are preserved. Every retained composer/test/parser source hash still matches its
qualification. No DT rebuild or repeated legacy test suite was needed.

All three A660 firmware files remain locally verified (1153192 bytes total).
A streaming inspection of all726 members of the exact58 MB packaged initramfs
found none of a660_sqe.fw, a660_gmu.bin or a660_zap.mbn. This claim is scoped to
that boot archive, not every mounted runtime filesystem. The audit records exact
sources, hashes and intended usr/lib/firmware paths for a separate successor.
Current config has MSM, SCM, ARM SMMU/QCOM, RPMh, AOSS and LLCC built in; GPUCC is
a module already packaged inert. A GPU successor still needs firmware placement,
GPUCC activation/dependency review, fresh qualification and controlled first-open
validation. Enabling nodes alone is not GPU acceptance. No image, boot profile,
DT source, module, phone state or prepared visible artifact was changed.

The bounded streaming audit took0.502 seconds, reusing the qualified DT and
firmware rather than rebuilding. Evidence: `gpu-current-boot-inputs-r1/result.json`,
`audit.py`, and `retained-source-verification.json`. Prepared r101 is still the
next operator action; do not execute old commands or infer readiness from an
automatic goal continuation.

Latest r101, 2026-09-11: **the visible test is fully prepared and waiting
for a fresh user Ready**. Previous r100 was progress: exact real-phone framebuffer
readback passed under graphics ownership. The current turn completed the visible
integration, 47 focused cases, protected RAM staging, actual cache/input preflight
and health. No display session, mode transition or pixel write ran during r101
preparation. No operator-response countdown is running.

On the next fresh Ready, immediately execute the exact `argv` from
`oled-startup-experiment-r1/prepared-visible-run-r101.json` once. Do not build,
render, stage, generate code or debug after Ready. Only the brief current health
check, logger arming and prepared runtime belong then. Never reuse an older Ready.
Launch record SHA:
`773ed0abc74d3b29f9f91878fe6b6b48446326ba0a30180844d59b67df516f7a`.
Prepared record SHA:
`bddf581b86b241ea55ef82cf957e42f8f4c7105e33aa5191d3d1f6c9dbbde391`.
Host SHA:
`38e2d2c612cc6c8516856ac316a1708a86b6e1baf03d8e3e9d04cfda38b0907b`.
Qualification SHA:
`867ca6f7da5be8669157c5c1df7ceadd700c5f22225303cde5f1e1eea689ad7f`.

The host is `oled-startup-visible-host-r1/coordinator.py`; target assets are
`oled-startup-visible-session-r1`. Preserve these staged/qualified sources. Local
`show-r1` is absent. The prepared namespace is
`/run/initramfs/rog5-oled-visible-94de6f9a33d034351e972e56a61f5e2f7c45236e5eeb5243bf583616cb6262ed`.
The new target one-use marker is `/run/rog5-oled-visible-validation-r1-entered.json`;
all r98/r99/r100 and older markers remain consumed and preserved.

As soon as `oled-startup-visible-host-r1/show-r1/visible.json` appears, give its
single physical observation prompt before `observe_before_monotonic`: look for
an upright TOP arrow, colour bars, corners and centre cross. The user only watches;
keep USB connected, with no button/password action. Save their actual reply with
the visible receipt hash. A command/readback PASS is not optical acceptance.
Keep the same execution handle through cleanup, 90-second kernel recording and
final health. If the session refuses or fails before a prompt, release the user
immediately and investigate independently; never rerun the consumed command.

The corrected writer is unchanged from r100. Cache restore and display share
the exact same Frame class. A combined durable intent binds console transition,
frame digest/bytes and brightness32/1023 for20 seconds. Zero brightness is required
through capture/write setup. Only the display's new begin-light callback, after
successful pixel readback and final blank/ownership checks, permits the owned
lighting phase. Graphics ownership remains checked while lit. The worker has a
35-second action budget and40-second supervisor lifetime, with a three-second
renewable host lease. Host entry must follow Ready within30 seconds; arming must
begin within15 seconds. Independent cleanup restores original console mode then
zero, including after action/monitor/prompt failure. Full worker failures are
retrieved as structured evidence when present.

All47 focused cases passed:12 VT/phase,6 frame-binding,16 display-sequence,
5 Ready lifecycle,8 real-fork/duplex. Tests cover wrong/missing visibility events,
expired Ready, consumed show, phase refusal, wrong frame/boot, uncertain brightness
writes and cleanup failures. Direct display cases use the existing sealed-frame
pipeline and virtual clock; unchanged inherited tests and the already-qualified
real20-second timer were not repeated. Focused suite times were0.121,0.163,4.111,
1.433 and3.011 seconds. The initial display fixture invocation used the wrong UID
namespace and remains failed; correcting the invocation preserved production
permission checks. The new `run-focused-tests.py --plan` records the correct host
or root-mapped context per suite and its five-job plan was checked without
rerunning unchanged tests.

Actual preflight took0.276 seconds: sealed cached bytes and current framebuffer
GET record match, tty1 remains KD_TEXT and brightness0. The frame is10653696 bytes,
SHA `859231dae5b6f5c8c80361a0cfcf748cd605f662ee3e9722ab8fda0f377276a8`.
Final full health passed at8081.64 seconds on unchanged boot
`229580f9-ac26-4b18-a0eb-ea9c05bc632f`; no phone reboot, module action or flash.
Final local launch validation took0.004 seconds. Evidence is indexed by
`oled-startup-experiment-r1/visible-preparation-summary-r101.json`.
The next milestone is actual optical observation; GPU acceleration and Denial
acceptance remain outstanding. Do not execute any older prepared command.

Latest r100, 2026-09-11: **the corrected framebuffer write/readback passed
on the phone under graphics-mode ownership**. Previous r99 was progress: its
real-phone transition and restoration qualified this combined experiment. No
operator availability was requested. The visible test is not yet prepared;
there is no Ready prompt pending.

The unchanged cached Rust pattern was restored into a sealed memfd without
rendering. A distinct durable entry bound the exact VT transition and frame
identity before either mutation. With tty1 in KD_GRAPHICS, the writer completed
11 writes and read back all 10653696 bytes. The SHA matched exactly:
`859231dae5b6f5c8c80361a0cfcf748cd605f662ee3e9722ab8fda0f377276a8`.
No byte/channel was ignored. Write/readback took 2.062 seconds; the exercise with
graphics hold took 4.268 seconds; target supervision and cleanup took 4.661
seconds. Current console ownership was checked during every write/read chunk.

Independent cleanup restored KD_TEXT and brightness zero. Both workers and SSH
were reaped. The 30-second kernel recording closed naturally with zero new
messages. Full health passed at 7205.96 seconds on unchanged boot
`229580f9-ac26-4b18-a0eb-ea9c05bc632f`. Active DRM and framebuffer layout remained
1080x2448 at 60 Hz. No nonzero brightness request, module action, reboot or flash
occurred. This is real framebuffer-memory write/readback acceptance; it is not
proof of optical scanout, damage completion, vblank or GPU acceleration. Text
restoration may redraw pixels, so do not assume the pattern remains intact.

This controlled successor used the same cached pattern and framebuffer capture
as the failed r98 text-console run. Successful all-byte readback with KD_GRAPHICS
supports console interference as the earlier mismatch cause. The old failure
remains FAIL and all consumed markers remain intact.

Executed sources are frozen in `oled-startup-vt-frame-session-r1` and
`oled-startup-vt-frame-host-r1`. Combined lease SHA:
`759a08ecff4fff55957637a29142653e78b1c260128bdb5e7133e64f146d2b45`.
VT action lease SHA:
`c64213c7b8309808f4e92adf0c5dc073e1a13bc1d3bd05c37b0e96dbf3b1c180`.
Host SHA:
`3097bb49bbe0d70f8a4af1123c8ba67c9b30826599c2de4672eab1a22c8d6bed`.
Qualification SHA:
`fb4ed3fd4c061405aa994b741d1f09b80f0a5d45a58c207686b1172cc508f487`.
The r100 host run and `/run/rog5-oled-vt-frame-validation-r1-entered.json` are
consumed. Never rerun `launch-r100.json`; preserve r98/r99/r100 exact results and
entries. Evidence and exact namespace are in
`oled-startup-experiment-r1/vt-frame-readback-summary-r100.json`.

Ten VT/action cases, seven frame-binding cases and five real-fork/duplex cases
passed. They cover combined entry refusal, wrong cached intent/boot, mode or
host-lease loss, writer/readback failures, independent restoration and repeated
entry refusal. Unchanged cache, renderer, writer and console components retain
their prior matching-source tests; no large build or rendering was repeated.

Next: prepare a distinct visible session around this qualified ownership/write
path and the fixed 20-second brightness32/1023 component. Stage and validate
all artifacts, cache and actual IO before asking Ready. After fresh Ready only
brief current health/logging arming and the prepared session may run. Extend the
owned action deadline for the display interval; bind the brightness/duration
into the durable combined intent; allow nonzero brightness only in the owned
display phase, while preserving zero requirements during capture/write setup.
Keep a single matching Frame class instance through cached restore and display
writer. Queue the physical prompt immediately after the acknowledged nonzero
readback, then restore console and zero independently. The host must retain a
fresh Ready receipt, one-use show entry, complete kernel log and post-health.
Do not reuse the old failed show command, rerender after Ready, or count this
unlit success as the required human optical observation.

Latest r99, 2026-09-11: **real-phone graphics-mode ownership validation,
console restoration, kernel recording and final health all PASS**. Previous r98
was progress: its failed readback and console diagnosis changed the next action.
No operator availability was requested or consumed in r99. There is no prepared
visible test yet. Do not rerun the closed r99 VT experiment or any old frame run.

The phone entered KD_GRAPHICS on its existing tty1 descriptor, retained the same
framebuffer GET record and active DRM 1080x2448 at 60 Hz, and held graphics mode
for two seconds with nine state checks. The exercise took 2.281 seconds; target
supervision including independent restoration took 2.567 seconds. A separate
cleanup worker restored the original KD_TEXT state and then confirmed brightness
zero. Both workers and SSH were reaped successfully. The 30-second kernel log
closed naturally with zero new messages. Final full health passed at 6667.06
seconds on unchanged boot `229580f9-ac26-4b18-a0eb-ea9c05bc632f`.

There was no application framebuffer pixel write, nonzero brightness request,
module insertion, reboot or flash. KD_TEXT restoration can redraw console pixels;
zero application writes is not a claim that framebuffer memory was unchanged.
This proves the bounded console transition/recovery boundary, not corrected
pattern readback or optical scanout. GPU/GMU remain disabled on this boot.

The parent retains a checked tty1 descriptor across the action and cleanup forks.
A fixed durable VT entry precedes KDSETMODE. The action requires the authenticated
host's three-second renewable lease and has a 15-second supervisor deadline.
Action failure, EOF or lease loss triggers independent restoration and zero
cleanup after reaping the action. Cleanup attempts zero even if mode restoration
fails, and such a failure remains FAIL. Eight component cases and five real-fork,
duplex-host cases passed; the existing eight console-discovery cases are inherited
by unchanged source. Focused recorded runs took 0.116 and 2.712 seconds. Actual RAM
staging validated all source hashes, protected namespace and the closed failed
frame predecessor before any mode transition.

Executed sources are frozen at `oled-startup-vt-session-r1` and
`oled-startup-vt-host-r1`. Lease SHA:
`a04cc08f8e5f5e2ffa317eb07385dc9d129eeb42418c5dd93f01bafebb782577`.
Host SHA:
`90bd9aab5fc037d26a4bd6e6cf87e7e62e7720ba8590e0037828ede78173639d`.
Qualification SHA:
`14dd3d974dcc0c35fa8fa181c8c89bf6f52317bdc297a51b27603e6947505226`.
The host `run-r1`, its hardware phase, and target
`/run/rog5-oled-vt-validation-r1-entered.json` are consumed. The old frame entry
and all older failed results remain intact. The shared frame lock continues to
exclude competing display work. Evidence and exact RAM namespace are in
`oled-startup-experiment-r1/vt-validation-summary-r99.json` and the host result.

Next: integrate the qualified console lease into a distinct unlit cached-frame
write/readback experiment. The r97 cached capture equals the actual r99 captures,
so its sealed-pattern bytes can be reused after fresh validation; no rendering
or kernel build is justified yet. Reserve an explicit successor frame intent,
keep the failed frame marker, compare every byte, and restore console/zero in
independent cleanup. Only after this actual corrected readback, reviewed/staged
visible-session preparation and health checks should a new Ready be requested.
The r98 cursor-cell cause remains strongly indicated; successful KD_GRAPHICS
transition alone does not prove that it fixes the pixel mismatch.

Latest r98, 2026-09-11: **the prepared frame test ran once and failed readback
before illumination; cleanup and current-boot health passed**. Fresh Ready was
used immediately; runtime arming preceded frame exchange by about2.6 seconds.
The user was released from watching. No physical prompt is pending, and no new
physical test is prepared. **Never execute `prepared-frame-run-r97.json` again.**
The host `oled-startup-frame-host-r2/show-r1` and target global frame entry are
consumed. Preserve executed r2 sources and the failed result.

The writer completed11 writes totalling10653696 bytes and read the same number
back in0.762 seconds, but the digest differed. Nonzero brightness was never
attempted; independent cleanup confirmed0 and reaped target/SSH. Show remains
FAIL. The90-second logger was cancelled after failure, retained one kernel
warning and is incomplete/FAIL. No module reload, reboot or partition flash
occurred. Full health passed at5552.97 seconds and, after read-only diagnostics,
at5684.19 seconds on unchanged boot `229580f9-ac26-4b18-a0eb-ea9c05bc632f`.
There is still no optical scanout or accelerated-GPU acceptance.

A0.193-second read-only comparison against the pinned cached frame found exactly
128 differing bytes: byte3 of eight pixels on each of16 rows, x104..111,
y48..63. `/dev/vcsa1` reports cursor column13,row3 with135 columns and153 rows
on1080x2448: the altered8x16 region exactly matches its cursor cell. Active tty1
is `KD_TEXT`, fbcon is bound, and `cursor_blink` is0. **Console drawing is strongly
indicated; a blinking cursor is not established.** A controlled ownership
experiment is still needed. Preserve all bytes in the readback check rather than
ignoring the changed channel. The expected digest is
`859231dae5b6f5c8c80361a0cfcf748cd605f662ee3e9722ab8fda0f377276a8`;
post-failure readback is
`a465f009aa96cc175a443845e0eff57792c90211d4a940616a64289cd7dd7cf3`.

The kernel warning is `fb0: Framebuffer is not in virtual address space.` Exact
local source shows `fb_sys_read`/`fb_sys_write` warn when FBINFO_VIRTFB is absent
and then continue copying; the warning alone does not establish the mismatch
cause. MSM uses those system-memory operations. `fbcon_blank` cancels cursor
work on a mode switch, while `vt_kdsetmode` invokes blank/unblank transitions.
Review these effects when preparing the graphics lease and restoration.

Scoped improvement: `oled-startup-vt-component-r1/console.py` discovers the
actual root:tty5,0600 tty1 node, uses only GET ioctls, checks active VT/binding
and stable metadata, and refuses text mode before frame entry. Eight focused
cases pass; actual phone preflight detects the known blocker in0.007 seconds.
This is a read-only component, **not an implemented graphics lease or permission
to rerun the frame**. The successor must prepare a bounded KD_GRAPHICS owner,
retain its descriptor and one-use entry, monitor mode/current boot/health,
and restore the original console mode with independent zero-brightness cleanup.
Validate that while blank before requesting fresh Ready. Keep exact framebuffer
readback, DRM geometry and all prior recovery protections.

Evidence: `oled-startup-experiment-r1/frame-show-summary-r98.json`,
`frame-readback-diagnostic-r98`, `console-discovery-r98-r2`,
`console-preflight-r98`, and the closed show. The first console discovery remains
failed because it attempted to read write-only sysfs `rotate_all`; the corrected
read omits that irrelevant attribute. No phone mode/permission was changed.

Historical r97 preparation below is superseded by the consumed r98 show.

Latest r97, 2026-09-11: **actual framebuffer layout capture, ARM64 rendering,
protected RAM cache, cleanup,90-second kernel log and final health all PASS**.
The first visible-pattern test is completely prepared and awaits a fresh Ready.
No user-response countdown is running: capture has closed and the cached frame
persists. On fresh Ready immediately execute the exact `argv` from
`oled-startup-experiment-r1/prepared-frame-run-r97.json` once. Do not render,
build, stage, debug or repeat capture after Ready. The runtime only checks current
health, arms logging, restores/seals cached bytes and revalidates the framebuffer.

On actual `oled-startup-frame-host-r2/show-r1/visible.json`, promptly give its
physical observation prompt before `observe_before_monotonic`: look for upright
TOP arrow, colour bars, four corners and centre cross. Keep USB connected; no
button/password action. Save the user's actual response with the visible receipt
hash; never invent an optical result. The display pulse is20 seconds at32/1023,
then independent zero cleanup. The kernel logger lasts90 seconds. Show has not
entered; only a new affirmative user reply may launch it. Earlier Ready replies
were consumed and do not apply.

Prepared command SHA:
`49b8d0ff17e169f6af51f22aa1e81c8c1360a8077f2572ef80e43db0b1843105`.
Prepared record SHA:
`3a770cebec6dbb660e68d5a59e4b4375e9549e31e49d1e4be23c53eab6c43e48`.
Coordinator SHA:
`ae7f61c9b5e9ec02b617b725687a25061abc77a1aafbb418b20db230da722793`.
Qualification SHA:
`96ab27b291c994eeddc329e9cab056cd187a325790b2f69c75bb016971788744`.
The coordinator is `oled-startup-frame-host-r2/coordinator.py`; its target assets
are in `oled-startup-frame-backend-r2`. Preserve both executed source sets.

Actual capture opened only the qualified framebuffer for GET ioctls; no pixel
or nonzero-brightness write occurred. The Rust helper validated1080x2448,32-bit
layout with4352-byte stride and rendered10653696 bytes in0.083 s. Its frame SHA
`859231dae5b6f5c8c80361a0cfcf748cd605f662ee3e9722ab8fda0f377276a8`
matches the retained fixture pattern. Capture exchange1.013 s; complete capture
including90-second recording and health95.345 s; final launch validation0.543 s.
Kernel recording closed naturally with0 new kernel records. Final health passed
at5054.72 s uptime on unchanged boot
`229580f9-ac26-4b18-a0eb-ea9c05bc632f`. Both modules remain loaded, active DRM
is1080x2448@60, brightness0, GPU/GMU DT disabled. No reboot, module reload,
partition flash or restored old selection is claimed. Optical scanout and GPU
acceleration remain unverified.

The first separate r97 capture in `oled-startup-frame-host-r1/capture-r1` failed
at the framebuffer node guard. Its complete worker error, cleanup, reaping and
post-health were saved; never reuse that attempted namespace. Actual discovery
shows `/dev/fb0` root:video983,0660, major29/minor0, inode1598, whereas the old
reader required group0. The corrected successor accepts only this observed
combination or private root:root0600; other UID/GID/mode/device/link combinations
refuse. A read-only node/sysfs preflight now precedes capture admission. No
permission was changed on the phone. New node/ARM64 cases5, backend16 and host15
pass; unchanged cache8 and protected-context9 results are inherited by source.

The new backend separates capture/cache from display and retains complete bounded
worker errors in a protected file before making a short root-cause summary. The
host fetches that file by exact hash. Cached show restores sealed bytes without
invoking the renderer; missing/changed cache or failed capture closure refuses.
Independent zero cleanup survives lease/Ready/worker failures. This removes the
old requirement to reply within a short live-preparation window.

Evidence: `oled-startup-experiment-r1/frame-preparation-summary-r97.json`,
`fb-node-discovery-r97`, `frame-node-correction-r97.patch`, and both new frame
host/backend scopes. The r1 failed capture and r93/r96 failures remain FAIL.
The r2 cached preparation is a distinct completed operation, not a retry of
consumed module insertion or a physical display acceptance. Never run r95 again.
The next authorized physical step is the prepared cached frame, then actual
observation and terminal cleanup/health review. No further Ready question is
needed until this prepared request is answered.

Latest r96, 2026-09-11: **both display modules are now loaded; active DRM
1080x2448 at60 Hz is confirmed; the module trial remains FAIL**. Fresh Ready
arrived during independent offline scanout preparation and immediately launched
the exact r95 command. That command and its host/target module entry are now
consumed. **Never execute `prepared-run-r95.json` again or retry module insertion.**
No physical prompt is pending; the user was released when the test stopped early.

`oled-startup-module-host-r1/run-r1/result.json` is terminalFAIL. The exchange
ended in1.202 s, independently verified zero brightness, reaped both target
workers and SSH, and retained nine kernel messages. Before/after health passed
in1.833/1.831 s at2735.59/2739.45 s uptime on unchanged boot
`229580f9-ac26-4b18-a0eb-ea9c05bc632f`. The logger was deliberately cancelled and
reaped after the component failure; its180-second capture is incomplete and FAIL.
There was no reboot or partition flash. Kernel messages show DRM initialization
and framebuffer registration. Read-only follow-up confirms REFGEN/panel modules,
`fb0`, connected/enabled DSI, and brightness0. Physical scanout/darkness remains
unverified. The old healthy selection was not restored.

The original backend flattened a structured worker exception into a2000-character
string beginning with a large blanking receipt. Original helper exit rows and the
innermost error are absent from retained terminal output. Do not invent them or
repeat insertion to recover evidence. A subsequent exact endpoint read reproduces
`framebuffer mode changed`: actual fbdev modes is `U:1080x2448p-0`, although active
DRM CRTC timing is60 Hz,166695 kHz, totals1128x2463. The compiled kernel's
`drm_fb_helper.c:1649` clears `info->var.pixclock`; `fb_var_to_videomode` leaves
refresh0 when pixclock is0; `fbsysfs.c` formats that value. This explains why the
fbdev string does not establish refresh. The complete original worker error is
still unavailable.

Separate `oled-startup-scanout-component-r2/endpoint.py` now accepts the zero
fbdev field only with same-controller DRM/card/DT identity, connected/enabled DSI,
an active matching CRTC and the exact observed60 Hz timing. It reads that timing
twice and keeps optical claims false. Missing/ambiguous/inactive/changed timing
refuses. This check passed read-only on the actual phone in0.423 s, opening no
framebuffer device and writing no brightness. Source SHA:
`354c3e5465d0457890c31933f966664237d848571c2b505bd0de52a7e529926e`.
34 focused cases pass:20 endpoint cases and14 new DRM/pipeline cases. The latter
includes the cached ARM64 Rust renderer under QEMU, file-backed framebuffer
writes, timed illumination/blanking fixtures and changed-mode refusal. Its first
negative assertion wrongly prohibited independent zero cleanup; it now requires
zero-only cleanup and no frame write. Original failed log is retained.

Earlier in r96, `oled-startup-scanout-component-r1` corrected stale capture/frame/
writer dependency hashes in a separate copy and passed63 directly defined cases
in29.852 s, including one real20-second duration fixture. Selecting direct cases
avoids168 inherited repetitions (231 default cases); existing endpoint cases were
already qualified. No Rust/kernel/module/image rebuild was needed. Both scanout
copies are component evidence, **not an admitted physical scanout session**.

Actual GPU/GMU DT nodes are disabled, and their platform devices are absent. This
accounts for the missing-device log and leaves acceleration unqualified; merely
having a DRM render node does not prove a GPU. Preserve the display-only boot
while preparing the first visible pattern. GPU bring-up requires a separately
reviewed DT/runtime plan after checking firmware and power dependencies.

Evidence: `oled-startup-experiment-r1/module-run-summary-r96.json`,
`post-module-r96-r2`, `drm-state-r96`, `endpoint-drm-validation-r96`,
`gpu-discovery-r96` and `drm-mode-fix-r96.patch`. The first read-only diagnostic
failed before mutation because inline source shadowed its BOOT variable; preserve
that output and use an isolated module namespace. All executed boot/module
sources and claims remain frozen. Next: prepare a separate bounded framebuffer
GET/layout capture and scanout owner for the already-loaded modules. Preserve
structured worker failures in the successor. Ask fresh Ready only after the whole
next physical session is prepared. Never relabel r93 or r96 as PASS.

Latest r95, 2026-09-11: **the three-minute current-boot display-module test
is fully prepared and awaits fresh operator availability**. The earlier Ready
was released while integration was unfinished; do not reuse it. On the next
fresh Ready, immediately execute the exact `argv` in
`oled-startup-experiment-r1/prepared-run-r95.json` once. It already binds the
validated coordinator and prepared record; only brief pinned admission, current
health and live logger arming remain. Watch `oled-startup-module-host-r1/run-r1/logger-ready.json`
for actual readiness and tell the user to watch the screen, leave USB connected
and avoid button presses. No password, compilation, generation or staging belongs
after Ready. The normal capture lasts180 seconds. Capture observations do not
by themselves prove scanout or physical darkness.

Actual preparation passed in3.008 s: current healthy boot
`229580f9-ac26-4b18-a0eb-ea9c05bc632f`, exact module/helper inputs, then protected
RAM source staging below `/run/initramfs/rog5-oled-modules-<owner>`. Health passed
at2457.84 s uptime in1.681 s. No module insertion, brightness write, reboot,
partition flash or new boot claim occurred. Final launch validation took0.694 s;
three host liveness prerequisites took0.081–0.082 s each, within the0.75-second
renewal interval and three-second remote lease. These timings are measurements,
not a guarantee under future load.

New `oled-startup-module-host-r1` composes the r94 endpoint/loader/backend and
bounded direct-file SSH kernel logger. Static prepared evidence grants RAM
staging only; actual logger readiness/liveness is required for runtime entry and
every lease. Independent same-boot blanking remains available after lease loss.
The one-use host run and target entry guards prevent automatic retries. Historical
binding accepts only the exact recorded capture-close failure and separately
checks current health; the startup trial remains FAIL with incomplete capture.
Logger completion failure or cleanup exception cannot produce a passing run.

26 focused current-host cases pass:13 duplex/staging checks in3.142 s and13
integration/provenance/prepared-evidence checks in2.189 s including import/setup.
Module effects are explicit fixtures. Initial composed tests correctly failed
because their imported fixture retained the old boot in cleanup identity; the
local peer now binds its complete identity from its explicit expected input.
Original failed logs are retained. The r94 72 component and7 logger cases were
not rerun because those sources did not change. No hardware loop was consumed
by this fixture issue.

Qualification SHA: `f51d67c3a37438b2c5cc962b819c5581fe9d8a67f8dbca2c866ab46f649a851f`.
Prepared SHA: `8c3bb147b91baeb18cb2389fa39ef2e8ad96dd0797b17dcde54c72d24bfaefb8`.
Coordinator SHA: `786f557c2ed4a20293faf19fcaadd0e8a4636fd19caf1015aa434dfa01a2379a`.
Evidence in `oled-startup-module-host-r1`: `review-r95.json`, `qualification.json`,
`tests-r2`, `tests-r3`, `preparation-r1`, `prepared.json`; exact launch command in
`oled-startup-experiment-r1/prepared-run-r95.json`. Preserve this prepared source
cohort. Never run the old module coordinator, r92 boot command, consumed startup
claim or old stager. No user availability remains valid until a fresh reply.
Kernel/non-cellular bring-up remains the priority; no rebuild or Denial build
was needed. Next evidence is actual REFGEN/panel insertion, DRM/backlight
discovery, cleanup, retained kernel logs and post-run health.

Latest r94, 2026-09-11: **current-kernel module primitives and a rootless
SSH kernel logger pass focused checks; the assembled module test is not ready**.
No module insertion, brightness write, reboot, new boot claim, password prompt
or availability request occurred. Previous r93 is progress: actual kernel boot,
health evidence and a reproduced/fixed recorder failure changed the next action.
All executed boot sources and consumed claims remain frozen. Never rerun r92.

Current target health passed in1.792 s at685.99 s uptime on unchanged boot
`229580f9-ac26-4b18-a0eb-ea9c05bc632f`, startup bundle/kernel05941 and its healthy
selection. Read-only input discovery found the expected matching helper/module
hashes, no prior OLED component entry, and actual root-owned `/run`1777,
`/run/initramfs`0755 and payload directories0755. Descriptor SHA is
`f7a4bd79bff9ca17339fb2144ba36498067c3eb92ca0caf53d7d11da573b858b`.

Separate source copies: `oled-startup-display-component-r1` and
`oled-startup-module-backend-r1`. Endpoint/fixture identities now bind the exact
startup descriptor/bundle. Payload traversal holds no-symlink descriptors and
requires root UID/GID; only the literal root-sticky1777 `/run` is accepted as a
writable ancestor, while writable payload children still refuse. Replacement
checks and held descriptors remain enforced. Backend staging now requires a
root0755 `/run/initramfs` parent on the active `/run` tmpfs device. The old host
coordinator still uses `/run`; do not execute it with this backend.

72 focused cases pass: endpoint20, module-loader17, actual private-tmpfs
ancestry5, backend-context8 and backend-process22. Initial backend fixtures
failed because umask077 created the supposed0755 parent as0700, the test mounted
an additional `/run` over the old mount, and process tests lacked their root user
namespace. Fix explicit fixture mode/namespace; match tmpfs to the active
`st_dev` rather than rejecting an obscured mount record. Only the affected two
suites were rerun (0.115/4.130 s). Module/sysfs effects remain fixtures. The exact
new endpoint and held-FD read-only input functions also passed on the ARM64 phone
in0.430 s. They read the staged helper and two modules without inserting them.

The existing module runner already drains its process pipes while polling its
lease; it does not share the startup supervisor's synchronous drain gap. New
`oled-startup-module-monitor-r1/kernel-log.py` instead adds authenticated live
`/dev/kmsg` recording to bounded disk files. It requires the exact USB route,
host key, source and current boot; produces readiness/heartbeats/terminal result;
limits lifetime/output, owns/reaps its SSH child, and changes no host networking
or sudo policy. Seven process/file fixtures pass in3.964 s, including a >1 MiB
burst while the parent does not poll, wrong boot, missing terminal, stderr and
cancellation. Actual read-only15-second phone capture passed and reaped in
15.412 s, with same-boot heartbeats and terminal closure. No new kernel message
arrived, so actual nonempty kmsg decoding is not claimed from that run.

Evidence: `oled-startup-experiment-r1/module-components-final-r94.json`,
`module-component-tests-r94` and `module-component-tests-r94-r2`,
`module-input-validation-r94`, plus `oled-startup-module-monitor-r1/phone-readonly-r1`.
The new logger and backend are **not module admission or a complete hardware
session**. Remaining: assemble a separate current-boot provenance/owner binding,
connect logger liveness to the module lease and independent blank cleanup,
update and qualify protected-parent staging, and validate the full composed
failure/cleanup path. Preserve the failed startup trial as FAIL; do not fabricate
its missing capture closure. Prepare everything before asking fresh availability.
No kernel/module/image rebuild or Denial build was needed.

Latest r93, 2026-09-11: **new kernel boots and remains healthy; full
startup trial FAILs on missing recorder closure**. No user action is pending;
leave USB connected. **Never rerun `prepared-run-r92.json`, `trial-launch-r1`,
the consumed startup claim, source readiness, or r84 staging.** The startup
claim `oled-startup-source-05941-r1` is consumed and the launcher is terminal.
Source `f02083f4` and the executed private source/metadata snapshot remain frozen.

Fresh Ready immediately launched the prepared command. Local authentication
passed, the same-process credential keeper refreshed successfully and stopped
cleanly. The source state/exitrd transition and one128-MiB RAM boot passed with
exact device/slot/image checks; no flash occurred. Target SSH health passed at
73.21 s, then199.53 s and534.62 s uptime. Current phone is
`oled-log-05941-c371bcc38a6a73fe`, kernel `7.1.4-g05941d04803f`, boot
`229580f9-ac26-4b18-a0eb-ea9c05bc632f`, current-boot healthy record
`b4d203a8acdd9d02a594e4725e5b2eb1f857d9f9c57639e912276e247edc0c4d`.
Physical/storage guards pass. The diagnostic sample measured battery99%, full,
30.1 C. **Old selection eligibility was not restored**; preserve the healthy
experimental boot and exact selection for separately prepared next actions.
No fallback restoration or second reboot was attempted.

Capture armed before transfer but only59 events/58.636 s of event span were
retained, including10 stage events and31 early-kernel observations. There is
no terminal capture or cleanup event. `close_capture` correctly failed with
`capture terminal result absent`; no full23-minute or release PASS is claimed.
The launcher and workers are gone/reaped. Independent present-state inspection
confirms original host profile and no diagnostic address, route, firewall rule
or listener; this does not manufacture the missing closure receipt.

The host supervisor pumped its pipe at readiness/closure but not continuously
while the health callback waited on SSH. A real-child regression with over1 MiB
of output reproduces the original stall (expected failure,3.941 s). Separate
candidate `oled-capture-drain-fix-r1` adds one serialized background drainer
between readiness and closure, with bounded stop/join and unchanged stream,
identity, timeout and cleanup checks. It passes21 existing cases and the burst
case (1.177 s); the initial burst fixture was only1,040,083 bytes, so its strict
1 MiB assertion failed despite completion. Increase only its payload to160
records and retain that failure; unchanged cases were not rerun. Candidate
`result.json` and `drain-fix.patch` are component evidence, **not live admission**.
Integrate/review/qualify it separately before another hardware recording.

Authenticated dmesg was recovered after the recorder failure. It shows early
SMMU faults, DSI PLL warnings and `Failed to get supply 'refgen'`; no DRM connector
is registered. Direct inspection confirms the exact matching REFGEN/panel .ko
files are staged and **both remain unloaded as intended**. This does not yet
prove a missing DT supply or require a kernel rebuild. No display module/frame
operation occurred. The current boot's survival does not establish the cause
of the earlier r77 reboot.

Evidence: `oled-startup-controller-r1/execution`,
`oled-startup-live-driver-r1/trial-launch-r1/result.json`, and
`oled-startup-experiment-r1/{capture-analysis-r93.json,host-cleanup-observed-r93.json,
post-run-r93-r2,display-module-observation-r93.json,final-phone-health-r93.json}`.
An initial read-only collector used an unsupported interpreter spelling and
was refused locally before any phone command; corrected isolated Python reads
are retained separately. Next: preserve this live boot, qualify continuous
recording and prepare guarded REFGEN/panel insertion on the current kernel.
Do not rebuild unchanged kernel/modules or continue Denial builds first. All
r92 Ready instructions below are historical and consumed.

Latest r92, 2026-09-11: **actual host privilege handoff passes; exact
startup test is prepared for fresh phone availability**. The user's Deck Ready
started the prepared local authentication immediately. Both UID0 guardian to
UID1000 deck probes passed in 9.599 s; authentication and owned children were
reaped. No password was retained. This check made no phone/network/claim action.
Never replay `privilege-probe-r1`.

Final qualification now exists at
`oled-startup-live-driver-r1/live-qualification.json`, SHA256
`f92291e31d48883995c843be8d8eecd6d406d45f8df57be39ede2fe299191ef2`.
Its459 bounded evidence files bind the unchanged final r89 software replay and
actual r92 privilege proof to clean source `f02083f4`, digest `642669b9...`.
All53 admission inputs and the frozen source/metadata snapshot match. Software
flow success is still separate from physical startup/recovery acceptance.

The exact pending local record `oled-startup-source-05941-r1.record` was created
exclusively, synced and verified; SHA256 `547422f3024ef294f5058ddbb87f47b5c7c7e5a03700ddf42ab99a3deeb2eb17`.
It is **unconsumed**. Launcher `prepare()` passes. Actual launch, execution,
source-readiness and boot-authentication directories remain absent. All previous
claims and consumed r84 staging remain preserved.

One fresh authenticated read-only phone query passed in 6.890 s: V11/359318,
boot `ee0d166e-5e69-4db7-8bbd-6266352594ea`, all11 installed files and boot_b
match. Battery/thermal/storage guards pass; selector and original shutdown are
unchanged, with no new transaction or reboot intent. No phone mutation occurred.
Current pinned capture-network checks pass: original shared profile, exact USB
identity, no diagnostic address/route/firewall rule/listeners, and no active
receiver lock in the kernel lock table. Host has40.5 GiB disk free. The legacy
host-doctor could not run because this frozen checkout lacks its old active-lock
manifest; this is not a full legacy host-doctor PASS. An unprivileged open of the
root-owned recorder lock correctly refused EACCES; read-only kernel lock-table
inspection replaces that preparation observation. Runtime root lock acquisition
remains mandatory and unchanged.

Prepared command and exact hashes are in
`oled-startup-experiment-r1/prepared-run-r92.json`; local preparation/phone/host
results are `launcher-prepared-r92.json`, `phone-route-r92/result.json` and
`host-resource-check-r92.json`. On fresh Ready beside the connected phone,
execute the saved argv immediately. It invokes the unchanged qualified launcher
with local authentication and keeps sudo alive within that same process. Leave
USB connected; no phone-button press is needed initially. A separate password
window may be required because the completed privilege probe had its own parent.
Do not assume its timestamp transfers to the boot launcher. Do not recompile,
regenerate sources or replay old one-use attempts after Ready. No operator
countdown is active. The following r91/r89 paragraphs are historical.

Latest r91, 2026-09-11: **goal blocked awaiting fresh Deck availability and
local sudo authentication**. The same condition persisted across r89–r91;
r90/r91 added no implementation progress. Offline preparation is complete for
the next privilege check. Its exclusive attempt directory is absent, and no phone
command or password window has started. The goal was marked blocked, not complete.
The pending availability question and exact r89 prepared command remain valid;
on fresh Ready, start that read-only probe immediately. Preserve frozen source,
qualification candidate and all one-use evidence. No unchanged test or sudo retry
is justified while waiting. The full Denial objective remains unchanged.

Latest r89, 2026-09-11: **startup boot profile registered in source and
final software replay passes; awaiting Deck availability for a prepared read-only
privilege check**. No phone command, reboot or new durable claim occurred.
No hardware Ready request was made. The pending question is specifically about
entering sudo's password in the local Deck window; no password window or response
countdown has started. Last phone evidence remains r87's unchanged V11 boot.

Controller repository is clean/frozen at `f02083f4` in
`oled-startup-controller-worktree-r1`. The literal registry adds exactly
`oled-startup-source-05941-r1`, matching the r83 descriptor's signed image,
composition/A01, V11 fallback and closed r77 predecessor result. All227 previous
registry records are byte-preserved. The21 claim tests pass normally and under
optimized Python (0.331/0.392 s), including descriptor agreement, wrong device/
image refusal and the still-required durable consumption gate. No pending record,
entered record or global guard exists for the new profile. Registration alone
cannot launch it. Compiled kernel/payload/A01 inputs remain unchanged.

An initial post-registration import caught the old claim-consumer digest still
pinned in the private boot callback. The refresh graph now includes that exact
pre-registration source mapping; no guard was weakened. Final53 inputs pass.
The source identity is `f02083f4`, digest `642669b9...`; private sources and input
metadata were captured before and after the final replay and match exactly.
All four full-flow scenarios plus admission26, boot19, launcher32, preparation21
and privilege-boundary10 tests passed in27.433 s total. The software fixtures do
not prove current root handoff or physical phone behavior.

Prepared evidence: `oled-startup-experiment-r1/qualification-candidate-r89.json`
and447 exact bounded copies in `oled-startup-live-driver-r1/qualification-evidence-r89`.
This is a non-admitting candidate; `live-qualification.json`, actual execution
and one-use source readiness remain absent. Final replay/result/source snapshots
are in `final-checks-r89`; registration records are in `registration-r89`.

On a fresh reply that the user is ready at the Deck, immediately run the already
prepared command, without another build or preflight:
`python3 -B /home/deck/.local/state/rog5-denial-20260910-r1/oled-startup-live-driver-r1/run-privilege-probe.py --run-id r1 --authenticate`.
Its check-only result passes, graphical environment and tkinter are available,
and the exclusive `privilege-probe-r1` directory is still absent. It performs only
UID0 guardian/runuser-UID1000 probes, no phone/network/claim actions. Password input
stays in the local private helper. Preserve any failed attempt; never replay it.
Do not retry the expired cached-sudo check unchanged. Once actual handoff is proven,
finish the exact qualification/pending-claim preparation and prepare the complete
phone session before a separate fresh hardware Ready request.

Latest r88, 2026-09-11: **all four assembled startup/recovery simulations
pass; final live admission remains incomplete**. No phone command, reboot,
new claim or operator request occurred. Last real phone observation remains
r87's unchanged V11 boot. No live qualification, execution or readiness exists.

The full-flow test found a production integration defect: source-action admission
still required `python3`, while the qualified install/reboot/restore callbacks
use sealed BusyBox shell. The first run stopped at install admission and restored
its staged fixture selection (5.376 s); no transfer occurred. Admission now requires
the exact shell generator and intent. Three focused tests cover all three actions
(nine subcases), rejecting Python transport and altered scripts. The corrected
full flow passed target success, early fallback, late failure with separate
fallback capture, and source abort in 33.400 s. These use real callback/admission
policy, receipt files and recorder processes, with explicit transport, root/network,
claim/qualification and virtual-clock fixtures. Physical boot/recovery is unproven.

Additional passing cases: target-health 20, RAM boot/owned child 19, assembled
driver 12, health readers 26, admission 26, admission/driver 3, bridge/supervisor 3,
root-route worker 19, capture bridge/guardian 16, fallback transport 16, launcher/
credential lifecycle 32, and privilege-probe boundaries 10. Checks cover signed
kernel-recorder configuration, one-use refusal, inherited sealed descriptors,
full observation closure, parent loss, lost replies and child/route cleanup.
The unchanged kernel, modules, signed payload and A01 were reused.

The copied touch askpass helper had correct bytes but mode0644, failing its
required0700 check. Six privilege cases passed; the four affected cases passed
in 0.737 s after restoring the private executable mode. The original failure is
retained. Source graph refresh now rejects this mode mismatch before publication.
No password window was opened. The existing shell/session 44286, PID251096,
remains available, but `sudo -n -- /usr/bin/true` returned1/password required;
its cached authorization has expired. Do not retry noninteractive sudo unchanged.

Final input inspection accepts53 pinned inputs. The mode change refreshed input
and dependent digests after full-flow execution; final qualification must bind
that final producer set rather than relabeling the earlier run as full admission.
Evidence: `oled-startup-experiment-r1/integration-progress-r88.json`, including
both failures, completed scenarios, test streams and final private-source snapshot.
Next: finish exact boot-profile registration and final qualification binding;
prepare actual read-only privilege probes with fresh sudo authentication, then
fully prepare live recording/recovery before requesting hardware Ready.

Latest r87, 2026-09-11: **V11 installed-route and preparation components
qualified; full controller remains in preparation**. The user's Ready was
released immediately after checking current state. No physical step is pending.
One authenticated read-only phone query passed in 5.806 s; the phone remains
V11/359318 on boot `ee0d166e-5e69-4db7-8bbd-6266352594ea`. All 11 installed
files and the 96 MiB boot_b hash matched. Selection `ed3a62d1...`, original
shutdown `ec3c7fd2...`, prior transactions and the consumed r84 RAM staging are
unchanged. No reboot, selection write, active shutdown replacement or new claim.

The new route generator uses sealed BusyBox shell and streaming hashes, with
metadata checks, boot block identity/geometry, and qualified source observations
before and after the inventory. It requires the actual installed modes: 0400
bundle members and 0600 selector. Its first local build correctly refused the
incorrect generic 0644/0755 assumption; this was fixed before any phone call.
Strict host parsing binds the installed inventory and normalized source proof.
11 isolated ARM64 file/race cases and four generator refusals passed in 25.279 s;
12 host route/receipt cases passed in 2.635 s. ARM64 block geometry and telemetry
were explicit fixtures; the actual phone query independently checked them.

The installed ARM64 selector passed three new-record cases in 0.337 s: new
pending/healthy records select V11 without altering their bytes; old healthy
selects V9 and transitions its fixture record to pending. This proves selector
logic, not physical fallback boot. Fresh evidence is in
`oled-startup-controller-r1/selector-tests-r3`.

Source preparation now binds the actual closed r77 trial, closed recorder,
stopped credential keeper, consumed prior claim, later verified V11 restoration,
and exact consumed r84 RAM-stage/readback records. A pinned historical index
preserves their identities independently of successor source digest refresh.
Historical 0644 summaries and empty streams have their own exact metadata reader;
live readiness still requires 0600/nonempty receipts. The shell route replaces
Python transport here too. All 21 preparation tests passed in 2.191 s, including
stale readiness, running prior owner, incomplete cleanup/restoration, ambiguous
transport, and duplicate entry. No real one-use readiness directory was created.

Fallback observation now exercises the new startup transaction and RAM namespace,
while retaining both completed historical transactions. All 11 ARM64 cases passed
in 56.801 s; 33 host parser cases passed in 0.004 s. The first fixture attempt
stopped before execution because its copied fallback-tools path did not exist;
that evidence remains. The corrected fixture checks exact retained tool hashes
before allocating cases, uses real tmpfs and the actual new Rust helper, and
labels physical telemetry/service/image hashes as synthetic.

Admission verified all 53 exact inputs in 0.104 s. Live qualification, execution
and one-use readiness are still absent. Selected component results do not admit
a physical launch. Evidence and current source pins are in
`oled-startup-experiment-r1/integration-progress-r87.json`; r86 evidence remains
unchanged. Next: finish target-health/boot/full-flow and root handoff/cleanup
qualification, then bind final producers and prepare fresh hardware availability.
No unchanged kernel, module, image or A01 rebuild is needed.

Latest r86, 2026-09-11: **successor controller/recorder integration is in
progress; selected component checks pass**. No phone command, reboot, new claim,
readiness request or user action occurred this turn. Last authenticated phone
observation remains r85's unchanged V11 boot. Never replay the consumed r84 RAM
stage or earlier trial entries.

New sources: `oled-startup-controller-r1`, `oled-startup-live-driver-r1` and
`oled-startup-controller-worktree-r1`. The Git worktree is clean at `fdfe1c4c`,
based on r83 composition source `98aa9610`. Its new import-only
`verified-oled-startup-hardware-boot.py` describes the exact r83 image, profile,
A01 and closed r77 predecessor result. Candidate is
`oled-log-05941-c371bcc38a6a73fe`; proposed claim is
`oled-startup-source-05941-r1`. Canonical admission currently refuses because
that claim is not registered. The successor live-qualification file is absent.
Only source files were copied; no execution, claim, launch, lock or qualification
records were copied from prior experiments.

Source action callbacks now use the qualified r85 sealed-shell generator and
strict key-value replies, and retain command intent/transport before parsing.
Source-read callbacks normalize the r85 observer's exact proof fields. Preflight
uses its closed-inventory verify-source-abort script, with host validation also
requiring an absent transaction. Fallback staging delegates to r84's generator.
Core identity is V11/359318 as source and fallback, with distinct boot IDs; the
new OLED bundle and pending/healthy hashes are bound to the target.

The root recorder now owns the r82 startup-pull socket within its existing
network lifetime. It binds kernel diagnostics to the observed startup boot,
drains/stops at return transitions and closes the socket on cleanup. The exact
r83 config (`0340516a...`) is included in owned/readiness receipts and live probe
responses. The supervisor checks that binding; immediately before transfer, the
boot callback compares it with the signed profile's startup-preservation fields.
Kernel diagnostics remain separate from authenticated health and capture outcome.

Passing checks: 25 controller ordering cases (1.418 s); 27 action/engine cases;
21 recorder cases with real TCP/UDP sockets in a separate user/network namespace
(0.415 s total); 21 supervisor cases with real child processes and live TCP probes
(16.667 s); 11 source-adapter cases using retained ARM64 observation replies.
The supervisor includes mismatched-config refusal and owned-child reaping.
Its kernel transport is an explicit fixture; actual UDP ownership is tested in
the recorder suite. These 105 component cases do not qualify the whole live
controller or physical boot/recovery. Evidence and exact current private source
hashes: `oled-startup-experiment-r1/integration-progress.json`.

Initial action tests caught a fixture still claiming old selection during fallback
staging; all 24 unaffected cases were preserved and the three corrected cases
passed in 1.377 s. The recorder fixture first lacked CAP_NET_ADMIN in its isolated
namespace (0.016 s), then used different virtual clocks for inner/outer capture
(0.415 s); diagnostic output proves the latter failed on capture deadline. The
fixture now grants only namespace-local network setup and injects the same clock
into the real kernel capture. No production guard was loosened.

Target runtime input inheritance compared nine unchanged members against r83's
final CPIO inventory and exact source files. The old baseline-health branch is
refused for V11; use its shell observer instead. `refresh-cohort.py` now derives
63 source/input files using an explicit dependency graph, including original
repository pins, without manual cascades. This is not live qualification.

Remaining before Ready: replace `route-checks.build`/`route-target` Python route
inventory with the V11 shell path; bind `source-preparation` to the actual closed
r77 trial and r84 staging/readback; qualify installed-selector decisions for the
new records and the updated fallback restoration namespace; finish health/route/
boot/admission/root-bridge full-flow and cleanup checks. The copied legacy route
and predecessor assumptions still refuse and must be updated before any launch.
No unchanged kernel/module/image/A01 rebuild is needed.

Latest r85, 2026-09-11: **V11 source exitrd actions and read-only abort
reconciliation are qualified components**. The phone was only read this turn;
no state-helper execution, active shutdown replacement, reboot or new claim.
No operator action is pending. r84 RAM staging remains consumed and must not
be repeated.

Fresh code is in `oled-startup-source-actions-r1`: `generate.py` SHA `1a89ff2d...`
and `observe.py` SHA `78cbc782...`. Preserve these qualified producers when
integrating the outer driver. Source actions use the sealed ARM64 BusyBox/loader,
nonblocking directory/selection locks with open-descriptor identity checks,
exclusive RAM receipts, retained original shutdown and atomic replacement.
They pin the observed V11 unit states and reboot provider. Installation,
restoration and reboot requests retain one-use intent checks. A lost reboot
reply never permits retry or source-abort inference. The observer distinguishes
absent, staged and restored selection with original/patched shutdown, and refuses
foreign owners, reboot intents, partial publication and incomplete restoration.
It is read-only and is required in the future outer preflight/abort paths.

Qualification: 23 ARM64 action cases, 11 reconciliation cases, four generator
refusals and direct verification that nine prerequisite refusals left no operation
marker. The first action run completed ten cases before its fixture writer tried
to alter a mode-0400 custody file and raised PermissionError. Its source, results
and failure remain recorded; only the remaining eleven cases resumed (131.090 s).
Two focused tests (30.749 s) prove same-byte/same-mode shutdown replacement and
replacement of the locked exitrd directory are detected. Reconciliation took
63.888 s. All mutation/reboot operations were confined to isolated fixtures with
synthetic physical telemetry and service/reboot responses, using real ARM64
file operations. This is not physical reboot/recovery or clean-teardown proof.

Authenticated source preflight passed on V11 in 0.689 s, including acquisition
and release of both nonblocking locks. Final read-only reconciliation passed in
1.219 s: boot `ee0d166e-5e69-4db7-8bbd-6266352594ea`, owner
`8799d4ece2db5fb5c322c0a24c198f97`, original shutdown `ec3c7fd2...`, selection
`ed3a62d1...`, new transaction absent and no reboot intent. Existing RAM staging,
prior transaction receipts, frozen r83 signed payload/A01 and claims are unchanged.
Evidence: `oled-startup-source-actions-r1/qualification.json` binds all results;
`phone-observation-r1/verify.sh` is reusable read-only verification.

Next: create the fresh outer controller and capture owner for r83's sealed
startup-pull config. Adapt action callbacks to sealed-shell transport and strict
key-value replies; the old Python/JSON callbacks are incompatible. Use the new
observer for source preflight, inspect-source-abort and verify-source-abort;
retain identity, intent and partial-state refusal. Qualify complete boot/failure,
source abort, fallback restoration and capture cleanup before fresh Ready. No
new live controller or boot admission is ready yet; no unchanged build/A01 rerun.

Latest r84, 2026-09-11: **new startup state helper and V11 RAM staging
qualified; full boot controller remains in preparation**. No phone reboot,
boot-selection change, active shutdown replacement or state-helper execution
occurred. No operator action is pending; request fresh Ready only after the
complete controller and recorder are qualified.

Current source is authenticated V11, release `7.1.4-g359318de534f`, boot
`ee0d166e-5e69-4db7-8bbd-6266352594ea`. V11 has no `python3` in its normal PATH.
Its active shutdown is 2,479 bytes, SHA `ec3c7fd2...`; the older kernel-source
shutdown and Python source-actions assumptions do not apply. V11's Wi-Fi rollback
timers and healthy-writer service are absent (`not-found/inactive/dead`), while
the SSH identity service is active/exited. The legacy P2 marker has no boot ID;
bind the boot through authenticated observation. `/run` is 1777; use the protected
root-owned 0755 tmpfs `/run/initramfs` parent for private controller files.

The fresh static ARM64 Rust state helper is SHA `49ec430e...` (1,253,208 bytes),
with byte-identical builds. New namespace `.oled-startup-05941-transition` and
pending/healthy records bind r83's signed `oled-log-05941-c371bcc38a6a73fe` bundle.
Previous kernel and OLED transaction inventories and hashes remain protected.
Qualification passed: 14 Rust tests plus ABI refusal, Clippy using pinned tools,
6 ARM64 interoperability scenarios / 17 operations, 35 storage guard cases plus
6 generator refusals (106.701 s), and 7 RAM staging cases (27.248 s). Tests cover
wrong state/shutdown, unsafe parent, completed prior transactions, duplicate
entry and partial transfer; emulated operations preserve historical records.

Authenticated read-only source guards passed. The one-use RAM staging took
1.240 s; independent readback passed in 0.569 s. Owner is
`8799d4ece2db5fb5c322c0a24c198f97`, RAM directory
`/run/initramfs/rog5-oled-startup-05941-8799d4ece2db5fb5c322c0a24c198f97`.
It contains only state-exchange, custody, staging-completed and an inactive
shutdown-to-fastboot derivative (`9423ce9f...`). Active shutdown, boot ID and old
selection `ed3a62d1...` are unchanged; the new persistent transaction is absent.
`oled-startup-controller-prep-r1/staging-r1` is consumed: never rerun stage-once.py.
Use its readback script for read-only verification, not the earlier preflight
that intentionally requires the RAM directory to be absent.

Evidence and frozen preparation inputs are in `oled-startup-state-exchange-r1`,
`oled-startup-state-guards-r1` and `oled-startup-controller-prep-r1` under the
state directory; the latter's qualification.json binds the terminal results.
No new boot claim is registered. r83 signed payload/A01 source `98aa9610` and
all prior consumed entries remain unchanged. Do not rebuild unchanged hardware
bytes or repeat completed A01.

Next: implement and qualify V11 sealed-shell source exitrd installation, reboot
request and pre-reboot restoration. Then bind the exact r83 logging config through
a fresh live controller, capture owner and readiness, and qualify complete boot,
failure, fallback restoration and cleanup. RAM staging alone is not boot admission.

Latest r83, 2026-09-11: **complete signed OLED startup-logging payload and
actual Arch-root composition PASS**. No new phone boot or Ready request occurred.
The user's Ready was released because no new guarded test was armed; the two
r81 passive entries and all prior OLED claims remain consumed and unchanged.
No operator action is pending.

The new bundle is `oled-log-05941-c371bcc38a6a73fe`, trial
`7936240ab44b669f4e911f5c68e5709c10d40ff548cc4c2fdf21d3cec2d9f531`.
Payload source remains `b3a964e6`; composition source is frozen at `98aa9610` in
`oled-startup-integration-worktree-r1`. Wrapper packaging reuses exact `f74e719c`
code. The unchanged 05941 Image, display DT, firmware, 32 loose module copies
and nested module package are preserved. Only init, trial descriptor and its
catalog changed; the exact relay and three-line startup-pull config were added.
Both full payloads match, 58,467,436 bytes, SHA `9c53ebaa...`, produced in
15.952/17.239 s without any kernel, module or Rust rebuild.

Signed wrappers also match and remain 134,217,728 bytes; boot SHA `6cc2f611...`,
manifest `7fc82767...`, recovery `f8f56544...`. Config SHA is `0340516a...`;
use the exact `oled-startup-payload-r1/kernel-relay.conf` in the future recorder.
The full config is sealed in the payload and bound by the new composition
profile, SHA `a9a6ee1c...`. Packaging took 86.212 s with 512 MiB/no-swap scope.

A01 passed all seven checks against the actual retained Arch base and deployed
upper in 80.793 s: wrapper, signed target, archive, root runtime, 51 software
module loads, firmware composition and generated timing/transport contract.
Both image hashes and metadata remain unchanged. The QEMU container exited,
was reaped/removed and reported no OOM. This proves offline runtime composition;
it does not prove OLED scanout, real early-boot USB, watchdog expiry or physical
firmware responses. No new boot claim is registered and no new live controller
is prepared. Evidence: `oled-startup-payload-r1/qualification.json`,
`oled-startup-package-r1/result.json`, `oled-startup-a01-r3/a01/result.json`.

The first two A01 attempts refused missing sparse-checkout files before VM work:
CPU-policy service in packaging (23.919 s) and retained test-shim source in tests
(24.256 s). Both source trees are now present. A01 checks these small prerequisites
before large root hashing; missing/symlink refusal and concurrent hash cleanup
are tested. The final relevant suite totals 84 tests (9 delta, 9 old OLED, 7 new
profile, 59 composition). Do not repeat the completed A01 for unchanged bytes.

Read-only authenticated observation confirms V11 still runs boot
`ee0d166e-5e69-4db7-8bbd-6266352594ea`, release `7.1.4-g359318de534f`, with old
selection `ed3a62d1...`, battery Good/100%/30.0 C/8.483 V and USB online. The
retained exact verification script passed physical/storage/readiness and restored
selection guards. A preliminary query guessed inactive unit names; it is not a
health failure and is superseded by the correct verified observation. `/run`
remains 1777 and `/run/initramfs` 0755. Phone state was not modified.

Removed 744,259,584 allocated bytes of this run's disposable extraction and
roundtrip scratch after verifying both durable target archives; manifests,
logs, receipts, signed packages and all prior recovery evidence remain.

Next: prepare a successor controller for current V11 source and protected RAM
parent, with fresh state/owner/one-use identity and the exact sealed logging
config supplied to capture readiness. Preserve source and executed entries.
Qualify complete boot, failure, fallback restoration and capture cleanup before
requesting fresh Ready; source observations are not reusable availability.

Latest r82, 2026-09-11: **startup request capture is integrated and passes
offline checks; no phone action or Ready request occurred**. Source is
`b3a964e6` in `kernel-startup-capture-worktree-r1`, based on frozen live-qualified
r81 source. Both r81 passive entries remain consumed and unchanged.

The optional recorder binds UDP 8085 within the existing capture owner's network
lifetime. It requests at 250 ms during target discovery, uses 20-second keepalive
requests once ready, preserves queued packets at transitions and stops at the
outer recovery phase. Actual host UDP timeouts are 30/120 s; the keepalive avoids
relying on the idle flow lasting exactly the relay's 120-second run. Limits:
960 requests, 1,040 packets, 16 rejections and 64 packets per ordinary poll.
It matches the kernel boot ID to the separate startup-stage boot. Raw packets and
complete/incomplete summaries stay unauthenticated diagnostics, separate from
boot-health/recovery evidence. Socket closure follows the capture owner.

The standalone builder now accepts explicit
`KERNEL_STARTUP_RELAY_TRANSPORT=startup-pull` with the existing binary/hash/nonce
inputs. Its config contains nonce, binary hash and transport on three lines;
old two-line optional inputs are rejected. The R01 capture CLI accepts the exact
config path plus its SHA-256; receipt and live readiness check bind that same
config. The outer new experiment must prove this is the configuration in its
signed payload. Original optional push/default-absent behavior remains available.

All 100 relevant offline checks pass: 18 startup capture/CLI, 17 existing recovery
capture, 6 relay assembly/runtime, 2 standalone archive and 57 rescue composition.
A nonbootable fixture with the unchanged live-qualified ARM64 relay paired through
builder, composition checker and host config loader in 0.226 s. No Rust or kernel
rebuild was needed. Evidence: `kernel-startup-capture-r1/qualification.json` and
`assembly.json`. This is not a complete bootable OLED bundle or actual Arch-root
composition, and it does not qualify real USB reconnection/startup timing.

Next: use this committed source and exact relay SHA `6fa7783c...` to prepare a
complete paired OLED payload, validate against the actual Arch root, and prepare
a successor controller for the current V11 source/protected RAM parent. Bind the
capture's exact config and keep existing recovery/one-use guards. Do not launch
old controllers, passive entries or consumed OLED claims. No human action is
pending; request presence only when the full next test is ready to start.

Latest r81, 2026-09-11: **both passive kernel-log runs passed; no Ready or
password action is pending**. Fresh Ready immediately launched the prepared r79
entry in PTY 44286. Authentication completed with no error and was reaped.
The push relay captured 118 packets / 116 records over 5.018 seconds, with zero
rejections, gaps, malformed records, send failures or truncation. Authenticated
SSH terminal counts matched UDP. The exact RAM helper was removed, the owned
firewall rule was removed and absence verified. This entry is consumed and must
never run again: `kernel-log-relay-live-r1/execution-r1/result.json` is terminal
`PASS_PASSIVE_RELAY`. Historical pending Ready instructions below are superseded.

A second, separately prepared passive test proved a simpler request-based path:
**no sudo, password prompt or firewall change**. The Deck sent four bounded UDP
requests from port 8085; the connected phone socket accepted the exact nonce and
returned 118 packets / the same 116 records over 5.008 seconds. Both capture and
SSH workers were reaped, the new RAM helper was removed, and the old boot state
and V11 boot ID remained unchanged. Rule absence was checked afterwards.
Evidence: `kernel-log-relay-pull-live-r1/execution-r1/result.json`. This separate
one-use entry is also consumed; preserve its scripts and execution records.

Request mode is committed at `859eb86d` in `kernel-relay-startup-worktree-r1`.
Freeze this executed source. Modes `usb-pull` / `startup-pull` use fixed port
8085 on both ends, a three-second request deadline and a sixteen-rejection cap;
original push modes remain available. Thirteen Rust tests, Clippy/formatting and
five real-loopback UDP/coordinator tests pass. The static ARM64 binary SHA is
`6fa7783cf54a6706f31e3db0f8ce9f937b5023ff64c8cde0088960d3080c5c5d`
(1,499,608 bytes). Build/check took 2.866 s; the ARM64-only twin took 1.248 s and
is byte-identical. No kernel/module build or reboot occurred. Qualification:
`kernel-log-relay-pull-r1/qualification.json`.

Current last authenticated phone remains V11, boot
`ee0d166e-5e69-4db7-8bbd-6266352594ea`, old selection SHA `ed3a62d1...`.
The records reproduce the already-known SID-5 PMIC warning; they do not establish
the earlier OLED reset cause. UDP remains unauthenticated diagnostic evidence.
The request method is proven on normal USB with this host firewall, not during
an early boot or USB disconnect. The optional startup unit still uses push mode.

Next: prepare startup capture/request timing and a complete exact-kernel OLED
payload/composition in a successor checkout, preserving all executed sources.
Account for the request wait in the outer deadline. Qualify against actual V11
source and protected RAM parent before any fresh OLED claim. Do not repeat the
completed passive tests merely to refresh presence. No operator step is needed
until a fully prepared future test actually requires it.

Latest r80, 2026-09-11: **r79 passive test remains fully prepared and awaits
fresh Ready**. Automatic goal continuation did not open authentication, start
recording or touch the phone. The complete prepared input/review hashes still
match and `kernel-log-relay-live-r1/execution-r1` is absent. Use the exact r79
command in retained PTY 44286 on Ready; no build or new preflight is needed.

Independent startup integration is committed at `8b20fbb3` in
`kernel-relay-startup-worktree-r1`. The standalone builder can optionally pair
the exact static ARM64 relay and a fresh nonce; default payloads stay without
this helper. Existing relay inputs in a base are rejected. Runtime verifies the
pair, claims private RAM and adds a separate sysinit service (120-second relay,
125-second runtime ceiling, 2-second stop allowance, no restart). The service
has no dependency on P2, service state or SSH. Composition now validates the
pair and carries the exact selected release into unit verification.

All 72 relevant offline tests pass: 5 new assembly/runtime, 2 standalone archive,
57 rescue composition and 8 existing startup observer tests. The generated unit
passes host systemd verification. Two explicitly nonbootable assembly fixtures
using the actual unchanged ARM64 binary match byte-for-byte, taking 0.229 and
0.222 s. No kernel/Rust rebuild or phone deployment occurred. Evidence:
`kernel-relay-startup-r1/qualification.json` and `assembly.json`.

This proves optional packaging and host fixture behavior only. Actual Arch-root
composition, live V11 relay transport and a new startup packet receiver/controller
remain unqualified. Do not turn the nonbootable fixtures into a phone payload.
After r79 passes, pair a separately validated complete OLED payload and host
capture with the actual V11 source and a fresh one-use claim. All prior claims,
prepared V11 inputs and frozen executed source remain unchanged.

Latest r79, 2026-09-11: **the passive V11 kernel-log relay test is fully
prepared and awaiting fresh Ready for sudo authentication**. The Ready received
while the prior launcher was unfinished was released explicitly; do not reuse it.
No password dialog or relay execution has started. No phone button/cable action
is required for this test.

Fresh authenticated full health/recovery observation passed in 5.077 s on boot
`ee0d166e-5e69-4db7-8bbd-6266352594ea`, with the old boot selection unchanged.
The exact r78 ARM64 binary is staged (not executed) in the private tmpfs directory
`/run/initramfs/rog5-kernel-relay-3e4b3e34ee108aba51187644c6cc670e`.
Staging and independent staged-file verification took 1.320 s. The relay will run
for 5 seconds under an 8-second hard timeout, then remove its exact binary while
preserving the one-use marker and small logs. No reboot, driver insertion or
persistent-state write is included.

Receiver source is frozen at `5f404597` in `oled-startup-observer-worktree-r1`.
Fourteen decoder/receiver checks and nine coordinator/payload checks pass,
including cancellation, loss, foreign peers, rejection flood, SSH failure,
authentication failure and uncertain firewall ownership. Kernel and Rust binary
were reused. The host port is available, USB zone matches, and the narrow UDP
rule is absent. The runtime rule expires after 45 seconds and is explicitly
removed when ownership is proven. SSH stdout must agree with the UDP terminal
summary; neither UDP nor software tests establish OLED health.

Prepared entry: `kernel-log-relay-live-r1/probe.py`, with `prepared.json` and
`review.json` pinning inputs, scripts and evidence. On fresh Ready, immediately
send this exact command to retained exec PTY **44286** (shell PID 251096), without
rebuilding or repeating preparation:

```sh
/usr/bin/python3 -I -B /home/deck/.local/state/rog5-denial-20260910-r1/kernel-log-relay-live-r1/probe.py
```

It validates the terminal, uses only the retained touch authentication primitive,
checks the staged phone, arms recording, and runs the passive probe. It does not
invoke the consumed OLED terminal entry. If `execution-r1` exists, do not rerun.
If authentication is requested, the existing touch password window is the only
user action. Collect `execution-r1/result.json` and cleanup evidence afterwards.
All earlier OLED claims remain consumed; the OLED reset cause is still unknown.

Latest r78, 2026-09-11: **V11 and the restored old selection are unchanged**.
A fresh authenticated read confirms boot ee0d166e-5e69-4db7-8bbd-6266352594ea
and old state SHA ed3a62d1... . Archived pstore is empty, and the system journal
lists only the current V11 boot. The OLED reset cause remains unproven.
Previous r77 is classified as progress: a real OLED attempt, retained failure
evidence, and separately verified recovery changed the next action.

A bounded Rust kernel-log relay and strict host decoder now pass software
qualification. Source is `9b6de57d` in `oled-startup-observer-worktree-r1`;
compiled kernel and executed controllers remain frozen. The helper reads
/dev/kmsg without clearing it, sends selected diagnostics to the Deck, and
reports gaps/truncation/limits. It never establishes health, changes readiness,
loads a module or requests reboot. No service is installed/enabled yet.

Ten Rust tests, Clippy and formatting pass; eight decoder tests cover malformed,
foreign, lost, reordered and inconsistent records. The 1,497,160-byte static
ARM64 PIE entered correctly under QEMU, and independent builds are identical:
SHA `b1be78b8c1c1592d750efef315a5a5818f6706bd4b1d9c10cb36b42216272851`.
Full component build/check took 2.810 s; ARM64-only twin took 1.166 s. No kernel
rebuild was needed. Evidence: `kernel-log-relay-r1/qualification-r1.json`.

**Live relay and startup integration are still unqualified.** The USB zone's
final reject rule requires a narrowly scoped temporary UDP 8085 allowance.
Noninteractive sudo validation in retained PTY 44286 now reports password
required. No password window, firewall change, phone deployment or reboot was
started. Do not request Ready until the complete recording/probe and privileged
entry are prepared. Credential expiry alone does not block independent work.

Next: prepare the bounded receiver and owned firewall lifecycle, then qualify a
short passive relay run on current V11 before adding it to a new startup payload.
Reuse the exact relay binary. Integrate its diagnostic records without treating
them as health authority. The next boot controller must accept the actual V11
source and the verified protected RAM parent; the old headless-source controller
and all consumed claims/entries must remain untouched. No physical user action
is pending. Kernel startup remains ahead of Denial/Flutter and the PMIC audit.

Latest r77, 2026-09-11: **OLED trial failed; V11 is running and the prior
boot selection has been separately restored and verified**. Fresh Ready launched
the prepared entry immediately. Authentication and both sudo reuse children
passed; `sudo -n -v` also passed later from the same retained PTY 44286. The
bounded credential keeper stopped with the job. No password was retained or
sudo policy changed. Current authentication can still expire normally.

The staged-source claim `oled-staged-source-05941-r1` is consumed. One 128-MiB
RAM transfer passed in 13.472 s, without flashing. Target boot observations
`19141e40-a435-4317-ba8b-89cc55133984` reached switch-root PASS, then USB vanished
9.021 s later. The startup observer reported P2 activating, state/identity
inactive and an unsuccessful SSH-service query; no explicit helper failure
was received. These UDP records do not prove authenticated target health.
V11 subsequently appeared. The full 23-minute recorder closed and reaped its
worker, with route/firewall/profile/address cleanup passing.

The original controller is terminal **FAIL** and must remain so. Automatic
restoration stopped before RAM staging because `/run` is root-owned mode 1777,
while its staging check expected 0755. The original RAM namespace was absent;
no restoration exchange was attempted. Do not rerun the original controller,
terminal entry, claim, or failed stage. Original evidence:
`oled-staged-controller-r1/execution` and
`oled-staged-experiment-r1/terminal-launch-r1`.

A separate one-use recovery **PASSed in 10.340 s**. It retained the exact
ownership, no-symlink, tmpfs, storage and helper checks, placing a fresh private
namespace beneath existing root-owned 0755 `/run/initramfs`. No `/run` mode
change was needed. Five actual ARM64 staging/helper cases and five coordinator
cases passed before execution. Preflight, RAM staging, one state exchange and
final authenticated observation passed; the old V9 healthy selection SHA
`ed3a62d198a2e33d26093e079534315ae86ab28c91f48805463fd025c5b88b75`
is restored. Installed V9/V11 inventory and protected boot_b remain verified.
Evidence: `oled-fallback-restoration-r1/execution-r1/result.json`.
This recovery is terminal and must not be rerun. Retain owner
`40c18651355c8690fca8b8afe6b15283` and its private RAM/durable transaction records.

Current phone: V11 `persistent-native-root-v11`, release
`7.1.4-g359318de534f`, boot `ee0d166e-5e69-4db7-8bbd-6266352594ea`.
P2, persistent-state, SSH-identity and early-SSH services were active; current
SSH boot identity is verified. V11's legacy readiness marker itself lacks a
boot-ID field, reported explicitly by the observer. No OLED module/frame run
or later reboot occurred. No current user action or Ready request is pending.

Next: diagnose the target reset before another OLED boot. Mounted pstore was
empty. The exact OLED DT has no ramoops node despite built-in pstore support;
empty logs do not establish cause. The shipped startup observer matches the
frozen source, and built-in MDSS/DSI can run before an explicit panel-module
load. Improve bounded startup failure evidence or verify a board-supported
crash-log backend before proposing another experiment. Preserve all compiled
kernel/modules/payload/signatures and both consumed OLED claims. Carry the
verified private-RAM-parent fix into a separately qualified future controller;
never edit executed sources or treat recovery as target success. Independent
SID-5/thermal audit remains secondary to this startup failure. Evidence:
`oled-startup-failure-r1`. The historical waiting paragraphs below are superseded.

Latest r76, 2026-09-11: **r75 remains fully prepared and waiting for fresh
Ready**. No password window or test was started on automatic continuation.
The retained terminal entry hash and pending exact claim were checked unchanged;
its execution directory is still absent. Use the r75 Ready instructions below.

Independent kernel diagnosis localized the boot warning: SID 5 is the declared
PMR735B, and its PMIC_TYPE (0x104) revision read returns -EIO before GPIO and
temperature-alarm children can be populated. Actual authenticated sysfs readback
in 0.363 s confirms PMICs 0-4 bound and SID 5 unbound on the same source boot.
The arbiter's printed 0xcf08 is a status offset. Neither chip absence nor a
specific firmware-access cause is proven. Compare the ASUS stock inventory
before changing this declaration; do not suppress the warning or probe registers.

The exact config also has `CONFIG_QCOM_SPMI_TEMP_ALARM=m`; the metadata query
reported no thermal-zone types beginning pm or battery. Module packaging/load
and alarm binding need a separate audit before claiming PMIC thermal coverage.
These are independent follow-ups, not a diagnosis of the missing staging files
or a change to the prepared OLED trial. Evidence:
`pmic-sid5-investigation-r1/result.json`. No phone writes, driver rebind, module
load, kernel build, claim consumption or reboot occurred.

Latest r75, 2026-09-11: **fully prepared; waiting for fresh Ready** to unlock
sudo on the Deck. No old availability reply may start this session. The fixed
entry is `oled-staged-experiment-r1/terminal-launch.py`, SHA
`9f3f39063cfd6827de0fc8a2f99cdef540464bc981699c5bf2cd50f850494589`.
Run it through retained exec PTY **44286** with the command in
`oled-staged-experiment-r1/ready-preparation-r1.json`. Terminal ownership and
foreground/session checks passed from that actual terminal. Shell PID/SID is
251096, start 2915076, pts/1, host boot e3393ab5-0cf9-43fd-8bcb-020cf78b1f1b.

The entry performs the local touch askpass authentication, then two independent
noninteractive sudo validation children in the same controlling terminal, and
only then invokes the qualified trial with authentication disabled. Cached sudo
can satisfy the initial authentication without opening a window. No password
is stored and no sudo policy changes were made. Ten focused tests pass in
0.298 s (2.319 s runner): auth failure, either reuse failure, changed source,
foreign terminal, failed qualification, concurrent owner and reused entry all
refuse before starting another trial. Actual sudo reuse is still unproven.

The exact new claim `oled-staged-source-05941-r1` is registered **pending**, not
consumed: 1393 bytes, mode 0600, SHA
`03e8adafe37cef0a5f78e281cba5ce01df1f21e7a674431246013aa4ffade565`.
The old OLED claim remains consumed. No old record was reset or overwritten.
Full preparation passed in 0.271 s, and the final actual phone
preflight passed in 2.833 s on the same de90d177 headless boot,
with original shutdown, staged helpers, old healthy selection, installed
V9/V11 files and protected boot_b verified. No phone write or reboot occurred.

On fresh Ready, perform only brief terminal/pin checks, immediately dispatch the
prepared command and direct the user to the local password dialog. The user
need not wait beside the phone during the approximately 23-minute automatic
boot recording. Keep USB connected. Do not rerun the exclusive terminal entry
or boot claim after entry; inspect its retained result/owner. Runtime output:
`oled-staged-experiment-r1/terminal-launch-r1`; underlying trial:
`oled-staged-live-driver-r1/trial-launch-r1`, controller:
`oled-staged-controller-r1/execution`. Module/frame qualification is already
prepared; actual OLED boot proof must precede any hardware component run, and
an illuminated frame still requires separately fresh physical readiness.

Latest r74, 2026-09-11: the staged boot controller and downstream display
qualification chain now validate. Eleven privileged handoff boundary sources
match the actually tested predecessors with only exact path/digest substitutions.
The retained actual UID0 guardian / UID1000 handoff remains applicable; this is
scoped inheritance, not a new authentication or current credential proof.
Current process/admission wiring was separately replayed. Live qualification is
`aeb2809792c10bc31d85c304003a7ade78f32846316fb11f90a66de346ddabe6`.

The component monitor now reads only the new staged controller/launcher and Q2
source. Completed boot proof also verifies the original fresh source-preparation
receipt. Tests reject missing preparation and the consumed failed predecessor.
The module and frame coordinators follow this new qualification chain.
**109 additional cases pass**, including 24 provenance, 19 monitor-session,
17 module-host and 17 frame-host cases. The unchanged real 20-second frame timer
was inherited after verifying that frame logic changed only dependency hashes.
No kernel, payload, selector or framebuffer helper rebuild was needed.

Evidence is `oled-staged-experiment-r1/integration-result-r74.json`. Updated
qualification hashes: monitor `93548237db2e9f7a52bdd38049515e231165b5a31ae378ae1d2c6d7ed4055456`,
module `cef925a709308d54c1f544c2abc26e8e5c3c435b384bda706713e1ff32b51397`,
frame `1abda57152e28ec3ebb832ca6b9812626965b77760400837f974a3aa11fb18bf`.
Previous display sources/qualification records are retained under
`display-bindings-before-r1`. Old executed boot source/results remain untouched.

No phone action, password window, claim registration/consumption or reboot
occurred in r74. The last actual phone observation remains the r73 preflight.
Next: complete the fixed same-terminal launch entry and its two sudo reuse
checks, then prepare the exact separate pending claim. Only request fresh Ready
once the complete entry has been reviewed and can start immediately. Privileged
handoff and downstream display binding are no longer pending; current sudo
authorization and actual OLED hardware results are still unproven.

Latest r73, 2026-09-11: the new staged controller imports and validates its
32-file input lock. Preparation is now part of admission: the closed predecessor
and actual RAM staging must match; a fresh read-only route observation must
finish within 15 seconds before admission. Failed observation cannot consume a
boot claim. Its attempt/output remains exclusive. The old trial stays consumed.

**76 focused tests pass** (18 preparation, 32 launcher/credentials, 26 admission).
They exercise actual receipt validators, missing/stale/changed preparation,
process identity, cleanup and refusal before claim consumption. All **four full
flow fixtures pass in 25.574 s**, including source abort and early/late fallback.
Privilege, USB and boot boundaries are explicit fixtures, not hardware proof.
The first flow run found a derivative path to absent selector files; the reader
now uses the exact retained installed-selector inventory. No selector rebuild.

The new Q2 controller's exact generated observer is byte-identical to the r72
phone-tested script. Its actual authenticated recheck **PASSed in 2.883 s** on
boot `de90d177-3532-49e0-9bfd-8f8c65889a8d`. It verifies staged helpers, physical
guards, old healthy selection, original shutdown, no reboot intent, installed
V9/V11 files and unchanged boot_b. The host source is clean `b0da65a7`, digest
`9e8efaba23afb18d3c41649eb3700786db15fe68e44b8748de9eabe563f95725`.
Evidence: `oled-staged-experiment-r1/integration-result-r73.json` and
`source-preflight-recheck-r1`. This diagnostic is not live admission.

No password window, new claim registration/consumption, reboot or phone write
occurred. Privileged handoff qualification and module/frame provenance still
need integration before requesting Ready. New paths are
`oled-staged-live-driver-r1` and `oled-staged-controller-r1`; old executed source
and results are preserved. Keep the kernel, modules, payload, wrapper and A01.
The persistent sudo terminal remains available subject to a fresh identity check;
password reuse across child processes still awaits actual authentication.

Latest r72, 2026-09-11: the missing preparation now **PASSes on the phone**.
The existing guarded source-staging function copied only its three exact helper/
custody files into a fresh root-owned RAM namespace in **1.323 s**. Owner is
`e7bb639c01a3ee395e7f6c98fd922bf5`; runtime path is
`/run/rog5-oled-05941-e7bb639c01a3ee395e7f6c98fd922bf5`.
No state exchange, shutdown replacement, reboot or partition write occurred.
Preserve the one-use staging result; do not restage this namespace.

The actual generated read-only source/route preflight then **PASSed in 3.011 s**,
authenticated on the same headless 05941 boot. It verifies RAM contents/custody,
original shutdown, absent OLED transaction, old healthy selection, physical
storage/power guards, installed V9/V11 files and the unchanged protected boot_b.
The script differs from the qualified reader only in the exact new owner,
receipt and custody hashes. Evidence is `oled-staged-experiment-r1`; the full
read-only preflight must be rechecked briefly before a future mutation.

The separate integration checkout `oled-staged-controller-worktree-r1` is now
`b0da65a7`. Its new experiment `oled-staged-source-05941-r1` binds the same exact
OLED artifact profile, manifest, trial ID, signed wrapper and A01 as the failed
attempt, with a separate one-use experiment identifier and an explicit staged-
source preparation requirement. Eleven admission tests pass (0.314 s runner),
and all 228 prior claim records remain byte-identical in the source registry.
The old consumed claim stays consumed. No new claim file was registered or
consumed on disk. Kernel, modules, payload, wrapper and A01 need no rebuild.
A new isolated live controller and admission binding remain to be integrated;
this source change alone does not authorize a boot.

The user asked to reuse sudo. A noninteractive check returned password-required
in 0.010 s, so the old authentication is not available to a new process. A live
persistent terminal is prepared: exec session 44286, shell PID/SID 251096,
start 2915076, pts/1, host boot e3393ab5-0cf9-43fd-8bcb-020cf78b1f1b.
Use the same controlling terminal for future sudo-capable launches and test two
child processes after the next fresh authentication. Cross-process reuse is
**not yet proven**. No sudo policy was changed or password window opened in r72.
Keep bounded credential refresh during active work; do not reuse a dead handle
or an old Ready. The next hardware session is not yet ready for the user.

Latest r71, 2026-09-11: fresh Ready immediately launched the prepared OLED
session. **Authentication succeeded**, with no timeout or retained password.
The launcher consumed the exact OLED claim, then stopped at its first read-only
preflight. The controller is terminal **FAIL**; only `preflight` was entered,
no phase completed and no reboot, state exchange, exitrd change, RAM transfer or
partition flash occurred. Preserve `oled-live-driver-r1/trial-launch-r2` and
`oled-controller-r1/execution`. **The OLED claim is consumed and cannot be reused.**
The r70 Ready instruction is now historical; do not launch either old entry.

The exact cause is missing source RAM staging, not a USB link or password
failure. Authenticated SSH completed in 0.734 s, but the generated observer
raised `FileNotFoundError` for the expected `rog5-oled-05941-ba670e08…` namespace.
The controller correctly requires staged recovery helpers before preflight.
The host-only preparation and full-flow fixtures had not established that the
helpers were actually staged on the phone. Do not remove `verify_runtime()` or
weaken that predicate. The missing prerequisite belongs before live admission,
claim consumption and the request for Ready.

Independent authenticated health passes in 1.541 s at 23,822.95 s uptime on the
same headless 05941 boot, with the old healthy selection still restored. The
expected staging path is independently absent. Credential refresh stopped
cleanly; the controller and transport processes are gone. The user is released
and no password or physical-response prompt remains active.

A two-case regression replays the actual staging/observer functions with real
files in a uid0 user namespace: unstaged preflight refuses without mutations;
staging then preflight passes while selection and shutdown bytes remain exact,
and a second staging attempt refuses. Both pass in 0.065 s. Hardware telemetry,
unit state and tmpfs identity remain explicit fixtures; this is not phone staging.
All 64 executed source/evidence files are archived by `oled-preflight-failure-r1`.

The retained kernel warning/error log also contains a boot-time SPMI type read
failure on SID 5, address 0x104, at 0.143 s. The printed 0xcf08 is the arbiter
status offset, not the PMIC register address. PMIC probing returned -EIO; this
requires separate hardware/DT investigation and is not the cause of the missing
RAM directory. Pstore has no records. General health PASS is not a claim of a
warning-free or fully qualified kernel.

Next: prepare a separately reviewed successor experiment with the source RAM
staging step included. Run its exact read-only source/route preflight on the
actual phone and retain the boot/owner/files-bound receipt **before** admission,
claim consumption or requesting Ready. Preserve the consumed OLED profile and
all failed results. Reuse the compiled kernel/modules and passing component
checks wherever their inputs remain exact; determine the new experiment's
canonical claim/identity requirements before packaging or rebuilding anything.

Latest r70, 2026-09-11: the OLED launch is prepared again after the r69
password timeout. Authentication attempts now have separate exclusive receipts
under `oled-live-driver-r1/boot-authentication-r1`. A shared flock excludes
concurrent launches; incomplete attempts, live prior owners and unreaped
credentials refuse. Fresh password availability is required for every retry.
The fixed next boot output is `trial-launch-r2`, created only after successful
authentication. Original r1 failure files remain exact and are checked before
preparation. The original boot execution function and claim-consumption guards
are unchanged; no attempted boot may be retried.

The revised launcher passes 34 focused cases in 0.896 s. Display provenance and
monitor checks pass 22/19 cases in 0.436/1.698 s, and module/frame host checks pass
17/17 cases in 1.937/3.581 s. Their runtime function bodies are unchanged;
only the fixed launch path and dependency pins changed. The previous actual
20-second component test is inherited without rerunning it. Integrated qualified
frame reading passes in 0.017 s and read-only boot preparation in 0.207 s.
No password window, claim consumption, controller execution or display action
occurred in r70. Reuse the existing kernel, DT, modules, signed wrapper and A01.

Fresh authenticated phone health passes in 1.347 s at 23,516.93 s uptime: same
headless 05941 boot, restored old selection, boot-bound readiness and physical
guards. The user has not yet answered whether the previous password window was
visible/usable. Do not infer a password or keyboard diagnosis. On a fresh Ready,
start the prepared launcher immediately; do not reuse the r69 Ready. The future
physical display prompt still requires separate fresh availability after the
new OLED boot, full capture, module loading and frame preparation.

Latest r69, 2026-09-11: fresh Ready immediately launched the prepared OLED
session. Authentication timed out after its 300-second limit. The Deck window
was observed, but no user response establishes whether it was visible or usable.
The owned authentication processes were reaped and the window is gone. Launcher
`oled-live-driver-r1/trial-launch-r1/result.json` is terminal FAIL, with no claim
consumption and no controller execution. No phone command or reboot occurred.
Preserve this entered launcher directory; the old launch instruction is no
longer executable. Do not clear it or retry the same entry. The exact pending
OLED claim remains unchanged. Resolve the authentication interaction and prepare
a reviewed fresh launch path before requesting availability again.

The retained successor touch/GPI/GENI twins were independently checked against
their guest receipt and exact 05941 vermagic in 0.022 s; all six copies match.
The earlier successor guest registration/unload result remains 3.797 s, with
GPI retained until guest poweroff. Updated the stale front-touch guide to reuse
these artifacts and distinguish the OLED-only DT, which does not enable touch.
This is cached artifact evidence, not physical touchscreen qualification.

Updated 2026-09-10: **Denial Wayland is now the active long-term destination**.
The user has reprioritized **kernel and non-cellular hardware bring-up first**.
Defer Denial/Flutter builds while qualifying the kernel: stable boot and recovery,
OLED scanout, front touch, Adreno with minimal DRM/EGL tests, and power management.
Track Wi-Fi, audio, Bluetooth, sensors and cameras explicitly; do not call the
kernel fully working while required hardware remains unqualified. Denial remains
the eventual application layer. Prepare hardware trials completely before Ready.
After each run and goal turn, review priorities, repeated failures and measured
bottlenecks using the [feedback loop](development.md#feedback-after-each-run).
The exact successor kernel is now running on the phone: release
`7.1.4-g05941d04803f`, bundle `kernel-hw-05941-a607a2bb249c918b`, boot
`de90d177-3532-49e0-9bfd-8f8c65889a8d`. Fresh Ready immediately launched the
prepared trial and local touch authentication succeeded. Exactly one 128-MiB
RAM boot completed; the one-use claim is consumed. No partition was flashed.

The full 23-minute physical capture PASSed, including ordered route/firewall/
profile/address cleanup and worker reap. Independent authenticated target health
PASSed at 108.19 s and again after terminal cleanup at 1,383.39 s on the same
boot. Healthy commit was 64.957 s; boot-bound readiness and physical/storage/power
guards passed. No later USB transition was recorded after target enumeration.
These are real headless-kernel observations; OLED/touch/GPU remain unqualified.

The automated controller result is **FAIL** and must stay FAIL. Its initial
health query encountered the still-enumerated fastboot device immediately after
RAM transfer. It failed before waiting for the new USB gadget. Later fallback
location hit a separate host adapter error: unpacking three values from the
network helper's two-value return. That error preceded network ownership or any
fallback SSH command. Old selection eligibility was **not restored during that trial**. The separate
r45 recovery below restores it without changing the original FAIL result. The signed installed fallback was not
modified, but this run did not physically qualify fallback boot/restoration.

The host fixes are now integrated in `successor-live-driver-r1`, with the exact
executed sources archived at `post-trial-driver-fixes-r1/executed-sources` before
editing. The two-value adapter defect also existed in `ssh-worker.py`; its tests
now call the real network adapter with only the subprocess result simulated.
A negative replay reproduced that sibling failure. Final affected regression
checks pass **63 cases in 53.078 s**, including four complete simulated flows.
The earlier integrated transition/route checks passed 32/25 cases. These are
host checks, not a second phone boot or qualification of automatic recovery.

Regression fixtures now tolerate retained terminal execution and consumed claims
without changing production guards. The actual 30-file input lock passes in
0.104 s; the old launcher refuses `trial was already attempted`. Its old live
qualification remains byte-identical, historical and stale for the new sources.
Do not rerun the consumed trial or treat these changes as a new admission.

The separate exact-current-boot recovery now **PASSes on the phone**. In
**7.656 s**, authenticated preflight, RAM staging, one atomic state exchange,
read-only restoration observation and final full health all passed. The original
V9 healthy selection SHA `ed3a62d1…` is restored; the running kernel/boot identity
above is unchanged. Final observed uptime was **3,548.72 s**. This is restored
next-boot eligibility, not a physical fallback boot or a repaired R01/S06 result.

The private `current-target-restore-r1` coordinator is terminal and one-use.
Preserve its `execution-r1`, original custody, RAM entry/completion, and durable
`.kernel-05941-transition` records. That transaction now retains the new healthy
record in `exchange` and the old backup in `old-backup`. Do not rerun restoration,
remove entries or reuse the consumed kernel trial. The old V9/V11 wrapper remains
unchanged. Subsequent read-only checks must use the separate `restored-health.py`
predicate: the original target predicate correctly requires the now-replaced
new selection and will refuse the restored one.

Preparation passed 17 real-ARM64-helper/guard cases (194.746 s summed case times),
11 restored-health cases and nine host ordering/output cases. Hardware telemetry,
systemd and tmpfs are explicit offline fixtures; the final SSH results supply
physical evidence. A fixture-only attempt to edit a read-only custody file
stopped the first batch; its result was retained and only remaining cases resumed.

The OLED successor payload is now composed as byte-identical twins under
`oled-successor-payload-r1`: **4.877/4.625 s** in sequential 512-MiB/no-swap
scopes. Bundle `oled-05941-a2be906cd7b36636`, trial
`b52ead05459f96ae5acde920c903d4ca3138a96083a7b4dbabfc941274fcb242`, archive
SHA `d108d868…`, 57,774,563 bytes. It changes only the descriptor and catalog;
**722 of 724 members**, all 32 loose module copies and the nested radio archive
are preserved. Ten focused real-newc preservation tests pass in 0.026 s.
Pair with the retained display-only DT `2ee1ed4b…`; do not rebuild the kernel or
matching REFGEN/panel modules. The signed wrapper completion below supersedes unsigned packaging status;
the new OLED profile remains unregistered, with no boot admission.

Fresh read-only phone health passes at **4,347.54 s uptime** on the same boot
with old selection still restored. The 2.045-second probe verifies both exact
display modules under `/run/rog5-native-wifi/display-trial`, unloaded, with no
current-release files in the standard `/usr/lib/modules` search tree, no DRM
nodes or backlight, and no fb0. This describes the current headless runtime;
new-DT early probing and future effective-root autoload still require checks.

OLED signed bundle and boot-wrapper twins now **PASS** in
`oled-boot-package-r2`, using the exact new identity above. Both wrappers are
134,217,728 bytes, SHA `08922813…`; raw size 129,966,080 bytes requires the
128-MiB envelope. Bundle signature, both AVB integrity checks and the sealed
verifier pass. Manifest SHA `95d0748d…`, recovery SHA `b9099828…`. All 18 stages
completed without cleanup errors. These are offline artifact checks, not a boot
admission or physical display result. Do not rebuild these successful twins.

The first attempt, `oled-boot-package-r1`, is terminal **FAIL: cgroup OOM**.
Both signature receipts survived; the second wrapper is partial. Preserve all
entered output. Kernel evidence shows 503,865,344 dirty file-cache bytes at the
512-MiB cap; this was a local packaging limit, not system-wide exhaustion.
The unchanged runner and exact inputs succeeded in a fresh output with
`MemoryHigh=256M`, unchanged `MemoryMax=512M`, and `MemorySwapMax=0`: about
75 seconds wall time and 361.5 MiB peak per systemd. Keep this early throttling
policy for future packaging. Twenty-two focused checks had passed in 0.389 s.

The refreshed `oled-root-autoload-r1` static check passes in 0.794 s for release
05941 and the exact new payload. It inherits the retained root inventory only
after checking its pinned receipt and both unchanged image identities, streams
the new 724-member archive/catalog, pairs loader/init source, and repeats four
host kmod dry-run refusals with the new inert display modules. No configured
automatic display loader was found. This does not execute Arch coldplug or prove
absence of early built-in MDSS probing with the display DT. Final root content,
wrapper/controller integration and physical checks remain necessary.

The OLED state-transition components are now separately prepared and tested.
`oled-state-exchange-r1` retains the Rust exchange algorithm, with the new signed
manifest and a fresh `.oled-05941-transition` namespace. Old V9 record remains
`ed3a62d1…`; OLED pending/healthy records are `e77c2e20…` / `aea03ea5…`.
The two static ARM64 PIE builds match SHA `472dfd36…`, 1,253,144 bytes, in
1.262/1.004 s. Fourteen Rust tests pass, including retention of all consumed kernel
transaction records and refusal of prior-kernel states. ABI header checks and
six real ARM64/v1/v2-helper QEMU scenarios pass (0.563 s); no phone write occurred.

`oled-state-guards-r1` recognizes the actual source bundle/kernel 05941 and
unchanged V11 fallback, and checks all six retained kernel transaction files.
Its original physical guard is inherited unchanged; 31 actual ARM64 guard/helper
cases pass in 87.309 s, including missing/tampered/extra prior records, unsafe
power/storage/identity, uncertain outcomes and no retry. Physical telemetry and
mount/device numbers are explicit offline fixtures.
`oled-source-actions-r1` prepares the new RAM/exitrd namespace and source-abort
observer. All 16 file-operation tests (0.644 s) and 22 read-only reconciliation
tests (0.391 s) pass in the intended uid0 user namespace, with telemetry and
reboot calls mocked. All eight action/observation scripts generate successfully.
The separate r49 assembly below now integrates these components; live OLED
admission is still absent.

The fresh authenticated source check passes in 2.094 s at **5,849.97 s uptime**:
same 05941 boot, old selection restored, exact retained prior transaction,
no OLED transaction or exitrd intent, original shutdown and reboot helper.
The initial read-only probe used `/usr/libexec` outside the exitrd and failed;
its receipt is retained. The corrected probe checks the actual helper under
`/run/initramfs/usr/libexec`. No RAM staging, state exchange, reboot or flash
was executed. Current-source identities remain time-bound observations.

The separate `oled-live-driver-r1` / `oled-controller-r1` cohort now passes
**all four offline assembled flows** across 22 unchanged controller phases:
target capture plus post-health, early fallback, late failure with separate
fallback capture, and pre-reboot exitrd/state restoration. Failure scenarios
correctly retain controller FAIL while proving restoration. The target scenario
passed in `full-flow-tests-r2`; only the three remaining scenarios were run in
`full-flow-tests-r3` (17.928 s). USB/SSH/privilege, admission, RAM transfer and
recording time are explicit fixtures; real host capture processes are reaped.
No physical OLED boot or privileged handoff is established by these tests.

The cohort uses a separate integration checkout, `oled-controller-worktree-r1`,
commit `30b72c12`. Exact OLED composition classification is added alongside the
unchanged default headless profile. The OLED profile SHA is `0fc132e8…`; mixed
DT/payload tuples refuse. The new `verified-oled-hardware-boot.py` explicitly
refuses before claim/snapshot/USB access while its composition admission is
unprepared. Nine profile/refusal checks pass in 0.077 s. Existing recovery tools
in the progress checkout and frozen compiled source are untouched.

Installed V9/V11 inventory is inherited independently of new source custody,
and is rechecked by the controller's live route query. Three actual installed
ARM64 selector scenarios pass in 0.332 s. Eleven new ARM64 fallback-observation
cases pass in 52.193 s with real tmpfs/readers/helper and explicit storage/power/
installed-image fixtures. Twenty health cases pass in 0.035 s; the new source
predicate also validates the retained actual r48 snapshot with restored OLD
selection. Seventeen transfer-boundary/process cases pass in 3.675 s.

New host-only custody owner `ba670e08f11d4c3f8e2f95573689619f` binds the exact
r48 source snapshot and old record. Its receipt SHA is `db852a12…`, custody SHA
`c6ebef80…`; it is not RAM-staged. Preserve the earlier custody separately.
Dependency-ordered pin refresh keeps all 59 cohort source references aligned.
Do not rerun `prepare-cohort.py` over the integrated sources. No live execution
directory, input lock, live qualification, registration or claim was created.

The r50 OLED composition run now **PASSes all seven A01 checks** in
**81.851 s**, including wrapper, signed target, archive, paired-root runtime,
module load, firmware and timing/transport. Evidence is `oled-a01-r2/a01/result.json`,
SHA `abcf577d…`, verified by clean source `30b72c12`. Both full logical root-image
hashes match before and after the VM; their metadata is unchanged. The exact
kernel VM exited normally, its container was removed, and its attach process
and group were reaped/closed. Physical OLED probing, scanout, touch and GPU
remain unqualified; virtual hardware cannot establish them.

Integration source is now `462cef05` in `oled-controller-worktree-r1`. Its only
changes after A01 are the explicit OLED boot-adapter evidence binding and tests;
the adapter correctly retains A01 verifier revision `30b72c12`. Twelve profile
and claim-refusal checks pass in 0.136 s. The new 31-file input lock SHA
`d905fc12…` validates in 0.098 s and contains the OLED A01, wrapper, payload and
DT evidence. The current dependency map is `oled-live-driver-r1/pin-refresh-r5.json`.
Do not rerun the initial cohort transformer or substitute headless A01 evidence.

Admission, privilege-fixture and launcher tests pass 24/10/21 cases in
0.447/0.528/0.772 s. Real host processes are used with explicit sudo/root/claim
fixtures; these do not prove privileged handoff. The actual noninteractive
read-only privilege probe stopped in 0.043 s: `sudo: a password is required`.
Its child was reaped, no root probe ran, and no password window opened. Preserve
`oled-live-driver-r1/privilege-probe-r1`; any next attempt needs a fresh output.
No phone query, write, reboot, claim registration/consumption, live qualification
or execution directory was created in r50. The binding receipt is
`oled-live-driver-r1/composition-binding-result-r1.json`.

The first A01 attempt is retained as FAIL: 23.970 s elapsed before missing
ignored Android boot tools stopped wrapper inspection. Five exact tools/template
files were verified against the frozen checkout and staged into Q; bytecode
caches were omitted. The new runner validates these prerequisites before image
hashing. The copied touch askpass executable mode was also restored to 0700
with unchanged bytes and a passing metadata/code preflight. These are host
preparation fixes, not kernel or phone failures.

Next: finish the prepared actual privileged handoff, remaining live qualification
and fresh one-use lifecycle, then fully prepare display capture, late REFGEN/panel
loading, endpoint discovery/blanking and the physical prompt before fresh Ready.
Reuse the passing kernel, modules, payload, wrapper and A01 result. Current-source
health remains r48 uptime 5849.97 s and requires a brief live recheck before
mutation. The r55 authentication outcome and prepared retry are recorded below.

The prepared host authentication check ran immediately after fresh Ready in
r55. Attempt `oled-live-driver-r1/privilege-probe-r2` is terminal **FAIL:
authentication timeout**, 300.014 s. The password window was observed in the
Deck window tree at 04:56:10 UTC, but authentication did not complete. Stderr
was empty; no user report establishes whether the window was accessible or its
keys worked. Do not infer a wrong password or a keyboard defect from this result.

The bounded runner killed its owned authentication group and reaped sudo.
Terminal inspection found no remaining dialog/probe process or password window.
Neither capture nor SSH privileged profile ran. No phone/network/claim action,
boot admission or phone change occurred. Preserve the attempt; never reuse r2.

The later fresh Ready in r56 immediately started the prepared r3 command.
**Actual host authentication and both privileged handoff profiles PASS in
13.378 s**. `oled-live-driver-r1/privilege-probe-r3` is terminal. Capture and
SSH profiles each ran the real root guardian with all four UIDs zero and a
runuser child with deck UID/EUID/GID/EGID 1000. Both child outputs match their
retained raw results, stderr is empty and all launcher/root/deck processes were
reaped or subsequently confirmed gone. Authentication exited zero without a
timeout or retained password. The password window closed.

Receipt `oled-live-driver-r1/handoff-preparation-r2/completed.json`, SHA
`b38eff45…`, binds the raw/proc/result evidence to clean Q `462cef05`, exact
worktree digest and host boot. This is actual host privilege evidence, with
zero phone/network/claim actions; it does not grant boot admission or qualify
OLED hardware. Preserve r2 FAIL and r3 PASS; do not rerun either. No password
request, retry or operator countdown remains pending. The user is released.

Continue live OLED lifecycle/registration and the admitted display
load/discovery/blank/frame/brightness integration. Human display availability
requires a separate fresh request only after the physical test is fully
prepared. Normal future privileged actions still need current credential checks;
this receipt does not promise an indefinitely reusable sudo session.

The r52 `oled-display-component-r1/endpoint.py` now provides an import-only
endpoint reader, guarded zero-brightness write/readback and subsequent framebuffer
sysfs discovery. Twenty tests pass in 0.131 s using actual files, symlinks and
file descriptors in a user namespace, with explicit sysfs write emulation.
No component code ran on the phone and actual sysfs layout is still unverified.
The exact compiled panel source matches the audited source SHA `45e8bcb9…`:
its default/max brightness is 1023 and it exposes no hardware brightness reader.
Zero command/readback success is not an optical-darkness or full-health result.

Backlight identity checks pin the OLED descriptor, expected boot/kernel, one raw
1023-level endpoint, DSI panel driver and DT ancestry. Only zero can be written;
missing/changed authorization, replaced/symlinked attributes, failed/short writes
and nonzero readback refuse. The exact backlight can be blanked before requiring
fb0, so framebuffer failure does not unnecessarily delay that cleanup action.
Framebuffer discovery then requires zero, the same display subtree, msmdrmfb,
1080x2448 at nominal 60 Hz and 32 bpp. It does not open /dev/fb0 or prove pixel
layout, refresh timing, visible output or GPU acceleration. Enclosing admitted
module-load/health/monitor/deadline and fixed-frame integration remain pending.
The r51 prepared authentication source was unchanged in r52; r55 records the later attempt.

The r53 Rust fixed-frame helper is now prepared in `oled-frame-r1`. Independent
ARM64 static-PIE builds match SHA `ed3e8081…`, 1,252,408 bytes; final validation/
build took 2.770 s and the independent build 1.056 s. Rustfmt, Clippy with denied
warnings, 13 release tests (0.02 s) and cross-compiled framebuffer ABI assertions
pass. Actual ARM64 C structure bytes feed the Rust decoder under QEMU; native
and ARM64 render outputs match SHA `859231da…`, 10,653,696 bytes with 4352-byte
fixture stride. Rendering took 0.031/0.125 s. The helper buffers at most one
16-KiB row, accepts bounded layout records on stdin, and emits metadata or one
fixed frame on stdout. It has no device-open, ioctl, module or backlight path.

The inspected preview has an up-arrow, TOP label, RGB bar, asymmetric corner
markers and border. It is generated host evidence, not an OLED photograph.
Malformed/truncated/extra records, interlace/rotation and output failure refuse.
Actual kernel depth24 XRGB (no alpha, offset zero) is recognized alongside
ARGB32. An independent ARM64 header check caught incorrect vmode/rotate offsets
in the first decoder and stopped before a usable ARM64 binary; corrected offsets
132/136 are now checked against C-produced records. Enclosing device/boot-bound
ioctl collection, fixed-frame write and low-brightness/blank controller remain.

The previously missing Rustfmt/Clippy 1.98.0 tools are now staged separately in
`rust-tools-r1`, verified against the retained release manifest hashes. They
work with the existing immutable compiler image, avoiding another repeat of the
known missing-tool failure. No systemwide install, compiler/kernel/package rebuild,
phone action or authentication attempt occurred in r53. The r51 authentication session
remains prepared and unstarted; a goal continuation does not count as Ready.

The r54 import-only `oled-display-component-r1/framebuffer.py` collects the
actual-layout protocol for that Rust helper. It requires the enclosing admission,
exact blanked endpoint/boot, sysfs 29:0 and root-owned character fb0. It first
opens O_PATH for inode validation, then reopens that owned descriptor read-only
through procfs. Only GET_FSCREENINFO/GET_VSCREENINFO are issued, with two equal
samples and renewed device/blank/admission checks around them. All descriptors
close on success or failure. No memory write, mode-set, mmap or backlight change
is exposed. Opening fb0 itself invokes kernel driver operations, so this remains
an admitted display action rather than a generic health query.

Thirteen tests pass in 0.150 s, with real descriptor/path/replacement behavior,
explicit character-device/ioctl fixtures, a real ENOTTY failure and actual ARM64
Rust decoding of the collector's record. All cases check for leaked descriptors.
Physical framebuffer open/GET ioctls are NOT RUN. The collector returns raw
capture, not a false Rust-layout or physical-scanout pass. Same-boot frame
creation/write, brightness session and enclosing load/health/capture/deadline
integration remain pending. Endpoint/frame binaries and prepared authentication
inputs remained unchanged in r54. The later r55 Ready/timeout is recorded above.

The r56 `oled-display-component-r1/frame.py` now connects the exact collector
record to the existing pinned ARM64 Rust renderer. It copies that 1,252,408-byte
ELF into a sealed descriptor, executes the owned descriptor for layout and frame
output, and streams at most 40,108,032 frame bytes with 4-KiB stderr and five-second
child deadlines. Timeout/error paths kill and reap the owned helper and close
all descriptors. No device or brightness access occurs.

The resulting frame is sealed against write, shrink and growth, with a receipt
binding the complete capture, boot identity, raw layout and renderer hashes.
Before device write, the enclosing action must compare a fresh admitted capture
with this binding. A matching receipt is not admission or physical evidence.
The actual ARM64 helper under QEMU reproduced the 10,653,696-byte fixture frame,
SHA `859231da…`, with describe/render times 0.021/0.122 s. Fifteen focused tests
pass in 1.221 s, including changed identity/node/record, replacement of the
renderer path, malformed layout, immutable frame, output/timeout/exit failures,
closed-pipe timeout, pidfd failure and sealing failure. Every case checks for
leaked descriptors. Device/sysfs/ioctl values remain explicit offline fixtures.
Receipt `oled-display-component-r1/frame-result-r1.json` is `787baaa3…`.
Actual framebuffer writes, bounded brightness and enclosing controller/load/
health/capture integration remain next; physical scanout is still NOT RUN.

The r57 import-only `oled-display-component-r1/write-frame.py` now provides
one admitted, entered write and complete memory readback from the sealed frame.
It verifies the full frame hash, consumes the frame's in-process attempt flag,
requires the enclosing durable entry callback, and compares a fresh GET capture
before opening the exact owned fb0 inode read/write. Every 1-MiB write/read chunk
rechecks admission, boot/endpoint/zero brightness, node and raw layout. Partial
writes stop immediately without retry; exceptions retain uncertain-write state
separately from acknowledged bytes. Cleanup errors retain prior write evidence.
All opened descriptors are closed; no illumination or mode change is exposed.

Nineteen tests pass in 3.855 s with the real sealed ARM64-rendered frame and
actual file I/O, descriptor ownership and cleanup. Character-node/sysfs/ioctl,
admission and durable-entry behavior are explicit fixtures. The successful
10,653,696-byte write/readback takes 0.097 s with 11 writes and matching frame
hash `859231da…`. Changes to boot, node, layout, brightness or admission stop
further writes. Short/corrupt readback, partial/uncertain write, entry uncertainty,
deadline and close failures refuse success. The original sources remain pinned;
no kernel, Rust or package rebuild was needed.

The exact clean 05941 kernel sources provide DMA fbdev read/write operations,
including deferred-damage wrappers and positioned I/O. Memory readback does not
prove damage completion, vblank or visible scanout. The ten-second deadline is
checked between syscalls; the enclosing bounded worker remains required for a
stuck kernel operation. Receipt `oled-display-component-r1/write-result-r1.json`
is SHA `da73f546…`. Bounded brightness/blanking and integration with the existing
admitted load/full-health/monitor/durable-entry controller are next. No physical
framebuffer write, phone query, authentication or human request occurred in r57.

The r58 `oled-display-component-r1/display-session.py` now joins the writer to
one fixed brightness request: **32/1023 for 20 seconds**, followed by the pinned
zero-only blank operation. It requires separate current cleanup ownership before
entry. The owner's durable frame/display intent carries the fixed brightness,
duration and cleanup value. A prompt event is queued only after successful frame
readback and nonzero brightness readback. Callbacks must already be installed,
bounded and nonblocking; no callback waits for the human response.

After entry, frame failure, normal health refusal, prompt failure, short/uncertain
brightness write and normal timeout all reach independent blank cleanup. A failed
zero request stays FAIL with no false blank result. Changed boot identity refuses
writes against the new boot. Deadline checks run after authorization callbacks
as well as before them, preventing an overdue callback from queuing a late prompt.
The enclosing worker, transport monitor and postcleanup full health are still
required; this component does not establish a hard hardware timing bound.

Sixteen tests pass in 23.933 s, including virtual-clock failures and a real-clock
production-duration check. That fixture reached confirmed zero in **20.003 s**
after the nonzero attempt (20.095 s total session), with 80 brightness samples.
The real ARM64 frame and file operations are used; sysfs/ioctl/device, admission,
monitor and durable entry are explicit fixtures. No OLED command ran on the phone.
Receipt `oled-display-component-r1/session-result-r1.json` is `d30d2168…`.
The first short-write test had an invalid no-newline sysfs fixture; correcting it
to canonical readback made the existing cleanup path pass without a runtime bypass.

Next, adapt the existing `buttons-module-monitor-r1` and
`buttons-module-physical-r1` components under the retained 20260908 CPU state to
the OLED identity, health, capture closure and prepared display phases. The
monitor proves bounded same-boot USB observation, not target recovery or health.
Reuse its owner/deadline protocol and the module-once loader; no new receiver
family, kernel/package rebuild or authentication retry is needed. Actual module
loading, OLED scanout, touch and Adreno remain unqualified. No human request is
pending; prepare the entire physical session before a fresh Ready.

The r59 `oled-component-monitor-r1/transport.py` adapts the existing pinned
module-monitor server/client/protocol in memory, preserving their original files.
Each OLED phase gets a separate boot/output context; the current source label
is Q `462cef05`. Source/current-headless/zero boots and outside namespaces refuse.
The original 660-second lifetime, 0.5-second sampling, one-second sample freshness,
permanent failure latch, Unix peer/socket checks and exact PID/start/argv guards
remain intact. The reviewed production `monitor.py` must be pinned with the
adapter and all three inherited sources. Reused output refuses before allocating
server resources. A finish still requires the owner's cleanup/health validator.

Twelve tests pass in 2.468 s with real child processes and Unix sockets, including
disconnect/reconnect latching, changed boot/admission/launcher/journal, dead PID,
wrong peer/socket inode, nonempty output and cleanup-gated finish. All test children
were reaped and sockets/FDs closed. USB, admission and physical cleanup/health are
explicit fixtures. `fixture-child.py` is test-only, not a production launcher.
Receipt `oled-component-monitor-r1/result-r1.json` is `1db833c4…`.
Production admission, exact closed OLED boot capture, fresh authenticated target
health, real USB sampler and post-component blank/health closure must still be
wired into this adapter and the r58 display session. No actual USB observation,
phone action, monitor job or human request is active. This reuses the existing
transport mechanism and does not create boot, recovery or target-health authority.

The r60 boot-controller qualification passed the production
`live-admission.py:qualification()` reader. All four full-flow replays pass in
14.843 s at Q `462cef05`; target is COMPONENT_PASS, while early/late fallback and
source-abort remain expected FAIL with restoration proved in their explicit
fixtures. The 31-file input lock passes in 0.162 s. Actual r56 capture/SSH root
handoff receipts match this exact source and host boot and are revalidated.
The historical r60 qualification is SHA `a60705b5…`, with 450 pinned
evidence files. It qualifies current software flows and actual host handoff only.
No phone boot, target health, display or recovery hardware result is added.

Two 1,682,152-byte replay requests are retained in ordered chunks below the
reader's 1-MiB per-file limit. Three mode0644 artifacts have exact private mode0600
copies; eight empty streams are represented explicitly in the archive manifest.
Original evidence is preserved. Initial assembly/validation failures are retained
under `qualification-preparation-r1`; the final production verifier passes. Future
assemblers must check size, nonempty content and metadata before writing the
canonical qualification, and finish all source/pin changes before final replay.

The r61 exact OLED claim is now **registered, pending and host-qualified** at
Q `538fab85a0cc809f0c9ff20a7ae64dd133d27b63` (clean source digest `ef59307b…`).
The sole registry addition is generated from the verified OLED expected fields;
all 227 previous record values are byte-identical. The 21 claim lifecycle tests
pass in 0.233 s, including pending preparation and permanent retry refusal.
The canonical OLED `.record` is SHA `51f8b2bf…`; its attempt remains unconsumed.
All 627 pre-existing claim files and global guards retain their bytes/inodes/
metadata. No OLED `.entered`, launch or controller execution directory exists.

Four derivative files change only digest constants; consumer functions and
actual privilege/authentication entrypoints are unchanged. The r60 source cohort,
input lock and qualification remain archived under `claim-registration-r1`.
The r56 actual root/runuser handoff is inherited with its original source identity
explicitly retained in `handoff-inheritance.json`; no new credential validity is
claimed. Pin map r7 and the 31-file input lock now match the final source.
The current 17 boot, 21 launcher, 24 admission and four complete flow tests pass
(66 cases, 21.898 s including runners). Full flows take 15.471 s internally;
external phone/USB/SSH/privilege/network/claim/time boundaries remain fixtures.

The new `live-qualification.json` is SHA `18b1717f…`, with 460 pinned evidence
files, accepted by the production reader. Every evidence input was normalized
and validated before publishing, without the previous archive failures.
The real read-only `trial-launcher.py:prepare()` passes in **0.256 s**, including
source/input/qualification/registry/pending checks. Result is
`oled-live-driver-r1/claim-registration-r1/result.json`. This is host preparation,
not phone admission, a boot or physical display qualification.

The r62 target module-loading component now passes **17 focused checks in
1.268 s** (1.384 s runner): `oled-display-component-r1/load-modules.py`, SHA
`ae33fc62…`. It reuses the exact 219,912-byte `module-once` ARM64 helper and retained
REFGEN/panel modules. No build was needed. After one durable paired entry, it
loads REFGEN, verifies its platform binding/regulator, then loads the panel once.
It watches for the backlight every 50 ms while the helper is still running and
issues the existing verified zero command immediately on discovery. Insertion
has a five-second deadline and bounded output/reaping; framebuffer discovery is
also bounded. Errors stop without unload or module retry. Separate cleanup
ownership can reassert zero after normal authorization is lost or brightness
changes after the first blank; a different boot refuses stale cleanup.

Tests use real files, held descriptors and child processes with explicit module/
probe/sysfs/health fixtures. The positive sequence takes 0.174 s, blanks during
panel-child execution and reaps both children. The exact ARM64 helper also ran
under QEMU and refused once with errno38 (unimplemented syscall in that path);
this is a refusal-path check, not a kernel insertion. Timeout, output overflow,
changed files/boot, uncertain entry, preloaded modules, missing framebuffer and
late brightness changes fail as expected. The original 15-case pass and initial
fixture setup failure are retained. Result `module-result-r1.json` is SHA
`a5da3d3e…`. No real module was loaded and the phone was not queried or changed.
The r61 boot qualification and unused pending claim remain unchanged.

The r63 completed-boot and fresh-health reader is now prepared at
`oled-component-monitor-r1/provenance.py`, SHA `f4c43495…`. It binds the fixed
actual OLED execution/launcher paths, exact consumed claim/current source,
1380-second capture and ordered cleanup, closed original processes, exact RAM
transfer, and the authenticated postcapture health script/raw result. Historical
boot admission proves that completed run only and grants no component authority.
The actual OLED claim check currently refuses `source BOOT_CLAIMED record still
exists`, as expected: its exact pending record remains unused.

Fresh component health reuses the existing read-only SSH worker and full target
validator. Results must follow capture closure, finish within 40 seconds and be
at most 120 seconds old. `modules`/`frame` phase directories are private; each
`health-before-rN` or `health-after-rN` is exclusive. Stale read-only health can be
refreshed into a new numbered receipt without consuming/repeating a hardware
attempt or replacing old evidence. The later owner must bind the exact path/hash
and enforce before/after role. Final 22 provenance/health checks pass in 0.505 s.
Root UID/time/source/claim/SSH facts in those tests are explicit fixtures.

The transport adapter now binds current Q `538fab85` and is SHA `7e754d20…`;
its 12 real-process/socket checks pass in 2.450 s. The unchanged original USB
sampler also passes an **actual host-only sample in 0.036 s**: target gadget on
`enp4s0f3u1u2`, `cdc_ncm`, product `ROG5 persistent root`, USB anchor `1-1.2`,
serial descriptor absent. No SSH or phone command ran. This is USB/route evidence,
not authenticated target boot/health. The executed sampler source is preserved
and its function matches final source. Evidence is under `source-refresh-r1`,
result SHA `4b1d7978…`; old r59 transport source/results remain archived there.
No actual monitor is running. The r61 boot qualification remains byte-identical.

The r64 rootless component owner and copied monitor entrypoint now pass their
software qualification: `oled-component-monitor-r1/session.py` SHA `3c32272f…`
and `monitor-launcher.py` SHA `f7e29311…`. `Owner` verifies the completed-boot and
fresh-health prerequisites, takes a global lock across module/frame phases,
copies the exact qualified entrypoint into a numbered monitor namespace, binds
the actual controller PID/start/argv, and owns start/probe/stop/reap. An unentered
monitor can be replaced with a new numbered monitor after closure; a durable
hardware phase entry refuses a later attempt. Monitoring grants no module/frame
action by itself.

The live sampler checks parent identity, admission hash and owner lifetime as well
as the inherited USB sample; failures stay latched. Finish requires the same owner/
boot/monitor, a terminal component result with no cleanup errors, a reaped remote
worker, exact zero-command evidence and newly collected full health after cleanup.
Normal owner loss does not prevent verifying independent completed cleanup.
The r65 module backend below now produces target records; the host coordinator
still must validate and convert them into monitor closure records.

Final **19 checks pass in 2.155 s** (2.624 s runner). A real host child and Unix
socket run through `Owner.start()` → live probe → gated finish → reaped exit.
A changed admission latches failure even after its bytes are restored; cleanup
can then finish the failed monitor without changing FAIL. Phone boot/health/USB
and the child bootstrap are explicit test fixtures. Global phase exclusion,
qualified source changes, old entry, stale health, wrong cleanup/health order,
boolean brightness and real process termination are checked. No production
monitor or phone action ran. The initial fixture used a terminal time before its
admission and was corrected; its failure remains retained. The initially qualified
phase-local lock was strengthened to one global lock before physical use, with
previous qualification/source archived.

`component-qualification-r1.json` is now SHA `438a0d20…`, accepted by the real
qualification reader against 13 source files and 15 evidence references. Result:
`session-qualification-r2/result.json`, SHA `76df5ebe…`. Existing endpoint/module/
frame checks are inherited only for unchanged source. Q `538fab85`, the r61 boot
qualification, and the unused OLED pending claim remain unchanged.

The r65 target module supervisor is implemented and passes **28 offline checks**:
22 real process/socket/pipe cases in 4.009 s, plus six root-owned RAM/source
validation cases in a private user/mount namespace in 0.008 s. Summed runner time
is **4.243 s**. `oled-module-backend-r1/backend.py` is SHA `303e9075…`;
its result is SHA `f14c31c0…`. Phone identity, sysfs and module effects are explicit
fixtures. No target SSH session, module insertion or physical display test ran.

The fixed backend accepts only sequenced start/lease/entry-ack/stop records bound
to boot, owner and monitor receipt. It uses the unchanged exact module and endpoint
sources, a global target flock, an exclusive RAM entry and host acknowledgement
before insertion. The lease is three seconds; total normal lifetime is 60 seconds.
Worker and helper process-group closure is checked. After entry, a separate
same-boot zero worker runs even on EOF, expired lease, component failure or blocked
normal worker. Cleanup has four seconds plus a two-second reap allowance. A stuck
kernel task can prevent closure; incomplete reap or zero readback remains FAIL.
These are command/readback checks, with no optical-darkness or scanout claim.

Actual fixture cases prove refusal of duplicate starts/entries/sequences, wrong
owner/monitor/ack, expired/missing lease, overlapping owners and retained entries.
They exercise real worker kill/reap, closed input/output, independent failed or
hung cleanup and changed-boot refusal. The root-file checks use the actual pinned
component sources. Their initial namespace setup could not read protected host
PID1 and failed before mounting anything; the corrected fixture captures its own
host namespace before unshare. That failure remains retained. Only those six
checks were rerun; the passing 22-case suite and earlier components were reused.

The r66 module host coordinator is now qualified offline in
`oled-module-host-r1/coordinator.py`, SHA `4f2e7e25…`. It uses the existing pinned
USB route/host-key/SSH credential checks and unchanged target backend. Exact
source files and manifest are staged only into private root-owned RAM. The host
reserves the module phase before opening the live command, and acknowledges only
the exact two-module intent. An uncertain transport start remains consumed.
Sequenced leases renew only while the qualified monitor is live; failure closes
input but retains a bounded interval to collect independent target cleanup.

Target identity, exact insertion results, zero readback, direct-worker and helper
group closure, raw output bounds and SSH exit must agree. Full authenticated
health follows observed host-side completion, then guarded monitor finish. A real
negative replay caught a coordinator bug: successful cleanup could mask a latched
monitor failure. It now verifies the finish reply, zero monitor exit and durable
monitor result before PASS. The original failed regression and source remain.

Final **17 checks pass in 1.941 s** (2.220 s runner), including the full stage →
module peer → cleanup → post-health → monitor-close sequence. Pipes, subprocesses,
target supervisor, staging files and private root/mount namespaces are actual;
SSH, phone identity/sysfs/insertion, boot proof and monitor/health are explicit
fixtures. The initial staging fixture mounted world-writable `/run`; the actual
parent permission guard refused it. Correcting the fixture to mode755 passed;
production guards were unchanged. A qualification-negative fixture was isolated
from future published records and its one affected test passed separately.

Qualification `oled-module-host-r1/result.json` is SHA `61ec008f…`; the real
qualification reader accepts it in **0.006434 s**, including unchanged r64 monitor
and r65 backend evidence. No actual SSH transport to the phone, health query, RAM staging,
module insertion or OLED boot occurred. All kernel/DT/module/renderer/boot
artifacts remain unchanged; no full boot replay or authentication was repeated.

The r67 target frame backend is now implemented in `oled-frame-backend-r1`,
SHA `1087ed7d…`, with **20 offline checks passing**:14 actual process/RPC/phase
cases in1.840s and six actual source/renderer/RAM metadata cases in0.039s
(2.136s summed runner). Capture/identity/frame/display effects and shortened phase
timers are explicit fixtures. The unchanged real ARM64 renderer and real20-second
display-component evidence are inherited, not repeated or relabelled.

It reuses the exact module backend's framing, owned fork/reap and independent
zero-cleanup implementation through a private imported instance, with a fixed
frame worker. All copied component/renderer bytes match retained hashes. The
worker obtains an acknowledged capture-only entry, collects zero-state GET data,
prepares a sealed frame, then waits for a Ready token bound to that prepared hash.
No frame write or nonzero command occurs before Ready. The one-use global frame
write entry is separate from preparation; expired availability closes and blanks
without consuming a write that never occurred.

Production limits are three-second leases,15s preparation,60s waiting for Ready,
35s active work and120s total, followed by independent four-second zero cleanup
and bounded reap. Leases cannot extend a phase deadline. After Ready, the exact
frame/brightness32/20-second intent must be acknowledged; the visible-command
prompt is emitted immediately after brightness readback, without waiting for a
human reply. Fixed20-second timing remains in the unchanged display component.
The parent independently stops blocked work and checks direct-child and helper
group closure. Changed boot refuses stale zero; cleanup failure stays FAIL.

The checks cover waiting unlit, missing/early/wrong/repeated Ready, blocked capture
or display, disconnect while lit, changed boot, bad intent/prompt, failed cleanup,
prior entry and wrong capture provenance. Namespace tests validate the actual
copied renderer and sources and reject changed bytes, symlinks, bad modes,
changed manifest and consumed frame entry. Existing namespace lessons were
applied immediately; both suites passed on their first run. Result SHA:
`f310d724…`. No actual target worker, frame preparation or physical test ran.

The r68 frame host coordinator and Ready/prompt controls are now implemented and
qualified in `oled-frame-host-r1/coordinator.py`, SHA `b3b23b5b…`. It reuses the
existing USB/source/route/credential gates, stages the exact eight target files
within the existing3MiB request limit, verifies completed same-boot module/raw
SSH/monitor evidence, and owns preparation, live leases, fresh Ready, prompt,
cleanup, after-health and final nonfailed monitor closure.

The actual20-second display component ran through the new host/target RPC and
prompt flow: **20.000656s from brightness attempt to zero**,80 samples,20.164s
coordinator duration. Framebuffer, capture/render, phone identity and monitor/
health are explicit fixtures; brightness commands used a real root-owned regular
file. This does not prove optical scanout. Final **17 focused cases pass in3.656s**
(3.978s runner), covering current publication, full flow, cancellation, module
proof, failed monitor, Ready and cleanup. The timer run is inherited from the
immediately preceding source: all existing function/class ASTs are unchanged,
and the sole new save implementation is separately covered by those17 cases.

A deterministic blocked-writer test reproduced visible partial control records.
The frame host now fsyncs a private temporary file and publishes atomically with
rename-no-replace. Prepared, Ready and visible records cannot be read mid-write,
and existing records cannot be overwritten. The first integrated suite timed out
before Ready with no nonzero command; its exact user-thread error was not retained,
so its cause remains unproven. That interrupted fixture was copied unchanged to
disk. The fixture now records such errors and stops leases promptly. The separate
20-second diagnostic passed. No unchanged20-second repeat was needed after the
publication fix.

Qualification is SHA `c295ea99…`, accepted by the actual reader in0.015404s.
`run(boot,run_id,module_run_id,pin)` publishes `prepared.json` while keeping its
process/monitor/SSH alive. Only a fresh human reply may call `ready(output,hash,
reply)`; `wait_visible(output)` returns the physical prompt as soon as armed.
`observe` retains the user's actual answer without inventing optical verification.
Capture-only cancellation requires zero, reap and fresh health; it preserves the
unused frame-write entry and does not fabricate a monitor finish. Any actual or
uncertain Ready/write attempt remains consumed.

Fresh authenticated source health now **PASSes in1.433s**, uptime **21,829.53s**,
on the same `de90d177…` boot, release05941, bundle `kernel-hw-05941-a607a2bb249c918b`.
The exact old V9 selection `ed3a62d1…` remains restored, current-boot health and
boot-bound readiness pass, and physical guards pass. Evidence is
`oled-frame-host-r1/source-health-r1`. This is current headless health, not OLED
qualification. No phone write occurred. The current read-only OLED launcher
preparation also passes in0.205s on clean Q538fab85 with qualification `18b1717f…`;
no claim or trial directory was consumed/created.

**Next:** request fresh Deck authentication availability and immediately launch
that prepared one-use OLED trial with its working touch-password path. The trial
includes the full23-minute observation. Then use actual OLED boot identity for
the qualified module coordinator, followed by actual zero-state frame preparation.
Ask for separate physical Ready only after `prepared.json` and live prompt reader
are ready; authentication availability is not phone-observation availability.
No old Ready may be reused. No actual OLED boot, module insertion, frame preparation
or brightness action is running yet. Preserve the pending claim until launch.

`display-integration-plan-r1/PLAN.md` describes the inert-module/late-load
sequence, but its f17 artifact identities are historical; the old display
packaging recipe also pins f236e710. OLED adds L12/L13 under the already-probed
RPMh parent, whose probe-time child scan does not establish live-overlay support.
Prepare a new DT boot, not regulator unbind. OLED/touch/GPU remain unqualified;
the combined DT proposal is offline only. Kernel work precedes Denial/Flutter.
No physical prompt or job is active. Request fresh availability only after the
physical display test is prepared. Use r68 for the complete frame host/Ready/prompt controls and latest authenticated source health, r67 for the target prepared-frame backend, r66 for the complete offline module host coordinator, r65 for the bounded target module supervisor, r64 for owner/monitor lifecycle qualification, r63 for boot/health provenance and current transport/sampler, r62 for the target module/early-blank component, r61 for current registry/pending claim/source qualification, r60 for its historical predecessor, r59 for the component transport adapter, r58 for the timed display session, r57 for the guarded write/readback component, r54 for framebuffer capture, r53 for the Rust frame helper, r52 for the offline display endpoint component, r56 for actual host handoff and sealed frame preparation, r50 for A01/input binding, r49 for controller integration, r48 for transition components/latest
source health, r47 for signed packaging/static autoload, r46 for payload, r45
for restoration, and r43 for the original trial.

Earlier coordinator milestones below retain their original scope and timings;
statements about pending jobs or absent trials there are historical.

Current coordinator handoff: the successor kernel, module and boot-package
builds are complete; do not restart them. All twenty-two controller phases now have
component implementations, including capture lifecycle and the one RAM transfer.
The capture supervisor passes **20 tests in 11.244 s**, using actual child
processes, process groups, pipes and loopback TCP. Two tests run the real
controller through target success and a separate fallback recording after late
failure. Recording time, privilege, USB/network, admission and phone behavior
are explicit fixtures; this does not qualify a physical capture or boot.
The supervisor verifies process ownership and the local readiness challenge,
preserves the original deadline, and checks cleanup records before accepting
closure. It distinguishes proven prelaunch absence from an uncertain launch.
The earlier passive worker's 19 isolated tests and bounded host source reader
remain qualified for their recorded inputs. The RAM-boot callback passes 17
focused tests in 3.696 s, including real sealed-FD child success/failure/timeout
checks with a four-byte fixture. It checks live capture after image preparation
and device queries, retains failed transfer output, and forbids a second attempt.
No production image snapshot or phone boot ran. The concrete installed-route
verifier now passes twelve host tests and six isolated file tests. Its actual
read-only phone probe passes in **2.912 s** on the unchanged V9 boot: all eleven
installed files, boot-partition hash, source state and storage protections match.
It binds a fresh inventory to the controller's preflight and replays the retained
selector decision evidence. This does not prove a physical fallback boot.
The twenty-two components are now assembled into an import-only driver. Twelve
assembly/source-abort integration tests pass in **8.942 s**, using real callback
and controller receipt flow with explicit simulated phone replies. Preflight uses
one combined source/route query; both boot paths use the same concrete route
verifier and distinct owned target/fallback capture checks. The driver checks
nested evidence paths and bridge interfaces before any source mutation.
The fixed sudo capture bridge and process monitor now pass sixteen real process/
pipe/pidfd tests in **7.354 s** and three bridge/supervisor integration cases in
**2.625 s**. The monitor watches both controller and launcher loss; bounded output
writes permit cleanup after reader failure. These tests explicitly substitute
sudo/root/network and recording duration. The actual privileged handoff remains
unverified. The shared admission verifier is now implemented as described below.
The fallback-route worker now passes nineteen component/process tests. It
borrows an exact existing route or cleans up its own temporary route, while
running SSH as deck. The shared child runner now uses `prlimit`, avoiding a
Python pre-execution hook inside the threaded monitor. Thirteen worker tests and
fifty affected integration cases pass; an actual threaded source query passes
in **0.115 s**. Fourteen dependent source-pin updates preserve prior source bytes.
The guarded fallback transport entrypoint and parent adapter are now connected
to action, direct health and nested fallback-locator callbacks. Sixteen transport
tests pass in **1.068 s**, three injection tests in **3.907 s**, and 112 affected
regression cases in **50.460 s** including launch overhead. Actual child sessions,
pidfds and durable output files are exercised; sudo/root/network are fixtures.
Raw root output is bounded separately on disk, preserving diagnostics larger
than the older four-MiB receipt limit. Failed or uncertain mutations cannot retry.
The shared admission verifier and concrete driver factory now pass **24 boundary
tests in 0.451 s** and **three source-abort/assembly tests in 4.835 s**. They bind
the exact input lock, current controller/host boot, qualification evidence,
one-use claim, phase history and generated command bytes. Both root entrypoints
use the same policy. The factory connects the capture and transport authorizers
before returning a driver. Full target/fallback integration and actual privileged
handoff are still unqualified; their required receipt is absent.
An actual 29-file input check passes in **0.105 s**, with an unchanged check in
**0.005 s**. Hashing streams the 128-MiB boot image; changed metadata invalidates
the cache. An actual entrypoint check refuses both the unregistered claim and
missing qualification in **0.339 s**. No admission record or physical execution
directory has been created.
Four complete assembled flows now pass in **22.853 s**: target capture plus
post-capture health, early V11 fallback without target switch-root, late failure
with a separate full fallback recording, and pre-reboot restoration of both
exitrd and selection state. These use real callbacks, admission phase/command
policy, parent fallback transport and recording subprocesses, with explicit
USB/SSH, privilege, RAM transfer and elapsed-time fixtures. They prove host
integration behavior, not phone operation.
The read-only privilege probe passes **nine preparation tests in 0.691 s**.
The first actual attempt stopped before root execution because sudo required a
password. The second attempt's GUI failure and third attempt's input failure are
retained; r2, r3 and r4 are terminal and must not be reused.
It performs no phone, network, claim or live-capture action. After actual handoff
qualification, finish exact claim registration and final qualification. No physical Ready
request or phone recording session is pending.
The import-only one-use launcher is now prepared: **15 focused tests PASS in
0.806 s**, plus **48 affected regression cases PASS in 36.646 s** including
launch overhead. Authentication and the first noninteractive credential refresh
precede claim consumption; the admitted record precedes controller execution.
A bounded refresher keeps the same controller's sudo credentials available
during long recordings. Failures block new phases; cleanup stops the refresher
and owned recordings. A recording requiring emergency cancellation cannot turn
the launcher result into success. Actual sudo refresh remains unverified.
The remaining RAM-transfer `preexec_fn` was replaced with fixed `prlimit` before
introducing the thread. A real four-byte sealed-FD child verifies both limits
and inherited data while another thread is alive. Admission now binds launcher
identity, and the input lock includes the credential helper. The root-boundary probe is unchanged; authentication and the launcher source
pin now include the GUI-limit correction and are prepared for a fresh reply. No trial directory, claim or phone action
was created by this work.
New routes/full capture need host sudo authentication, while normal USB SSH
works as deck. No receiver or Ready request is pending.

Latest actual phone health passes in **2.083 seconds** on unchanged V9 boot
`7c945aa5-80d0-4af2-aa76-113d68e23ac5`, observed at 50,061.14 seconds uptime.
The same boot committed healthy at 64.143 seconds; pinned runtime, current-boot
markers, services and storage/power guards pass. Battery temperature was 30.3 C.
The prepared RAM helper/custody and original boot selection remain preserved.
The new health predicate works after full capture without relaxing the
300-second healthy-commit deadline. This is V9 evidence, not a successor boot.
Use the latest `kernel-hardware-checkpoint-r*.json` in the private state directory
for exact current sources and receipts; later sections retain earlier milestones.

The last hardware inventory has no DRM card/render nodes, framebuffer or
backlight, and only the three qualified key inputs. MDSS, DSI, GPU and GMU are
disabled in its device tree. The existing 60 Hz display evidence belongs to a
different kernel/DT pairing.

The exact historical panel source and unchanged REFGEN regulator source now
build as external modules against the current server kernel. Both module twins
are byte-identical; the two builds and verification took 12.967 seconds. Their
load/unload and driver-registration checks passed under the exact V9 Image in
QEMU in 2.199 seconds. No phone module was loaded and no display was activated.
This establishes a smaller display preparation path without rebuilding the
kernel; it does not establish scanout or GPU rendering on V9.

The current-V9 display DT now composes identically twice and passes strict
preservation checks: ten added nodes and fourteen changed properties. Nine
focused tests pass in normal and optimized Python. The package remains unsigned
and unactivated. Full local source CI passed at
`752742fc2f7aeb1ce19d8389a81658399f1a28fc` in 563.196 seconds; physical
admission and full paired-root qualification remain pending.

Denial source, engine source dependencies and Rust toolchain are pinned in the
[source lock](../configs/denial/source-lock-v1.json). The isolated Rust 1.98
builder is provisioned. The ARM64 control client built offline in 22.010 seconds
and passed emulated help/version checks. Full ARM64 compositor compilation also
passed in 464.094 seconds under the same 3 GiB limit. Both resulting binaries
pass isolated ELF/help/version checks; no engine or phone session was run.
Static closure against the retained Arch layers passes for `denialctl`.
`deniald` still needs GBM, libseat, libinput and xkbcommon libraries there.
The isolated Flutter engine builder is now provisioned, and its exact Flutter
and bootstrap depot_tools checkouts passed verification in 22.003 seconds.
Dependency sync was deliberately stopped at the user's priority change after
796.080 seconds. The container and runner have exited; its partial source/cache
is retained. The raw sync receipt is FAIL/137 from the requested stop, not a
successful dependency closure or evidence of an OOM. Do not restart it during
the kernel-first phase. No hooks, engine compilation or shell assembly ran.
The public mobile shell is available, while the reference
build helpers use x86-64 paths and checksums. See the
[bring-up record](../test-results/2026-09-10-denial-bringup.md) for next actions.

The new unsigned display composer preserves the corrected buttons payload and
adds two inert module files with a fresh descriptor/catalog. Focused composition,
module closure and runtime installer checks pass. Actual unsigned initramfs twins
match SHA-256 `3fcbf6d3dfa9dd45719c0ab167940961c76ee10a5500c8913bfd3e76eff294dc`;
both are 56081476 bytes and composed in 14.745 seconds total. Complete boot-image composition,
paired-root autoload absence and physical display behavior remain unqualified.
The new DT permits built-in display probing before userspace.

Reviewed cleanup removed 67.218 GiB of generated compiler intermediates from
completed historical builds. All 15,559 protected outputs remained unchanged;
sources, final images, recovery data and current module kits were retained.
Approximately 82 GiB was free before temporary full-CI fixtures.

The hash-verified stock DTBO now corroborates the ASUS MP2 front-touch
controller, GPIO22/23/131, L3C/L8C consumers and final 1080x2448 extents.
This is offline board-data evidence; no touch probe or driver activation ran.
The private first FTS3658U driver now builds against the unchanged current kernel.
Twins match in 9.062 seconds; 24,324 parser/ID/transfer checks pass in optimized
and UBSan runs, and six disabled-DT checks pass. Module SHA-256 is
`fc94acd0bc6cd6ce4900e5ccb62c3edb6ca6c17ae332cefdb0ed31d6624bbb60`.
Driver review passes. GENI I2C/GPI provider twins now pass in 16.832 seconds;
the three-module stack registers under the exact V9 Image in QEMU in 2.687
seconds. Touch and I2C unload cleanly there; GPI has no unload implementation
and remains until guest reboot. This does not prove real bus, IRQ or rail behavior.
The disabled touch overlay now composes against both V9 and display DTs with
unrelated properties and boot metadata preserved; twelve hostile-delta tests
pass. The enabled proposal makes five status changes, leaves SPI4 disabled and
retains L8C always-on. Touch unbind cannot undo that rail's always-on vote.
The physical probe remains pending. The
component intentionally leaves suspend/resume unqualified and cannot yet serve
as a complete touch implementation. No module was loaded on the phone.

The reviewed source, disabled overlay and portable test are now integrated at
`e8cebfcd`; C/header bytes match the private build inputs. The test passes eight
cases and 24,324 decoder checks per C build mode in both ordinary and optimized
Python (0.573/0.520 seconds). It is wired into the repository runner. Full CI
for this new integration is pending; the earlier 752742fc result remains scoped
to its own source. See [front-touch prototype](front-touch-prototype.md).

The current-kernel GPU audit found that GMU power-level setup errors were
ignored. Existing patch 0012 fixes that exact path; eight actual-source
fault-injection cases pass and the unpatched baseline fails. Clock and RPMh
fixes 0026/0035 are already present. The clean successor kernel source is
`05941d04803f54208da1e9920a81874edc540ca1`, containing only 0012 over f17.
Its unchanged-config/compiler/release preflight passed in 21.955 seconds.
Cache-assisted kernel twins now **PASS**: 2729.501 and 2698.331 seconds,
with identical Image, Image.gz, vmlinux, Module.symvers, configuration and all
25 scoped modules. Both containers exited without OOM and were removed.
Do not restart the completed runner. The exact Image also passed the earlier
2.633-second generic QEMU boot; physical successor boot remains pending.
The compiled integration source stays frozen at `f74e719c` in private
`worktree`; current progress documentation is maintained in `progress-docs-r1`
so downstream verification can still authenticate the original clean source.

All three pinned A660 firmware files have been recovered from official
linux-firmware 20260622 into private `gpu-firmware-r1`, with matching sizes/hashes
and retained licenses. Fresh ZAP parsing needs 4 KiB within the existing 8 KiB
reservation. SCM authentication, GPU initialization and submission remain
unproven. The first DRM open initializes hardware; it is not a read-only health
check. Use a small explicit DRM test before Mesa or Denial.

Unsigned GPU DT proposals now reproduce on both V9 and display-V9 bases:
exactly four status properties plus the ZAP firmware name change, with all
other property bytes, boot CPU and reservations preserved. Eight focused
test groups pass in ordinary and optimized Python; no phone activation ran.
The private Rust open/query helper passes fourteen native tests per build mode
and exact ARM64 UAPI compile assertions. It permits one operational open and
three scalar queries, preserves primary and close errors separately, and has
no submit or retry path. ARM64 binary twins now match after 1.683/1.271-second
builds. Static library, version and strong-symbol closure passes against the
retained Arch providers. Separate debug-stripped deployment twins are 542,016
bytes, 88.3% smaller, with loaded code/data preserved and originals retained.
No target executable or phone GPU operation ran. A cooperative timer cannot
bound an uninterruptible kernel ioctl. Evidence: private `gpu-query-arm64-r1`.

The matching 3,378-file kernel kit was derived in 9.701 seconds and additively
completed in a 2.582-second service run. Original files remain unchanged;
packaged PDR alone retains the accepted BTF-removal exception. External module
twins now **PASS** in 216.131 and 38.580 seconds, with all 31 raw outputs
identical and clean container cleanup. Selecting the two diagnostic provider
replacements yields 54 unique production modules across both build groups.
The cached comparison took 82.1% less elapsed time than the first module build;
this measures this module run, not a full-kernel or future-build guarantee.

All 54 selected raw modules pass exact export/dependency, namespace and GPL
checks against the successor kernel in a 6.253-second service run. Ordinary
defined symbols do not count as exports. The typed S12 provider/consumer edge
also passes. This static check does not prove full module ABI/BTF compatibility.
The actual ten-module guest passed in 3.797 seconds: indicator, GPUCC, REFGEN,
panel, GPI/GENI and touch loaded and registered; nine unloaded and permanent
GPI remained until poweroff. Physical probes did not run. The remaining 44-module
guest now passes in 8.096 seconds: 41 ordinary loads with runtime BTF checks and
three exact one-call ENODEV board refusals. Its test-only S12 shim was rebuilt
twice against 05941, with identical outputs and clean cleanup in 11.957 seconds
total. The shim observed the activation consumer's BTF COMING, zero LIVE and
zero validator calls, then unloaded. Packaged PDR alone omits BTF as explicitly
qualified; no raw-PDR BTF or successful physical S12 hold is claimed.
Private receipts are in `successor-module-build-r1`,
`successor-module-closure-r1/verification-r1` and
`successor-components-vm-r1/run-r1` and `successor-baseline-vm-r1/run-r1`.

Unsigned successor payload twins now pass in `successor-payload-refresh-r2`:
57,774,555 bytes each, SHA-256
`c7d757727bc6e9295087b02d207e90d44e43d9ac2f1ccb345a4923c04365e058`.
All65 previous module copies were refreshed and four hardware modules added
outside the automatic module search tree. Nested membership stays37 modules;
the new host depmod's exact comment-only `modules.weakdep` is explicitly
qualified as metadata file14. The original inventory refusal is preserved.
Corrected runtime, indicator, shutdown, firmware and other unrelated bytes
remain unchanged. The reserved unsigned bundle is
`kernel-hw-05941-a607a2bb249c918b`, using the retained headless V9 DT.
Signed headless boot-package twins now pass in `successor-boot-package-r2`
(89.009 seconds, 512 MiB/no swap). The 129,966,080-byte raw image requires the
128 MiB AVB envelope; both final wrappers match
`d21405d94a9eabc4b6b8e1b7990bf7c9f2aef1da0795a39e94761a5a09ab3fa6`.
Both AVB checks, nested authenticated runtime plan and signed bundle comparisons
pass. The first packaging failure is preserved: AVB resolves partition `boot`
as sibling `boot.img`, requiring an exact canonical verification copy. Local
signing has occurred; release qualification, admission and phone execution have
not. Paired-root content/runtime checks and exact059 A01 now pass as recorded
below. A complete 128 MiB controller and guarded pending trial-state preparation
remain required.

Full CI on frozen f74 stopped after 84.809 seconds on an unchanged five-second
host-test timeout under a two-CPU quota. The reviewed scheduler now defaults to
two workers, capped by affinity and inherited quota. CI on corrected cc53c3ec
passed that 12-test suite, then stopped after 255.505 seconds at UFS inventory
sorting: the desktop service inherits en_US.UTF-8, unlike the shell's C.UTF-8.
The production verifier now pins C locale; exact inventory/profile refusals
remain unchanged. Full CI now passes on frozen source `492d8cf2` in 593.246
seconds, source unchanged, under 3 GiB/no swap and a two-CPU quota. Receipt:
`source-ci-r6/result.json`. The previous failures remain preserved.


The exact059 A01 integration is now implemented with one versioned artifact
profile. It recognizes all 54 module identities, 32 loose copies, 37 nested
copies and 14 exact metadata files. The retained payload inventory passes in
1.332 seconds (335.5 MiB/no swap). Historical f17 recognition is unchanged.
The profile permits offline wrapper lookup only; it creates no boot claim.
The original test-only shim twins bind through an explicit reference envelope
and actual vmlinux-to-Image comparison in 0.865 seconds, without rebuilding.
The integrated VM now pins the qualified QEMU image and records owned-container
creation, terminal state, removal and process-group cleanup. Console parsing is
bounded. Focused profile, fixture, lifecycle and wiring tests pass, including
missing/duplicate runtime markers, stale identities and incomplete cleanup.
Actual full A01 passes on `f316fe58` in 80.308 seconds: all seven composition
checks, 51 ordinary module loads, two expected board refusals and the separate
activation boundary. Root and upper hashes stayed unchanged. The owned VM
closed cleanly without OOM and was removed. Full source CI on that same clean
commit passes in 596.538 seconds (`source-ci-r7/result.json`). These results
establish offline qualification, not physical hardware behavior.

The exact059 import-only 128 MiB boot primitive is now implemented. It binds
the immutable composition profile, trial, wrapper, fallback and A01 evidence;
requires the successor's own entered claim; and reuses the existing sealed
snapshot/capacity primitives without changing either historical boot path.
The successor remains absent from the claim registry and therefore cannot boot.
Nine new tests plus the existing seven R01 and four ordinary helper tests pass
in both Python modes. The actual wrapper snapshot seals and closes in 0.184
seconds; focused service runtime is 2.450 seconds, peak 281.8 MiB/no swap.
Evidence: `successor-boot-helper-r2/result.json`. Full integration CI for this
helper now passes on clean `63a0c1a1` in 602.727 seconds
(`source-ci-r8/result.json`). The service is terminal; do not restart it.

The private Rust trial-state exchange primitive now passes offline qualification
in `successor-state-exchange-r1/result.json`. It writes and syncs a backup and
new pending record, then atomically exchanges the two names while holding file
locks. This supersedes the proposed absent-record creation interval. Restoration
exchanges the original V9 inode back and retains both records and one-use intent
files. Eleven native test groups cover interruption, locks, tampering, pathname
replacement and retry refusal. Corrected static-PIE ARM64 twins match after
1.071/1.119 seconds. Six isolated ARM64 cases (17 process calls) pass in 0.582
seconds, including real v1/v2 target-helper health acknowledgment and exact
old-record restoration, in an empty root without shared libraries. This does
not establish phone-filesystem power-loss durability or physical authorization.

The ARM64 replay caught a repeated host/target open-flag mistake; target-header
compiler assertions now bind the Rust constants and reject the old values.
An earlier DYN-labelled image crashed before its first syscall because rustc
passed contradictory static/no-PIE options. The corrected linker and actual
ARM64 startup/operation checks qualify the working artifact; failed images and
receipts remain retained. Rust fmt/clippy are absent from the pinned builder;
the attempted lint run is preserved, not labelled PASS.

Source/V11 shell guards now wrap the retained static helper, with exact boot,
sealed tools, power, storage, custody and exclusive operation-entry checks.
All 28 namespace cases passed across two runs with the actual ARM64 tools and
explicit synthetic telemetry. The first run remains FAIL: fixture setup stopped
after 19 passing cases. The corrected harness records each result durably and
completed only the remaining nine in 15.572 seconds. Retained outputs and final
fixture states were replayed without repeating ARM64 operations. Seven host
custody tests pass in normal and optimized Python. A fresh real-phone health
check passed in 1.206 seconds; the new guard's read-only subset then passed on
the same V9 boot in 0.972 seconds. The exact old selection record is now retained
in durable host custody. Evidence: `successor-state-guards-r1/result.json`.
That guard run did not upload a helper or change selection.

The source transition primitives now pass sixteen focused tests in normal and
optimized Python (0.750/0.749 seconds). They separate RAM staging, exitrd
installation, one-use reboot request and pre-reboot exitrd restoration. A lost
reboot reply permanently refuses retry and automatic source restoration; an
interrupted exitrd installation can restore the exact old script before the
reboot intent exists. The original Python V11 staging proposal is unusable on
V11, which has no Python; it was never executed there. Use the qualified
BusyBox replacement below. Full controller admission remains pending.

Fresh physical inspection confirmed V9 already has corrected shutdown bytes
`fc1ce027`; the old R01 source shutdown differs. Reuse the previously qualified
`0ee47fb5` fastboot dispatch variant, preserving all corrected cleanup code.
Source RAM staging now **PASS** in 1.368 seconds, followed by independent
readback in 0.258 seconds. Four files are retained under
`/run/rog5-kernel-hw-5ff5ab2bf15642c7a07e788a73caefa2` on the unchanged V9 boot:
the exact Rust helper, custody, inactive fastboot shutdown copy and completed
staging token. The active shutdown and healthy selection record are unchanged;
the state transaction directory is absent. No helper execution, reboot or
persistent write occurred. Do not repeat the completed staging action. Evidence:
`successor-source-actions-r1/result.json`.

The private successor controller ordering now passes 25 failure-injection cases
in normal/optimized Python (13.156/6.148 seconds), with real durable host receipts
and explicitly synthetic driver/capture observations. It preserves full capture
after failed or ambiguous execution, requires fresh post-capture target health,
and keeps successful V11 restoration separate from trial failure. An early target
failure can authenticate V11 without a preceding switch-root event. A fastboot
return requires a separate full fallback capture before one ordinary reboot of
the installed selector. This is ordering qualification; the concrete SSH,
fastboot, capture and admission driver is not implemented or admitted yet.

The exact installed selector function and ARM64 helper now pass three namespace
cases in 0.342 seconds: successor pending/healthy records both select signed V11
without changing those records; restored V9 healthy selects V9 and rearms pending.
Physical installed `boot_b` readback passes in 0.545 seconds, matching the retained
96 MiB wrapper `dcc487f1`, with protected storage read-only and V9 state unchanged.
Storage preparation/cleanup in the selector test is synthetic, so these results
do not establish a physical fallback boot. Evidence: `successor-controller-r1`.

The V11 RAM stager now uses its exact sealed BusyBox/loader and static ARM64
Rust helper. Five actual ARM64 namespace cases pass in 33.006 seconds in an
empty root without Python: pending/healthy restoration, wrong boot, partial
transfer and duplicate staging. Kernel/storage telemetry is synthetic. A bad
fixture device-number encoding was corrected from the fixture's actual sysfs
major/minor; the original failed run remains retained. No V11 phone action ran.

The bounded SSH worker now runs over an existing USB route as deck. Thirteen
focused tests pass in ordinary/optimized Python (0.530/0.569 seconds), including
an actual isolated-process repository import. The first privileged launch failed
before execution because sudo requires a password; a later local probe exposed
a missing sibling import, now fixed and covered. Actual read-only normal USB
SSH then passed in 0.611 seconds, authenticating the same V9 boot and kernel
without host network changes. This is transport continuity, not a new full
hardware health qualification. Evidence: `successor-live-driver-r1`.
New network setup and full capture still require host privileges. These worker
and staging pieces do not yet constitute the complete concrete driver.

Seven concrete mutation callbacks now bind the existing controller to the
qualified source actions, Rust state guard and BusyBox V11 staging generator.
They recheck durable context/intent/custody, write an exclusive command intent,
retain the complete transport response before parsing, and reject stale,
ambiguous, nonzero or timed-out responses without retry. All 27 tests pass in
normal/optimized Python (7.304/7.890 seconds): 22 boundary cases and five actual
controller sequences. Transport, capture, health and admission remain synthetic;
real generated scripts, existing custody and disposable fsynced receipts are used.
The complete driver and admission gate are still pending. The adapter currently
uses deck's existing-route transport; a scoped privileged bridge for fresh
fallback routes must be bound before live execution. Evidence:
`successor-live-driver-r1/callback-tests-r1/result.json`. No phone action ran.

Three read-only source callbacks now implement preflight, interrupted-source
inspection and restoration verification. Their observer accepts only recognized
selection/exitrd transactions, checks both ends of the snapshot, and refuses
reboot intents, partial publications, changed records and unknown owners.
Twenty-two real file/lock namespace tests pass in normal/optimized Python
(0.568/0.510 seconds), with physical telemetry synthetic. Twelve callback tests
pass (2.869/3.045 seconds), replaying actual V9 proof with explicit alterations.

The new observer's actual V9 preflight **PASS** in 1.694 seconds on the unchanged
boot: physical storage/power guards, staged helper/custody, original shutdown and
old healthy selection all match; state/exitrd transactions and reboot intent are
absent. No source mutation or reboot occurred. Evidence:
`successor-live-driver-r1/live-source-observation-r1/result.json`. This qualifies
the current read-only source check, not successor hardware or full boot admission.

The successor health component now derives seven runtime/unit members from the
exact built payload and two healthd files from frozen source. Twenty synthetic
proof tests pass in normal/optimized Python (0.452/0.490 seconds), including late
observation versus late healthy commit. The same complete reader passed on V9
in 2.083 seconds. Replaying that real observation demonstrates why the existing
startup-only smoke predicate cannot serve as a post-capture health check; it is
unchanged. Evidence: `successor-live-driver-r1/health-tests-r1`,
`live-baseline-health-r1` and `health-late-replay-r1`. The successor and V11 still
need their own physical evidence; neither boot nor full capture ran.

Next: implement and qualify V11 health and verification, target health callbacks, capture/fastboot
and privileged fallback routing, then complete admission for the concrete driver using
the staged source artifacts and exact one-use boot admission. The embedded RAM wrapper
bypasses the installed selector, so its
recovery phase stays read-only and requires a separate authenticated V11 return
path. Keep the ordinary full capture and failed-target result separate from
successful assisted recovery. No phone action or Ready request is pending.

The expanded display autoload audit passes for configured root paths: udev
loading uses the absent current-release index, while the new payload is outside
that tree. Historical REFGEN and dormant display scripts remain preserved.
Final wrapper/generated-runtime checks and actual coldplug are still pending.
The next display boot also needs fresh embedded-bundle admission, a matching
guarded userdata trial record, and measured boot-image size/controller binding;
unchanged paired root bytes alone do not satisfy those requirements.
Checkpoint read-only phone health passed again in 1.357 seconds on the same V9
boot after all offline work. That earlier health checkpoint involved no phone module insertion or reboot;
subsequent local successor signing is recorded above.

## Preserved buttons/LED milestone

Updated 2026-09-10: **buttons and visible green indicator have passed component
verification on the current V9 Arch boot**. Power (116), volume-down (114) and
volume-up (115) each supplied one complete press/release and an IRQ delta of two.
The user saw the green light. Three natural pulses at brightness 31/511 returned
to zero after approximately 180 ms; the user confirmed several power presses.
The strict one-pulse session remains FAIL for that extra activity. Its valid
power event and visible-light evidence are retained separately from the later
volume-only COMPONENT_PASS. Final LED readback is zero, full server health
passes, and all component monitors and controllers have closed.

The combined private receipt is `buttons-hardware-result-r1/result.json`, SHA-256
`0c7b0deeda132598b0c50eeffbe7971a97e6f1764d3c10c06fc44684fd4db557`, under the retained
`rog5-cpu-startup-20260908.kjE4IqCf` evidence root. The
[dated report](../test-results/2026-09-10-mobile-input-preparation.md) records the
separate component and strict-case outcomes. The full original V9 boot
observation lasted 1380.892 seconds and its host cleanup passed. S06 and R01
remain failed; this work does not qualify shutdown or autonomous recovery.

The live fixes are RAM additions on kernel `7.1.4-gf17befd4ef17`: the missing
`qcom_pon` parent, the corrected LED firmware-node lookup and the local reader's
ARM64 read-only FD mask. The accepted signed V9 image still contains its original
inert payload. Persistent activation and a promoted successor image remain
unqualified; component success must not be described as an installed release.
Repository integration carries the corrected artifacts and complete module
closure forward without changing the accepted boot image or consumed claims.

Integration commit `bc424ae6` passed full local CI in 531.274 seconds. The unsigned
five-file payload reproduced identically in two compositions (6.949 seconds
each); final archive metadata, four-module ABI/dependency closure, integrity
catalog and radio preservation checks passed in 0.623 seconds. These offline
outputs remain inert and grant no signing, activation or boot authority.

Human-assisted sessions must be fully prepared before asking for Ready. A fresh
reply starts only the brief current checks and recording setup, followed by the
actual key prompt. No operator timer runs while awaiting availability.

## Previous preparation checkpoint

Updated 2026-09-10: the user clarified the destination as a native touch-first
Arch Linux phone inspired by Denial, with cellular excluded. Display, touch
and GPU are central next milestones in the [roadmap](../ROADMAP.md). Buttons
and a default-off status LED are the current bounded step, not final product
completion. The [signed input package and module composition](../test-results/2026-09-10-mobile-input-preparation.md)
passed offline verification at source `458cb42a` in 6.13 seconds. Full
root/runtime composition and physical input/LED evidence remain pending;
V9 is now registered against those exact signed bytes, with all prior records
unchanged. It has not been admitted or booted. Sparse checkout of two completed
review worktrees recovered 5.93 GB while retaining their Git objects and evidence;
the host reserve is restored. A01 now prepares exact-kernel VM load checks for
the three indicator modules while keeping physical behavior NOT RUN. Its
46-test suite passes; paired-root VM composition and full CI remain pending.

After the unplugged startup investigation, installed V8 returned as boot
`159aa8ca-a7d5-425c-87c8-481e9484ff22`; the final authenticated readback passed
installed bytes, power/thermal and local storage checks. The full capture and
cleanup completed and all phone controllers are closed. S06 and R01 remain
failed; the shutdown/startup issue is unresolved. Current readback supersedes
the historical boot and S06 status in the retained checkpoint below.

## Previous qualification checkpoint

Updated 2026-09-09: the corrected RAM-only shutdown passed its physical source
component. Its clean receipt reported mounts and loops clear, with all **117**
physical block nodes read-only. Fastboot followed in **11.801 s**.
One guarded ordinary reboot returned installed V8 as `a60a8d6d-5dda-4e15-9ab3-d46fb015ecf2`;
health committed at **65.542382 s**. The complete **1380.848 s**
capture and route/firewall/profile/address cleanup passed. Final authenticated
readback passed installed bytes, healthy selection, storage guards and absence
of staging at **1336.860 s** uptime. Independent terminal replay passed.
All phone controllers are closed. R01 remains FAIL with its claim consumed;
S06 remains NOT RUN. One coherent release is not yet qualified.

This observation used frozen source `6e7402e2`: full local CI **582.141 s**,
all four GitHub jobs PASS in run **34307973735**, 64 admission cases and nine
assembly cases in both Python modes. Private action/receipt/controller/launcher
checks passed 22/36/28/11 cases per mode. The clean source receipt is component
evidence; it does not establish the original R01 cause or autonomous fallback.

The preceding diagnostic refused residual userdata ext4 (`259:58`, `/dev/sda23`)
after the old shutdown reported clean. A real namespace reproduction showed
that systemd's relocation of a busy mount could bypass fixed-path cleanup.
The correction accepts only one recorded root ext4 userdata mount at its
canonical or exact systemd relocation path, verifies node and reachable-device
identity, strictly unmounts, verifies disappearance, then relocks storage.
Sealed regression passed **71 default / 72 diagnostic cases**. The corrected
shutdown is in source and was tested from RAM; installed shutdown, kernel,
root images, signed fallback and consumed experimental claims remain unchanged.

S06 preparation also exposed two host-side defects. S05/S06 replay now derives
executed shutdown identity from the canonical installed release while keeping
observer-source provenance separate. A scoped `--powered-off-start` receiver
mode reserves the contract's extra 60-second operator transition: 1440-second
capture lifetime, unchanged 1320-second recovery requirement and 1380-second
S06 remaining/deadline gates. The mode is bound on start and check and excludes
experimental source-teardown captures. S05/S06/receiver tests passed 11/19/42
cases in both modes; ordinary smoke passed 23. Retained real S05 replay passed
in 0.711 s with its original input index unchanged. Integration full CI is pending.
No powered-off cycle is admitted; direct operator input and a reviewed live
controller are still required.

## Goal and authority

Deliver the mobile Arch phone described in the [roadmap](../ROADMAP.md), with
the buttons/status LED milestone first. Preserve the headless server and its
existing [acceptance contract](release-acceptance.md) and
[mandatory matrix](../configs/release-acceptance.json) as the baseline.
Missing prerequisites/evidence are BLOCKED or NOT RUN, never PASS.
Use the clarified roadmap for scope; unrelated work stays in the backlog.

Exact phone: `M5AIKN00F0353YH`, product `lahaina`, side USB anchor `1-1.2`.
Preserve official WW33 slot A (`33.0210.0210.200`) as charging/rescue.
Stock charging restoration is complete; do not repeat super/stock restoration.
Keep identity/slot/topology, signatures, battery/thermal, storage scope/backups,
independent fallback and permanent experimental one-use protections.
No new flash, GPT or protected-data operation. Destructive scope is separate.
Private credentials, packages and raw evidence remain outside Git.

## Running release and recovery

Running bundle `headless-server-selector-v8`, kernel `7.1.4-gf17befd4ef17`,
ordinary boot `a60a8d6d-5dda-4e15-9ab3-d46fb015ecf2`. Pinned SSH, current-boot health,
healthy selection, protected storage and all twelve installed hashes passed
again after full capture closure. Health committed at **65.542382 s**;
final readback was at **1336.860 s** uptime. The original installed shutdown
is present, exitrd is tmpfs, the restart provider is bound and staging is absent.

Source boot `545c66d9-35d7-47d9-9432-b54aaffbfcac` produced one clean
source teardown receipt using the corrected RAM shutdown and reached fastboot
in **11.801 s**. The subsequent installed return and full capture
passed independently. This does not qualify R01 or retry a consumed RAM claim.

V11 boot `96c3e790-a422-4723-b9ca-a5039da2a14a` provided the separately guarded
selection restoration. The later ordinary smoke remains FAIL because capture
hit a source NetworkManager teardown race and its first SSH probe timed out.
The readback confirms current service, not that failed smoke or autonomous R01
recovery. The prior S05 result keeps boot `af66d09d-f512-4954-a036-0904616e17af`.
Signed primary manifest:
`27f18d68cf2f7aaa791efb14de3ccc728506dca6b772b5ef006c890b3a787334`.
Other primary identities derive from the canonical expected record.

Installed boot-B loader unchanged:
`dcc487f17d6b4926ea633cbb242c62b598019e332640a81c1100c2d91087f723`.
Retained previous boot B:
`340f639276d9df3dfc073b8614a72f82507ea18c622c9df5d1e60f2c1622ccad`.
Signed V11 fallback manifest unchanged:
`a684bad14f84251ba342a87bde07da1f7b9aea412275ad124f7000716e94bbe2`.

Pinned USB SSH is `10.77.0.2`, alias `169.254.77.2`, fingerprint
`SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
V8 reached authenticated readiness in **98.215 s**. Local-root component PASS:
P24 RO/no replay, expected persistent overlay, 117 physical nodes, only
sda/sda23 writable, exact deployed userspace and current-boot readiness.
Wi-Fi, Tailscale and persistent-state services started. The full-hour load result is recorded below.

V8's experimental claim is permanently consumed, as are V6 and V7.
Do not retry their RAM execution or issue replacement claims. R01 armed the
accepted V8 record as pending; its exact healthy state was restored only after
fresh authenticated V11 and installed-file guards passed. The normal installed path is separate from a RAM
claim and does not constitute full release acceptance. V7's pending failure record and old
selector were archived during staged V8 installation. V5 accepted payloads,
prior claims, V11 fallback and the failed-soak scratch remain preserved.

## Proven startup correction

V7's CPU guard refused 62.4°C before applying any cap. Its CPU unit had waited
for tmpfiles because `PrivateTmp=yes` added an implicit dependency.
V8 uses `PrivateTmp=disconnected` plus inaccessible `/var/tmp`; all existing
power/storage guards and the 60°C thermal threshold remain unchanged.

Physical journal: CPU unit started at **20.654 s**, before tmpfiles at
**21.485 s**; policy application completed successfully. Verified maxima:
policy0 **1,209,600 kHz**, policy4/policy7 **1,555,200 kHz**.
Later read-only observation: all zones below 60°C, maximum **35.8°C**;
battery Full 100%, Good 29.8°C, 8.593 V, USB online, current 0.
This answers the startup question, not H03 regulation or a 60-minute load soak.

The cycle reused the existing kernel/DT/modules and boot wrapper. No flash.
Staging **2.126 s**, independent postcheck **0.747 s**, orderly V11-to-fastboot
transition **9.327 s**, exact fastboot battery 8.606 V / SOC gate yes.
Full capture completed **1,380.863 s**; route/firewall/profile/address cleanup
all PASS. No further phone execution was requested during that observation.

## Current checkpoint and next mandatory outcome

One coordinator owns this phone. S01–S05, S07 and F02 retain their completed
independent evidence. The failed R01 capture closed its full lifetime and all
host cleanup passed. The separate installed recovery capture after
normal-address SSH timed out has also closed; the later authenticated V8 readback
is recorded above. No phone controller is running.
Do not retry the consumed negative candidate or run a second phone controller.

On `f0a3420b`, full local CI passed **520.115 s** and all four jobs passed in
GitHub run **34214045938**: exact head, merge compatibility, publication and QEMU.
The original failed CI and USB-teardown capture remain preserved. The receiver
fix permits only precisely tagged ENOENT/ENODEV followed by positive absence
before target observation, within the existing 150 ms check. Identity mismatch,
permission errors, unresolved discovery and post-target loss still fail.

Fresh S01 reached authenticated local-root SSH in **93.193 s** and completed
its full **1,380.504 s** capture. Fresh S02 passed four 256 MiB USB/Wi-Fi transfer
directions in **303.671 s**; fresh S03 recovered all four services in **35.081 s**.
Both independent replay checks passed on that same boot. Earlier S03 r1/r2
remain FAIL; r3 and its actual producer revision are retained.

Fresh S04 passed **102.744 s**: one 64 MiB file was written/fsynced, survived
one ordinary reboot, read back with the expected hash and was cleaned by exact
file identity. SSH returned in **93.850 s**. The complete **1,380.582 s** capture
had no failed diagnostics, and its independent S01/S04 checks passed. The
original failed S04 capture is not relabeled. Its old scratch, the existing
acceptance namespace and unrelated files remain preserved.

S05 passed three distinct ordinary boots in **330.639 s**. Per-boot closed
observations took **103.910 / 102.807 / 103.412 s**; healthy-state observations
took **102.849 / 101.872 / 102.368 s**. Each started a full failure receiver
before one reboot request. Successful capture closure used the qualified full
S04 baseline plus the new exact healthy record; no failed boot was retried.
The independent three-boot checker passed. Kernel, DTB, signed archives,
installed boot B, selector and V11 fallback are unchanged.

On `af960758`, full local CI passed **526.883 s** and all four GitHub jobs
passed in **34221548267**. S07 then measured **3600.030 s** of combined load;
its full run completed **113 storage windows and 188 transfers**, each 64 MiB.
All workers stopped and exact scratch cleanup passed in **3666.628 s** overall.
The independent S07 checker passed in **68.277 s**. Old failed-soak scratch and
receipts remain preserved; this successful run has fresh identities throughout.

Across 367 heartbeat samples, maximum thermal-zone temperature was **51.4°C**,
battery temperature at most **30.8°C**, minimum pack voltage **8.413 V**.
Final power was Good, 30.8°C, 8.436 V. No new kernel messages appeared during
the measured load; ext4 error counters for loop1, sda23 and sda24 stayed zero.
Backing-device I/O and log continuity passed the original strict criteria.
This is endurance evidence; H03 retains its separate radio-free charging method.

Exact V8 F01 passed **85.412 s** using disposable networkless QEMU disks;
interrupted-update recovery succeeded and genuine corruption was rejected.
The original kernel/archive/root and protected fixture stayed unchanged.
F02 passed WPA/DHCP recovery in **29.141 s**, with three authenticated Wi-Fi
endpoint checks and unchanged radio/core service identities. Independent replay
passed; the sole coordinator closed in **30.104 s**.

The existing `headless-acceptance-rescue-v8` uses the same kernel and base Arch
root as the server. Its sealed runtime still matches all eight historical
runtime files. Fresh paired-root A01/C02 passed **66.261 / 76.473 s**. Its
September-6 original boot, capture, watchdog and 61 charging samples are retained;
the 600.265 s firmware-Full interval reproduces its original result offline.
That rescue claim remains consumed; signed V11 remains the independent fallback.

The dispatcher now supports an explicit `rescue_companion` receipt sharing
the primary's exact kernel and base-root files. Completed H01/H02/H03 replay
checks original producer versions, full capture/cleanup, paired composition,
raw samples and original boot/source identities. It grants no boot authority.
Portable and actual retained-data regressions passed; the integrated focused
suite passed **138 tests per mode in 20.793 s**.

On `be0a8d2e`, full local CI passed **533.795 s**, and all four GitHub jobs
passed in **34229955565**. One explicit paired receipt then passed H01/H02/H03,
S01–S05, S07 and F02 in **153.915 s**. Final source/artifact revalidation passed;
the original producer revisions and distinct rescue/server boots remain intact.
The rescue rows took **1.568 / 1.518 / 1.518 s**; S07 replay took **68.672 s**.
These are offline replay times, not fresh physical observations. Full release
qualification remains false; powered-off startup and controlled failed-boot
recovery remain outstanding.

R01 preparation confirmed that an ordinary watchdog reboot after a RAM-only
failure would still select healthy V8. That alone does not prove return to V11.
The existing trial helper offers a narrower preparation route: healthy-to-pending
rearming followed by a different trial's rejected health acknowledgment leaves
V11 selected at the next loader entry. The new regression passed on the host
and exact ARM64 helper, normally and optimized; all four 17-test suites passed
in **8.978 s** (one ARM-only test skipped in each host run). Retained V8 helper,
health and rollback bytes match current source; its outer timer is 900 seconds.
On `a1f9a10c`, full local CI passed **545.761 s**, and all four GitHub jobs
passed in **34232752925**. Unsigned `headless-recovery-negative-v1` target twins
then matched after **8.225 s**; only the trial descriptor and its checksum
manifest differ from accepted V8. Kernel, root, services and rollback are reused.
No signing, candidate registration, new claim or phone action has occurred.

The private V8 arming primitive passed six isolated ARM64 integration cases
normally and optimized, including namespace containment and lost-reply handling;
six synthetic guard tests per mode cover boot, power and storage refusals.
V11 has no Python, so restoration uses a separate sealed-shell generator.
Its six cases passed in **12.268 s** with the actual V11 BusyBox and canonical
ARM64 helper; kernel, sysfs and mount observations were explicit fixtures.
These are component tests only. A separate passive two-boot receiver now
preserves the original receiver's exact bytes and prior evidence bindings.
It requires an explicit canonical R01 fallback, a completed initial root
handover and positive USB absence before accepting one distinct rescue boot.
Premature/third-boot loss, wrong identity, unclassified teardown, networking
errors and earlier failures remain fatal; the capture lattice is unchanged.
Its 15 portable tests passed normally and optimized, and the original receiver's
33 tests passed. The receiver-only active checkpoint passed **47.789 s**.

The read-only negative-health observer requires the exact helper-refusal journal
sequence within the failed unit's execution, the unchanged installed pending
record, current-boot SSH/core readiness, sealed health/rollback bytes, an armed
900-second timer, and safe power/storage. Its nine focused tests include actual
bounded file reads and pathname replacement; malformed or unrelated failure
cannot qualify. Raw SSH output is retained before post-read topology checks,
including partial output on timeout. The one-shot controller, autonomous timer
stream and complete R01 evidence replay still need integration, followed by
signed packaging, admission and fresh physical preflight. No new phone action,
claim or full release qualification is implied by these observer components.
The combined active tier passed **45.383 s**; both focused suites also passed
optimized, with all recorded runtime/producer inputs unchanged. Full integration
CI and publication remain pending with the controller/evidence work.

Private rollback journal replay now checks the retained Arch catalog's fixed
service-job identifiers, the exact boot, PID 1, job ID, execution ordering and
callback deadline. Eight replay tests per mode and five shell cases passed;
the shell used the unsigned negative target's actual BusyBox timeout under
QEMU with explicit host/synthetic fixtures. The V8 source-to-fastboot RAM
shutdown delta also passed exact sealed-shell syntax and reversible byte checks.
It preserves teardown/poweroff and is separate from the unchanged negative
target shutdown. The first namespace fixture failure remains recorded; no live
transition, state arming, candidate execution or new claim has occurred.

The private controller ordering engine passed nine fault-injection cases per
Python mode. It fsyncs exclusive phase intents before callbacks, refuses phase
re-entry, preserves full capture after ambiguous execution, and requires a fresh
independent V11 guard before restoration plus a distinct healthy ordinary V8
boot afterward. User interruption permits cleanup without later mutations.
The generated source-side arming and RAM-transition scripts then passed eight
namespace execution cases in **0.640 s**, using the real ARM64 trial helper and
sealed BusyBox. Physical guard observations were explicit fixtures; a harmless
recorder replaced reboot. Genuine file metadata, exclusive publication, RAM
replacement, chroot syntax and mount-namespace containment were exercised.
Wrong state/source, symlinks, existing backup state and failed reboot replies
were handled without retry or changes to the original synthetic trial state.
The import-only private driver now implements every controller phase. Eleven
boundary tests cover raw reply retention, timeout/no-retry behavior, claim-account
selection, exact fastboot fields and the twelve-file installed inventory. The
inventory derives payload hashes from canonical primary/fallback manifests and
pins their signature companions. Local admission additionally requires the
exact six artifact roles, canonical restoration helper, unchanged producer
closure and exactly four successful CI jobs. Twenty-two admission cases passed
in **0.651 s**, using explicitly synthetic canonical/CI records and real file
pins, source hashes, primitive compilation and inventory derivation.

Actual driver restoration passed five namespace cases in **43.915 s**, using
the V11 BusyBox and ARM64 helper under QEMU. Lost staging/restoration replies
were not retried; exact fixture state and helper leftovers were retained. Five
execution-child cases passed in **1.217 s** with real disposable claim handling
and sealed-memory snapshots, while a harmless sink replaced fastboot. Failures
after consumption kept those fixture claims consumed. The real V8 claim was
checked read-only under its existing lifecycle account and stayed unchanged.

The offline R01 consumer and matrix dispatcher now accept a pinned completed
input envelope. They independently replay the full ordinary S01 prerequisite,
all raw controller commands, negative state/journal, two-boot capture and later
ordinary health. A regression caught consistent but wrong primary trial IDs;
those now refuse. The integrated checkpoint passed **60.500 s**, including
active **48.502 s**, with all inputs unchanged. Six subsequent tests exercised
the actual Driver/Core phase sequence and public replay with synthetic
transport/clock/admission in **6.581 s**; restoration never converted a failed
experiment into PASS. That checkpoint predates the reset-log binding.

Bounded reset diagnostics read only already-mounted pstore locations before
arming and after full capture on V11. Absence, unsupported mounts, read errors,
truncation and overflow are explicit; empty pstore never proves reset cause.
Twenty cases passed with both actual sealed BusyBox binaries in **6.347 s**.
They caught and corrected disabled glob expansion that had skipped present
records. The original failure and raw logs remain private; fixture bytes were
unchanged. Five public protocol tests cover malformed/stale/ambiguous evidence.

The latest combined checkpoint includes the reset-log binding and passed
**66.838 s**, including active **55.014 s**, with sources unchanged. All six
actual phase simulations passed again against the current producers; no real
transport, receiver process or claim was used.

The fixed root entrypoint now binds all nine private sources and hands closed
evidence to the desktop account only after every owned producer exits. Exact
primary/fallback manifests and signatures were verified from retained artifacts;
27 admission cases passed in **0.659 s**. The complete binding assessment
`r01-controller-bindings-r2` passed **0.103 s**, retaining compatible earlier
restoration coverage and the current full entrypoint simulations.

The full negative target cannot fit beside the unchanged ASUS kernel in the
existing 96 MiB RAM image. A separate R01-only helper requires an exact
**128 MiB** image, its canonical hash and consumed claim, plus a fresh single
unambiguous bootloader download-capacity response before consumption. Existing
96 MiB boot helpers and partition sizes remain unchanged. Seven helper tests,
twelve driver boundary tests, raw replay contradictions and the active suite
passed in **60.939 s** (active **55.566 s**). The actual 128 MiB execution child
passed five cases in **1.704 s**; six current lifecycle simulations passed
**6.976 s**. These use disposable claims and simulated transport, not a phone.

Signed twin packaging passed **24.182 s** with byte-identical outputs and sealed
signature verification. The recovery archive is 77,011,442 bytes; the padded
RAM boot image is exactly 134,217,728 bytes. Its canonical record now binds the
actual image, distinct negative trial and unchanged V11 fallback. Registration
consumer tests passed in both Python modes in **3.275 s**. Exact negative A01/C02/C01 subsequently passed
**77.695 / 96.128 / 134.995 s** on `b00a1b81`, retaining unchanged root/upper
bytes. Subsequent full integration CI and the physical result are recorded below.

The first exact negative A01 ran every functional check successfully but failed
its unchanged 120 s deadline at **146.582 s**. Root/upper hashes remained exact.
A read-only sparse-hash probe reproduced the entire accepted 34.36 GB logical
root digest in **20.903 s**, reading 4.19 GB and hashing 30.17 GB of holes as
zeros. A01 now reuses the already-tested C02 hasher for both root/upper checks
and records timings. The original failure is retained; the corrected exact
A01/C02/C01 run passed. Focused and active
validation passed **55.595 s** (active **55.430 s**), with source inputs unchanged.



Full integration on `c0025810` passed **532.692 s** locally and all four GitHub
jobs in **34266500765**; PR1 remains draft. The first controller stopped during
read-only preflight because its private userdata guard assumed `8:23`. Actual
userdata is `259:58`, with matching partition identity, geometry, mount and
inode. It made no state change or claim. Corrected private guards passed sealed
V11 shell/helper tests, full lifecycle simulations and connected read-only
preflight. All original failed evidence was preserved.

A fixed continuation then consumed the negative RAM claim once. The bootloader
accepted the exact 128 MiB image, but boot
`8f739c2f-c755-4ec7-8fc0-2f346d0fae1f` reported `final-storage FAIL` with
`ufs-q0-s0-j1-e0` before switch-root. It returned to fastboot. Full capture
closed at **1,380.488 s**, all four cleanup steps passed, and 60 files transferred
unchanged to the desktop reader. Independent replay refused qualification.
The journal count identifies one recovery match outside the allowed overlay
exception; it does not identify the filesystem or prove corruption/causality.
R01 is **FAIL**, with no autonomous V11 return and no experimental retry.

A separate normal installed boot reached V11 switch-root, but SSH to `10.77.0.2`
timed out. Its full capture closed with all cleanup checks passing. A pinned
read-only probe of `169.254.77.2` authenticated the same V11 boot and observed
the exact pending record, protected partitions read-only and safe power.
Fresh readiness, all twelve installed hashes and sealed storage/power guards
then passed. The existing helper restored V8 selection to its exact healthy
record and was removed. Assisted restoration cannot convert R01 to PASS.

The later ordinary reboot check could not connect to diagnostic SSH: the passive
receiver classified V11 as the source and skipped preparing its diagnostic
route. No reboot command reached the phone; the failed controller retains its
full observation window. A separately gated ordinary service check must first
verify closed evidence, unchanged source-boot continuity and healthy selection.

The repository observer duplicated the same `8:23`/`2071` assumption. Its
correction binds the runtime allocation to the exact userdata partition and
geometry, then matches mount and pending-record device IDs. A second observer
fix records terminal transport failures once per transition instead of flooding
the log on every poll. Both preserve strict failure classification and the full
capture lifetime. Full local CI for those two fixes passed **498.013 s** on
`91ff9e24`, with terminal completion and unchanged source. Two earlier checkout
setup failures are preserved; the pinned boot tools and canonical 12 KiB template
were restored from verified retained inputs.

Ordinary capture now prepares the diagnostic route before declaring the source
ready. It still rejects source stage frames and requires an observed disconnect
before accepting a new target. All **35** focused receiver/network tests pass,
including pending route convergence and permanent route failure. Full CI for
that correction passed **492.129 s** on `9d4cd138`, and all four GitHub jobs
passed in **34276164597**. A fresh ordinary reboot was then acknowledged and
V8 reached switch-root. During source teardown, repeated source route setup
raced `nmcli -g`; capture retained a permanent failure. The first normal-address
SSH probe then timed out. The smoke controller closed FAIL in **1,384.354 s**
after its full capture, with all four owned network cleanup steps passing.

The receiver now retains successful source-route preparation until an observed
disconnect instead of repeating NetworkManager setup during source shutdown.
Initial route failures remain fatal, source stages remain inadmissible, and new
target routing still runs after disconnect. A retained-event fixture reproduced
21 setup calls and the failure before the fix; all **36** receiver/network tests
pass after it. Full local CI passed **499.610 s** on `95cbc09d`, with its
completion marker and unchanged source; all four GitHub jobs passed in
**34278168035**. After full capture closure, fresh pinned SSH verified the same
V8 boot, readiness, local root, healthy selection and all twelve installed hashes.
An optional reset collector initially refused an extra serial field locally;
its corrected three-field call and final same-boot storage/state guard passed
in **0.640 s**, preserving and independently replaying the required reads.
Pstore remained present but empty, so reset cause is still unproven. No further
reboot or selection change occurred. Kernel, root/upper images, signed payloads
and claims remain unchanged.

## Mandatory results

Do not combine incompatible releases or simulation and physical evidence.

| Outcome | Current result / next action |
|---|---|
| A01 / C01 / C02 | V8 offline PASS; A01/C02 include complete retained upper |
| H01 / H02 | Explicit paired rescue replay PASS on `be0a8d2e`; original rescue boot retained |
| H03 regulation | Paired dispatcher PASS on `be0a8d2e`; all 61 original raw samples revalidated |
| S01 local startup | Fresh V8 full ordinary capture PASS on `f0a3420b`; latest 93.850 s to SSH |
| S02 transfers | Fresh V8 PASS on `f0a3420b`, four 256 MiB directions in 303.671 s |
| S03 service recovery | Fresh V8 PASS on `f0a3420b`, 35.081 s; earlier failures retained |
| S04 durability | Fresh V8 file and full capture PASS; original failed capture retained |
| S05 repeated boots | V8 three-boot sequence and independent replay PASS, 330.639 s |
| S06 powered-off start | NOT RUN |
| S07 combined load | V8 full 3600.030 s observation and independent replay PASS on `af960758` |
| F01 / F02 | Exact V8 F01 PASS 85.412 s; fresh F02 plus independent replay PASS, 29.141 s |
| R01 recovery | FAIL: early final-storage gate; negative claim consumed, full capture retained |

## Evidence, fast loop and retention

Use [development](development.md) for impact-based selection and cache reuse.
Full V8 A01/C01/C02 took **88.128/131.751/104.415 s**; unchanged artifacts reused.
Complete-upper correction `cdfe00572b81fca619231bdba26702bf8982667d` is pushed:
focused **18.252 s**, full local **533.553 s**, all four GitHub jobs PASS in
34172685138 (including exact-head/merge). Retain those original results; do not relabel them as testing later changed code.

Preserve the complete inactive upper snapshot used for composition:
`dff8988f3c2f4c5204d2e827114f63e54068acc530a75010dd2d522de3795388`.
Normal persistent state may change after boot; do not relabel the snapshot.
Private current work: `rog5-cpu-startup-20260908.kjE4IqCf`.
Detailed V6/V7 failures, V8 staging/runtime proof, fixture fixes, original
timings and exact retention procedures are in the
[existing dated report](../test-results/2026-09-05-headless-acceptance.md).

Home has about 6.6 GB free with the two isolated observer checkouts; preserve the 3 GiB reserve. V5's lossless reverse
delta and durable V7 base must stay together. Unique archives still occupy RAM:
no host reboot until retained safely. Never remove failed-soak scratch, accepted
payloads, private evidence or claims. Leave unrelated SteamOS CEF port 8081 alone.
Schedule heavy A01/C02 separately from full local CI; remote checks and bounded
independent preparation may overlap. No test deadline or release gate is reduced.

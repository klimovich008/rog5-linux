# Test-defined headless acceptance checkpoint

The existing server goal remains active. Display is optional. No boot, signing,
claim entry, experimental flashing or phone-storage mutation occurred in this
checkpoint. Exact read-only fastboot telemetry later confirmed the anchored
serial/product, slot B, 7699 mV and SOC yes; this is not charging/thermal proof.
Private retained inputs/fallbacks were not modified.

Registry correction: start `979e25eb77cb163f212020086490648389afb823`, published
`bf5f2e3125c073e188502fc664d2c5b554fabd76`. Full local CI 470.670 s;
GitHub 33935980881 passed exact-head, merge, publication and QEMU.

## Executable acceptance, not a new lifecycle

[Contract](../docs/release-acceptance.md) and
[manifest](../configs/release-acceptance.json) cover 25 mandatory outcomes.
`rog5-dev accept` provides quick/offline/device-smoke/release checks and a single
per-run results matrix. Missing prerequisites, unimplemented checks, skips,
deadline failure and source drift cannot become success. Results are never
imported/merged across builds. Source regression PASS is not device PASS.
Acceptance bookkeeping has 11 isolated tests; the skip-is-success regression
failed before correction. The first quick run passed in 16.515 s, slower than
the aspirational 3–6 s, and correctly reported `qualified=false`.
The first offline run correctly blocked D02 because host replay skipped retained
ARM compatibility. D02 now invokes the existing ARM binary replay directly:
all 14 tests execute without a skip (0.878 s), with no helper rebuild. This is
an acceptance-selection correction, not a weakened pass criterion.

## Demonstrated defects and smallest fixes

- **R2 / optimized Python:** composer used 31 removable assertions for hashes,
  metadata and output protection. New real-composer tests found 27 optimized-mode
  failing subcases before correction (3.481 s). Explicit rejection replaces
  assertions; 28 tests pass normally (5.076 s) and under `-O` (5.088 s).
  Accepted synthetic output/receipt remains byte-identical; no kernel change.
- **R2 / early power safety:** good temperature/voltage could hide unhealthy or
  absent battery health. Three pre-fix cases demonstrated acceptance or wrong
  failure classification. Good health is now required and rechecked during the
  existing bounded USB-ready wait. All seven focused tests pass (0.325 s);
  voltage/temperature/radio thresholds are unchanged.
- **R2 / deployed composition:** standalone builder refreshed init/attestation
  but retained the old power gate. A real disposable-archive build reproduced
  the stale payload (0.080 s). It now refreshes the existing power helper too;
  regression passes (0.082 s), unrelated fixture bytes preserved.
- **R2/R8 / watchdog evidence:** QEMU accepted an arbitrary archive but executed
  watchdog functions from repository source. It now extracts the exact archive
  functions and refuses missing/legacy disarm-style code before QEMU. Eight
  selection/provenance regressions pass (0.318 s). Mocked logs are explicitly
  not QEMU or physical evidence.

## Recovery subset physical inputs, offline only

Unsigned archive assembled in **3.104 s**, SHA-256
`05ed5bc4fdc0da1fe7d1799796a1d4a6c40b70058eca767442e22fe575c5b17f`.
Base hash `1daff38a2059b78d8376af01791fe4173fbe39dd9f1566f8c13f95ed76998b43`.
All 19 modules and all unrelated member payloads unchanged. Init, attestation,
power helper, shutdown and accepted service-state/identity helpers match their
rendered source. No kernel rebuild, new firmware or wrapper build occurred.
This is archive-subset evidence, not final retained-root/units qualification.

Exact sealed ARM BusyBox syntax: init 0.514 s, attestation 0.463 s, power helper
0.478 s. Syntax does not prove runtime hardware behavior.

Actual diskless ARM64 QEMU, retained kernel plus this archive's watchdog/BusyBox:

| Case | Result | Seconds |
|---|---|---:|
| current-boot ACK | PASS | 16.904 |
| missing ACK | PASS | 10.889 |
| stale ACK | PASS | 10.940 |
| retained helper unavailable → SysRq | PASS | 10.840 |
| hang after successful init exec | PASS | 10.790 |
| failed init → separate panic | PASS | 5.676 |
| watchdog FD-open failure | PASS | 2.670 |

The harness uses real switch_root/systemd and archive watchdog functions, but
its ACK producer/init fixture does not prove complete deployed units. No
simulation is substituted for physical recovery. Root filesystem composition,
real late SSH restart and independent capture remain separate mandatory tests.

## Next action and non-passing criteria

Preserve the old signed fallback and newly verified archive. Complete exact
retained-root composition and pre-boot receiver/address/lifetime checks, then
use existing admission for one fresh headless rescue. Do not issue another
display/radio successor. Health telemetry/charging must be measured on the phone;
fastboot SOC and historical voltage are insufficient. Remaining acceptance
rows are explicitly BLOCKED or NOT RUN, not an alleged completed release.

Offline acceptance r2 took **18.119 s**: six PASS, eight BLOCKED, eleven NOT RUN.
The per-run private `matrix.md` is the current executable matrix; no simulated
or historical device pass was imported.

Full local CI stopped after **324.537 s**: two native-controller terminal-response
timeouts (`zero_packet_rights` and `maximum-rights`). Those two cases passed in
8.300 s on focused replay; the entire 95-test controller suite then passed in
28.919 s. Source was unchanged. Host reconstruction I/O overlapped the initial
run, but contention is a hypothesis, not a demonstrated root cause. No timeout
was widened and no production controller/kernel change was made. The failed
full run remains failed; it was not rerun or relabeled green.

The obsolete temporary retained-root extraction was absent. For read-only
composition work, a host copy was reconstructed from the preserved compressed
sparse backup. Its compressed hash `5f03a8d…34f830` and sparse hash
`e6b3afac…f69996` match the recorded inputs. The expanded copy does **not** match
the original pre-sparse whole-image hash. Independent comparison verified every
RAW chunk and every zero-filled DONT_CARE region; reconstructed SHA-256 is
`06cc805b8735def6ee0d761705cdc33df217f975e8282df92ead31b3056506b0`.
The sparse backup omits 31,265,030,144 bytes: do not claim byte-for-byte recovery
of unspecified original regions. This is a derived inspection input, not proof
of complete restoration equivalence or authority for any flash. Read-only
`e2fsck -fn` passed all five passes. No mount, repair or original-backup write
occurred. The raw/sparse host copies each occupy 2.9 GiB and are retained read-only.

Host disk now has approximately 40 GiB free; no build data deleted. Kernel/
wrapper build and peak build usage are not applicable here. Source checkpoint
publication and fresh exact-head CI must retain the explicit local-CI caveat.

## Retained-root and RAM-delivery continuation

Continued from `21b2375c783254c3fac8ecee7fe7d4c4493b3ddd`. Its GitHub
run 33937660322 passed exact-head, merge, publication and QEMU; the earlier local
failure above remains failed. No phone contact or target candidate execution
occurred during this continuation's composition work.

The reconstructed host ext4 image was mounted **read-only, norecovery**, in a
private mount namespace, with backing-file and block read-only verification.
Mounts were removed automatically and absence verified. Root bytes and original
backups were unchanged. A debugfs extraction could not preserve all owners and
the host filesystem rejects OverlayFS lowers because of casefold capability;
neither is a target defect. Use the actual ext4 loop lower and tmpfs upper.

`rog5-dev check-rescue-root` exercises exact sealed `prepare_runtime` functions,
Arch systemd 260.2, volatile test host-key generation, effective key-only SSH
policy and all four generated units. PASS, **32.892 s** including final input
hash revalidation (initial receipt hashing/mount setup is additional). The
earlier runtime-only probe took 3.052 s. The deployed SSH host key was neither
read nor replaced. Five gate tests pass normally (0.030 s) and optimized
(0.028 s); 11 acceptance tests pass (0.256 s). A four-role component receipt
cannot qualify the five-role final release. A01 remains incomplete.

**R2/R8 delivery gap:** the prepared fallback-only recovery can load only the
old signed V11, not the corrected archive. A narrow `existing-recovery-ram`
branch now copies one fixed embedded bundle into private RAM and rejoins the
existing signed verification/kexec/Haven tail. It preserves storage geometry
checks and all-117-node read-only relocking; it never mounts P24, reads a
selector, opens trial state or modifies an installed bundle. No new kernel,
claim architecture or recovery controller. The builder derives the sealed
executor's manifest hash from staged bytes; packaging grants no admission.

Three RAM-path tests failed first (11 subcases); after implementation they pass
in 0.277 s, and all seven existing fallback tests pass in 0.494 s. Real sealed
recovery BusyBox replay of the same parser, file checks and shared-tail fixtures
passes in **3.008 s**. Hardware/crypto endpoints are explicit fixtures here;
actual signature verification remains a separate mandatory check. Unsigned
packaging fixtures produce identical twins for both existing and RAM modes;
extra embedded files fail before output publication. These are not candidates.

Next: freeze/full CI for this recovery change, then verify a fresh signed RAM
bundle/wrapper and establish pre-boot capture before the one-use rescue. The
old wrapper/claim remains unused; no source-only fix is described as deployed.
Current host free space is approximately 38 GiB; no build data was deleted.

## Prestarted capture and exact signed rescue

Delivery checkpoint `0afbc63e1a3811250b5cd5af1be5e7d34273943d` passed one
full local CI in **478.334 s** and GitHub **33940190642** (exact-head, merge,
publication, QEMU). Its clean offline matrix took 17.859 s: six PASS, eight
BLOCKED, eleven NOT RUN. These results do not qualify the new dirty checkpoint.

**R4/R8 host capture:** the old collector did not establish preboot addressing,
prove remaining lifetime or survive disconnect. The passive receiver now uses
canonical candidate/manifest identity, bounded concurrent clients, immutable
source/process receipt, a live TCP readiness challenge and retained last-stage
records. It never issues execution. H01 binds it to the release's exact boot
image. Missing capture is BLOCKED; mismatched candidate/image is FAIL.

A real host rehearsal exposed NetworkManager shared mode silently dropping a
secondary IPv4 address. No phone was booted. The partial temporary zone change
was restored, then the implementation kept the single shared address and used
a scoped loopback diagnostic address/direct USB route. The regression fails
the original approach. Corrected host rehearsal **PASS 2.699 s**, including
profile/address/firewall/listener restoration. A disposable network namespace
test passed real ARP/TCP and device-bound receive; namespaces were cleaned up.
Thirteen receiver/network tests pass normally (0.086 s) and optimized (0.089 s).
Twelve acceptance bookkeeping tests pass (0.220 s). The rehearsal predates the
final source-receipt binding; fresh final-release H01 is still required.

**R2/R8 exact delivery:** deterministic signed bundle and wrapper twins took
**11.085 s** total. Wrapper archive builds were 3.662/3.654 s, repacks
1.422/1.382 s; signing/packaging 0.301/0.274 s. No kernel was rebuilt. Retained
target Image/DTB and all 19 modules are unchanged. Archive size 45,586,876 bytes,
raw boot 96,092,160 bytes, boot-envelope image 100,663,296 bytes. The AVB footer
is algorithm NONE; authentication is the embedded Ed25519 target signature,
plus exact outer-byte admission on the intentionally unlocked phone.

- Target manifest: `18b365468fe42d5e374abcbc57bae10d06ca1fd42708348f6d38afe59fd718dd`
- Recovery archive: `316cb1f83f2f65d2ed57ee38fc5042b8031465feb2093ee7e9a624278a6b75e3`
- Boot image: `dd96e3aab8775301f4bcef9313aa02b31b7efa3c18a3aee580e0052c314efcfb`

Exact sealed ARM verifier passed in **2.686 s**, including signature, payload
hashes and generated plan (600 s target, 900 s rollback). Public trust identity
matches the retained verifier; private material remains outside Git. No new
key was generated. Old signed V11 and the unused old rescue are preserved.

The new RAM-embedded family initially failed canonical admission closure (six
failures/one error, 3.082 s). Its consumer now derives this family from the same
fixed registry. Altered records and repeated consumption are regression tested.
All 31 admission tests pass (3.317 s); all 18 claim tests pass (0.138 s).
Active tier passed in **9.639 s**. A fresh host rehearsal with source/receipt
binding and the actual new candidate passed in **2.836 s**, restored all owned
state and performed no boot. A subsequent delayed-link/zone regression failed
first: sysfs discovery incorrectly installed a route before link-up. The final
receiver waits for link/profile/zone convergence within the unchanged global
deadline. All 14 receiver tests pass, including optimized Python (0.090 s).
No claim was issued/consumed, phone boot performed, slot changed or phone
storage accessed. Peak build disk usage was not instrumented; no peak figure
is claimed. No build data was deleted. Live recovery remains the next milestone,
not postponed until all later server criteria are implemented.

## First coherent rescue trial and acceptance-driven continuation

`eef710f713184755bc67a30904f4cfd6b7fe2dd1` passed full local CI **485.693 s**
and GitHub **33942832456**, all four jobs. The wrapper's actual header retains
`rog5.recovery_timeout=300`; its verified target plan carries 900 seconds.
Final input rehash (including the retained 32 GiB inspection filesystem) passed
in 31.637 s. The retained bundle/wrapper/inspection outputs occupy 665 MiB,
not a measured peak build footprint. No kernel rebuild or artifact replacement.

The actual privileged/unprivileged receiver handoff rehearsal passed in
**3.161 s**. A later private preflight failed before any claim/boot because
the restricted PATH omitted the installed GitHub CLI. It now uses the exact
installed executable; restricted-PATH replay passed. This was an R4 host-only
failure, not a reason to build another target. Failed evidence is preserved.

One subsequent RAM-only boot consumed `headless-acceptance-rescue-v1` permanently.
Fresh preflight: exact serial/product/topology, slot B, 7700 mV, SOC yes; both
slots not marked unbootable. No flash, slot change, GPT or destructive write.
The target's accepted bounded service-state behavior remains its storage scope.

| Required observation | Result / evidence | Next action |
|---|---|---|
| H01 preboot readiness | PASS: live nonce/process/source/artifact check before claim; ACM/NCM started in advance; full 1380.783 s capture and owned cleanup passed | Retain exact record, no retry |
| Recovery verification/kexec | ACM reported bundle verified, kexec loaded and execute; exact fastboot accepted in 12.817 s | Preserve consumed record |
| Target handover | `switch-root PASS`, sequence 25, boot `7c433fca-508e-4c5a-865d-3cc8808a6473`, about 47.7 s from host adapter start | This precedes exec; not systemd acceptance |
| H02 pinned SSH | **FAIL at 300 s**: listener offered a different host key; expected pin unchanged | Diagnose P2/state/identity startup, do not bypass host authentication |
| H03 charging/thermal | BLOCKED: no authenticated telemetry | Restore qualified access first |
| R01 physical recovery | NOT RUN: no controlled failed-test boot was performed | Do not substitute this unexpected failure or QEMU |

The target remained enumerated beyond its 900-second timeout. This is consistent
with a P2 readiness acknowledgment but does not prove it; watchdog failure is
also not excluded without target evidence. There is no pstore/crash conclusion.
No candidate retry or second boot was requested. The full 1380.783-second
capture completed independently of offline edits; owned route, firewall,
profile and address cleanup passed. The phone remained in target gadget mode.
Physical fastboot re-entry is requested because pinned SSH cannot request a
clean reboot. Raw logs and credentials stay private.

**R2 SSH format defect:** real Ed25519 files reproduced three valid-key refusals
(0.139 s). Their comments change encoded lengths; the historical test invented
399/92-byte stat output. Validation now preserves exact owners, modes, no links,
bounded input sizes, Ed25519 type and cryptographic public/private agreement.
It does not change the pinned identity or admit mismatched keys. Three focused
tests pass (0.253 s); the old state/helper suite passes with real metadata.
Exact sealed BusyBox and retained Arch ARM ssh-keygen reproduced the old defect
and passed the correction in **2.145 s** (399/92 versus 419/107 bytes). These are
disposable test keys, not device credentials. The retained hostname `alarm`
means this defect is not established as the current phone failure's root cause.

**F03 slow-client defect:** the real service timed out another healthy client
while a sender kept its header incomplete (2.118 s). An absolute timeout alone
still failed concurrent idle/trickle clients (1.123 s). A four-client bounded
threaded server plus an absolute one-second request deadline now lets a healthy
client finish within the predeclared one-second bound. Eight tests pass in
**0.539 s**. F03 now runs these actual behavior tests from the acceptance
manifest. The fixed service and SSH helper are source-only, not this trial's
deployed bytes. No mixed-release qualification is claimed.

Follow-up active tier passed in **11.087 s**; acceptance bookkeeping passed
all 12 tests (0.318 s). The final slow-client case waits for an actual timed
0.2-second trickle byte before requesting health, preserving the declared
one-second healthy-client response limit. Full CI/publication belongs to this
separate frozen source checkpoint, not the already consumed rescue's identity.

`0daad2546a1adf171196b458c281b4b40c125e97` passed full local CI in
**479.828 s**, once on the frozen clean tree. The offline acceptance dispatcher
took **19.122 s**: seven PASS, seven BLOCKED, eleven NOT RUN; result BLOCKED,
qualified false. No historical artifact receipt was relabeled as this source.
GitHub 33944557168 exact-head, merge, publication and QEMU all passed.
The latest F03 replay took 0.816 s under
concurrent CI load, within its unchanged deadline.

The concrete next observability gap is post-handover: P2/state/identity helpers
write failures to target kmsg, while the early NCM stage record ends at handover.
The old SSH diagnostic waits for an authentication event and forcibly reboots;
it must not be enabled unchanged as a passive startup observer. A scoped
source-only observer now reports these service outcomes over the existing
prestarted channel, without exposing key material, accepting an unpinned key,
delaying rollback or changing storage operations. No successor has been built,
signed, issued or executed. Physical fastboot re-entry was requested after the
full capture/cleanup; no authenticated software reboot is available.

Observer regressions first failed on the absent implementation (eight errors).
Four producer/receiver cases now pass normally and under Python optimization,
including missing/failed services, unavailable journals, framing bounds, wrong
release/boot, and unrelated-log exclusion. The early stage stream remains
separate: unauthenticated observations never become stage or SSH PASS. The
receiver preserves the latest startup observation on disconnect and completion.
The standalone builder includes exact observer bytes and runtime-unit lifetime;
no kernel/module change. The active tier passed in 10.116 s before the final
kernel-journal filtering refinement. Initial sealed ARM replay passed in 4.005 s;
its isolated fixture needed private `/dev/null`, not altered production syntax.
Actual sealed BusyBox timeout/kill behavior passed in 1.515 s, and retained Arch
ARM journalctl exposes the required current-boot/kernel/grep options. The helper
limits each query/send to two seconds and the full observation to the existing
target budget, independently bounded by systemd RuntimeMaxSec. These component
results are not live deployment or full A01 qualification.

Final focused checkpoint: active tier PASS **10.613 s**; sealed ARM producer
replay PASS **6.016 s** under concurrent host tests. Full local and exact-head
GitHub checks are required for this new receiver/initramfs checkpoint before
any successor admission. The consumed physical rescue is unchanged.

Observer commit `42c729d89035c6668e85b19320f725a30926621e` passed full local CI
**479.663 s**, and GitHub **33945569616** exact-head/merge/publication/QEMU.
Seven exact-archive watchdog handover cases passed against unsigned archive
`ce1b0b11…dce1a` (23,831,684 bytes). Only init and SSH-identity helper changed;
the observer was added, nothing removed, all 19 modules byte-identical.

**Host composition fixture omission:** real sealed preparation against the
retained read-only Arch loop image failed in **0.877 s** with
`recovery_timeout: parameter not set`. This is the checker's synthetic driver,
not a missing variable on the actual target boot path. Two regressions failed
before the correction: missing lifetime input and stale observer acceptance.
The checker now supplies a labeled one-second unit-generation fixture (never
activated; not a deployed deadline), verifies current observer bytes when
present, and includes its unit in real ARM systemd-analyze validation. Seven
focused checks pass normally/optimized (0.034/0.036 s); active tier **11.462 s**.

Exact archive/root replay then passed in **31.786 s** with the same archive,
kernel, DTB and root image. Preparation, ARM systemd, volatile key generation,
key-only SSH policy and generated units passed. This result binds the changed
checker via the dirty-tree digest at the old HEAD; it is not relabeled as a
clean published release. No kernel/archive rebuild was needed for this host
fix. Both host-only loop mounts were read-only/norecovery, in private namespaces,
and removed afterward. No phone contact, storage mutation, signing, candidate
issuance or boot. Final wrapper/deployed timing/module-load A01 checks remain.

Host-only checker fix `df871166458599e61d02b6732147b70077fade64` passed all
GitHub **33946155200** jobs. No unchanged full local suite was rerun for it.

**F02 restart preparation defect:** the real `prepare_network` function refused
every second invocation with `network already prepared`, preventing WPA's
ExecStartPre from succeeding on restart. A real-file regression failed first
(0.283 s). Repeated preparation now validates existing directory/file ownership,
modes, regular-file/link status, exact inventory, DHCP config emptiness and
unchanged private-config bytes. It never replaces changed secrets or repairs
ambiguous partial state. The same qualified interface is brought up again;
radio/module activation is not part of this function.

Three real-file test cases (with hostile subcases) pass in **0.501 s**; 28
existing Wi-Fi boot tests pass in **4.938 s**. Exact sealed BusyBox replay passes
in **14.375 s**, using private writable fixture directories and fake hardware,
mount and service endpoints. The active tier passes in **11.090 s**. No key or
network credential is used beyond disposable fixture text. These results do
not prove a real systemd restart transaction, DHCP recovery or live SSH, so F02
remains BLOCKED and the acceptance criterion is unchanged. No kernel/archive
rebuild or physical attempt; the prepared headless archive has no Wi-Fi payload
and is unaffected by this userspace source change.

**C02 real transaction component:** source checkpoint `a8558244` passed all
GitHub 33946711767 jobs. A new isolated test uses the real host user systemd
manager and loopback-only sshd with a disposable host key (all logins disabled).
The source timer and SSH Requires/After relationship drive the production
rollback function under sealed ARM BusyBox. Identity, healthy ACK and reboot
are fixtures; no host system bus or block device is exposed in that sandbox.

Two fixture runs failed (10.902/11.507 s): transient units disappeared after
stop, then the fixture incorrectly expected an already-fired OnBootSec instant
to fire again. User journal evidence confirmed timer reactivation without a
second callback. The corrected test matches the production health sequence:
stop the timer before first expiry, wait past the deadline, then restart SSH.
The valid current-boot ACK prevents reboot; a stale ACK records rollback. Both
SSH PID replacement and unchanged disposable host identity are checked.
This passed in **10.875 s**. Runtime-only unit links, daemons and fixtures were
cleaned up. These were host fixture failures, not newly proven phone defects.

The sealed archive is unchanged (`ce1b0b11…dce1a`); host systemd is 257.7,
whereas retained Arch is 260.2. The timer/runtime are current repository source,
not extracted Wi-Fi payloads from the headless archive. Therefore this is a
supporting component, **not a full C02 PASS**, not authenticated phone access
and not S03. Its `rog5-dev check-ssh-rollback` entry has a fail-first dispatch
regression. No kernel, candidate, claim, signing or physical execution changed.

Frozen entry-point replay passed in **10.997 s**, alongside active tier
**10.613 s**. Acceptance bookkeeping passed all 13 tests normally and optimized.
No full local CI repeat was needed for this host-only test/entry/documentation
checkpoint; the prior full local result remains separately identified, not
attributed to these edits. The current physical descriptor remains persistent
Linux, not fastboot; no authenticated recovery or charging PASS is inferred.

**A01 sealed module metadata gap (R2):** the root composition checker paired
scripts with repository source but did not inspect the archive's module
inventory/dependencies. A fail-first regression exposed the missing check.
It now reads all module metadata from those exact bytes, requires regular
single-link root-owned AArch64 relocatables, matching names/release/full
vermagic, and resolves each dependency before its consumer in the reviewed
power-then-UFS order. Missing/extra/aliased modules, bad architecture/release,
unresolved or late dependencies and a ten-second overall expiry are refused.
Eight focused tests pass normally/optimized (0.037/0.038 s).

All **19 unchanged modules** from unsigned archive `ce1b0b11…dce1a` passed
the real host metadata check in **0.499 s**, with hashes and order retained
privately. Separate exact BusyBox metadata inspection passed in 1.474 s only
after supplying its explicitly labeled empty `modules.dep` fixture. Without
that file BusyBox modinfo refused the query; production uses direct insmod,
so this standalone inspection failure is not a demonstrated boot defect.
No artifact changes were needed. BTF/symbol resolution and hardware load are
not inferred from metadata; A01 remains BLOCKED on complete final composition.

The timeout source audit confirms signed `rollback_timeout` feeds
`rog5.recovery_timeout`; target init accepts 300–900 seconds, and observer and
watchdog share that variable. The consumed manifest specifies 900 seconds.
This is source/historical evidence only: a new wrapper and signed target must
still prove their actual command line together before admission. No new
candidate is issued and the consumed rescue remains permanently non-retryable.

Final module replay passed in **0.507 s**, including verification that sealed
init actually invokes power before UFS. Focused normal/optimized tests passed
after that refinement. GitHub **33947683439** completed all four jobs for
`a7f088c5`; this is the previous checkpoint, not CI for the new module check.
Frozen active tier passed in **10.320 s**; no kernel/archive rebuild or full
local CI repeat for this supporting host-only composition check.

**Prepared v2 recovery checkpoint:** all GitHub 33948165386 jobs passed for
`17d7fbb663c696a9e8047f126cb3d25f4df65230`. The next signed bundle and RAM-only
wrapper are now packaged as `headless-acceptance-rescue-v2`, not yet executed.
The primary question is which post-handover P2/state/identity service prevents
pinned SSH acceptance. The existing optional startup observer supplies the
missing failure channel; no kernel, DTB, module, radio threshold or storage
scope changes are included.

One private build specification generated the successor recipe. The reviewed
signing/repack workflow produced byte-identical target and wrapper twins in
**28.690 s**, including focused checks. Both retained kernels were reused;
there was no kernel compilation. Retained packaging/inspection occupies about
664 MiB; 37 GiB host space remained. This is retained usage, not a measured
peak. Private material and proprietary artifact bytes stay outside Git.

The final wrapper was unpacked independently. Embedded recovery/kernel/target
bytes and the exact generated RAM executor match. Its actual sealed ARM
verifier authenticated the signature, hashes and target plan in **3.767 s**:
600-second target budget, 900-second rollback, one exact v2 bundle token.
All 19 sealed module metadata/dependency checks also pass. Wrapper
`b0cb5a31…`, recovery `13ba0b6f…`, manifest `a49507e8…` are now bound in one
canonical registry row generated from that verified record; no live claim
file was created or consumed. Existing all-family tests exercise the new row.

Explicit reuse: target archive `ce1b0b11…dce1a`, accepted kernel/DTB and retained
Arch bytes are unchanged, so their prior exact-archive watchdog and root
preparation results remain supporting evidence. No passes from a different
release are imported into the acceptance matrix. Full A01, live rescue/charging
and final server qualification remain incomplete. The v1 consumed record and
all old evidence are preserved. Source is frozen for one full local candidate
checkpoint, followed by exact-head publication; no phone boot is part of it.

Registry-focused checks passed in **3.719 s**. The frozen full local suite
passed in **480.918 s**, once, ending with `PASS repository Linux ci tier`.
No kernel/source edits occurred during that run. Exact-head/merge CI for the
new registry publication remains separate; parent CI is not substituted.

## V2 physical result and acceptance-driven corrections

Exact published source `3e41768e8e087f3d96ac429e615c77e30863d8cd` passed all four
GitHub 33949091531 jobs. Connected preflight checked exact serial/product/path,
slot B, both bootable slots, the expected bootloader, 8.386 V and SOC=yes before
claim consumption. Capture/addressing/firewall preceded one RAM-only boot.
Transfer/boot acceptance took **12.728 s**; v2 is permanently consumed.

Boot `910d80ee-51ec-4629-a6bc-debd52803606` reached sequence 25, root handover.
The passive observer then reported P2 active/exited success, persistent-state
failed/exit 1, identity inactive and early SSH running. This is diagnostic,
not authenticated proof. The pinned host key was never accepted or changed.
H02 **FAIL**, 300-second bound, final accounting **301.696 s**; H03 **BLOCKED**.
All journal queries returned error, so the failing state predicate remains
unknown. Kernel, DTB and module bytes were unchanged; no kernel cause is proven.

At 12:45:37 local, host kernel logs show the parent hub `1-1` and sibling
`1-1.1` disconnecting with the phone (`1-1.2`). A concurrent `nmcli -g` failure
escaped the receiver loop as RuntimeError. Capture ended prematurely after
**322.454 s**, so rollback observation is incomplete, not a watchdog PASS.
Route, firewall, profile and address cleanup each passed. No flash, GPT or
protected storage operation occurred. Admitted normal p23 service-state effects
remain possible; unauthenticated output does not prove their exact extent.

The sanitized real-observation fixture is
`tests/fixtures/persistent-root/rescue-state-host-loss.json`. Private execution,
ACM, NCM, SSH, receiver and cleanup logs remain intact with computed hashes.
The receiver regression reproduced the same RuntimeError before the fix.
Known discovery/network failures now keep the original bounded capture alive,
retain last stage/startup evidence, permanently invalidate readiness, and
recheck identity. A mismatch still stops; an unverified target cannot send
accepted evidence. No retry/claim/boot action was added. Sixteen tests passed
in **0.088 s**. R7 host exception and R8 premature observation loss apply.

The observer regression reproduced lost helper text when journal access fails.
A bounded, read-only 64 KiB kernel-ring fallback now filters only the fixed
helper prefix; journal failure remains explicit and unrelated text is excluded.
The exact sealed BusyBox supports the requested dmesg flags. Tests execute the
updated shell/filter with that BusyBox in isolation; kernel/journal endpoints
are fixtures, not new live evidence. This addresses R3/R2 observability, not
the unproven state-start cause. No successor was built to test these changes.

**E02 optional isolation:** a valid optional payload with no power-key input,
backlight or tty previously failed core installation or its display precommand.
Four cases failed against the old runtime (0.831 s). The updated installer
validates artifacts before tolerating exact input absence, enables only available
optional units, and makes the display-off precommand nonfatal. P2 still rejects
a physical backlight left on; module/ABI/integrity/identity and ambiguous input
failures remain fatal. No radio or health acceptance rule was changed.
New executable tests passed normally (1.300 s) and with sealed v2 BusyBox
(13.667 s); existing Wi-Fi tests passed (28 tests, 5.504 s). Hardware and service
endpoints are fixtures. E02 is registered in the active/broader tier and the
acceptance contract; exact release composition and physical proof stay separate.

**Storage cleanup status (R8):** `relock_storage()` reset the callers' global
`status`, masking earlier unmount/detach failures and even the startup cleanup's
incoming exit status. A scoped result variable fixes that defect without changing
any storage operation or identity/read-only guard. The regression executes the
actual stop and EXIT-cleanup functions with 117 mocked physical nodes, including
failed relock/read-only checks. Six cases failed per runtime before the fix;
all 22 host-shell/exact-v2-BusyBox cases pass afterward (**17.85 → 17.87 s**
for the focused suite). This does not identify the live startup predicate.
An existing `/persist` is also rejected in volatile-overlay mode, but no retained
live evidence proves that directory existed; that guard is not weakened.

All corrections above are source-only. No kernel/DTB/modules were changed,
no new successor was built, and consumed images remain immutable. The final
sealed observer regression passed five tests in **5.561 s**. Current source is
frozen for the active/acceptance checks and one full local CI checkpoint.

That frozen checkpoint passed active in **10.737 s**, quick acceptance in
**16.704 s**, offline acceptance in **18.964 s** (seven PASS, seven BLOCKED,
eleven NOT RUN), and full local CI in **477.740 s**. It was not published as
a recovery-ready release: a targeted caller check then reproduced another
shutdown defect, not a new live startup diagnosis.

Non-overlay `stop_state()` called the startup owner resolver, which required
all physical storage RO despite successful startup's exact disk+p23 RW window.
It refused before inspecting runtime identity or attempting cleanup. The resolver
now has explicit lifecycle modes: startup/preflight retain all-RO admission;
stop requires the unchanged exact two-node write window. Overlay behavior and
runtime-record guards are unchanged; invalid lifecycle modes reject.
The real resolver, validators and stop path failed before this correction on
both host shell and archived ARM BusyBox. All **52 cases** now pass, including
wrong writers/count/runtime identity and cleanup failures (**32.86 s** focused).
This test no longer mocks away the resolver that hid the entry contradiction.

The combined source is frozen again for final CI because storage code changed;
the preceding full pass is not substituted. No unchanged-code full rerun or
kernel rebuild is involved. Startup's exact failed predicate, complete watchdog
recovery and authenticated charging remain open before successor admission.

Final combined full local CI passed in **479.193 s**, ending with
`PASS repository Linux ci tier`. Frozen tracked diff SHA-256 was
`94ba32cab5cffeb47607234d7cadfefcaf141eb9a2b917201516e37d5911f6e3`;
source did not change during execution. Only result documentation is added
afterward. Publication/exact-head CI and live qualification remain separate.

## Publication portability correction and fastboot recovery

Published `5ee350c5ce9d36da3d08ef0aa7696b91021e3125` failed both head-exact and
merge-compat in GitHub run 33963548732; publication and QEMU were skipped.
Ubuntu Dash rejects the fixture's function named `[` with `Bad function name`.
The host Bash and sealed BusyBox runs had accepted that test-only syntax.
All 26 host cases reproduced the CI failure in the existing read-only Ubuntu
container, with networking disabled. This is R3/R7, not a phone/kernel defect.

The fixture now redirects bracket command tokens in extracted functions to a
portable named predicate; production source and case globs are unchanged.
Each runtime syntax-checks its complete fixture before running cases, and failed
cases now include bounded stderr. All 26 Dash cases pass (1.324 + 0.929 s),
as do the 52 host/sealed-ARM cases (3.062 + 2.074 + 14.324 + 13.490 s).
Active tier passes in **12.266 s**. No unchanged-production full local rerun;
the corrected exact-head/merge run remains required before candidate admission.

After the operator reconnect/recovery, read-only checks identify exact serial,
product `lahaina` and canonical side topology, active B, **8523 mV**, SOC=yes.
No boot, flash, claim, slot change or storage access occurred. The black screen
and earlier hub loss do not establish a target crash. Authenticated SSH,
temperature and sustained charging remain unverified.

## Startup failure discrimination

Primary question: which service-state startup gate prevents persistent SSH
identity activation? Layer: target shell/observation (R3/R2), not the kernel.
Four injected pre-write rejections all produced the same generic message before
this correction (0.014 s), losing the distinction between device, owner,
root-mount and filesystem checks. Fixed, non-secret phase labels now accompany
startup failure without changing predicates, write operations or cleanup.
The existing bounded observer protocol carries these labels unchanged.
Tests execute the actual startup dispatcher and failure exit, mock the four
read-only endpoints, and reject unexpected I/O. They do not claim a live cause.
Other startup phases label existing path, loop, mount, tree and publication
groups; no new framework, kernel build or candidate is involved.

The user permits Debian if it is easier. Debian 13 supports ARM64, but this
project currently binds Arch-specific root metadata and `/usr/bin/sshd` units.
The retained failure is in the project's distribution-independent storage
helper; switching the root would require new composition/boot qualification
without removing that helper or the custom hardware-support work. Keep Arch
for recovery; a Debian migration is not justified as a fix for this evidence.
Reference: https://www.debian.org/releases/trixie/arm64/

Validation: six observer tests pass in 0.192 s; the sealed BusyBox run passes
in 8.691 s. The production failure function retains exit 1; only its test log
destination is redirected, so named observations cannot manufacture success.
Active passes in 10.977 s. Full local CI passes in **480.168 s** on frozen
diff SHA-256 `7a0c89da589b2faf234a3df29e7e6c839d81e297e353c09aa593eedaeedf4ddd`
over `04d4d0122ac6f9846ce3e4febcbfd05770e71260`. Source stayed unchanged through
CI and archive assembly. Publication result documentation is added afterward.
All four GitHub jobs for parent `04d4d012` passed (33964552884); these are not
substituted for the diagnostic checkpoint's eventual exact-head checks.

An **unsigned, non-admitted** target archive built in 3.116 s: 23832280 bytes,
SHA-256 `e2192af94efe1dcc8e00e9041b29305bc4b82ed9352ea19d49d1d49da5ce2ffe`.
Full entry comparison against retained v2 finds exactly two changed files,
`usr/local/sbin/rog5-persistent-state` and `usr/local/sbin/rog5-startup-observer`,
both equal to source. No additions/removals; all 19 modules are identical.
The isolated archive shell syntax check passed in 0.441 s; six observer tests
using its actual BusyBox/filesystem passed in 8.877 s with mocked endpoints.
No kernel rebuild, signing, candidate issuance, phone contact or boot occurred
during this diagnostic checkpoint. The source archive's consumed status grants
no right to execute it again; this derived archive also has no boot authority.

Read-only watchdog inspection and the existing executable acknowledgment test
confirm that P2 alone is currently sufficient, with no persistent-state/SSH
identity record present. The earlier QEMU `systemd-ack` fixture deliberately
models that narrower condition. It must not be presented as recovery from
failed persistent-state startup after P2. Close this readiness gap before
another rescue while preserving current-boot identity and healthy late-restart
behavior. This does not establish what caused the physical USB disappearance.

## P2/identity watchdog readiness correction

Focused independent read-only review confirmed the narrow fix; main review
verified the actual producer ordering and consumer. The v2 observed combination
(P2 pass, state failure, identity inactive) reproduced premature acknowledgment:
twelve missing/stale/malformed/unsafe identity cases incorrectly passed before
the fix (0.212 s). The old producer also accepted an invalid boot fixture and
published no boot binding (fail-first 0.007 s).

The existing identity record now appends a validated `identity_boot_id` after
successful local key/reload/listener setup, preserving atomic no-overwrite
publication. The watchdog requires P2 **and** an exact four-line, bounded,
root-owned 0444 single-link identity record for its captured boot. It rejects
legacy producers, metadata errors with plausible output, unknown/duplicate
fields and stale identity. The record remains a latch: no systemctl/PID/listener
liveness check can reboot a previously accepted boot solely for an SSH restart.
This is local startup evidence, not host-authenticated SSH or full server health.
The reset helper, SysRq path, panic behavior and phone deadlines are unchanged.

Eight focused watchdog/publication tests pass (0.471 s), including preflight and
failed-apply nonpublication, once-only publication and valid identity not
rescuing invalid P2. Active passes in 12.641 s before composition follow-up.
Read-only review found no actionable issue in the producer/consumer/test diff.

The unsigned archive built in 3.183 s without recompiling a kernel; SHA-256
`399e2b9099401961b9e0bbe51bbb5447d148a1b75a89310d397962e41460aded`.
Its exact watchdog functions and BusyBox passed all **nine real QEMU handover
cases in 133.550 s**: current P2+identity; missing P2; stale P2; P2 alone; stale
identity; unexecutable helper reaching SysRq; post-exec hang; failed init/panic;
and failed watchdog FD setup. The successful fixture has no running SSH listener.
ACK producers remain fixtures; this does not replace C02 real service restart
or physical recovery qualification. The nine subprocess bounds plus setup need
500 s offline: a fail-first lattice test reproduced 400 < 9×50+50, and C01 now
uses 500 s. No hardware deadline was extended and no pass condition relaxed.

Composition follow-up reproduced four missing/stale helper cases being accepted
despite a fresh watchdog. The exact archive/source checker now requires both
startup and identity helper bytes; eight tests pass in normal/optimized Python
(0.058/0.057 s). The real archive builder test binds the new producer too.
No candidate was signed, admitted or executed. All fixes remain source-only.

The complete frozen correction passed full local CI in **502.802 s** (previous
diagnostic checkpoint 480.168 s). Source remained fixed at dirty-tree digest
`550fd21deadf82cc870e5d93c4d1a773097a881e09f52ec7eed8bade3fa78ee4`
over `35f15179f60b4810671896d7537b47af7aecc9ad`. Only result documentation is
added afterward. No unchanged-source QEMU or full local run was repeated.
The exact-head publication result and a new connected preflight remain required.

## Fresh identity-gated rescue packaging

All four GitHub jobs passed at source `e6966506e987a9b7681ef118bd6f001726c4855c`
(33966699057): head-exact, merge-compat, QEMU and candidate publication.
Fresh `headless-acceptance-rescue-v3` packages that source's verified archive.
Its one question remains the persistent-state startup phase behind missing
pinned SSH; R2/R3 diagnostics and R8 identity-gated rollback are now paired.
No distribution or kernel change is inferred from the retained failure.

Signed target bundles and RAM-wrapper twins match. Packaging took **12.936 s**
(v2: 28.690 s), with no kernel compilation. Final assembled wrapper verification
took **3.771 s** (v2: 3.767 s): exact recovery/loader and target bytes, Ed25519
signature, artifact hashes, module metadata and 600/900-second target/rollback
plan. The unlocked RAM wrapper retains the reviewed AVB NONE outer format;
it is the embedded target manifest that is signed. Output footprint is about
664 MiB. Full source CI is explicitly reused from the unchanged correction
(502.802 s), not represented as a new registry-only full run.

The canonical claim record is generated from the verified artifacts and binds
the source commit. Consumer tests pass (18 cases, 0.145 s), receiver tests pass
(16 cases, 0.091 s), and admission/registry closure passes (31 cases, 3.407 s
wall clock). No duplicated executable family branch was added. Adding the
expected BOOT_CLAIMED record is not an actual claim transition or boot authority.
No claim/anchor, phone execution, flash or storage operation occurred during
packaging. Publication and connected admission of this exact registry checkpoint
remain separate; v1/v2 remain permanently consumed.
The registry/documentation checkpoint's active tier passed in **11.134 s**.

## V3 live startup-path finding and narrow handover correction

Publication `0d4b30bc36624e126b0464c584145f6c5873eacb` passed all four GitHub
jobs (33967429714). Fresh connected admission verified exact identity/topology,
slot B, 8509 mV/SOC=yes, both slots bootable and the reviewed bootloader version.
The final archive/retained-Arch runtime check passed in 32.652 s; its private
read-only mount was cleaned up. This is composition evidence, not full A01.

V3 was consumed exactly once. Fastboot transfer/acceptance took **12.879 s**;
supervisor execution return took 15.602 s. No flash or GPT operation occurred.
Boot `f6118c33-f715-438a-a3f2-9bf934abdad0` reached switch-root PASS (sequence 25)
and reported P2 success, state exit 1 at `start/userdata-path`, and inactive SSH
identity. The host rejected the unpinned early key. H02 failed its 300 s deadline
(301.633 s accounting); H03 is BLOCKED. Diagnostics are unauthenticated and do
not constitute SSH acceptance. The receiver remains active through rollback.

R2/R3 composition defect: `handoff_persistent_root` creates userdata-rw in every
mode, while state-owned startup/preflight require it absent before opening the
write window. The retained Arch lower has no such directory. A regression joins
the actual handoff and pre-write state predicates, with mocked device/mount I/O:
the native non-overlay case fails before the fix (0.169 s). Only the handover
destination is now created when needed. Legacy image-root and persistent-overlay
paths remain available; empty preexisting directories, files and symlinks are
not removed or accepted as state-owned startup paths. Storage guards are unchanged.

Seven observation/boundary tests pass (0.374 s) and pass under the sealed ARM
BusyBox/filesystem (12.427 s); handover/rollback tests pass (0.658 s). The captured
failure text is also replayed through the existing kernel-buffer/parser test.
The fixture does not perform real mount moves or start/write the service image.
The patch changes target init only, not either kernel or the running v3 bytes.
Full CI and a fresh composition remain required before any successor.

Final source validation: active **12.501 s**, full local CI **499.971 s**.
The frozen diff SHA-256 stayed
`4c6b7594b4d94fcc778ce74a4f33c1249f6cbde28a1505a5e056b148b814065f`
over `0d4b30bc` throughout CI and archive assembly; only result docs follow.
Unsigned archive assembly took **3.147 s**, size 23833960, SHA-256
`1b4db7d1cce046ee9d11413152b66817081187b0970a3c888d7a1cf10ff8cea2`.
Complete entry comparison finds only `init` changed, with all 19 modules and
other payloads/owner/mode/link metadata unchanged. Source/composition pairing
passes; seven boundary/observer tests on its sealed BusyBox pass in **12.404 s**.
No successor was signed, admitted or booted.

The v3 phone disconnected at 15:21:59 +0200, about 900 s after target enumeration,
and exact fastboot returned at 15:22:04 without any intervening host reboot
command. Fresh serial/product/topology checks passed, slot B, 8544 mV/SOC=yes.
This strongly supports the deployed identity-gated rollback but does not provide
an independent PMIC/reset-cause reading or qualify the full persistent fallback.
Capture ran **1380.532 s**. The known bounded `nmcli -g` failure occurred during
target USB removal: readiness remained invalidated and the result is FAIL, but
the receiver stayed alive to capture fastboot. All four owned cleanup steps
(route, firewall, profile, address) passed. No transport exception was waived.
No authenticated charging result exists; the voltage rise alone is not H03.

## V4 corrected handover packaging

Fresh `headless-acceptance-rescue-v4` packages the unchanged verified archive
from `0b4e821635fcb303495b003679cd7cc497de8223`. R2/R3 question: does corrected
handover restore persistent state and pinned SSH? Packaging took **12.122 s**
(v3: 12.936 s); signed bundle and RAM-wrapper twins match. No kernel compilation.
Final sealed verification passed in **3.769 s**: wrapper embedding, signed
manifest/artifact hashes, exact target/recovery plan and module metadata.
The outer RAM image retains the reviewed AVB NONE format, not a signed AVB chain.
Private output footprint is about 664 MiB. No retained artifact was deleted.

Full local source CI is reused explicitly (499.971 s). Retained-root preparation
and unit evidence is reused only for its unchanged function/helper/root inputs;
new joined handover/state tests cover the changed boundary. This is not full A01
or physical qualification. Claim/receiver/admission tests pass (18/16/31 cases,
3.929 s combined). Registry data is generated from the verified artifacts.
No claim entry, boot, flash or phone-storage action occurred during packaging.
Exact-head publication and connected admission remain separate.
The registry/documentation active tier passed in **11.394 s**.
All four source CI jobs passed at `0b4e8216` (33969178949); these are not
substituted for the registry checkpoint's connected publication gate.

## V4 live handover and pinned SSH recovery

Publication `385ed8c9d7c3176bb3f10cc27e5b9987ab02011b` passed all four GitHub
jobs (33969700863). Connected admission passed and v4 was consumed exactly once.
Fastboot transfer/acceptance: **12.788 s**; supervisor execution return:
**15.453 s**; pinned SSH acceptance: **57.196 s**. No flash or GPT change.
Boot identity: `0a81d0a7-7d96-44d0-93a2-0758ef803a33`, kernel
`7.1.4-g359318de534f`. Expected host-key verification was never bypassed.

The handover question is answered: persistent state and identity startup pass.
The identity record binds this boot ID and the expected fingerprint; no failed
systemd units were reported. P24 is RO/norecovery. The existing bounded P23
service-state image is mounted on /persist; exactly sda and sda23 are writable
across 117 checked UFS nodes. Startup reports supported journal recovery for
sda23 and loop0; this is not an assertion of zero storage writes. Wi-Fi is
intentionally inactive. Tailscale acquired an address, but remote reachability
has not been qualified. Full raw snapshots remain private.

Authenticated snapshots: battery 93%/30.1°C/+39 mA/4784000 µAh initially;
93%/30.4°C/+125 mA/4796000 µAh at uptime 161 s; and
94%/30.3°C/+129 mA/4838000 µAh at uptime 686 s. Health is Good and USB input
reports online, about 4.98 V with a 500 mA limit. These corroborate net charging
but lack H03's predeclared limit/noise interpretation and complete 10 s cadence;
H03 remains BLOCKED, not retroactively passed. Duplicate UCSI supply telemetry
must not be summed with the battmgr input. Final capture/cleanup and subsequent
service-test observations are recorded below.

Keep the existing Arch image. V4 changes target init only; successful recovery
with the same root/kernel directly supports a project composition defect,
not a demonstrated need for a Debian migration. No distro rebuild is started.

## Completed capture, observer timeout and SSH restart failure

The same v4 boot remained reachable after the 900 s deadline (uptime 971 s).
Capture completed in **1380.790 s**, exit 0, without capture failure. Its
qualification status is intentionally NOT RUN: passive evidence cannot prove
authenticated acceptance. Route, firewall, profile and address cleanup all
PASS. Normal USB pinned SSH subsequently passed at uptime 1517 s. Battery
96%, Good, 30.2°C, +128 mA, 4908000 µAh. Tailscale reported Running/Online with
no health warnings, but this host lacks a Tailscale client/route; an attempted
overlay-address SSH check timed out. Remote mesh SSH is not qualified.

New R4 observation defect: the installed observer runs with argument 900 and
RuntimeMaxSec=900. The exact target unit/journal shows start 22.007275 s, end
922.010684 s, Result=timeout, SIGTERM. Core services continued. A virtual-clock
test of the actual unit generator and loop reproduces the deadline collision
before the fix. The observer now ends after all four startup services report
present/active/success; otherwise its loop budget leaves a 30 s margin under
the unchanged hard ceiling. This ends diagnostics only, never acceptance or
rollback. Partial/error observations cannot complete the startup round.

Eight focused tests PASS (**0.724 s**), exact sealed BusyBox tests PASS
(**19.902 s**), assembled-archive composition PASS (**0.086 s**). The first
full CI stopped after 39.618 s on an obsolete composition assertion pinning
the old argument; it now checks the assembled invocation against the actual
generator, with behavior tested separately. The initial long virtual-clock
fixture timed out under emulation; jumping directly to the final in-flight
operation preserves deadline coverage without hundreds of repeated forks.
Final full local CI PASS **484.020 s**. Frozen production/test diff SHA-256
over `385ed8c9`: `df29d5ca87db602572a169b2f3c0611a9f1c7b068c101ed2728c135aabfbddcf`.
No running target byte was changed; no successor was built or issued.

**S03 FAIL, not a crash:** one SSH service restart at uptime 1668 s lost normal
10.77.0.2 access. No repeat was sent. Host USB remained enumerated; ARP failed
for that address. With a scoped temporary host diagnostic route, pinned SSH to
169.254.77.2 succeeded at uptime 1946 s with the same boot ID and new SSH PID
(4976 → 567480). Live systemd logs prove Requires propagation stopped P2,
persistent state, identity and Tailscale; its cleanup removed the normal USB
address. The restarted one-shot P2 exited 1, preventing state/Tailscale restart.
The diagnostic route/address were cleaned up. This is a concrete service-graph
failure, not proof of UFS/USB/kernel instability. Charging remains active.
Next correction must reproduce that actual systemd transaction and preserve
the initial P2 storage gate while preventing routine SSH restart from tearing
down state/networking. C02/S03 and the final release remain incomplete.

## Corrected core service lifetimes; normal USB access restored

Starting source `8f10bacc79c575a4a97fa75712bef9bc62c59d57` passed all four GitHub
jobs (33972012512). Extended the existing `check-ssh-rollback` integration with
the actual generated P2/state/identity/Tailscale dependency graph and its real
loopback sshd. Executables for storage/P2/Tailscale are disposable fixtures;
there is no physical storage or radio activation. A denied initial P2 blocks
state. Its first successful pass is deliberately boot-only, matching the
observed non-repeatable contract. This is not full target-systemd qualification.

Before the fix the test fails after the real SSH restart: P2 is no longer active
(6.656 s), reproducing the live cascade. After replacing only the SSH lifetime
edges with Wants plus existing After ordering, it passes in **11.226 s**.
State still Requires P2; identity and Tailscale still Require state. The actual
P2 attestor and SSH identity helper still verify the initial listener. No P2
record is removed, fabricated or accepted under relaxed rules. Healthy/stale
watchdog cases retain their distinct no-reset/reset outcomes.

Normal phone SSH was recovered without a boot: exact topology, pinned key,
boot ID, power gates and all 117 block nodes RO were verified, then only the
missing 10.77.0.2/30 address was restored at uptime 2916 s. Temporary host
diagnostic route/address cleanup passed. Pinned normal-address SSH passed at
uptime 3019 s: 98%, Good, 30.2°C, +141 mA, 5032000 µAh. P2's retained failure
is `ext4 journal recovery appeared`, caused by evaluating the boot-only gate
after the previously authorized state mount. State and Tailscale remain
inactive; the current boot was not forced past that failure. No storage write,
service retry, replacement identity or flash was used to restore the address.

Frozen source/test diff over `8f10bacc`:
`b167b8a7365775aa678c1acb342a561a6fce41ed3ed00b473d3a72e9340b972e`.
Unsigned initramfs assembly **3.935 s**, 23834617 bytes, SHA-256
`6d948432e07f3170515ceaac72934df829274451ddfa3a2b65b94e6797a67fa7`.
Complete archive comparison changes only init and startup observer relative
to v4. All 19 modules, other members/metadata, both kernels and root are reused.
Archive/source parameters and module metadata/order pass. Real-systemd restart
test on this archive's BusyBox passes (**11.202 s**); eight sealed observation
tests pass (**19.609 s**); retained-Arch runtime/command/unit preparation passes
(**33.115 s**) with private RO loop mount cleanup. The latter uses fixture
timing and activates no services; exact signed plan and target execution remain
separate. No full A01, C02 or S03 release PASS is inferred from these components.

Full CI first stopped after 97.473 s at an obsolete Requires-string assertion.
Focused updated state lifecycle tests pass (5.322 s), storage-resolution tests
pass (24 cases, 1.803 s), and root-initramfs tests pass. Final full local CI
**PASS 488.955 s** on the frozen tree. No new signing, admission, phone reboot,
kernel build or destructive operation occurred. The next physical question is
whether this corrected graph preserves state/network access across SSH restart
on a fresh coherent boot, after exact-head publication and connected admission.

## V5 packaging and canonical registration

Source `adfe80d7b1d9dd301b12f46cb302b52508679633` passed all four GitHub jobs
(33973668522). V5 packages the corrected core dependency graph and bounded
observer with unchanged kernels/DTB/modules/Arch lower. Twin packaging passed
in **12.404 s** and sealed signature/composition verification in **6.111 s**.
Wrapper SHA-256: `d77d64f96791dda2e210165770855fe6ce59e05be912a1cf22e58f28d601f0b0`.
Manifest SHA-256: `11fbc8cfd0b8fc65ef72f3392afbee9a9390f5dab9685acaf35aebe0fa2fccd6`.
The registry row derives artifact identities from the retained verifier result;
it creates no claim or boot authority. Focused claim (18), receiver (16) and
admission (31) tests pass in **4.295 s**. Reuse the source checkpoint's full
local CI (488.955 s); this child changes registry data and documentation only.

Fresh exact fastboot checks identify the expected serial/product/full topology,
slot B, 8647 mV and SOC=yes. No current temperature or charging trend is inferred.
V4 remains consumed; V5 remains unconsumed pending publication and connected
admission. The physical question is whether SSH restart preserves P2, state,
identity and normal USB on the corrected graph. Offline tests cannot qualify
the actual target systemd transaction, charging window or final server release.

## V5 physical restart, watchdog and completed capture

Publication `3f4f2e5f4898a061a24eea8df22b6851e2e494da` passed all four GitHub
jobs (33985592033). Connected admission and the sole RAM boot passed; V5 is
permanently consumed. Fastboot took **12.820 s**, pinned SSH **59.298 s**.
Boot `c2149c4a-6ce4-47c6-9c3b-e3ca55ea43fb`, unchanged kernel
`7.1.4-g359318de534f`. No flash, slot change or new storage operation.

The actual target SSH restart passed in **2.547 s**: PID 4560 → 25053;
P2/state/identity/Tailscale invocation IDs and readiness hashes stayed unchanged,
as did boot identity and 10.77.0.2. Deployed P2/state/identity unit hashes match
the final signed archive. The optional observer exited successfully. At uptime
902.576 s, the watchdog acknowledged current-boot P2 and SSH identity readiness;
pinned SSH subsequently confirmed the same boot. These answer the V5 question,
but are component evidence, not complete C02/S03 or release qualification.

The **600.615 s** read-only power/core collection completed 61 samples at 10 s
cadence: 100% Full/Good, 30.0°C, 8.632–8.635 V, battery current 0 µA and charge
counter 5116000 µAh throughout. USB stayed online, with 500 mA input limit,
4.985–5.035 V and 250–500 mA reported input current. Do not sum duplicate UCSI
supply readings. H03 remains BLOCKED pending predeclared qualified full-regulation
and noise interpretation; the data is not retroactively accepted as H03 or
net-positive battery charging. No charging control was written.

Capture completed in **1380.711 s**, with no capture error; owned route, firewall,
profile and address cleanup all PASS. Passive-capture qualification is NOT RUN
by design. After cleanup, authenticated normal USB SSH confirmed the same boot
at uptime 1594 s, five core services active, 100% Full/Good and 30.0°C. Wi-Fi
remains intentionally inactive; remote Tailscale access is unqualified.

New R2/R3 optional-service finding: the rescue's empty volatile pacman keyring
causes `archlinux-keyring-wkd-sync` line 64 `fpr_email[1]: unbound variable`;
three failed refreshes led to start-limit-hit. This does not invalidate pinned
SSH or prove a kernel fault, but the failure remains visible. The existing
persistent-keyring helper is not wired into this composition; its intended
rescue/update lifecycle needs a regression before another candidate.

## A02 persistent composer optimization bypass

Starting HEAD `3f4f2e5f4898a061a24eea8df22b6851e2e494da`, originally clean.
The existing A02 test command now exercises the actual persistent composer CLI,
not just its base composer. Five new regression methods fail in **1.965 s**
with 13 failing subcases before the fix: -O accepted wrong base/helper hashes,
an incompatible marker, reused successor trial/bundle identity and a changed
retained helper. A preexisting receipt could leave a new archive before refusal;
a dangling receipt symlink reproduced that even without optimization.

Replaced removable assertions with explicit ValueError checks and rejected
existing output/receipt paths, including dangling links, before composition.
Exclusive output creation remains. Valid initial/successor bytes and receipts
(apart from measured duration) match in normal and optimized Python. No valid
payload transformation, signature policy, execution claim or source pin changed.
This is host artifact-validation code, not a kernel or live-phone defect.

Five focused methods PASS **2.027 s**; the complete Wi-Fi boot test PASS
**33 tests, 6.821 s**. These already run through A02 and the broader repository
tier; no new framework or separate test list. Full frozen validation follows.
Current-state reduced from 326 lines to a compact current snapshot; active
context is a pointer. Historical evidence remains here and in Git, with no
build/private evidence deletion. No successor is needed for this offline fix.

Normal/optimized complete composer tests pass (33 tests, **6.821/7.138 s**).
Independent bounded read-only patch review found no concrete issue. Active tier
passes; its aggregate wall time was not captured, so no timing is invented.
The current quick acceptance matrix reports A02/B01/G01/G02 PASS
(7.129/3.837/7.660/0.465 s); 21 other rows NOT RUN, release qualified=false.
This matrix does not import incompatible live or historical passes.

Full CI exposed a fixture-mode issue under the private-log 077 umask:
the fake P2 unit was created 0600 while deployed composition requires 0644.
A new umask regression fails before explicit fixture chmod (0.062 s); all
six optional-display tests pass afterward under 077 (**1.332 s**). No production
permission check changed. The first CI stopped in 26.049 s. A second stopped
in 25.741 s on a legacy trial-state fixture's 0755-directory assumption;
that existing test fails under 077 and passes under the usual 022 (0.198/0.190 s).
The final invocation creates its log privately, then restores the normal 022
test environment. That fixture limitation is retained, not represented as fixed.
An earlier missing /usr/bin/time invocation ran no tests; Bash timing was used.

Final **full local CI PASS 490.925 s** (prior source 488.955 s). Frozen diff hash
over starting `3f4f2e5f4898a061a24eea8df22b6851e2e494da`:
`528c3e9b18efd8ed59cc59658cc46d2b848e25b3092ae3ad2ad099e10cebf5a9`.
Only result documentation follows that passing run. No full suite was repeated
after a successful unchanged-source result. No kernel/wrapper build occurred.

While CI ran, one additional RAM-only USB component check transferred 256 MiB
each way over pinned SSH under a predeclared 180 s/direction limit. Upload
**7.429 s**, download **6.659 s**; exact lengths and SHA-256 matched. Before,
between and after: same V5 boot, five core services active, Full/Good, 30.0°C;
RX/TX errors stayed zero, RX drops zero, TX drops retained the prior value one.
No scratch file or storage write was used. This is not Wi-Fi/full S02 evidence.

Captured deployed WKD script SHA-256
`964fdb8aa2e6a0e4405ebe2ef6f979a0a4142ed8f9ba2d605c20a1a296c16216`
reproduces the exact line-64 empty-list error in a disposable unshared namespace
in 0.014 s. GPG/pacman-conf endpoints are fixtures, with no network, real keys
or refresh operation. The genuine public script and replay remain in private
incident evidence; the running failure is neither cleared nor masked.

## E01 safe radio refusal checkpoint

Continued the dirty worktree at `c1c1d6315fff7946cbfa902e2add4fe2421f49e5`.
Primary question: can pre-activation radio refusal preserve a qualified headless
server without reducing radio power safety or accepting partial activation?
Layer: userspace/initramfs composition, not kernel/DT/recovery. No new build,
signature, admission, boot or phone-storage operation was performed.

The old fatal radio voltage check prevented core state startup through systemd
Requires. The preserved implementation adds a distinct one-use, current-boot
refusal record and exit 77 only after integrity/storage/power checks and proof
of the armed rollback timer. Radio activation still requires at least 8.4 V;
the conservative core-only interval is 7.5–8.8 V with USB online. WPA, DHCP and
Wi-Fi trial commit skip only a valid refusal. Core P2 + identity acknowledgment
may suppress the radio deadline, without creating Wi-Fi healthy evidence or
committing a trial. Malformed records, partial activation and unsafe power fail.

Initial producer regressions failed four cases (2.210 s). Focused source
tests now pass four methods (7.056 s), and optimized composer tests pass 34
methods (7.120 s). Mixed old/new radio runtime/unit composition is rejected in
base, initial/successor persistent and failure-diagnostic composers; four
normal/optimized initial/successor subcases failed before that closure check.
Historical archives remain preserved, but cannot be silently repackaged with
incompatible new consumers.

Real user-systemd testing executes shipped preflight/condition scripts with
fake hardware and core executables. Safe refusal permits core state and SSH;
unsafe temperature and activation-entered failure prevent state startup. It
does not simulate successful hardware activation. All three cases pass in
3.679 s. The first harness incorrectly assumed skipped units retained
Result=exec-condition (FAIL 1.596 s); systemd may unload inactive units. It now
records actual condition exit 1 and independently proves optional ExecStart
was not called, instead of treating inactivity alone as success. Owned units
are stopped and removed; no system services or persistent units are changed.

Sealed BusyBox replay uses the retained V5 archive's ARM applets inside a
network/device-isolated root, with fake sysfs/proc and shipped source scripts.
Initial four methods passed in 59.000 s. This is applet compatibility evidence,
not a claim that the old V5 archive contains the new scripts. Added thermal-rise
regression then failed in 4.602 s: the new refusal rollback path rechecked battery
temperature but not other zones. It now rejects a supported zone at 60°C or
higher; absent/unsupported optional telemetry remains observational.

E01 is registered in the existing acceptance manifest with exact archive input
and user-systemd prerequisites; the fast source suite joins the single shared
probe list. Missing prerequisite exit 77 now maps to BLOCKED, never PASS
(fail-first regression 0.153 s; complete dispatcher 13 tests PASS 0.368 s).
Active tier PASS 15.869 s. Bounded independent read-only review found no
actionable issue. Frozen full CI and final sealed replay results follow.

Read-only device observation at uptime 4091 s confirms unchanged V5 boot,
five core services active, 100% Full/Good, 30.0°C, 8.632 V, 0 µA; the optional
keyring refresh failure remains visible. This is not a new charging or release
qualification. The next implementation after this checkpoint is intended
package-keyring/update composition, not another kernel rebuild.

Frozen full local CI PASS **485.345 s**, versus prior 490.925 s; this small
variation is not a claimed performance improvement. Source digest before/after
the run remained
`acd3a23b3fa22ee84a56ab5a96e3dfa2feda2644fd03ca430b943c00d885a1e1`.
Final sealed ARM replay including thermal rise PASS **64.087 s**. Only result
documentation changes follow the frozen run. Remote exact-head/merge checks are
separate; no candidate was built or granted execution authority.

Subsequent read-only keyring diagnosis found active synchronized timesyncd and
the packaged ARM trust files at root-owned 0644, but no persistent GPG directory
and no deployed bootstrap helper. GPGDir remains in the volatile root overlay.
This supports wiring bootstrap before refresh; it does not authorize importing
unverified keys, disabling package signature checks or hiding refresh failures.

## Package-keyring startup composition

Starting published E01 HEAD `2fe2a299fd3c6dc731bfbe988b60920ddbb81f4f`;
all four remote jobs passed run 33990202242. Primary question: does the actual
bootstrap/refresh composition initialize package trust without blocking core
access on failure? Layer: userspace/initramfs; kernel, DTB and modules reused.

Refreshed init now stages the existing package-keyring helper and service into
/run, and WKD refresh Requires/After successful bootstrap. The normal and Wi-Fi
builders include both inputs; the paired archive checker rejects missing or
stale copies. This fixes the observed unwired helper, not the upstream script
by masking it. Package signature policy and GPG initialization logic are unchanged.

Fail-first packaging: three missing-input/init-call subcases (0.012 s). Paired
archive checking: four missing/stale member failures (0.070 s). After correction,
packaging/staging two methods PASS 0.043 s; checker eight methods PASS 0.077 s;
optimized composer36 methods PASS 7.220 s. The staging fixtures exercise actual
copy/metadata/collision handling without GPG, service startup or phone contact.

A new bounded user-systemd component test, exposed as
`rog5-dev check-package-keyring --output PRIVATE_NEW_DIRECTORY`, extracts the
actual WKD dependency and uses the production bootstrap unit with disposable
GPG/storage/core endpoints. Success, failure and a one-second fixture timeout
all pass in **2.550 s**. Refresh never runs before successful bootstrap;
refresh restart does not repeat initialization, and core invocation/PID/state
identity remains unchanged. All owned units/links are cleaned up. The production
120-second startup timeout is preserved. Dispatcher discovery failed before the
entry existed (0.006 s); all 14 dispatcher tests pass afterward (0.478 s).

An unsigned offline archive fixture built in **1.470 s**, retaining the exact
kernel/DTB/modules and changing init plus package-trust inputs only. It carries
no signing/admission/boot authority. Sealed BusyBox staging against the exact
retained read-only/norecovery Arch image passed executable/unit compatibility
and module metadata closure in **33.329 s**. This is composition evidence,
not a full module BTF/symbol or physical-release qualification.

Actual retained ARM pacman-key/GPG tests in a disposable tmpfs home passed
bootstrap, signer trust and master-key reuse in **11.775 s**. The installed WKD
script exits successfully by skipping local/ARM keys; network was isolated, so
online refresh was not tested. The first GPG fixture did not execute: a new user
namespace could not traverse the private host path. It was corrected to retain
the setup identity while isolating mount/PID/network/IPC/UTS/cgroup state and
dropping payload capabilities. The passed sealed-root check was not repeated.
The GPG fixture's tmpfs home had 0755 mode and emitted a permission warning;
this test exercises initialization functions, not directory preparation. The
production start helper creates its private home with 0700. No generated key
material survives namespace exit; the retained image was verified and read-only.

Pinned same-boot on-phone **read-only preflight PASS** validates the real
service-state mount, directories and packaged trust inputs. No initialization,
mount change, refresh restart, key write, signing or phone boot occurred.
The old visible service failure remains. Active tier PASS **15.022 s**; existing
initramfs and persistent-state lifecycle focused suites pass. Full frozen CI
and publication are separate and follow this checkpoint.

Frozen full local CI completed with `PASS repository Linux ci tier`. Its process
handle and PIDs are now absent; the retained terminal log proves completion.
Source digest still exactly matches
`6b2c780a3ee853af08ed9c70afa03f78fe116366666bee5317ee4be9b8625efd`
at parent `2fe2a299fd3c6dc731bfbe988b60920ddbb81f4f`. Only these result documents
were edited afterward. The log's birth-to-final-write interval is **486.251 s**;
this is an approximate filesystem-timestamp duration, not recovered monotonic
shell timing. Prior E01 full CI was 485.345 s; no speedup is claimed. Do not
repeat this passed suite on unchanged implementation.

Read-only pinned SSH continuity at uptime 6893 s confirmed the same V5 boot,
active core services, battery 100% Full/Good at 30°C, 8.630 V and 0 µA, USB online.
The sole failed unit remains the undeployed keyring-refresh defect. The first
ad-hoc read assumed `/sys/class/power_supply/battery`; that optional path was
absent. Inventory instead found `qcom-battmgr-bat`, without changing the phone.
This did not affect a candidate or production observer and is not a hardware
failure. No new boot, signing, storage mutation or combined-soak PASS is implied.

Keyring publication: `3dc02580aa276cbd223ca511bed49655eb143bae`, normal push to
the existing branch. Exact-head/merge run 33991878159 is separate from local CI.

## WPA/DHCP restart hypothesis (disproved offline)

The missing explicit `PartOf` edge raised the possibility that restarting WPA
would leave DHCP stopped. `rog5-dev check-wifi-restart` exercises the actual
shipped dependency edges under user systemd, with uniquely named units and
fixture radio/WPA/DHCP/core executables. **PASS 1.380 s**: WPA restart gives both
daemons new invocation IDs; DHCP restart leaves WPA unchanged. Radio executes
exactly once, core invocation/PID identities stay unchanged, and state teardown
does not occur. All owned unit links were removed and unload verified.
The production graph was not changed: the hypothesis did not reproduce.

This test replaces hardware/network daemons and skips their already-qualified
preparation/activation conditions. It does not prove a real lease, association,
SSH reconnection, target systemd version or complete F02 PASS. The new command
exists to preserve the discriminating evidence and prevent speculative graph
changes, not to replace device validation.

Independent bounded read-only F01 mapping found directory/mocked journal tests,
not an actual replay/remount qualification. The existing historical stale `#b`
OverlayFS work entry remains a relevant retained failure fixture. Next storage
test must use disposable ext4 images and real OverlayFS; no phone crash or
live-storage corruption is needed or authorized by that offline check.

The WPA restart command-discovery tests pass (15 tests, 0.458 s); active tier
passes in 15.143 s. No production WPA/DHCP unit changed.

## Merge-CI fixture deadline regression

Run 33991878159: head-exact PASS (6m19s), candidate-publication PASS (1m4s),
merge-compat FAIL (6m1s), QEMU skipped. The failure is in
`test_concurrent_helper_is_excluded_without_second_fetch`: exit 54,
`cannot normalize staged bundle`. No release/candidate admission follows a
partially passing run.

The fixture paused its first helper while exercising a concurrent rejected
helper, but left the successful fetch on the general 700 ms test budget.
Reusing the existing bounded fsync-delay shim reproduced exactly exit 54 with
a single 750 ms publication delay (fail-first 1.476 s). The successful first
fetch now receives 3000 ms, while the contender remains at 250 ms and dedicated
timeout tests remain unchanged. No production C, timing contract, signature,
lock, cleanup or one-use behavior changed. Focused slow-publication/concurrency/
timeout tests: three PASS in 2.628 s. This supports a fixture-budget diagnosis;
the original hosted runner did not record the precise slow syscall duration.

## Disposable OverlayFS workdir evidence (partial, not F01 PASS)

No phone was contacted by this experiment. A new 64 MiB ext4 image, private
mount namespace and immutable lower recreate the historical `work/work/#b`
character-device whiteout. The current production pre-mount function rejects
it; host Linux `6.16.12-valve24.5-1-neptune-616-gb2f7cfe85e45` successfully
mounts the overlay and removes that entry. This is evidence against treating
every stale work entry as corruption, not authority to relax arbitrary paths.

The first fixture could not mount: the host's case-insensitive-capable lower
filesystem was unsupported. The revised fixture uses read-only tmpfs lower;
mount and whiteout cleanup succeed, but the later source guard rejects the
host-created `work/index` directory. Both runs are retained with nonzero exit
status. Read-only debugfs confirms empty `work/work` mode 0000/link count 2
and the separate index directory; loop detachment is verified. Do not claim
target behavior, real journal replay, full readback/fsck completion or F01 PASS.
The next experiment must bind the target's actual OverlayFS feature defaults
and exact release shell instead of silently accepting host-kernel differences.

Read-only pinned SSH at uptime 7755 s confirmed the same V5 boot, target
OverlayFS parameters `index=N`, `redirect_dir=N`, `metacopy=N`, and systemd
260.2-2-arch. Battery remains Full, 30°C, 8.630 V, USB online. A third disposable
experiment explicitly matched those feature settings: stale whiteout rejected
by the source guard, successful host-kernel mount/cleanup, post-unmount guard
PASS, unchanged lower/source hashes, and read-only e2fsck PASS after loop
detachment. Final disposable image SHA-256:
`51883484efce07ba94579cee494308b0b76bb9909cf73829e1e8a86a09ea393e`.
Exit 0, with all owned mounts/loops detached and all three fixtures retained.
This is a narrowly successful host reproduction; it still does not prove real
journal replay or behavior of the phone's 7.1.4 kernel. The next source fix must
review that kernel's cleanup semantics and reject unrelated/aliased work entries.

Final test-only checkpoint: fetch suite 35 PASS, **9.570 s** total (9.444 s test
body); active tier **15.041 s**. The earlier full local keyring CI remains valid
for its unchanged implementation; it was not rerun for the new fixture-only
deadline and service-graph tests. Exact-head/merge CI on publication remains
required and must not be replaced by the earlier partially passing run.

## Exact-kernel interrupted OverlayFS recovery

Starting HEAD `059afe4f3bad7ed435040edf66d057c2c17c7927`; all four GitHub jobs
passed run 33992627778. Primary question: does the accepted kernel recover a
legitimate interrupted update while the initramfs preserves scoped validation?
Layer: initramfs/storage predicate, R3 exact-runtime mismatch. No phone contact,
candidate issuance, signing, kernel rebuild or live-storage mutation is needed.

Audited retained clean source `359318de534f196c1281de7195fbf5868c6f7333`,
OverlayFS tree `4e95f67c41c99df570a1bf355c7af3bd10b9dd38`: `ovl_tempname`
uses `#%x`; `ovl_whiteout` caches and hardlinks character-0:0 whiteouts;
`ovl_workdir_create` invokes cleanup on an existing nonpersistent workdir.
The exact V11 kernel SHA-256 is
`bdceaa516cafbe276179344c8d55d78f20319e7cb3f3375498536fca37879806`.
Its actual QEMU behavior, not merely source similarity or host Linux, proves
the tested recovery below.

Fail-first **40.255 s**: the guest deletes a lower file through OverlayFS,
syncs the filesystem and performs a VM-only SysRq reset. `dumpe2fs` confirms
`needs_recovery`; next boot records ext4 `recovery complete`. The real retained
`work/work/#3` is mode 000, character 0:0, with **two links**. Source guard
rejects it; the kernel successfully cleans it. An additional missing runtime
sysinit target directory was a harness omission, independently corrected.
The manually created mode-600 host fixture was not used to broaden admission.

Production change permits only root-owned mode-000 character-0:0 entries with
canonical 1–8 digit lowercase-hex names. All existing outer-directory checks
remain. No shell deletion is introduced; the kernel removes its scratch link.
Symlink, dangling link, regular file, subdirectory, hidden entry, noncanonical
name, wrong device, wrong mode and wrong owner are rejected without deletion.
Exact storage UUID/geometry/write windows, signatures and fallback are unchanged.

Unsigned fixture SHA-256
`f863ae87ff7b22b858690be58309344e0514bd6d1261dc5a5229ee50fe65e710`
was generated in **1.441 s**, changing only init. After-fix QEMU **PASS 44.040 s**:
prepare 2.780 s, recover 8.064 s, corrupt-superblock refusal 2.409 s. Kernel
whiteout cleanup, legitimate etc-only/independent markers and malformed-marker
refusal pass. Inputs include exact retained Arch cache, not a synthetic copy;
the rest of the root is a disposable fixture, not a full Arch/systemd boot.
No input image is mounted writable or copied wholesale.

The integrated runner additionally verifies var-only interruption, clean
post-unmount guard, read-only fsck, final input/source identities and reports
missing prerequisites as BLOCKED. It is exposed through `rog5-dev` and F01.
Two integration regressions failed before adding the command and `{rootfs}`
binding (0.007 s); all 17 acceptance tests pass afterward in **0.534 s**.
Final integrated execution and frozen full CI are still pending; no coherent
release qualification is claimed from earlier unsigned component results.

Final integrated QEMU **PASS 76.421 s**, including a second hash of all exact
inputs. Prepare 2.704 s, recover 10.962 s, corrupt refusal 2.217 s; var-only
interruption, post-unmount guard and read-only e2fsck pass. No source/input
changed while this test ran. Extra missing-runtime and F01 binding tests bring
the focused acceptance suite to 19 PASS in 0.534 s. The earlier two integration
failures did not consume a phone cycle. Frozen full CI/publication follow.

Read-only continuity at uptime 9209 s: same consumed V5 boot and authenticated
SSH identity, core services active, Full/Good 100%, 30°C, 8.630 V, 0 µA, USB
online. The sole failed service is the known undeployed keyring-refresh fix.
Wi-Fi remains inactive. This does not substitute for the release soak or H03.

Frozen source index tree `e2b456eaadee747ee1623a44f81154f2e993e023` passed
the active tier in **15.528 s** and full local CI in **485.305 s**. No unstaged
source changes existed at completion; only result documents changed afterward.
Compared with the prior approximately 486 s full run, no material CI speedup
is claimed. Historical optional retained-artifact skips are not device or
release qualification. No kernel build was performed; exact-head/merge remote
CI follows normal publication of this checkpoint.

Read-only next-composition inventory confirms the Wi-Fi-soak record's retained
Image `2649a272eb2a6814db6302630a585fcab3d4422802e774ec55a55cc489f629e1`,
DTB `8b1250cefd69870662edb9131190f005f492b4c93c192ee7e2b89b9a121f22da`,
and V3 archive `987d28c31b90516b88437321bc7b795e721f55c58cdc0b4b9770a00e64b4956c`.
All 22 direct and 37 nested radio/dependency modules have one matching vermagic,
`7.1.4-g1eea8970e87f`. The nested package includes ath11k/PCI/AHB, mac80211,
cfg80211 and WCN power sequencing. This is not compatibility with current rescue
g359, symbol/BTF verification or permission to retry the consumed V3 target.
Use the retained coherent set with refreshed userspace and fresh reviewed
execution identity for future tests; no kernel recompilation is justified by
this inventory alone.

## 2026-09-06: coherent Wi-Fi/server archive preparation

Starting HEAD `0150d853fcb4930ac6057f6016ebc0af0c8d7b99`; all four GitHub jobs
passed run 33994287705. Primary question: can the retained Wi-Fi hardware set
be reused with current initramfs/services for the headless server? Layer:
userspace/archive composition, not kernel or phone storage.

R2 fail-first: the real standalone builder refreshed init, which requires
`prepare_package_keyring`, but omitted its helper/unit when refreshing an old
base. Both absent and stale input cases fail (0.207 s). The builder now installs
the two exact repository inputs and excludes only those named updates from its
unchanged-file comparison. It generates no keys. Final standalone composition
tests pass (two methods, 0.268 s). A suspected `./` archive-name mismatch did
**not** reproduce; the real cpio output already uses the consumer's namespace.
No namespace rewrite was introduced.

Existing identity-only successor composition deliberately rejects old radio
consumers and an old trial helper. Added explicit `--successor --refresh-userspace`
to recompose repository radio scripts/units and the canonical helper together.
Default identity-only output/behavior stays unchanged. Kernel/init refresh is
still the existing standalone builder's responsibility; neither tool grants
execution authority. The authenticated base hash binds the old helper; the
new helper argument must match the canonical repository hash. Retained-helper
mode/owner/link metadata is checked before replacing it. Firmware/module bytes
and unrelated archive members remain unchanged.

The new CLI case first failed as an unsupported option under both normal and
optimized Python (0.123 s; an additional test reporting IndexError was corrected).
Final persistent-composer group: eight PASS in 2.732 s, including identity reuse,
wrong base/helper refusal, unchanged hardware and normal/-O identical output.
The full Wi-Fi test file passed 38 tests in 7.770 s before the last helper-refresh
extension; the final eight-method group covers that extension. Active tier
passed before that final extension; no final full-CI result is claimed yet.

The helper change reuses the already-reviewed artifact from `545f2118`:
`ff6ede42d089a6a651db320a007947091029aca504500227e0c51bed6792f3ca`
→ `c1aab57b43d32d14714af96f3ee1feb936c363c8a86b4ac0b312ea5d08f69d0d`.
The persisted record format is unchanged. Its `decide` path durably rearms a
healthy primary to pending before selecting it, so a later failed boot can
select fallback; the healthy-record transition remains compatible. Installed
recovery still needs its separately verified update. No helper was executed on
the phone and no persistent state was changed by this packaging step.

Repository builders produced unsigned offline-only server twins in **18.519 s**:
`e57bf7d447dac8489a5aaf99952928aa8cef627b03da7a9b7464913cacadfc91`.
The intermediate standalone archive is
`0ee5ed3ba0151e7d734b941ee3989104c0e85245b682feac69ab327059709921`.
They retain persistent-overlay mode=1 and 33 identified hardware payload members
unchanged, with no optional display marker. The fixture identity is not in the
admission registry; no candidate, signature or one-use claim was issued.

Exact matching Wi-Fi kernel
`2649a272eb2a6814db6302630a585fcab3d4422802e774ec55a55cc489f629e1`
and that final archive passed all nine existing QEMU watchdog/root-handover
cases: valid/absent/stale acknowledgment, P2-only, stale identity, unusable
helper, post-exec hang, failed-init panic and FD-open failure. This reuses real
archive watchdog functions with fixture ACK/init paths, not full phone startup.
The existing disposable OverlayFS suite also passed in **85.349 s** including
exact input rehashing: prepare 2.546 s, recovery 10.727 s, corruption refusal
2.222 s. The two QEMU suites ran concurrently; no new kernel was compiled.

Current-state was compacted from about 1469 to 780 words; historical evidence,
accepted builds and all private artifacts remain preserved. Current builder
changes remain a dirty, locally tested checkpoint. Next: exercise the server
archive against retained Arch userspace, then freeze/publish and admit only a
fresh reviewed physical cycle. The existing rescue-only checker explicitly
rejects radio-bearing persistent-overlay archives; its earlier PASS must not
be relabeled as server composition proof. Full release acceptance remains open.

### Actual Arch runtime check and dormant-display-helper regression

Extended the existing checker with explicit `--profile server-runtime`, preserving
the default rescue-only refusal. It requires current paired init/startup/radio
userspace and persistent-overlay mode. It runs exact archive functions and radio
unit installation in an isolated retained-Arch root with disposable upper/run.
Core power/UFS metadata/load-order checks stay strict; the three probe modules
and nested radio package are hash-recorded as **NOT RUN** for radio load/closure.
Unknown extra modules still fail the core inventory check. This is a component
test, not A01 release qualification or radio activation.

The first run failed because the fixture omitted the prior overlay stage's
userdata-path record; its focused regression failed in 0.003 s. Supplied the
explicit nonexistent-device fixture with exact expected mode. No block node or
real storage-stage claim is fabricated. A subsequent private sealed-shell trace
located the remaining failure in `runtime install`, after package-keyring setup.

R2 production defect: both initial composition and userspace refresh include
the common `load-pwrkey` script. `install_status_screen` counted that dormant
helper as one of seven display opt-in members, then rejected the headless archive
as incomplete before root handover. A behavior regression failed in 0.010 s with
only that helper present. Exclude the helper from opt-in detection; the six
actual display payload members still opt in together, and helper metadata is
still required before activation. Absent/dormant-helper cases now pass without
activation or unit writes; partial display still fails. No kernel change.

Focused runtime group: 22 PASS in 1.277 s. Checker: 12 PASS in 0.109 s; earlier
normal/optimized checks both pass. Full composer file before the runtime fix:
38 PASS in 8.717 s. Active tier after the fix: **18.178 s PASS**.

Reused the verified intermediate standalone archive; refreshed only target
userspace into new, identical offline twins in **8.095 s**. Only `runtime` and
`boot-files.sha256` differ from the earlier fixture. Corrected archive:
`6934f7323a1aec6711045b11a7ff7e7d370636e357aa01fb64da545d16552fda`.
Kernel, DTB, all modules/firmware, init, watchdog and trial helper are unchanged.
All prior archives and failed-run logs remain retained. No execution authority.

Actual corrected-archive/retained-Arch runtime check: **PASS 33.808 s**, including
sealed BusyBox preparation, systemd 260.2-2-arch execution, volatile Ed25519 key
generation, real sshd key-only effective policy and core/radio unit verification.
Input hashes and source were reverified; private read-only no-recovery loop and
disposable upper cleanup passed. Prior-stage input and radio directory-copy are
explicit fixtures; no physical storage, radio, root handover or final timeout
qualification is claimed. No phone was contacted during this composition work.
Source remained at `0150d853fcb4930ac6057f6016ebc0af0c8d7b99`, dirty digest
`1edc26352a012746e374c0e84894a3d709eb303efbc1a88ddccc932b9b912627`.
Next: one frozen full CI/publication checkpoint and remaining final-release tests.

Frozen checkpoint full local CI **PASS 485.604 s**, versus prior 485.305 s;
no meaningful speed change is claimed. Only current/result documents changed
afterward. No kernel rebuild or new device execution was performed.

Read-only comparison with the hash-verified earlier Wi-Fi-soak archive found all
33 hardware members identical in content, type/mode, owner and link count.
Only CPIO inode numbers differ. All 51 nested module-package files match the
retained build record for the exact g1ee Image. This supports reusing hardware
bytes; it is not a new module-load test or transfer of the old soak PASS into
this release.

Independent read-only phone continuity while CI ran: exact anchored USB route
and pinned SSH identity, same consumed V5 boot at uptime 12371.55 s, Full/Good
100%, 29.9°C, 8.628 V, 0 µA, USB/UCSI online, all six checked core services
active. Existing keyring-WKD failure remains (fix not deployed); Wi-Fi inactive.
Root remains overlay and /persist the bounded ext4 loop. No new full block-node
inventory, temperature soak or remote Tailscale qualification is claimed.

### Selector validation and persistent-trial preparation checkpoint (2026-09-06)

Starting HEAD `d6def104ecd57e410e5f330ed621ba302a39953f`; all four jobs in
GitHub run 33996636085 now PASS. Primary question: can the refreshed persistent
server enter the correct trial before its health ACK? Layer: selector/trust and
userspace composition; no kernel rebuild or phone execution.

R2 validation defect: selector generation used Python assertions for manifest,
identity, fallback and output checks. CLI regressions produced 17 failing
subcases in 1.471 s before the fix. Several malformed inputs succeeded under
`python -O`; malformed hash/size also succeeded normally. An existing JSON
sidecar under optimization left a newly created selector before failure.
Use unconditional validation, descriptor-based no-follow bounded regular-file
reads, hash/size syntax checks and refusal of either existing output (including
dangling links). This is not a new signature verifier or an atomic two-file
publication guarantee; live admission still verifies signed artifacts.
Thirty hostile normal/optimized cases and unchanged valid output are covered.
Five selector methods PASS in 1.690 s; acceptance-manifest tests 19 PASS in
0.536 s. A02/D02 split the selector cases to avoid repeating them.

The embedded-RAM loader intentionally bypasses `read_selector` and
`select_trial_bundle`. Exact canonical ARM trial-helper tests prove a missing
pending record cannot be acknowledged, nor can an old healthy identity
acknowledge a new trial. These two cases plus rearm-before-each-boot PASS in
0.249 s using the existing isolated QEMU harness. No helper source changed.
Do not strip persistent trial metadata to make a RAM rescue look like a
persistent-server qualification.

Read-only anchored-USB/pinned-SSH inspection found the installed V10 selector
SHA `65ede599ca13b2c3ea651af2212bb80156d38919419792e3fd78d263c6216fd4`
and its matching healthy trial record SHA
`36f6141b8e6f2285aed6ceac2cb2ba6c058de5820efcd1f7cf5b83cc09ea88a9`.
Both installed bundle manifests still match that selector. Use the existing
normal selector-backed recovery and reviewed staged bundle/selector update
with preserved old state for the next persistent trial; do not reuse the
consumed V5 adapter or synthesize a pending record in the health service.

Latest same-boot read at uptime 14052.99 s: Full/Good 100%, 29.9°C, 8.627 V,
0 µA, charge counter 5116000, USB/UCSI online. Actual named rescue units remain
active; an initial query of generic sshd/networkd/tailscaled names returned
inactive because this rescue uses project-specific units. Follow-up unit
inventory confirmed the expected services and only the known keyring-WKD
failure. P24 remains RO/norecovery; P23 and the bounded /persist loop remain RW.
This is continuity evidence, not H03 or soak qualification. No staging, signing,
candidate issuance, boot, mount change or phone write command was performed.

Final focused checks: selector 5 PASS **1.837 s**; all 16 exact canonical ARM
trial-helper cases PASS **0.888 s**; acceptance runner 19 PASS **0.524 s**.
The generator also reproduced the retained installed V10 selector and JSON
record exactly from its real descriptor and both retained signed manifests.
Frozen full local CI PASS **491.554 s**, versus prior 485.604 s. Private complete
log: server-composition evidence directory, `selector-full-ci-r1.log`.
Only these current/result documents were updated after the frozen test run;
no implementation changed afterward. New exact-head/merge publication pending.

### Fresh normal-selector server package (2026-09-06)

Starting HEAD `ad9398d179b8dae5725d2ae405f243fdda8be065`, clean. That
checkpoint's exact-head/merge jobs now PASS in run 33998025054; other jobs were
still running when checked. The current package is `headless-server-selector-v1`,
unissued and unconsumed, with no phone contact during packaging.

R1 host closure gap: the receiver/admission import recognized fallback-only and
embedded-RAM execution but omitted the normal selector trial. Receiver tests
failed in 0.007 s and fixed-registry import failed in 0.025 s before support was
added. New `fastboot-boot-selector-trial` classification retains manifest hash,
exact pre-boot USB, capture lifetime and fixed repository lookup gates. Unknown
execution kinds remain rejected. No kernel or target-loader source changed.
Receiver 17 PASS 0.098 s; focused admission 3 PASS 0.137 s. The canonical record
binds the selector, trial, primary/fallback manifests, recovery bytes and bounded
P23 trial-write scope. One-use consumer tests include changed hashes/IDs and
permanent refusal after consumption; 19 PASS 0.153 s. The old test family filter
initially omitted the new row; it now derives selector-family records from the
same registry instead of copying candidate identities.

Existing builders produced identical signed target/recovery twins in **18.509 s**
without compiling either kernel. Target archive:
`16efb362d6c55f6275924fd3a0374384f4b7b61baae22a10037140daf39de70f`.
Recovery archive:
`4ba0fccdc3752a64a1cf72de68a8d426eb3ef04ceaf871b50b8ea3b4d7e0c3a9`.
100663296-byte AVB wrapper:
`dcc487f17d6b4926ea633cbb242c62b598019e332640a81c1100c2d91087f723`.
Only `trial-descriptor` and `boot-files.sha256` content differ from the tested
6934f732 server archive. All hardware payloads and runtime/health/watchdog code
remain unchanged. Prior trial identity was not promoted or reused.

Exact final repack inspection and its sealed native verifier PASS **6.771 s**
for both new primary and preserved V11 fallback. Recovery cmdline contains one
300-second deadline; signed target plans retain 600-second target / 900-second
rollback values. Sealed recovery uses the normal selector/trial executor and
current canonical ARM helper, with no embedded-bundle bypass. Core module
metadata/load-order checks pass; radio load and hardware remain separately
qualified, not silently counted as new PASS. This does not execute target init
or replace the earlier retained-root/QEMU evidence.

Private build/verification records are in the selector-server-v1 evidence
directory. Build source was the starting HEAD plus worktree digest
`3494faef9ac08176f608b42ca1488e9a46f71d4962633c4a148f814f65923ebf`;
it stayed frozen throughout packaging/checking. A private pre-build receipt-key
typo (`head` versus `revision`) failed before key use or outputs, was corrected,
and is not a target failure. No staging, claim file, boot or flash was performed.
Next: frozen full CI/publication, bounded reviewed staging and captured RAM trial.

Frozen full local CI PASS **500.609 s**, versus preceding 491.554 s. No
implementation changed during the run or afterward; only current/result text
was finalized. Read-only registry/artifact comparison passes, and the new
candidate's claim, entered record and global consumed marker are all absent.
The previous ad9398d1 checkpoint now has all four GitHub jobs PASS.

Same-boot continuity at uptime 15638.21 s: exact USB topology and pinned SSH,
six named core services active, Full/Good 100%, 29.9°C, 8.626 V, 0 µA. Installed
V10 selector and healthy-state hashes remain unchanged. No new physical test,
phone write or fallback mutation occurred. The private old rescue supervisor
still pins g359 and embedded-RAM semantics: adapt and check it for the new
selector/g1ee trial before use, rather than invoking it unchanged.

### Selector-backed persistent server: live checkpoint (2026-09-06)

Executed from clean `918f3f6d48c6eed3c46a4b0b0858c121a4bc85fb`; all four
GitHub jobs PASS run 33999018607. Reused the signed twins and sealed verification
above; no new kernel build, flash, GPT or protected-partition operation.
Primary question: can the corrected persistent server reach exact P2/SSH and
trial health using normal selector-backed RAM recovery?

The private reviewed staging adapter preserved the old V10 selector and healthy
record both on the host and device. All five new bundle files passed readback;
P24 was relocked RO, with only sda/sda23 writable. Persistent transaction took
2.324 s. No trial helper state was synthesized by the host.

R3 pre-install failure: `/run/initramfs/bin/busybox` could not execute from
Arch because its ELF interpreter is `/lib/ld-musl-aarch64.so.1`. The interpreter
exists inside the exitrd, not the Arch root. The attempted syntax check failed
before backup/install/reboot. Same-boot inspection proved the original exitrd
and absent staging destinations; the failed entry was retained. The exact
`chroot /run/initramfs /bin/busybox sh -n` check passed. Only the terminal reboot
action was then replaced in RAM; all normal storage teardown remained intact.
This is not a retry of ambiguous execution. Eight private adapter tests PASS
in 0.025 s, including default-read-only, failed backup before transfer, permanent
staging refusal after entry, exact identities and the musl command regression.

Normal teardown reached exact slot-B fastboot in 9.288 s: product lahaina,
battery-soc-ok yes, 8640 mV. Both slots remained bootable, bootloader lineage
unchanged. Prestarted capture verified its listener/address/firewall/route
ownership before the new one-use claim was consumed. Sole fastboot boot:
12.831 s. Recovery ACM recorded S70 loaded then S90 execute. New target boot:
`dd9cd15a-d9a6-4128-9dfa-5d8ef8d91fbd`, Linux `7.1.4-g1eea8970e87f`.
Authenticated P2/SSH identity ready at 83.174 s. Local P24 root plus bounded
persistent overlay passed, with one allowed journal-recovery event and no UFS
errors. Wi-Fi radio/WPA/DHCP and package trust initialization completed; trial
became healthy. No failed units or outstanding jobs remained.

R2 deployed-userspace gap: existing overlay healthd SHA
`019418fa79530d0dd0d9383c781c4b599a058f4f0e5c9784193a2b5ef47b1e51`
was still the older single-client version. One idle TCP connection caused a
concurrent health request to time out after 2.276 s. Existing eight repository
health tests PASS in 0.748 s. Backed up the deployed script and atomically
installed tested SHA
`6bed593e08f6e561cbe52cae092769845eefd08aadea5660e03e520655213d26`
inside the accepted persistent overlay; unchanged systemd unit, no reboot.
Update/restart/readback took 0.538 s. Concurrent idle/trickle clients then
permitted exact health responses over USB (0.006 s) and Wi-Fi (0.660 s), and
both stalled connections were closed. This overlay update is a distinct
deployed component; it is not silently attributed to the signed initramfs.

Same-boot component measurements (not formal all-release acceptance):

| Check | Result / duration |
|---|---|
| 256 MiB USB upload/download | PASS 7.366 / 6.582 s |
| 256 MiB Wi-Fi upload/download | PASS 171.180 / 104.777 s |
| Transfer integrity/cleanup | All SHA-256/size checks pass; no new interface errors/drops; exact test-owned RAM files removed |
| SSH restart | PASS 1.484 s; same pinned host and boot |
| WPA+DHCP restart | PASS 17.513 s; radio InvocationID unchanged |
| Health restart | PASS 0.383 s |
| Powered observation | PASS 61 samples, 600.697 s, same boot/scope |
| Capture lifetime | 1380.501 s; four owned cleanup steps PASS |

Powered observation: Full/Good 100%, 8.622–8.624 V, 29.9–30.0°C,
-13000 to 0 microamps, unchanged charge counter 5116000. Wi-Fi was active:
this is neither H03 charging proof nor the 60-minute combined soak. Kernel-log
prefix was preserved, with no new panic/oops, UFS I/O, emergency-RO or PMIC IRQ
fault signature. Watchdog acknowledged P2 plus persistent SSH identity at
uptime 902.559 s; the earlier SSH restart did not cause a rollback reboot.
Final pinned SSH after capture cleanup proved the same boot, systemd running,
healthy trial, expected selector and deployed healthd. Five live runtime/helper
hashes match expected source. Tailscale Running, online, Health `[]`; independent
peer SSH remains unproven. Phone PHY reported high-rate Wi-Fi 6 while host
reported 54 Mb/s; investigate host-path performance without guessing a kernel fix.

Private exact adapters, source/boot receipts, host rollback backups, raw capture,
hashes and samples are retained in the selector-server-v1 evidence directory.
All coordinator/sampler/transfer/restart processes completed. Installed boot B
remains old recovery `340f6392…`; no ordinary boot or physical fallback test
was substituted for the accepted RAM cycle. Preserve stock A and signed V11.
Remaining work is the full acceptance matrix, deployed-overlay composition,
updated recovery qualification, ordinary/off-start boots, durable scratch,
combined soak, regulation criteria and independent mesh access. Goal not complete.

### Reproducible deployed-userspace check (2026-09-06)

Starting source `6b682c9b8247296a9bbefca2db0bdd42d2fbf08e`, clean; its four
GitHub jobs passed run 34001434885. Same healthy server boot remained reachable.
This checkpoint adds one read-only `rog5-dev check-deployed-server` command,
not a successor image, loader or deployment framework.

R2 defect addressed: source/composer validation did not bind healthd in the
mutable persistent overlay. One repository-owned six-file inventory now derives
expected hashes/sizes from source and compares actual runtime, healthy helper,
trial helper, healthd, healthd unit and normal exitrd bytes. Canonical claim and
manifest validation precede exact USB/NCM route verification and existing pinned
SSH. The probe refuses wrong boot/bundle/kernel before userspace reads; all
path components use descriptor-relative no-follow opens. Files are bounded and
their identity/content metadata revalidated before/after read and at the path.
No boot, mount, service change, new credential or storage-write command is used.

The sanitized real stale-overlay hash/size is an executable regression fixture.
Tests also reject missing/error/extra entries, wrong boot/bundle/kernel, metadata
and hash changes, symlinks, oversized files and a pathname changed after read.
An initial Python equality check accepted boolean/float zero as integer UID zero;
both hostile cases failed before explicit integer type validation was added.
Wrong transport is tested to fail before credential use. A02 includes both
normal and optimized interpreters; active and broader CI retain the same suite.
Ten focused tests PASS in 0.104/0.095 s; existing acceptance-runner 19 tests
PASS in 0.537 s. Active tier PASS, approximately 16.616 s from log creation to
last write; the final pathname revalidation then passed focused tests and is
included in the frozen full-CI checkpoint.

First actual-phone check PASS in 0.297 s with all six exact files on the same
boot. It records source/worktree identity, canonical manifest, expected and
observed file metadata/hashes and duration in private result JSON. This is a
composition component only, not whole A01 or a qualified release. The complete
hardware acceptance rows and installed-recovery qualification remain pending.
Frozen full local CI PASS in 488.169 s (previous checkpoint 500.609 s; this
single-run difference is not a performance guarantee). No source changed during
the run; subsequent source-reuse assessment edits are documentation-only.
No new candidate is needed to validate this host-only improvement.

The bounded source-reuse assessment in `docs/kernel-port.md` pinned four public
repositories and reused retained ASUS source without another checkout. It found
different OEM control protocols and optional newly published Denial mobile UI,
not evidence for a kernel correction. No phone test was interrupted. Resumed
mandatory quick acceptance: A02 PASS 11.078 s, B01 PASS 4.287 s, G01 PASS 7.608 s,
G02 PASS 0.866 s; total 23.873 s. Other rows remain NOT RUN in this run and
`release_qualified` remains false; these passes are not merged with old releases.

### Exitrd composition and power prerequisite checkpoint (2026-09-06)

Starting clean source `b6532e208bad31588e8e073b359a84533771ae06`; all four
GitHub jobs PASS in run 34002850859. Same exact server boot remained healthy
beyond 3744 s. Read-only inventory found Full/Good 100%, 29.8°C, 8.623 V,
battery current 0, charge counter 5116000; USB 5.021 V/366 mA, online, 500 mA
input limit, Type-C device/sink. H03 remains BLOCKED: no start/end-threshold
attributes; charge_full/design report ENODATA. Do not turn this into a guessed
charge-policy write or qualify full-state regulation from a single sample.

An ad-hoc host import omitted the repository scripts path before phone contact.
A later optional Tailscale query used a nonexistent PATH entry and discarded
the aggregate stdout on nonzero exit. Both were observer errors, not hardware
failures. Recollection preserved stdout/stderr and optional errors separately;
exact `/run/rog5-tailscale/tailscale` and its runtime socket report Running,
online, Health `[]`. Custom `rog5-early-sshd`/`rog5-tailscaled` are active;
generic `sshd` is intentionally masked. Independent peer SSH remains NOT RUN:
the development host has no Tailscale executable, service or mesh route.

A01/R2–R3 correction: `archive_parameters()` previously accepted a missing,
altered or linked shutdown member. New regression failed for all three cases
before binding exact source and root-owned executable metadata. The actual
runtime fixture now tests the post-handover Arch/exitrd interpreter boundary,
with syntax-only commands: wrong direct path fails when Arch lacks musl, while
the nested chroot passes. No shutdown payload is executed.

Focused tests: 14 PASS in 0.128 s and under `-O` in 0.125 s. Active tier PASS
18.604 s. Exact existing server archive, kernel/DT and retained 32 GiB root
were reused without rebuilding or copying the root. The real host-only
read-only/no-recovery loop + disposable upper composition run PASS, reported
37.465 s (excludes initial input hashing). Log contains the actual missing
`/lib/ld-musl-aarch64.so.1` failure and subsequent EXITRD_PASS. Artifact hashes
were checked before/after; owned mount/loop cleanup passed and no mapping
remained. This is still an A01 component, not full-release or physical recovery
qualification. Frozen full local CI PASS in 497.686 s (previous 488.169 s);
no implementation changed during or after that run.

Separate pinned-SSH comparison matched all 19 sealed core-module GNU build-ID
notes to live `/sys/module` notes and confirmed initstate=live. This is physical
core-module identity/load evidence, not radio closure or a whole A01 PASS.
Kernel taint 4608 comprises out-of-tree modules and the retained boot-time WARN.
The single early SPMI transaction failure reads SID5 address `0x104` during
`pmic_spmi_probe`; `0xcf08` in its message is the arbiter status-register offset,
not the PMIC register being read. This warning predates this release (July 25
and August 31 evidence); it must not be hidden or newly blamed on charging.
No new kernel change follows from the bounded comparison.

### Updated recovery fallback qualification preparation (2026-09-06)

Starting clean source `7865f0a8c4d13dfaaaf56c58873822bebb9395a8`; its exact-head,
merge, publication and QEMU jobs all passed run 34003755950. The existing
server's six-file deployed check passed again in 0.249 s. At uptime 5750 s,
the same boot had Full/Good 100%, 29.8°C, 8.622 V and zero battery current;
USB was online at 5.050 V/175 mA with 500 mA input limit, device/sink role.
Systemd/project SSH/health/Tailscale services were active, Wi-Fi addressed,
selector unchanged and trial healthy. Native lower stayed RO/norecovery;
existing P23/service-state mounts were unchanged. An ad-hoc first read used
Android-style supply names; those missing paths were observer errors, corrected
using the already retained `qcom-battmgr-*` names, not missing hardware.

R2 recovery-composition evidence: exact installed backup `340f6392…` and tested
RAM archive share init, local executor, bundle verifier, kexec and trust key.
The selector loader and trial helper differ. Exact ARM binary replay of
decide → healthy → decide → decide leaves v1 selecting primary/healthy;
v2 rearms pending and then selects V11. Replay took 0.450 s in a disposable
fixture, not on the phone. Current fallback-order tests passed 7 cases in
0.495 s and exact ARM trial-helper tests passed 16 in 0.945 s.

Prepared new `headless-selector-rescue-v2` from the same reviewed ASUS kernel,
current recovery source/v2 helper and one executor pinned to the current
selector. Its intended question is verified fallback selection/transport with
no recovery trial write; it is not the separate R01 failed-target experiment.
Existing signed V11 is unchanged. Recovery archive and boot twins are identical;
the sealed ARM verifier accepted the exact fallback signature and every payload.
The canonical claim registry alone records the new identities; other consumers
derive them. Extending the existing fallback claim regression to all such rows
avoids another candidate-specific copied test. Registration is not issuance.

R3 host-only check failure: `avbtool verify_image` resolves the descriptor's
partition name `boot.img`, not `recovery-a.avb.img`. The check initially stopped
after verifying the NONE vbmeta footer because that sibling did not exist.
No image or phone change followed. Verification of an exact temporary `boot.img`
copy passed; offline replay also rejected the missing-name and changed-payload
fixtures. Corrected verification took 1.454 s, reusing the already built bytes.
The original build timer was not saved before the exception: no precise build
duration is claimed. Retained outputs occupied approximately 291 MiB; no new
kernel compilation, target signing, private-key use, admission, claim issuance,
phone reboot, selector change or installed-image write occurred.

Frozen validation passed: active 16.568 s; full local CI 487.116 s (previous
497.686 s, not a performance guarantee). No source changed during either run.
Read-only physical hashing then confirmed installed boot B itself, not merely
its retained backup, is `340f6392…`; all five V11 payload hashes still match.
The default transition inspection passed on the same boot at uptime 6538 s.
Five offline private-adapter tests passed in 0.007 s, covering exact derivation,
source/target identity, read-only default, publication failure before entry,
and an ambiguous install refusing both reboot and retry. These adapters reuse
the prior one-shot supervisor and normal exitrd teardown. They have not executed
a transition or created a claim. Remote publication/CI and connected admission
remain separate gates; a fallback branch PASS will not be relabeled R01.

### Fallback qualification execution and observer mismatch (2026-09-06)

Published source `23e8fe430dff4fb1dcc7c6634d660bf390458bb3` passed all four
GitHub jobs in run 34005091904 before the sole execution. Exact transition to
slot-B fastboot took 11.419 s. `headless-selector-rescue-v2` is permanently
consumed: fastboot accepted the exact 100663296-byte image `bb6bffb1…` in
12.812 s (adapter execution 15.216 s). The unchanged signed V11 fallback
manifest `a684bad1…` reached recovery ACM S90 and target switch-root PASS.
Its authenticated boot is `6aa96219-c542-441c-9500-dd540e89b249`, kernel
`7.1.4-g359318de534f`. No flash or GPT mutation occurred.

**R2/R3/R7, host observer defect:** the reused supervisor required
`attested_boot_id=$boot` in `/run/rog5-p2-ready`, but the exact sealed V11
producer has no such field. Captured pinned SSH returned the expected kernel,
bundle, P2 PASS and active identity service. The offending predicate fails on
that actual marker. The original smoke remains FAIL at **300.115 s**, not a
kernel failure or a successful H02. A second read-only probe initially assumed
Python existed on V11 and returned 127; its evidence is preserved. Exact shell
collection instead passed in **0.209 s**, checking the same boot before/after,
tmpfs marker, stable root-owned 0444 regular single-link file, target identity
and pinned SSH. This is only a separately scoped fallback/SSH component;
H02 and R01 remain NOT RUN in that component and no release is qualified.

Private fail-first replay verifies the sealed producer and executes the actual
failed predicate (2 tests). A draft family-specific observer contract has four
regressions: captured legacy format is fallback-component-only, current server
families still require boot-bound attestation, wrong/stale metadata and identity
fail, and duplicate/failed/stale marker fields fail. It neither changes the
running supervisor nor creates boot authority. No new candidate was built.
Repository integration of this observer correction remains next work.

The untouched supervisor ended normally after **1380.804 s**, retaining its last
target stage, switch-root PASS. Capture alone reports NOT RUN for authenticated
qualification. All four owned host route/firewall/profile/address cleanup
events passed; subsequent host inspection confirmed the original shared USB
profile, no temporary loopback address and no TCP/8079 listener. Same-boot
read-only SSH at uptime 1398 s confirmed unchanged selector `c15c7782…` and
healthy primary trial `bfc82fac…`, Full/Good 100%, 29.7°C, 8.621 V, zero battery
current, USB online and empty pstore. Empty pstore is inconclusive; full-battery
continuity is not proof of net-positive charging or qualified H03 regulation.

Systemd is degraded solely by V11's existing empty-keyring WKD failure, with
the same `fpr_email[1]: unbound variable` at line 64 already diagnosed above.
It retries three times and hits its limit. The primary's tested bootstrap
composition is absent from this old immutable fallback; no service was masked,
reset or changed to hide it. This finding does not justify kernel replacement.
The fallback's tmpfs upper also lacks the primary's Python/deployed userspace;
do not combine acceptance evidence from these incompatible roots.

After capture/cleanup, the unchanged implementation passed acceptance quick:
A02 **10.180 s**, B01 **3.837 s**, G01 **7.309 s**, G02 **0.666 s**.
The private observed-marker replay passed 2 tests in **0.378 s** and draft
contract passed 4 in **0.001 s**. `git diff --check` passed. Only current-state
and this incident changed after published HEAD; no redundant full CI or kernel
build was run for these documentation updates. Quick PASS is not release PASS.

The next observer-only correction extends existing `check-deployed-server`
with `--readiness-only`; it does not introduce a second lifecycle or alter
the old supervisor/results. A sanitized captured V11 marker reproduces the
original failed grep. Five new test methods failed before implementation;
the resulting 15-method suite passes normal/optimized Python in 0.113/0.103 s.
Coverage includes legacy-only fallback scope, mandatory current-server boot
binding, malformed/duplicate/stale fields, identity/metadata errors, exact
NUL framing, no target Python and failure before credentials on wrong USB.
Same-boot pinned-SSH execution of the integrated command passed in **0.251 s**.
It reuses canonical entered-claim/manifest/credential/route checks, verifies the
fixed runtime marker and records exact source/boot identity. No phone mutation,
kernel rebuild, target signing, new claim or execution was requested. The
legacy component remains distinct from the original smoke FAIL and H02/R01.

Frozen checkpoint: active **16.633 s**, full local CI **483.726 s** (previous
487.116 s); all tracked implementation inputs remained unchanged during CI.
Only these final documentation timings followed CI. No kernel build was needed.
The read-only recovery-path review still requires a separate isolated signed
failure experiment for R01: installed helper v1 is not qualified for a formerly
healthy primary's next failure, and RAM fallback selection does not prove that
case. Keep the original failed smoke, current signed fallback and slot A intact.

### Coherent headless rescue V6 preparation (2026-09-06)

Starting clean source `4205a261b1e625aeeb9e307340e563071c34090d`; its head-exact,
merge, publication and QEMU jobs all passed run 34007323724. Question: does the
current headless composition initialize package trust while preserving pinned
SSH and boot-bound watchdog readiness with Wi-Fi intentionally inactive?
This advances H02 composition, not R01 or full-release qualification.

The existing standalone archive builder refreshed the canonical V5 payload.
Relative to V5 only init changed and package-keyring helper/unit were added.
The exact accepted g359 kernel, DTB, 19 core modules and firmware archive were
preserved. Both unsigned twins match; preparation took **6.983 s**. The actual
retained Arch image was reused read-only/noload, without copying its 32 GiB.
Sealed runtime/unit/module-metadata composition passed in **35.642 s** and
owned mount/loop cleanup passed. All nine exact-archive QEMU watchdog/handover
cases passed (summed case runtime **93.948 s**, not total wall-clock duration),
including missing/stale ACK, P2-only, post-exec hang and separate failed init.

Existing signing/build/repack tools produced identical signed bundle/recovery
twins in **15.167 s**, with no ASUS or mainline kernel compilation. The final
assembled wrapper was unpacked and checked against exact source/payloads; its
sealed ARM verifier accepted signature, hashes and target plan. AVB verification
used the descriptor-correct temporary `boot.img` name, avoiding the previous
host-only basename defect. The outer AVB hash footer is not a cryptographic
signature; the embedded target bundle retains its verified Ed25519 signature.
Wrapper timeout stays 300 s; target rollback/target deadlines remain 900/600 s.

Prepared `headless-acceptance-rescue-v6` identities:

- target archive: `7703f3984dd161ee2ee13f9198068afcbebeb325624f1ce167f5922b0eb46c2d`;
- manifest: `8beb3ab75ef406b1c293d0b207df8ab527b8da9b842beb1c0002539bef8494b3`;
- recovery archive: `e2aa0c64e7eb3ae3260b42ff78a51cac1495e1d2653a9b0fd21a3449841ecb86`;
- 100663296-byte boot image: `32704e44d04f650ca720ef260e4a62062b41c0a488907347ed4a710b4cc13d97`.

Private output allocation was 868196352 bytes, including retained QEMU fixtures;
this is not a measured peak-build high-water mark. Source stayed frozen during
preparation/tests/packaging. Registration adds only one canonical data row;
generic claim tests (19, **0.161 s**) and admission closure (33, **3.469 s**)
cover it without new executable candidate branches. No new claim/admission,
phone reboot, selector change, flash or phone storage operation occurred.
Full local CI from unchanged implementation is reused explicitly; data-only
registration gets focused/active validation before publication. A future live
supervisor must use the integrated observer and independently inspect the
current fallback's actual exitrd; V5/primary transition assumptions are not
silently applicable to the now-running legacy V11 fallback.

Registration active tier passed in **16.776 s**. The subsequent read-only
source inspection passed in **0.261 s** on the same fallback boot at uptime
3162 s: exact sealed V11 shutdown `ec3c7fd2…` is deployed, while repository
shutdown is `1cd007ea…`. Its BusyBox/musl are present as root-owned executable
regular single-link files in tmpfs. This is a confirmed version difference,
not an unexplained mutation; a primary-derived transition expecting current
shutdown must not be used blindly. Battery remained Full/Good 100%, 29.7°C,
8.620 V, zero current and USB online; selector/trial remained unchanged.
The publication scope is only the canonical prepared artifact row and these
existing documents. Full implementation CI is explicitly reused from 4205a261;
connected preflight and the new head's publication checks are still required.

Bounded source-reuse recheck at `2d5a0994…` reused the existing kernel-port
assessment and retained ZS673KS charger source; all four public source pins
remain unchanged. Denial's current release listing still provides no
ARM64-named package. No imported driver, policy write, kernel rebuild, large
checkout or device interruption was justified. Only the existing assessment
was clarified. Returned to mandatory quick acceptance on this revision with
the documentation-only diff frozen: A02 PASS **10.181 s**, B01 PASS **3.837 s**,
G01 PASS **7.309 s**, G02 PASS **0.666 s**; total **22.018 s**. Other rows are
NOT RUN in this run, not imported passes or release qualification. H02's exact
V11-to-coherent-rescue transition remains the next physical checkpoint; this
review does not issue, admit or execute V6. Existing exact-head CI was left
running; no unchanged full local suite was repeated.

Registration CI run 34007871579 finished successfully at exact `2d5a0994…`.
The private V6 exitrd checker derives an action-only delta from the hash-bound
sealed V11 archive, preserves its complete storage teardown, and parses the
result in the exact ARM BusyBox/filesystem namespace. This is syntax/delta
coverage, not hardware teardown proof. Pinned read-only same-boot inspection
also verified deployed shutdown, BusyBox, musl, reboot helper/provider, selector,
fallback manifest, healthy trial, RO P24 and unchanged installed boot B. Combined
check PASS **0.516 s** at uptime 3871 s: Full/Good 100%, 29.7°C, 8.620 V, USB
online. The known legacy keyring failure remains visible. New action-delta SHA
`a3da03bf558a814c10388471eb38323e4f923349f87024274efa4408addb8753`
is host-prepared only; no phone file was installed, no reboot requested, and no
candidate consumed. Adapter execution and actual supervised H02 remain pending.

### V6 physical rescue and powered checkpoint (2026-09-06)

Published source `ae819406f4c4bbb37cc479ff6da8287ba6d393c2` passed all four jobs
in run 34008374648. The exact legacy shutdown action-only RAM transition passed
in **9.260 s**, reaching anchored slot-B fastboot at 8.632 V / SOC-safe yes.
No flash, GPT, selector or target-bundle staging operation occurred. Existing
prepared signed twins were reused without rebuilding either kernel.

The first privileged supervisor preflight failed before capture/claim/boot:
`runuser` inherited a PATH without `gh`. Its log and adapters were preserved;
the existing absolute executable path corrected it. Eight private adapter tests
passed normal/optimized Python in 0.305/0.309 s, and actual runuser preflight
passed before starting a new capture. Capture-aware network preflight also
distinguishes the original empty zone from receipt-verified `nm-shared`.

`headless-acceptance-rescue-v6` is **consumed permanently**. The sole fastboot
operation completed in **12.824 s**. Recovery reported verified bundle,
loaded kexec and execute; the target reported switch-root PASS. Integrated
pinned SSH/current-boot readiness passed at **59.555 s**, boot
`64e209e2-0efe-40c6-8396-29f3e481f0ff`, kernel `7.1.4-g359318de534f`.
Wi-Fi remained inactive. The refreshed keyring bootstrap and subsequent WKD
refresh both succeeded, with no failed systemd units. Eight live runtime files
matched the exact sealed archive in **0.246 s**, with root ownership, modes,
single-link regular files and stable before/after metadata. Package trust is
bound from the accepted service-state image; no key material was exported.

Bounded powered continuity passed **95 samples / 960.494 s**: same boot and
selector, Full/Good 100%, 29.7–29.8°C, 8.619 V and USB input online. The deployed
watchdog logged current-boot P2 + SSH identity ACK at **902.519531 s** uptime.
Kernel-log prefix continuity held, with no new matched warning/oops/UFS-error
lines; the initial SPMI warning is retained, not suppressed. This idle/full
battery component does not qualify H03 regulation or a loaded server soak.

A first service-restart invocation failed in host Python's input encoding
before any script was sent (`bytes` with `text=True`). A local cat fixture
reproduced it; corrected text input passed. Both failure/entry records remain.
The subsequent single SSH service restart passed in **0.230 s**, changing its
main PID; fresh pinned readiness passed in **0.191 s**, on the same boot.
This is not a retry of candidate execution or full C02 release qualification.

Capture ended in **1380.479 s** with exit zero; all four owned route/firewall/
profile/address cleanup events passed. Its result correctly remains evidence,
not authenticated qualification by itself. Pinned SSH/readiness after cleanup
passed in **0.193 s**. All monitor/capture processes are terminal. The original
selector and healthy trial remain unchanged; signed V11 and stock A remain
preserved. The current rescue has a tmpfs upper, not the primary persistent
upper. No passes are silently imported across these different compositions.

Read-only R01 review verified that this exact sealed reset helper requests
fastboot, not autonomous fallback boot. A later host-assisted failure/rescue
cycle needs fresh separately bound execution records; it cannot qualify the
old installed loader's previously-healthy-primary demotion or autonomous rescue.
No R01 candidate or failure injection was issued. Complete H02 integration,
H03 criteria, persistent-server boots/soak and R01 remain outstanding.

Bounded source-reuse follow-up at `ca0359868…` confirmed the four existing
remote pins unchanged and the retained ZS673KS charger hash unchanged. No
checkout, driver import, control write, rebuild or reboot was needed. The
existing assessment now distinguishes Denial's exact-byte release promotion
from reproducible builds. Resumed the H02 readiness component: 15 observer
regressions passed in **0.107 s**; a fresh strict-pinned, canonical-claim-bound
readiness check passed in **0.237 s** on the same V6 boot `64e209e2…`.
Private result: the existing V6 cycle's `source-reuse-readiness-checkpoint`.
This is new same-boot component evidence, not a replayed boot or a complete
H02 PASS; the dispatcher integration remains pending. No running device test
was interrupted, and no unchanged full local suite was repeated.

### Executable startup-evidence checkpoint

Added `rog5-dev check-rescue-startup` to close the missing original-timeline
replay component of H02. It checks the canonical consumed record, exact
manifest and capture receipt, pre-execution setup ordering, original deadline,
producer/source versions and raw boot-bound readiness. It does not contact the
phone or grant authority. Its result explicitly leaves whole H02 and release
qualification false: watchdog/archive, Wi-Fi isolation and power components
must still be connected before that row can pass.

The new regression file first failed because the runner did not exist. Final
13-case suites passed in normal/optimized Python (**0.104/0.098 s**), including
late/missing capture, wrong boot/candidate, ambiguous execution, changed
producer, malformed metadata and deadline failures. Existing dispatcher tests
passed **19 cases / 0.528 s**. The retained real V6 transcript passed replay in
**0.028 s**, explicitly reusing its original **59.555 s** startup timing, not
starting a new deadline. Source and every consumed evidence hash are retained
in the private V6 `startup-replay-r1/result.json`.

Active tier exited zero in **16.869 s**; its two pre-existing retained-ARM-artifact
skips (PMIC rail reader and V1/V2 trial-state replay) remain visible,
not mandatory hardware PASS. The first timing invocation lacked `/usr/bin/time`
and did not start tests; Bash's timing keyword captured the actual run. Logs
remain in the private `rog5-startup-integration-20260906` checkpoint directory.
The prior published head's CI run 34010050129 completed successfully; it does
not validate these uncommitted additions. Full local/exact-head publication
CI remains due when H02 integration reaches its frozen publication checkpoint.
No kernel/recovery rebuild, candidate issue, phone operation or storage write
was performed for this host-only change. Keep this checkpoint; finish the
remaining same-boot H02 evidence integration without another physical attempt.

The subsequent integration closes H02: `--qualify-current` verifies canonical
boot/archive bytes, paired sealed watchdog/identity producers, eight actual
runtime files, intentional radio absence and safe power through pinned SSH on
the original boot. The exact sealed BusyBox probe passed in disposable target
paths with fixture mount/dmesg observations; an actual fixture radio directory
was rejected. No target Python, new boot, control write or candidate is needed.
Five new runtime regressions first failed for missing implementation; final
normal/optimized suites passed **18 cases / 0.108–0.104 s**. Dispatcher coverage
now has **22 cases**, including refusal of exit-zero component output without
complete exact H02 proof. Supplied private inputs are named arguments, not
commands, and original-cycle reuse remains explicit.

Fresh same-boot qualification passed in **1.102 s**. Integrated device-smoke
recorded **H01 PASS 0.166 s / H02 PASS 1.366 s / H03 BLOCKED**, total **62.396 s**
including all five retained artifact hashes before/after. The original startup
deadline remains 300 s and observed startup remains 59.555 s. Watchdog arm
2.468063 s and ACK 902.519531 s match the signed 900-second interval. Battery:
Full/Good, 100%, 29.7°C, 8.618 V, zero current, USB online; this is not H03 net
charging or full-state regulation proof. Kernel/boot remain unchanged.

The frozen implementation passed full local CI in **486.402 s** (previous
implementation checkpoint 483.726 s; not a controlled performance benchmark).
The full tier separately passed retained ARM trial-state replay; its optional
rail-artifact skip remains visible. Private logs remain alongside the previous
active run, and the V6 directory retains `h02-current-r1` and
`acceptance-h02-r1` with exact source/worktree, artifact and evidence hashes.
The latter matrix is not a green release. No experimental flash, GPT change,
kernel/recovery rebuild or repeated target execution occurred. Only this
completion documentation changed after the full run; exact-head/merge CI will
cover the publication commit. Next resolve H03 criteria, then qualify one
coherent persistent server release and the separate failed-boot recovery route.

### Bounded H03 source regression (not deployed)

Publication `ac25155eb77d98cb8a4d02018895adbd2c4df1b5` passed all four jobs in
GitHub run 34011983097. The next H03 check traced the actual ENODATA capacity
failure into the sealed driver's source; provenance and upstream attribution
are in the [existing source assessment](../docs/kernel-port.md#h03-capacity-unit-follow-up).
Unlike the incompatible downstream controls, this is a demonstrated mainline
unit-initialization defect, not a host parser or charging-policy failure.

Before patch 0038 existed, the regression reproduced ENODATA from compiled
unfixed SM8350/SM8550 source fragments; its two correction checks failed.
After the one-assignment correction, three tests passed in **0.133 s**;
retained-source excerpt/application checks plus test process took **0.206 s**.
Optimized Python passed in **0.144 s** (process **0.298 s**).
The fixture tests all four protocol variants with both unit states and both
charge/energy full/design readouts; it does not emulate firmware transport.
Only temporary copies are patched. The retained source, accepted build,
running rescue, fallback, signed artifacts and one-use records are unchanged.
No build, candidate issuance, module reload, phone contact or storage change
was performed for this follow-up. H03 and whole-release acceptance remain
incomplete; this does not prove net charging or regulation.

Active tier passed **17.196 s** (previous 16.869 s); the frozen code then passed
one full local CI in **489.593 s** (previous 486.402 s). These adjacent runs are
not controlled benchmarks. Historical/optional retained-artifact skips remain
visible, not hardware PASS. Full log is retained in the private
`rog5-battmgr-units-20260906` checkpoint. Only this completion text and patch
description wrapping changed afterward; focused normal/optimized/source checks
were repeated, not full local CI. Kernel checkpatch via stdin reports no errors
or warnings after wrapping. No production kernel/module build was needed.
Exact-head/merge GitHub CI is required for the publication commit and is
separate from the passed prior H02 checkpoint.

### Exact-Arch C02 component checkpoint

`83e2c66e6c7ad7ca5dc097c5a758a3ad9c033c65` passed all four jobs in
CI 34013013582. Fresh pinned same-rescue readiness passed **0.245 s**;
full H02 revalidation passed **1.210 s** at uptime 6931.37 s, same boot,
Full/Good 100%, 29.7°C, 8.616 V, zero current, USB online and the same 900 s ACK.
No SSH restart or reboot was requested on the phone in this iteration.

Extended the existing QEMU handoff runner, not the kernel or lifecycle, with
`--root-image`. The retained Arch root is presented as a read-only virtual disk
and mounted ro/noload under a RAM overlay. Its actual systemd **260.2-2-arch**,
sshd and account database execute with the exact archive's SSH/keygen units,
BusyBox and watchdog functions. Private ephemeral VM keys, loopback-only SSH,
fixture configuration/ACKs and a 20 s test timer do not qualify phone credentials,
hardware activation, optional Wi-Fi rollback, or the final release.

Preserved failed attempts: r1 rejected a duplicate archive member before QEMU;
r2 exposed missing startup diagnostics; r3 identified the fixture's missing
`nobody` privilege-separation account; r4 reached SSH but rejected authentication
with world-writable default tmpfs `/run`; r5 authenticated and restarted SSH
but exceeded the unchanged 40 s guest ceiling due to a redundant fixed wait.
Complete-archive regressions cover duplicate/replacement and account/mode errors.
The fixture now preserves Arch accounts, uses `/run` 0755, waits boundedly for
the real listener and observes actual watchdog exit instead of sleeping a new
full interval. No security check or timeout was weakened; these were fixture
defects, not demonstrated production-kernel defects.

r6 passed both cases in **30.004/22.884 s**, total **115.192 s**. Final r7 adds
explicit false C02/release-qualification fields and also passed **30.402/23.034 s**,
total **115.357 s**, including both 32 GiB input hashes. Healthy SSH PID changed
**121 → 177** with pinned, key-only command execution after restart; stale
identity instead caused the exact bootloader reset without a restart PASS.
The root remains `06cc805b…`; kernel/archive remain `bdceaa51…`/`7703f398…`.
Both guest archives/logs total about **3.7 MiB** per run, no root-image copy.
The existing private V6 directory retains `c02-arch-qemu-r1` through `r7` and
the fresh phone observers. **11 focused tests pass** (final 0.440 s), including
roundtrip archive, read-only disk, exact-unit and unchanged nine-case C01 checks.

C02 still requires the optional Wi-Fi rollback timer in the same target runtime
and dispatcher integration; commands remain empty/BLOCKED. Do not combine this
component with host-systemd or prior-primary evidence into an invented green row.
Kernel rebuild, admission, physical failure injection and full publication CI
are not needed merely to continue this in-progress offline integration.
Dispatcher regressions passed **22 cases / 0.567 s**; active tier passed
**17.369 s**, with the existing optional artifact skips explicit. This is a
local checkpoint, not a published/full-CI-qualified C02 implementation. r1
failed before guest logs existed; its traceback remains in the task record.

### Exact-Arch optional rollback component

From `fd387eb4897a9abfa5d35e530973a2459e379e8f`, extended the same handoff
runner with `--wifi-rollback`. Retained server archive `6934f732…` supplies
runtime `a96de52d…`, service, timer and SSH drop-in byte-for-byte. The actual
Arch systemd/sshd, sealed watchdog and read-only root remain; only fixture
identity/keys and a 15 s timer drop-in live in RAM. No radio or phone operation.

Private `c02-arch-wifi-qemu-r1`–`r3` under the existing V6 evidence directory
preserve failed single-VM attempts (102.269/102.031/101.689 s). Healthy restart
passed, but the second timer did not fire. The systematic-debugging procedure
traced r3 to guest uptime **36.23 s**, requested deadline **34 s**,
`SubState=elapsed`, next trigger infinity, and the prior healthy invocation.
The 3.525 s daemon reload had overrun the new two-second deadline.
[Systemd v260.2 timer.c](https://github.com/systemd/systemd/blob/v260.2/src/core/timer.c)
confirms that a previously fired, expired one-time trigger is disabled; this
was fixture state reuse, not a charging/kernel defect. Opus review could not
authenticate (expired OAuth); an independent agent could not start because
the existing agent limit was reached. No authentication settings were changed.

Two fresh VMs eliminate reused timer state and runtime reload entirely.
r4 passed in 33.561/26.284 s but totaled **121.161 s**, above the 120 s C02
row, so it was not accepted as that row. Removed only the healthy Wi-Fi case's
redundant three-second sleep: it already waits for the actual rollback service
to finish and re-authenticates. Its regression failed before that correction.
r5 passed **30.449/26.592 s**, total **118.564 s**. Healthy SSH PID changed
**124 → 187**; stale Wi-Fi acceptance caused ordinary systemd reboot after
the valid core watchdog ACK, not a panic/core-watchdog reset. Root hash remains
`06cc805b…`; kernel remains `bdceaa51…`. Runner hash:
`57f164eaf6cce106e9241cb55a0833dda2219bff6f346763b3e65279d90af98a`.

Thirteen focused regressions cover sealed-member metadata/absence, archive
roundtrip, distinct VM cases and required outcome evidence (0.857 s process).
The active tier passed in **17.576 s** before the final wait-only correction
and **17.525 s** afterward; dispatcher regressions passed 22 tests in 0.701 s.
Optional retained-artifact skips remain explicit. Full local/publication CI
is deferred to coherent C02 dispatcher integration, not claimed passed here.
The result still says `c02_qualified=false` and `release_qualified=false`.
Next bind the complete proof to the dispatcher and exact release inputs, with
deadline headroom measured before publication. No kernel build is needed.

### C02 dispatcher integration

From `42c9b7e6fb19f034efad47a7028dcdad5b78e787`, made C02 executable with
archive-selected `--c02` coverage and exact result validation. Fail-first tests
proved that the old dispatcher accepted exit zero without a C02 proof. New
tests reject partial cases, wrong kernel/archive/root hashes, stale source or
runner identity, missing proof, false qualification and deadline overrun.
The optional Wi-Fi service readout now uses one systemctl property snapshot
instead of repeated processes; no production service or timing value changes.

The first integrated row reached both VM outcomes but failed at **120.016 s**.
Inspection and a fail-first regression identified a separate host defect:
`run_one` hashed every file argument, including the 32 GiB root, as test source
inside the deadline. It now hashes only repository-owned relative test source.
Receipt verification, exact artifact identities and runner pre/post root hashes
remain. No artifact check or deadline was removed.

`c02-integrated-wifi-r2` under the existing private V6 directory records
**C02 PASS 118.811 s**; guest cases **29.195/27.190 s**. Kernel/archive/root
remain `bdceaa51…`/`6934f732…`/`06cc805b…`, explicitly an offline retained
server composition, not an admitted candidate or proof about current rescue.
Runner `e49ea51d…`; proof SHA-256
`716ff3a94d549704d1127aef9aad1f461554b63c3544e04c9dead7932dfd61e6`.
The private input receipt and driver preserve exact paths, source/worktree,
contract and command identities; `release_qualified=false` remains explicit.
The timing margin is narrow. Do not silently relax 120 s or reinterpret an
overrun as PASS. Normal/optimized dispatcher tests and archive regressions pass;
full frozen CI and publication checks follow this integration checkpoint.

Final focused checks passed **25 dispatcher tests / 0.921 s** and **15 archive
tests / 1.166 s**; optimized dispatcher execution also passed. Frozen full local
CI passed once in **485.614 s** (previous published checkpoint 489.593 s;
not a controlled benchmark). Private log: `c02-full-ci-r1.log` in the same
evidence directory. Only completion documentation changed afterward.
Fresh pinned same-rescue H02 passed **1.297 s**, uptime **9931.81 s**,
Full/Good 100%, 29.7°C, 8.615 V, current zero and USB online. Same boot, sealed
runtime files and 900 s watchdog ACK; no radio activation, service restart,
boot, build or flash. `c02-publish-health-r1` retains this separate proof, not
imported into the offline composition's C02 row or a green release. Exact-head
and merge publication CI must cover the new commit before any hardware use.

### Bounded source recheck and A01 resumption

At `d82e459ff5a3837f09be9d5e7b8b49f1434de9f9`, all four external source
pins in `docs/kernel-port.md` remain unchanged. Retained ASUS charger source
hash matches; the incompatible `0x2108` meanings were reverified directly.
Denial v0.3.1 is a prerelease, with no ARM64-named asset; its latest-stable API
returns 404, which is not evidence that no prerelease exists. No code imported,
large checkout, kernel build or phone interaction. Existing CI continued.

Resumed A01 using existing `archive_parameters`, `core_module_members` and
`module_closure` against the retained server-runtime-r2 archive and its original
receipt kernel. Exact sizes/hashes and banner match: archive `6934f732…`, kernel
`2649a272…`, release `7.1.4-g1eea8970e87f`. Nineteen sealed power/UFS module
metadata entries passed in **1.367 s**; four auxiliary radio payloads remain
**NOT RUN** for load/closure. This is not the different `bdceaa51…` kernel used
for C02's userspace-only VMs. Do not combine those component results into a
coherent release PASS. A01 still needs final wrapper, full module-load/BTF,
root/timing/transport integration. No root mount or module execution occurred.
Fourteen composition regressions pass in normal and optimized Python; 25
dispatcher regressions pass. Full CI was not repeated for documentation only.

### A01 startup member metadata correction

The existing checker compared startup/helper content but omitted owner, mode
and link-count checks for seven mandatory members and the optional observer.
A fail-first test preserved the exact contents while altering metadata: **47
cases were incorrectly accepted** before the fix. The checker now requires
root-owned, single-link regular executables (0755), and a regular 0644 keyring
unit, before executing any fixture. Observer absence remains optional. The
old stale-observer test now uses valid metadata so it still tests content.
This is R2 offline composition coverage, not a demonstrated deployed defect.

All **15 composition tests** pass under normal and optimized Python. Existing
server/rescue archives pass the strengthened check in **0.680/0.386 s**;
no artifact changed. Active tier **PASS 18.025 s**, private
`a01-metadata-active.3fwGMKbT.log` in the V6 evidence directory. Full local CI
will run once on this frozen checkpoint; previous exact-head, merge,
candidate-publication and QEMU CI all passed run 34016170872 for `d82e459f…`.

Fresh read-only same-boot H02 **PASS 1.242 s**, retained under
`a01-health.Bsg16f8c/result` in that directory: uptime **11083.54 s**, Full/Good
100%, **29.7°C**, **8.614 V**, zero current, USB online and original watchdog
ACK. No radio activation, reboot, charging write or release qualification.

Frozen full local CI **PASS 487.855 s**, private
`a01-metadata-full-ci.BUtVRXPv.log`; optional unavailable-artifact skips remain
visible and do not qualify those artifact tests. Only completion docs changed
afterward. No rerun on unchanged implementation.

While CI ran, a private isolated QEMU experiment used the existing archive
parser/metadata/load-order checks to construct a VM-only init from exact sealed
BusyBox, musl and 19 power/UFS modules. Under their **exact server kernel**
`2649a272…`, every module reached `live`; exit 0, completion marker present,
no detected module/symbol/BTF/panic/oops/warning errors: **PASS 8.148 s**.
Archive `6934f732…` and kernel hashes were checked before/after. Container
`a7303c3b…`, network disabled, no phone/host block access or real root image.
Private `rog5-a01-module-qemu-20260906.2YwQWQ2V` retains harness, command,
VM archive, log and result; harness SHA-256
`e4bcc0c6a7b69905c287d6a9fa3f926d3ac81fe3383429c1ca7cf094ee68b87d`,
result `5912a4fd0f019c0b6411d37b372c8c074ed616e2b8b18ca121008c8e2595e552`.
Hardware probing and four auxiliary radio payloads remain **NOT RUN**.
This proves core module insertion, not whole A01, physical operation or an
admitted release. Next C02 uses this exact server kernel with the retained
server archive/root; its earlier different-kernel evidence is not imported.

### C02 with the exact server kernel

After publishing **52b24f66d29e2371b6843facc799787fe0001d47**, ran the existing
C02 dispatcher with kernel `2649a272…`, archive `6934f732…` and retained Arch
root `06cc805b…`. Source stayed clean/unchanged. **PASS 117.759 s** under the
unchanged 120-second deadline; healthy/stale fresh VMs **30.098/25.887 s**.
Actual Arch systemd/sshd, exact sealed watchdog/SSH/Wi-Fi rollback helpers;
healthy late SSH restart survived and stale acceptance caused ordinary reboot.
Root hash unchanged; no radio activation or physical access. This replaces
the mixed-kernel limitation for C02 but is not combined-release qualification.
Evidence: `c02-exact-server-r1` under the private module-QEMU directory above;
runner proof SHA-256
`16ac97a7a904d2953f1e3013cce247a4c51aece2ce3e6894973c1eed8f2dce6f`.
Remote run **34017100368** covers the published checker checkpoint; still
in progress when this result was recorded. No full CI rerun for these result
notes; no production input changed after its frozen full-suite PASS.

### A01 sealed radio software closure

At `52b24f66…` with only the preceding result notes dirty, inspected the sealed
radio package: 86 tar entries / 65,022,576 bytes, including its module indexes
and 17 load roots. A private QEMU fixture validates tar bounds/type/ownership/
paths, uses exact sealed BusyBox/core modules, mounts retained Arch ext4
RO/noload, and invokes that root's `modprobe --show-depends` followed by module
insertion for each sealed load root. Only virtual hardware is exposed; no
S12/PMU/PCIe activation helper, phone DTB, credentials or host storage writes.

All **17 roots returned successfully**, from crypto dependencies through
ath11k_pci; **PASS 90.525 s** including full pre/post retained-image hashing.
Kernel/archive/root are `2649a272…` / `6934f732…` / `06cc805b…`; source and
inputs unchanged. Exit 0/completion marker; no detected symbol, invalid-module,
BTF, panic/oops/warning errors. This is software insertion evidence only.
The log explicitly retains `sha256` out-of-tree taint and `regulatory.db`
lookup failure. The archive contains `firmware/regulatory.db` (6380 bytes)
and `.p7s` (1085 bytes); this VM omitted the production custom firmware path.
Do not promote the result to firmware availability or physical Wi-Fi PASS.

Private evidence: `rog5-a01-radio-qemu-20260906.hXRbZPnh`, including harness,
VM archive, command, log, input identities and result. Harness SHA-256
`a6a35e17b07a426761c72e4633562dc64e568eb5fc4a440313558670af5388fd`;
result `3f9c891cdd22e82f356d86438db1dc9e55759329586dffa014fb20e873b948c9`.
No production source/artifact modification, build, signing, admission or phone
contact. Full local CI was not repeated for private experiments/result notes.
All four jobs subsequently passed remote run **34017100368** for `52b24f66…`.

### A01 reusable wrapper pairing

Added `wrapper_composition` to the existing composition checker, extracting
the payload-pairing responsibility from retained private packaging practice.
It reuses the hash-pinned Android unpacker and compares complete command line,
kernel and recovery bytes. Boot-v3 magic/version/header size/reserved fields,
truncation and declared lengths are checked; malformed/mismatched fixtures
fail in normal Python and `-O`. The initial new test failed because this
shared entry point did not exist; subsequent header-size/reserved-field tests
exposed two omissions in the new helper before they were corrected. This is
new A01 coverage, not a claim that a deployed wrapper was broken.

Retained V6 boot `32704e44…`, ASUS kernel `838425a8…`, recovery `e2aa0c64…`
and original template `1636cf80…` were hash-verified before comparison.
Full template command line (including the 300 s recovery-stage timeout)
matches: **PASS 0.735 s**. Result explicitly says `avb_verified=false` and
`release_qualified=false`; nested signed-bundle plan/admission are separate.
No signing, claim consumption, kernel build or phone contact.

All **16 composition tests** pass normally and optimized; active tier
**PASS 18.146 s**, private `a01-wrapper-active.dJXYDpai.log` in the existing V6
directory. This helper still needs combined A01 runner integration; full CI
will run at that coherent checkpoint. Existing result notes were consolidated
in current-state rather than creating another ledger.

### A01 sealed verifier and plan consumer

Extended the existing composition checker with an isolated invocation of the
verifier from a caller-authenticated recovery archive. It requires exact
runtime metadata and manifest identity before extracting through the existing
safe extractor. Only the fixed selected bundle is copied into private tmpfs;
network/host devices/capabilities are absent. No source-built verifier is
substituted, and no claim, signing key or target executor is called.

The plan consumer requires the complete 12-field v1 record, rejecting duplicate,
unknown/missing fields, malformed framing, changed bundle/hash/filenames and
incorrect command hash. New tests first failed because this shared consumer
did not exist; they are additional A01 coverage, not a historical-root-cause claim.
All **18 composition tests** pass normally and with `-O`; active tier
**PASS 18.124 s**, `a01-plan-active.7WYVj6fk.log` in the V6 private directory.

Against hash-verified V6 recovery `e2aa0c64…`, the actual sealed verifier
accepted manifest `8beb3ab7…` and emitted the expected plan in **2.216 s**.
Two disposable corrupted copies were rejected: changed `manifest.sig`
(invalid signature, **0.243 s**) and changed `Image` (kernel SHA-256 mismatch,
**0.920 s**). Recovery/target timeouts remain 900/600 s in the signed target
plan, distinct from the wrapper's 300-second recovery-stage timeout.
This still does not complete A01: AVB, target/root identity, timing and module/
firmware checks must be connected in one executable row. Full CI/publication
remain deferred to that coherent integration checkpoint. No phone contact.

### A01 executable integration checkpoint

At HEAD `52b24f66d29e2371b6843facc799787fe0001d47`, preserved the dirty
composition work and connected `check-release-composition.py` to the existing
A01 manifest and `rog5-dev`. The manifest defines the required check set once.
The entry authenticates the canonical wrapper identity before executing sealed
code, verifies AVB integrity, runs the sealed bundle verifier, and compares the
supplied kernel/DTB/archive with the authenticated embedded target. Offline
inspection of retained consumed artifacts does not consume or reuse execution.

New regressions first exposed an empty A01 command and acceptance of a zero-exit
substitute without proof. The dispatcher now rejects missing/partial proof,
wrong source/candidate/runner/artifact identities and deadline overrun. All
28 dispatcher tests pass in normal and optimized Python. No criteria were
removed to manufacture a PASS.

The actual five-role V6 receipt run completed **BLOCKED in 4.074 s** (inner
3.924 s): wrapper, signed target and archive PASS; root runtime, module load,
firmware and timing/transport NOT RUN. Source/worktree digest remained
`a8d98a2b71e58293d820bba8471bd0a645a8ec06d7f869260bdfa8637137b6ae` throughout.
Private `rog5-a01-integration-20260906.2RLL82x8` retains the receipt, command,
AVB log and proof. This is an honest incomplete A01, not release qualification.
Full local/exact-head CI still covers published `52b24f66…`, not these edits;
the next full run belongs to the coherent frozen integration checkpoint.

The bounded source-reuse investigation is finished in `docs/kernel-port.md`.
The Denial release-page recheck still lists the pinned v0.3.1 as an x86-64
prerelease explicitly excluding AArch64 binaries. No new checkout, framework,
charging control, phone contact or boot followed from the references. Resume
the remaining A01 dynamic checks rather than repeating that investigation.

### A01 combined exact-kernel runtime and core modules

Integrated the existing Arch runtime-preparation driver with core module
insertion in one isolated QEMU run. It uses exact V6 kernel `bdceaa51…`, target
`7703f398…`, root `06cc805b…`, and the same authenticated wrapper/bundle as the
preceding A01 entry. No phone DTB, radio activator, network or physical block
passthrough; the virtual root disk is read-only, mounted ro/noload, with a
disposable tmpfs upper. No fresh kernel, signing or execution claim.

The first fixture build failed before QEMU in **34.695 s** because its archive
builder refuses duplicate mountpoint/init members. Captured in private
`rog5-a01-runtime-20260906.t3csw195`. A focused regression reproduced the exact
exception before correcting only the disposable fixture's member reuse. Input
archive members remain unchanged. Additional tests reject absent/duplicate
completion markers, echoed markers, module failures and nonzero VM status.

The corrected integrated run in private `rog5-a01-runtime-20260906.31qo8yc5`
completed **BLOCKED 82.353 s**, within the unchanged 120 s deadline. Wrapper,
signed target, archive, root runtime and core module-load checks PASS. The VM
took **18.016 s**: all 19 modules reached live state; actual Arch systemd and
sshd executed, generated units verified, key-only policy and the exact nested
exitrd parse passed. No matched panic/oops/warning/symbol/BTF failure. Root
pre/post SHA-256 is unchanged, with source/worktree digest
`c899fc321f12676ac452b5569cfda9c985416c07e36382578a266dc0d50c96a6`
stable for the run. These passes do not imply physical driver probing.

All **20** composition regressions pass normally and optimized (optimized
0.146 s). Firmware and timing/transport remain NOT RUN in combined A01; the
runtime preparation still uses its explicitly labeled unit-generation timing
fixture. Server radio extras cannot inherit the rescue core-module PASS.
Next finish these composition gaps before the frozen full-CI/publication
checkpoint. No candidate, phone contact or alteration of installed recovery.

After this offline run, the active tier passed in **18.479 s** (private V6
`a01-runtime-active.dF9UsOjE.log`). A separate read-only, identity-gated pinned
SSH check passed H02 in **1.209 s**, private V6
`a01-runtime-health.ZmYBiGyT/result`: same boot `64e209e2…`, uptime 14795.36 s,
all expected deployed files matching, Full/Good 100%, 29.7°C, 8.613 V,
zero current, USB online and original watchdog ACK. Wi-Fi remains inactive.
No service mutation/reboot; Full-state zero current does not qualify H03.

### A01 complete embedded-rescue composition

Completed firmware and timing/transport integration without rebuilding target
artifacts. The existing builder's firmware-tree digest and loader's inventory
count remain the only accepted source; all 29 file hashes and safe metadata
are checked, including intentionally empty adsp.b26. QEMU executes the sealed
loader's firmware-staging section and verifies firmware_class's search path.
No physical remoteproc, thermal, charging or radio control is exercised.

The signed manifest/plan/wrapper values are checked against the existing host
capture lattice: recovery 300 s, target 600 s, rollback 900 s, capture 1380 s.
Duplicate or mismatched command-line values and sender/receiver endpoints fail
closed. The sealed target timeout parser executes in BusyBox; generated units
use the actual 900 s value and the optional observer receives 870 s. The sealed
publish_stage function emits a real VM-boot-bound record; the existing host
consumer accepts its exact runtime/PASS/composition frame. No watchdog timer is
shortened or allowed to fire in this composition test; C02 remains separate.

New tests initially failed because the missing integrated checks had no entry
points. All **23** composition tests now pass normally (**0.173 s**) and with
`-O` (**0.167 s**); all **28** dispatcher tests PASS (**1.140 s**). Corrupt
firmware/metadata/count, malformed budgets and wrong transport endpoints are
covered. The dispatcher requires every check and exact artifact/source proof,
never just zero exit. Its successful next-action text now reflects completion.

Actual combined A01 **PASS 83.502 s** (inner 83.300 s, VM **18.720 s**) within
the unchanged 120 s deadline. Private `rog5-a01-complete-20260906.vb4tjcnd`
retains the five-role receipt, invocation, AVB/runtime logs and final proof SHA
`6aaf1e7960f2ed8eec3008ae8bc9698b90131a4ba3361085300ccc2c6fc8b38e`.
All seven checks passed together against exact V6 artifacts; root hash
`06cc805b…` and other input hashes remained unchanged. Source `52b24f66…`,
worktree digest `f2e723cee42ebfa523b07d197cdb0e4ab61e28fa4a406a7b70d40246af4e94e7`
was stable during the run. Subsequent edits update result/docs and dispatcher
next-action wording only; this retained dirty-source proof is not silently
relabelled as a clean final server release.

Selector-backed external bundles and auxiliary server radio/firmware closure
remain BLOCKED. No rescue PASS is imported into that distinct composition.
Full local/exact-head CI follow at this frozen publication checkpoint. No
phone contact, claim consumption, signing, build or installed-state mutation.

Frozen full local CI **PASS 496.219 s**; previous published checker checkpoint
was 487.855 s. Private V6 `a01-complete-ci.J0gx4tEt.log` retains the full run.
Both Python modes also pass all 28 dispatcher tests (1.138/1.128 s). No code
changed during full CI; only these result notes follow it. Publication will
use the existing branch/draft PR and exact-head plus merge CI. No claim that
GitHub CI executes the private artifact test or qualifies the final server.

Publication completed: all four jobs (head-exact, merge-compat, qemu-system,
candidate-publication) PASS run **34020356108**, exact
`8ad3e64d1e87153c3d35a1a8d9c6f69ce117661f`. No candidate execution follows.

### Server A01 stale retained root and bounded read-only refresh

Continued the next mandatory composition check, not another source review.
The old retained P24 image `06cc805b…` has selector-v1 SHA
`650e09d6b17cc055cabde291d29602ba33cb2c487b4f0712455fcd2b6a0b4c63`.
Canonical selector-v2 is
`c15c77824e3cecf128288f2c273c6bd7f93825e837568c669d8288145541d904`.
Private `rog5-a01-selector-check-20260906.E1ZsYmmI` records **FAIL 0.773 s**
before QEMU: wrapper PASS, remaining composition NOT RUN. R2 stale host
composition is the demonstrated defect; no production kernel change follows.

The new preflight reads only `/boot/rog5-linux/selector` with read-only debugfs,
checks bounded regular root-owned single-link metadata, checks input stability
and compares its digest with the canonical record. Captured obsolete selector,
absent/symlinked/oversize metadata and no-write regressions cover the refusal.
All 25 tests PASS normal/optimized (**0.334/0.328 s** wall); active tier
PASS **18.920 s**. No full CI repeated or publication claimed for these edits.

Separate exact-topology/pinned-SSH readouts in private
`rog5-selector-live-read-20260906.gc98jxna` and
`rog5-selector-live-hashes-20260906.pxh86g01` prove that the live P24 is
RO/norecovery at `/.rog5/root-ro`, contains the expected selector-v2, and matches
the retained primary/fallback manifest, signature, kernel, DTB and archive
hashes. The mismatch is in the old host snapshot, not the installed selector.

A replacement full P24 capture was bounded to RO reads, the exact existing
boot/UFS node/size, periodic power/identity checks, host disk caps and deadlines.
The first attempt, private `rog5-current-p24-snapshot-20260906.ymrNnRgr`, failed
before any bytes because target Python was unavailable (R3); its zero-byte
archive and failed script are preserved. Subsequent explicit installed-tool
checks established Bash/dd/gzip/sha256sum/timeout/blockdev/stat compatibility
and actual block identity **259:59**, not an assumed major/minor.

The shell implementation in private
`rog5-current-p24-snapshot-20260906.rH76Zs5n` passed its exact target gate and
codec preflight, then captured **407,339,008 compressed bytes** before SSH
reported `Timeout, server 10.77.0.2 not responding.` This is **FAIL**, no source
completion/hash match, no decompressed root and no automatic stream retry.
The last periodic sample at 44.371 s was safe (29.7°C, 8.610 V). The new script
and partial data are retained; the old verified snapshot is unchanged.

Independent post-failure pinned SSH PASS **0.209 s** on unchanged boot
`64e209e2-0efe-40c6-8396-29f3e481f0ff`, 29.7°C, 8.611 V, USB online and P24 RO.
No dd/gzip snapshot reader remained. Kernel tail ends at the existing
900-second watchdog ACK with no new error there; a tail alone cannot exclude
all faults. USB stayed on its anchored interface. The stream's short SSH
liveness budget is a hypothesis, not a proven NCM/kernel cause; healthy
concurrent sessions must remain part of the next discriminating observation.
No boot, signature/claim operation, service restart, charging control, phone
write, old-evidence deletion or candidate reuse occurred. Server A01 remains
incomplete until the exact paired root and external signed-bundle closure pass.

### Same-boot bulk-transfer boundary investigation

No new candidate, boot, storage write, daemon restart or kernel change.
Invoked explicit project-local systematic debugging after the second failed
snapshot at the SSH boundary. Its source-first comparison stopped further
unobserved snapshot attempts. The existing bounded tool-free Opus reviewer
exited with expired OAuth; no authentication bypass or credential disclosure.
Private `rog5-ssh-opus-review-20260906`-prefixed output retains that diagnostic.

| Discriminating observation | Result and private evidence |
|---|---|
| Same SSH settings; generated 2 GiB zeros through gzip, then 12 s idle | PASS 28.783 s, exact expanded zero bytes; `rog5-ssh-stream-diagnostic-20260906.r0boN8pA` |
| 128 MiB P24 ranges, each compared with a separate source-range SHA | First 38 ranges (4.75 GiB) verified in 99.067 s; range 38 failed after 13,336,576 compressed bytes; `rog5-current-p24-chunks-20260906.QHaOsqhy` |
| Instrumented read of that same range 38 | Completed in 3.663 s, host range SHA `f290ec1ae3df37ad8155825349b50d204f187f19fd6e660cfaa153c659967b65`; no independent hash completion is claimed for this diagnostic; `rog5-ssh-range-trace-20260906`-prefixed evidence |
| Instrumented 2 GiB physical prefix, original SSH limits | Supervisor stopped it at 25.398 s because parallel health exited 255; stderr was not retained by this first tracer, an explicit evidence gap; `rog5-ssh-bulk-trace-20260906.mQu9Hq71` |
| Same bulk probe, only diagnostic ServerAliveCountMax 2 → 8 | Supervisor again stopped it, at 34.988 s. Retained health stderr explicitly says TCP connection timed out; `rog5-ssh-budget-trace-20260906.zMyLFII3` |

The last two stream logs say killed by signal 15: those are supervisor-aborted
traces, not independent stream-alive expiry. ConnectTimeout remained 3 s and
the fixed overall probe bound remained unchanged. No diagnostic relaxation is
promoted into lifecycle or acceptance code. OpenSSH documents that encrypted
server-alive replies are distinct from connection establishment and TCP
keepalives ([manual](https://man.openbsd.org/ssh_config#ServerAliveCountMax)).

Both-end `ss -tinp` traces show retransmission, DSACK and reordering during
otherwise advancing bulk traffic. They do not localize packet loss to the host,
USB link or target kernel. A successful 12 s idle period rules out silence
alone; a successful same-range read argues against a consistently unreadable
sector. Short-connection failures under load are now directly evidenced.
Server settings are ClientAliveInterval=0 and ChannelTimeout=none. SSH session
events are under `_COMM=sshd-session`, not `journalctl -u sshd`; the latter's
empty result must not be called absent logging. The target observed connection
reset by the client after earlier stream-alive expiry.

All readers/tracers are terminal. Fresh exact same-boot gate passed in
0.189 s, 29.7°C, 8.610 V, USB online, P24 still RO. Kernel tail still ends at
the old watchdog ACK; no new matched fault there, not proof of no kernel fault.
Target TCP listen-overflow/drop and checksum-error counters are zero; host
cumulative counters lack a per-experiment baseline and are not attributed to
this incident. No complete new root image exists. Preserve all partials,
original scripts and original root. Next obtain packet-level direction/loss
evidence during the known load-dependent condition, not another guessed
kernel or an uninstrumented complete snapshot. Headless acceptance remains
active and incomplete; Opus authentication is not treated as the goal blocker.

### Target packet evidence and reproduced NCM timer defect

Prepared tcpdump 4.99.6/libpcap 1.10.6 from signature-verified Alpine 3.24
packages using the retained ARM64 verifier container. Direct ARM64 container
execution failed because binfmt was unavailable; explicit qemu-aarch64-static
ran apk with package scripts disabled. No privileged host change or binfmt
installation. The 6.7 MiB dependency set was staged only into verified tmpfs
with no active swap, package SHA
`90f2536c9cea0df1079a03b51e65e7baa22f71b795b8a8e10c7a1114fe7c504a`.
Deployment/version check completed in **0.416 s**. Not a persistent package
installation, phone-storage write, candidate or modification of sealed inputs.

Private `rog5-tcp-observer-20260906.yP6qPYSw` retains the package, deployment,
90-second process record, filtered packets and exact Image disassembly.
The non-promiscuous filter selected only SYN/FIN/RST between the two exact USB
addresses on TCP/22, with a 4096-record cap; capture readiness preceded load.
It terminated with **112 records / zero kernel capture drops**, PCAP 9340 bytes,
SHA `1453d09c76863f07e5997479d6376a8adefc065f3f06a5ab03e8e42d6227dbff`.
The test stream was supervisor-aborted at **19.618 s** after a parallel TCP
connect timeout. Host port 54918's SYNs reached the target; the target generated
SYN-ACKs immediately and retransmitted them. Resets arrived in a tight later
burst. This rules against absent sshd listening for that request, but outgoing
packet taps occur before physical transmission and do not prove host receipt.
Target qdisc had no drops and 144,359 cumulative requeues; host TCP checksum
errors were zero. Neither cumulative statistic independently establishes cause.

Inspection found the exact upstream NCM timer defect: `ncm_tx_timeout` ignores
`NETDEV_TX_BUSY`, while `u_ether` returns BUSY when transmit requests are absent.
No timer retry then flushes the pending NTB. The signed accepted Image
`bdceaa51…`, located using same-boot symbol offsets without publishing raw kernel
addresses, contains `blr x8` followed by unconditional zero return: the missing
return handling is present in the accepted bytes, not only repository source.
Independent upstream reports are linked from `docs/kernel-port.md`.

Added a compiled actual-callback regression **before** the backport. The old
callback demonstrably strands the reply after its first BUSY result; the new
patch-dependent tests initially failed without the patch. Backport 0039 adds
only BUSY handling and timer rearm at the unchanged 300us interval. All three
tests PASS, including exact retained-source application, **0.196 s** normal and
**0.214 s** optimized wall time. Added to the existing active/full test list.
No active build source, image or module was changed; no signature, claim, boot,
phone update, hot-unload or threshold adjustment. Physical resolution remains
unproven until a fresh coherent kernel reproduces the same load scenario.

Active tier PASS **18.900 s** at this frozen source checkpoint; private observer
`active-tests.log` retains output. Full local CI **PASS 487.255 s**, including
the preserved stale-root selector correction (previous full run 496.219 s).
Private observer `full-ci.log` retains the run. No source edits interrupted it;
only result/documentation updates follow. No private captures or binaries are
staged for publication; exact-head publication is not yet claimed.

The requested bounded external-source recheck reused the existing kernel-port
assessment and confirmed all four pins unchanged. No new checkout, source
import, charging-control change or phone contact. The current-kernel baseline
is also retained: source `359318de534f196c1281de7195fbf5868c6f7333`, tree
`8528fcd29e4ad19cf944f79c2ebb3438feee5e0b`, config `889d836f…` and accepted
Image `bdceaa51…`. Its Git object exists in the retained UFS source repository;
the removed temporary build path does not mean the source must be recreated.
The display build is not substituted. Resume acceptance, not an architecture
review; A01 still needs a complete current root after transport correction.

Resumed the executable acceptance loop with `rog5-dev accept quick`:
**PASS 23.153 s** (A02 10.660 s, B01 3.887 s, G01 7.360 s, G02 1.217 s).
Private observer `acceptance-quick` retains the exact dirty-source record and
matrix. No historical release evidence was imported; A01 and unselected rows
remain NOT RUN in this run and `qualified=false`. Only result notes follow it.

### NCM kernel publication and exact-source build

Published **56fcdc8667fd7d4b3c8f8b924a96242d937e0148** normally to the existing
branch/PR; all four publication CI jobs **PASS**, run **34023915775**.
The draft PR now distinguishes current headless acceptance from its historical
consolidation results. No private payloads or credentials entered Git.

Private `rog5-ncm-kernel-20260906.FwMH1o8D` contains the source worktree,
`build.sh`, `launch.sh`, baseline config, preflight logs and active `build-a.log`.
Source **601c84c0c3c42bec6da377ce38564a76d357f90a**, tree
`dc8fb2613dea2594830e1a2ac70e816925bd37b6`, adds only patch 0039 above
retained `34318ad1…`. The latter's UFS core SHA `f7bcbad6…` is exactly the
source already used for the accepted external high-speed module; its integration
is not a new storage-policy experiment. Config remains byte-identical
`889d836f…`; no display, charging-control or capacity-unit patch is included.

The initial container preflight failed before output creation because the
retained source is itself a worktree whose common Git metadata lives elsewhere.
Mounting the resolved common Git directory read-only fixes that host composition
error. The next preflight verifies unchanged olddefconfig output, source/tree,
UFS source, Clang 18.1.3, exact-state output locking and the new kernel release
`7.1.4-g601c84c0c3c4`. The actual-source NCM regression passes all three tests
in **0.249 s**. No new full suite was rerun on unchanged production source.

Build A is running in pinned container `bdb4bbda…`, four jobs, 6 GiB memory
cap, no network, read-only source and a 7200 s process bound. The first compile
continues its prepared exact-state config output; there is no retained kernel
object-cache hit. Source plus measured 5.5 GiB prior full-output scale leaves
room for clean twins (27 GiB free after source preparation); recheck headroom
before B and deployment. Do not edit this running recipe/source or call an
observation timeout terminal. No twin/build PASS, candidate or admission yet.

Fresh same-boot read-only health passes **0.368 s**, Full/Good 100%, 29.7°C,
8.609 V, USB online, P24 RO and no failed systemd units. The installed NCM timer
is unchanged until a separately verified fresh RAM release is executed.

### External-root A01 composition implementation during compilation

Demonstrated gap: even a coherent selector-backed server root had no path
through A01; only embedded RAM bundles were supported. Added fail-first tests
for paired primary/fallback verification and stale-selector refusal, then a
bounded fixed-store `debugfs` reader. Neither a host bundle directory nor a
repository-built verifier can substitute for retained-root bytes and the
verifier authenticated in recovery. Parent/file symlinks, unsafe modes/owners,
hardlinks, oversize/truncated reads, extra/mixed entries, altered manifests,
signature refusal and source changes fail. Child file-size/time bounds cover
actual reads; image metadata is checked across extraction and final runtime.

The initial fake-directory parser expected the wrong slash-field count. Actual
read-only `debugfs ls -p` output supplied the eight-field fixture, including
empty directory-size fields and blank lines. The private component invocation
also initially lacked the existing host-module import path and failed before
artifact access; its corrected invocation uses the script directory explicitly.
No phone cycle was used to discover either host issue.

All **28** composition regressions PASS normally and optimized (optimized
**0.524 s**); active tier **PASS 31.445 s**, concurrent with the four-job build.
Actual component **PASS 4.913 s**: read all five V11 files from retained P24,
verify manifest `a684bad1…`, signature and Image/DTB/archive with the verifier
from authenticated V6 recovery. Private kernel-build evidence retains
`external-root-component.py`, `.log`, `.json` and `external-active.log`.
This is explicitly NOT A01: the old selector is still invalid for the current
release, and no current paired-root or server-radio proof is claimed. Kernel
build inputs were not modified. No phone contact, signing or admission occurred here.

The frozen full local CI **FAIL 429.335 s** (`external-full-ci.log`): composition
checks passed, but the unchanged lifecycle suite timed out at 15 s in the
`mismatch` and `malformed` bad-progress subcases. Exact original focused replay
then **PASS 3.409 s**, including all four subcases. Build contention/race remains
a hypothesis, not a proven root cause. A diagnostic wrapper reproduced no
timeouts but invalidated four source/guard assertions by replacing the runner;
that run is not valid CI evidence. Preserve all logs, leave production deadlines
unchanged, and resolve the targeted failure before publishing this checkpoint.
The published NCM checkpoint's four GitHub jobs remain PASS; that result does
not cover this dirty external-root implementation.

### NCM build-A component checkpoint

Build A **PASS 1258.793 s**, 3.0 GiB output, exact config `889d836f…`, Image
`81fdcf8e600e09704e544f2add0a875276d598c3b21d8528807f398edda530c0`,
Image.gz `796695512315f13022625fdc818f4a363844cec0d09788a9cad77ed991ad7db8`.
Actual ARM64 object disassembly confirms BUSY-only timer rearm and return 1;
success/no-netdev returns 0. All 19 modules match accepted allocated code/data
and relocations; `.modinfo` differs only in expected release/intree metadata.
Independent build B passed preflight and is still running in a distinct output
directory; no source/recipe change or twin-reproducibility result is claimed.

Existing initramfs tooling staged an unsigned component archive
`01245c2dcfa7c2e0bee7b05b37b4f0266980b40ce653035ea6abf0b32e72f19a`,
preserving the accepted pdr_interface-only BTF packaging exception. Isolated
Arch/QEMU component **PASS 100.969 s** (VM runtime **31.112 s**), all 19 exact
module loads, sealed firmware preparation and runtime stage parser. Source was
unchanged across the run; kernel/archive/root hashes agree before and after.
The VM had no networking or phone passthrough and used the read-only old root
with a tmpfs upper. `vm-a/result.json` explicitly records `a01_qualified=false`
and `release_qualified=false`: no current-root selector, physical NCM, radio
activation or watchdog expiry proof is substituted by this component pass.

Build B subsequently **PASS 1248.796 s**. `kernel-twins.json` compares all 25
kernel/config/ABI/release/module files, byte-identical with clean exact source
in **0.986 s**. Both raw outputs occupy 3.0 GiB. Target B was independently
packaged through the same builder and accepted BTF exception; its archive hash
is identical to A (`01245c2d…`). About 21 GiB host headroom remains. These are
unsigned offline artifacts, not a new candidate or reuse of consumed V6.

Fresh pinned same-rescue gate **PASS 0.390 s**, Full/Good 100%, 29.7°C,
8.608 V, USB online, P24 RO and no failed systemd units (`health-b.json`).
No phone reboot, charging control or persistent storage write occurred.

Corrected diagnostic invocation preserves original source/guard assertions and
traces only offline Fixture.run children. All 89 cases **PASS 98.408 s** with
no timeout. The original uninstrumented suite then **PASS 97.600 s** (test body
92.762 s). These replays do not establish why the initial full-CI run timed out.
The remaining original CI tests were run sequentially from the repository's
existing list with a disk-backed short TMPDIR, without rerunning the earlier
passing prefix: **110 tests / 228.163 s PASS**. `ci-remainder/result.json` records the exact suffix, durations,
runner hash and unchanged production digest. This completes local coverage but
does not relabel the original **FAIL 429.335 s** run as PASS. Keep the original
failure and require exact-head/merge CI before candidate admission/publication
is accepted. No production deadline or lifecycle behavior was changed.

### Published composition and prepared NCM rescue V7

Published **04ac38576edef855d3e4bab2aef253b6f390f5d3**, normal push to the
existing draft PR. All four jobs PASS run **34026414183**. This fresh remote
result covers the actual implementation head; it does not erase the retained
local timeout. Nine exact-archive watchdog cases on the new kernel PASS
**131.517 s**, including no/stale ACK, P2-only, unexecutable helper, userspace
hang, failed-init panic and failed FD arm. Real retained Arch/systemd/SSH
healthy/stale cases PASS **113.439 s**, same root hash before/after. These are
offline component proofs, not R01 physical recovery.

One private JSON recipe now names **headless-acceptance-rescue-v7**. Existing
runtime signer, recovery builder and boot-v3 repacker produced identical twins
in **13.711 s**; the ASUS kernel was reused. No phone contact, new claim,
admission or boot was performed by packaging. Artifact evidence remains in
the existing private `rog5-ncm-kernel-20260906.FwMH1o8D` directory:

- manifest: `eca02756542e0af41c0ef45479fdcce9cad0e6f06a13ae3253fae139a8cfb18f`
- boot: `52b68f4e5f3a74deaddb07f0efcf21848604eb4177ef2d0fe789b6a05c630f4c`
- recovery: `2069fa20b8ebcde4720eae4514101b1d445d1cf4b0c6086e1dbcfc54e6a59f1d`
- target archive remains `01245c2dcfa7c2e0bee7b05b37b4f0266980b40ce653035ea6abf0b32e72f19a`.

Generated only the new literal canonical registry row from the signed package
result, preserving historical rows and all execution/claim code. Claim (19),
admission (33) and stage-receiver (17) tests PASS. All three live claim/entered/
anchor paths are absent; a registry template is not an issued claim. Active
tier PASS **18.961 s**.

Combined V7 rescue A01 **PASS 82.709 s**, all seven required checks with one
source/artifact-bound report (`a01-v7/result.json`); VM runtime **19.195 s**.
Actual wrapper, AVB, sealed verifier/manifest, target archive, 19 modules,
firmware and timing/stage protocol agree. Its old retained root is valid only
for this embedded rescue runtime test, not the current selector-backed server.
Server A01 still needs the complete current snapshot. Physical NCM correction
is unproven. Next: finish reviewed live coordinator/preflight, then one fresh
RAM attempt with parallel SSH and bulk evidence. Preserve consumed V6 and the
already signed V7 bytes; do not rebuild or re-sign merely to continue.

### V7 physical NCM and current-root checkpoint

Frozen source **69a6806188c9957b1bca59206acf92d39746e4f1** passed all four
publication jobs in **34027214673**. Eight private adaptor checks PASS 0.406 s;
exact sealed exitrd syntax/action-only delta and same-V6 inspection PASS 0.738 s.
The existing teardown, modified only in RAM to request bootloader, reached exact
slot-B fastboot in **10.243 s**, 8.622 V and battery-soc-ok yes. No flash.

V7 was issued/consumed once and accepted by fastboot in **12.727 s**;
authenticated readiness **57.513 s**. Boot
`120b2938-b143-4c17-ade4-69f4304c5802`, kernel `7.1.4-g601c84c0c3c4`.
Manifest/boot/recovery/archive identities are the verified preparation hashes
above. Private coordinator/capture/evidence remains in the existing
`rog5-ncm-kernel-20260906.FwMH1o8D` directory. Never retry this candidate.

Read-only `bulk-r1` **PASS 125.505 s**: 8,589,934,592 bytes, SHA-256
`ac1e0fe9ae8aed60ab63cde411a73358ed5a86b7b504e59b4278fb217fb0a6aa`,
independent source/host hashes; 39 parallel pinned SSH/power/RO checks, maximum
0.250 s. Source deadline 180 s, host 210 s, health 15 s; existing SSH keepalives
unchanged. Private host decode tests reject truncation and wrong lengths.

Complete `snapshot-r1` **PASS 386.132 s**: 34,359,717,888 bytes, SHA-256
`e1692971646809ff412363014d69a363aa543336a715e918ec0cc978cafa36c6`,
independently hashed on phone and host. 118 concurrent pinned SSH/power/RO
checks, maximum 0.501 s. Target 550 s/host 580 s deadlines unchanged. Direct
sparse decoding avoids a second compressed copy: 4,081,041,408 bytes allocated
on host, against an 8 GiB bound and 7 GiB reserve after a 20 GiB initial gate.
The completed private image is 0400. Previous partial snapshots remain intact.
No phone-storage mutation, hot-unload or additional boot occurred.

Temperature across reads 29.8–29.9°C, Good health and USB online. Deployed
watchdog acknowledged current-boot P2/SSH at **902.552 s**; kernel-log prefix
was preserved. Wi-Fi stayed inactive. These bounded passes support the NCM
timer fix; they are not a combined soak, H03 regulation or R01 failure test.

Capture **FAIL 1380.577 s**, independently of successful target checks:
`[Errno 19] No such device` was recorded during recovery → absent, before any
target frame. Exact exception phase was not retained. Later same-boot stages
reached switch-root PASS and sshd running, but the receiver intentionally keeps
its failed latch. Four owned cleanup operations (route/firewall/profile/address)
PASS; final pinned read confirms the same boot at uptime **1380.79 s**, 29.9°C,
8.599 V and zero current. All coordinator/read processes are terminal.

The sanitized `rescue-pretarget-enodev.json` fixture replays this host observation
and proves later target readiness cannot erase the FAIL. All **18 receiver
tests PASS 0.115 s wall**. No production guard is relaxed: determine the exact
discovery/route/bind phase offline before proposing a narrowly scoped host fix.
Do not rebuild the kernel or consume a phone cycle to test a host classifier.

Resumed server A01 against the new paired root: **BLOCKED 96.626 s**.
Wrapper, signed primary/fallback, archive, actual root handover and timing/
transport compatibility PASS; the root remained unchanged. Extra radio module
and firmware proof remains NOT RUN. Its VM powered down cleanly at 12.920 s.
That is the next mandatory offline integration task, not another source-review
or hardware admission. The server release uses its own accepted kernel; no
cross-release aggregation with V7's core-only module PASS is allowed.

Checkpoint changes are documentation plus the retained host-observation replay,
not production code. Active tier **PASS 19.075 s** (log creation-to-final-write
interval); `git diff --check` PASS. No repeated kernel build or local full suite.
Classify the new host observation under **R7**, with its exact exception phase
still unproven; keep H01 FAIL rather than changing admission on that assumption.

### Server radio firmware composition

Continuation from clean **d7b8fe1e62ba17db70db98558102ec4eb469e205**; all four
publication jobs subsequently PASS **34029155854**. No new phone cycle, source
checkout, kernel/module build, firmware write or charging-policy change.

Concrete gap: A01 validated/staged the charging firmware but deliberately left
all server radio firmware NOT RUN. Added a bounded validator for the archive's
actual `radio-files.sha256`, exact WCN6855 hw1.1/regulatory inventory and safe
regular metadata. It rejects changed/missing/extra files, symlinks, wrong owner,
writable payloads, duplicate/traversal/unlisted manifest entries. The initial
regression failed before implementation. Normal and optimized composition
suites now pass **29 cases**. A separate missing/duplicate VM-marker regression
binds the result consumer to the actual firmware check, not an echoed claim.

Actual server A01 **BLOCKED 91.949 s**, now **firmware PASS** and only
`module_load` NOT RUN. The same virtual boot executes sealed BusyBox manifest
verification and retains `COMPOSITION_RADIO_FIRMWARE_PASS`; actual virtual
poweroff uptime **12.391 s**. Source was frozen for the run and current root
`e1692971…` was unchanged. Private `a01-server-radio-fw-r1` retains the whole
report, signed artifact identities and VM log. A later host-only marker-consumer
refactor passes normal/optimized regressions; this earlier proof is component
evidence, not a new coherent final-release result.

The private `radio-module-component-r1` subsequently **PASS 98.258 s**:
37 actual core/software radio modules inserted into the exact server kernel;
runtime runner **38.464 s**, virtual poweroff uptime **14.574 s**. The canonical
17-root list and complete nested module hash inventory were checked; host
`modprobe --show-depends` (no insertion) supplied the dependency order. Only the
same sealed bytes were inserted in network-isolated QEMU. Six radio firmware
files were placed in the disposable VM's default search path for regulatory
lookup; this is not the phone's activation path. No warning/oops/BTF/unknown-
symbol marker matched, and kernel/archive/root hashes matched before/after.
The first read-only inventory command omitted the host script import path and
failed before artifact execution; the corrected invocation is retained.

This component intentionally omits `rog5-pmic-pon-readonly`, `rog5-s12-ufs-vote`
and `rog5-wifi-activate`: they require exact ASUS board state and the activation
helper has a direct S12-provider dependency. Do not invent a successful hardware
initialization on QEMU or weaken their guards. The component explicitly records
`a01_qualified=false` and `release_qualified=false`; integrate software closure
and resolve the board-only ABI/refusal proof separately before claiming A01.

Frozen implementation: active tier **PASS 18.808 s**, full local CI **PASS
492.78 s**, `git diff --check` PASS. Full CI was run once; no wrapper/kernel
rebuild. Fresh pinned same-V7 health PASS **0.257 s** at uptime **2690.55 s**,
Good/USB online, 29.9°C, 8.599 V, zero current and no failed systemd units.
This remains component continuity, not H03 or a 60-minute combined soak.

### Integrated server software-radio closure

Continuation from `433960e72b6c714bb45cf05ddcd8c28ed3b702e0`; all four
publication jobs PASS run **34030476565**. Reused the pinned source assessment,
existing artifacts and preserved dirty work; no new checkout or phone contact.

Concrete A01 gap: the verified nested radio-module package was not included in
the integrated VM load test. The new reader validates bounded gzip/tar data,
exact inventory and hashes, owner/mode/type/path safety without extractall.
Metadata-only host modprobe resolves the canonical roots; full vermagic,
dependencies, exact overlapping core bytes and ELF identity are checked before
inserting the selected bytes into network-isolated QEMU. Firmware uses the same
sealed files, with production observation parameters for the two software
power-sequencing modules. No hardware endpoint or helper success is fabricated.

Initial missing-reader regression failed before implementation. Final **31 tests
PASS**, normal **0.262 s**, optimized **0.259 s**. Hostile cases include nested
symlinks/traversal, duplicate/extra entries, changed hashes, wrong metadata,
outside-host paths, install actions, ABI/dependency conflicts and deadlines.
A final empty-plan subcase failed against the new implementation, then passed
after explicit refusal; missing module proof cannot count as success.

Actual `a01-server-radio-integrated-r1`: **BLOCKED 107.115 s**,
runtime **PASS 38.797 s**, virtual poweroff **14.782 s**. All **37** selected
core/software radio loads and six radio firmware checks passed. Exact kernel,
archive and paired root hashes are unchanged. The only pending module entries
are the three PMIC/S12/activation helpers already described above. Overall A01
and release qualification remain false; this is not physical radio activation,
charging qualification or a retry of the consumed server candidate.
The empty-plan refusal was added after that actual-artifact run and covered by
focused regressions; do not call the earlier proof a complete final-release run.

Frozen code checkpoint: active **PASS 18.754 s** (log creation-to-final-write
interval), one full local CI **PASS 496.610 s**, `git diff --check` PASS.
Only these timing notes changed afterward. No wrapper/kernel build, large
checkout, phone contact or deployed-byte change. The remaining mandatory work
is board-helper ABI/refusal qualification, not importing another phone's code.

### Exact PMIC/S12 wrong-board refusal

Continuation from clean `f942b8ba168e2eb3fa064aea85d39f940524bb62`; all four
publication jobs PASS run **34031598540**. Fresh read-only pinned V7 gate PASS
**0.233 s**, boot unchanged, uptime **4840.49 s**, 29.9°C, 8.599 V, zero current,
Good/USB online, P24 RO and no failed systemd units. No phone mutation or boot.

New A01 component uses the archive's exact `module-once` binary with exact PMIC
and S12 module bytes, strict metadata/dependencies/vermagic and bounded host
metadata reads. QEMU inserts each once; it must return status 1 with exactly one
ENODEV line and no live module. The S12 command uses production `action=held-oem`
but rejects the non-ASUS board before any rail access. No fake DT or provider.

Initial missing-function/consumer regressions failed before implementation.
One test fixture incorrectly included an automatically added parent directory
in its regular-file mutation loop; fixed the fixture without weakening archive
validation. All **33** tests PASS, normal **0.316 s**, optimized **0.309 s**;
active tier **PASS 19.237 s**. The separate host metadata inspection initially
lacked the script import path and failed before execution; its corrected read
confirmed the exact module dependencies and full vermagic.

`a01-server-helper-refusal-r1`: **BLOCKED 109.741 s**, VM runtime **PASS
39.519 s**, virtual poweroff **15.520 s**. Both helper refusals PASS and all
37 software loads still PASS; source was frozen and all artifacts/root unchanged.
The S12 identity-check message appears once live and again in the final dmesg
replay at the same timestamp, not evidence of a second initialization.
Only `rog5-wifi-activate.ko` remains pending: it needs the actual S12 export.
The retained August activation VM used a substitute provider; that fixture is
not imported as proof of the production dependency. Earlier live core-module
notes also explicitly exclude radio BTF, so they cannot close this gap.

Keep this focused checkpoint uncommitted while resolving that last dependency;
full local/exact-head CI remains due at the coherent publication boundary.
No kernel rebuild, replacement module, candidate, control write or flash.

### Activation dependency: split proof prototype

Preserved the dirty two-helper checkpoint. Opus could not authenticate (expired
OAuth, zero API tokens); OX Alpha is absent from the installed OpenCode model
list. A bounded read-only Codex review under AGENTS.md recommended separately
proving the real static edge and exact consumer loader/BTF/refusal, not importing
the old shim-only receipt. Six already-completed agents were closed to release
slots; the new reviewer was also closed after completion. No source was deleted.

Independent exact-source audit used kernel commit
`1eea8970e87f1e1509fc12a85456f55570cfb4b1` from the retained S12 source metadata.
The unrelated build-source checkout does not contain that object. Module symbol
resolution precedes COMING/BTF validation; the BTF notifier has priority zero.
The verified archived config disables MODVERSIONS and BTF-mismatch allowance,
and enables DEBUG_INFO_BTF_MODULES. CRC checks would not prove this ABI.

The exact provider has a genuine GPL export, empty namespace and PREL32 export
relocation; the consumer has the matching strong undefined symbol, one CALL26
relocation, GPL license and explicit S12 module dependency. Provider split BTF
describes signed 32-bit `int(void)`; consumer DWARF agrees (prototyped declaration,
signed four-byte result, no parameters/variadic declaration). Its compact BTF
does not retain the external declaration, so names/vermagic alone are not used
as type proof. LLVM/pyelftools reject a provider DWARF R_AARCH64_NONE relocation;
provider type inspection instead uses its actual BTF/base through installed
libbpf, without suppressing that diagnostic or editing the artifact.
Private `helper-type-inspection-r2.json` retains the parsed data. This is static
metadata evidence, not a replacement for kernel BTF verification.

Added `tests/fixtures/rog5-a01-s12-shim.c`, explicitly test-only. It refuses ASUS
or non-QEMU boards, and kernels built without BTF checking or with mismatch
allowance.
Its sole export always returns EPERM and counts calls. A priority-minus-128
module notifier observes the consumer only after the accepted kernel's BTF
notifier; it requires actual BTF/base data and counts COMING/LIVE transitions.
This cannot claim a protected hold or replace the real provider in production.

`helper-fixture-build-r1` PASS **5.261 s**, 430 MiB private cache, using only
retained exact source headers/scripts and hash-verified config/vmlinux/symvers.
Those kit inputs were mounted read-only and remained unchanged. Fixture module
SHA `495e5560ceb1e8cc2649b661103fc662d617abb0fe700797184451b85751e927`;
matching full server vermagic. No production kernel/module or wrapper build.

`activation-split-runtime-r1` PASS **100.859 s**, VM runtime **40.014 s**,
virtual poweroff **15.569 s**. All 37 software loads and both real-provider/PMIC
refusals passed, followed by the unchanged exact consumer's one-call ENODEV.
Consumer BTF-COMING count **1**, validator calls **0**, consumer LIVE **0**;
consumer absent, fixture removed. Root/kernel/archive hashes and frozen source
were unchanged. The report explicitly sets A01/release qualification false:
real-provider successful initialization, dynamic real-pair binding, actual
validator/hold lifetime and hardware changeset/probes are NOT proved here.

Integrate the static-edge validation and fresh runtime component with focused
regressions before changing A01's pending result. Keep offline closure distinct
from the mandatory physical radio/server tests; no acceptance threshold was
relaxed. The existing 33 composition regressions still PASS **0.314 s**.
No new full suite/publication during this unfinished integration checkpoint.
Fresh pinned V7 health PASS **0.248 s**, uptime **7498.89 s**, 29.9°C, 8.597 V,
zero current, Good/USB online, P24 RO and no failed units. This is not H03 or soak.

### Integrated server A01 static edge and exact-consumer refusal

Continued from `f942b8ba168e2eb3fa064aea85d39f940524bb62`, preserving the dirty
two-helper checkpoint. Reused the completed pinned source-reuse assessment;
the Denial v0.3.1 release page still excludes AArch64 binary packages. No
downstream code, second framework or large source checkout was introduced.

The remaining A01 gap was offline proof of the exact activation dependency,
not a demonstrated production-driver fault (R2 composition evidence). The new
static reader checks the real ELF export/GPL/namespace/PREL32 and strong
undefined CALL26 edge, provider BTF/base signed-int32(void) and consumer DWARF.
It explicitly does not claim kernel BTF or dynamic pair initialization.
Missing inspection libraries block; malformed metadata fails, including under
optimized Python. A bounded independent code sidecar supplied the reader/tests;
integration review additionally reproduced and fixed acceptance of a nonnormal
DWARF calling convention. No unrelated worker writes or phone access occurred.

The existing QEMU-only fixture build is now bound to its source, module and kit
hashes. The actual retained vmlinux reproduces the accepted Image using the
reviewed arm64 objcopy flags; this check PASS **1.020 s**, without recompilation.
Output size is bounded. One explicit optional argument feeds A01 through both
`rog5-dev check-composition` and `rog5-dev accept`; no automatic fixture selection,
target packaging, signature substitution or execution authority is introduced.

Fail-first missing-function/marker tests and a nonnormal-calling-convention
regression failed before correction. Final focused results: **33** composition,
**3** fixture (including counter/error/cleanup cases), **63** static-edge tests
PASS normally/optimized. Optional mutations against the hash-verified actual
archive PASS **113 / 12.401 s** optimized. Active tier PASS **19.475 s**.
An initial timing invocation lacked `/usr/bin/time` and failed before the suite;
the retained corrected invocation uses Bash's builtin timer. A mistaken Python
invocation of the shell entry point likewise failed before execution; direct
`rog5-dev --help` passed. Neither is a kernel or physical execution failure.

`a01-server-split-integrated-r1`: **PASS 110.953 s**, VM **39.505 s**.
Frozen source worktree digest
`45163ab8586481ecf110151ca5c9009681ebee25c1d26cb2077c324ed414bcba`;
virtual boot `e45336c9-cf10-468c-91c7-9c64762d277d`. All seven required checks
passed in one run. The same 37 software loads, two separate actual board-helper
refusals and exact activator refusal passed. Its post-BTF COMING count is one,
validator calls/LIVE zero; fixture removed. Exact kernel/archive/DTB/wrapper
and paired root hashes are unchanged. Root is RO/noload with a tmpfs upper.

This closes the offline A01 gap only. Real-provider successful initialization,
dynamic actual-pair binding, hold lifetime, changeset/probes and physical radio
remain distinct mandatory live evidence. `release_qualified=false`; consumed
candidate state, slot A/V11 fallback, installed bytes and capture FAIL remain.
No phone contact, new build, admission, signing or boot. Only these result notes
changed after the frozen artifact run; no claim of final-release qualification.

Frozen local checkpoint: one full repository CI **PASS 498.829 s** versus
**496.610 s** previously; active **19.475 s** versus **18.754 s**. No complete
suite was repeated on unchanged code. `git diff --check` PASS. Only completion
timing/status notes changed after full CI. Existing kernel/wrapper/fixture
artifacts were reused; no source tree, private evidence or build data deleted.
Publication must use the existing branch/draft PR and exact-head/merge CI.

#### Publication-only libbpf compatibility correction

Published `aa59c3a34515c608eff2ed042e07e201e996f22e` normally. GitHub run
**34035655758** failed both head/merge at the new static module suite:
Ubuntu `libbpf1 1:1.3.0-2build2` has no exported `btf__new_split`. This is an R6
host-library assumption, not a production-kernel or phone failure. Raw failing
logs remain private; their generic killed worker messages are not the cause.

The fail-first missing-constructor regression reproduced the exact exception.
Use `btf__parse_raw_split` over a private anonymous memfd instead; unchanged BTF
bytes are copied before closure. The signature is also present in upstream
libbpf commit `20c0a9e3d7e7d4aeb283eae982543c9cacc29477`,
[`src/btf.h`](https://github.com/libbpf/libbpf/blob/20c0a9e3d7e7d4aeb283eae982543c9cacc29477/src/btf.h).
Actual package capability, not header availability, is the runtime proof.
No skipped checks, weaker types, dependency upgrade or phone change.

Host normal/optimized **64 PASS / 0.329/0.328 s**. Retained Ubuntu builder
`bdb4bbda…` with the exact CI libbpf package PASS **64 / 0.460 s** optimized;
real sealed-archive mutations PASS **114 / 12.734 s**, network disabled and
inputs read-only. Its first invocation lacked pyelftools and failed before
inspection; supplying the already-installed pure-Python package as a read-only
bind (no dependency download/image change) resolved that fixture prerequisite.
No QEMU/whole local-suite result is relabelled as rerun after this host-only
API correction; published A01 and full local CI remain evidence for `aa59c3a3`.
Run focused/active checks and new full exact-head/merge CI for the correction.
Corrected active tier PASS **19.626 s**; whitespace check PASS. Only this timing
note changed afterward; no additional full local run on the unchanged lifecycle.

### H03 read-only prerequisite follow-up

At clean source `8253a95a205e0b1014a54f2a9576af7778e67659`, GitHub run
**34036160719** completed successfully: head-exact, merge-compat,
candidate-publication and qemu-system. No full local suite was repeated for
this documentation-only follow-up. The bounded source-reuse assessment remains
complete; no additional checkout, framework, driver import or source rebuild.

The next mandatory acceptance question is whether the deployed power interface
can support predeclared H03 regulation criteria. Private
`h03-initial-health.json` and `h03-readonly-inventory.json` in the existing V7
evidence directory bind the readout to the exact serial, bundle, release and
boot UUID. Existing strict SSH, USB topology/route, safe-power and P24-RO gates
passed. Initial health took **0.254 s**, inventory **0.449 s**. Same V7 boot at
uptime **11055.69 s**, no failed systemd units; no running test was interrupted.

Battery: Full/100%, Good, 29.9°C, 8.596 V, zero reported current and
5,106,000 µAh charge counter. USB: online, 5.010 V/350 mA, 500 mA input limit;
Type-C device/sink, default power mode. Optional absent fields and the two
full/design-capacity ENODATA errors were recorded without aborting observation.
The retained SM8350 driver exposes no charge-control thresholds or setter;
their absence is expected for this interface, not proof of missing firmware
regulation. The source-checked 0038 capacity-unit regression PASS **3 tests /
0.204 s**, applying only to a temporary source copy. It does not fix or prove
charging policy and has not been deployed.

**H03 BLOCKED**, not PASS: configured regulation limits and validated
current-polarity/noise interpretation are still required before its unchanged
600-second observation. Full/100%, a reported 8.8 V maximum or one zero-current
sample cannot supply them. Next action: establish these criteria from the
exact supported firmware/interface and retained charging evidence, then run
the existing acceptance window. Carry the already-tested unit correction in
an ordinarily required coherent release; do not hot-unload charging modules
or issue a dedicated successor merely for optional telemetry. No control,
storage, slot, signature, admission or execution state changed.

#### Exact V7 capacity-module build and load checkpoint

Continued on `8253a95a…`, preserving the documentation changes above. The
question is whether existing patch 0038 can supply an ABI-compatible capacity
telemetry correction without rebuilding the accepted NCM/UFS kernel. Private
recipes and all failures remain in `rog5-battmgr-module-20260906.R8ZllyeH`.
No new production patch, source checkout, signing, admission or device boot.

The first external-module twins matched in **3.632/3.432 s** but intentionally
carry external-module metadata. The diskless VM loaded all 15 modules; its
first assertion wrongly expected the auxiliary driver directory to equal the
module name. Exact driver and auxiliary-bus source prove the required name is
`qcom_battmgr.pmic_glink_power_supply`. A source-checked assertion corrected this
fixture-only defect; its failed VM log remains, with corrected PASS **6.213 s**.
No production driver was changed to satisfy the fixture.

Normal in-tree module builds now reuse a private minimal kit, original
read-only `vmlinux.o`, config/BTF base and the full imported-symbol module set.
The initial copy failed before make on a dot-file spelling; the initial entered
make correctly refused absent `vmlinux.o` symbols. Neither failure was ignored.
The corrected invocation explicitly targets the accepted kernel ABI and checks
full resulting vermagic; no warning-only modpost, forced insertion or BTF bypass.
Accepted source, Image, config and module inputs were hash-checked unchanged.

Patched in-tree twins PASS **36.221/36.501 s** (whole preparation **74.463 s**),
SHA-256 `998c30ca68914f7bce0b55f37df6b769abf295031c82a173506b5038beee818b`.
Only the battery module is selected for later integration. Four incidental
dependency rebuilds differ from baseline; they are not substituted or qualified.
The final VM uses the original sealed dependency bytes plus only this corrected
module: **15 loads, enforced BTF, driver registration and empty battery-module
taint PASS 6.325 s**. Actual firmware callbacks/capacity readout and H03 remain
unproved. The accepted Image SHA is `81fdcf8e…`; no kernel/wrapper rebuild.

Active tier PASS **21.207 s**, versus **19.626 s** previously. Existing patch
regressions remain in that tier; no full local/GitHub rerun for unchanged
production code. New private allocation, including failed attempts, is
**1,244,295,168 bytes** (post-run allocation, not sampled peak). Nothing deleted.
Final pinned same-boot V7 health PASS **0.245 s**, uptime **12460.40 s**,
29.9°C, 8.595 V, zero current, Good/USB online, P24 RO and no failed units.
All experiment processes are terminal. No charging-policy or threshold write,
module reload on the phone, storage or execution-state change occurred.

#### Combined server source: rescue/server built-in dependency mismatch

Continued from `3cbbb350…`. Exact comparison of V7 `601c84c0c3c4` and the
accepted server source `1eea8970e87f` finds nine changed files: the RPMh readback
and ASUS S12 regulator support plus the NCM callback. V7's actual symvers lacks
`rpmh_read`; its public header also lacks the declaration. The server S12 helper
uses that function and the ASUS regulator point. A radio-only rebuild against
V7 would therefore not yield the required server. No phone cycle was consumed
to discover this R2 composition gap; the prior capacity-module result remains
valid only for its stated rescue kernel.

Fail-first tests reproduced ten rejected-input cases incorrectly crossing the
old builder prefixes. Both builders now require one unnamespaced GPL
`rpmh_read` export from vmlinux, before output creation or compilation. Missing,
renamed, module-owned, non-GPL and duplicate records refuse. The positive fixture
continues; this is a necessary dependency check, not complete ABI/board proof.
S12 tests **9 PASS**, normal/optimized **0.566/0.578 s**; activation **5 PASS /
0.234 s**. Existing RPMh **3**, ASUS selector **2**, capacity **3** and NCM **3**
regressions pass. No readback, regulator voltage or charging policy is changed.

New detached local source `f17befd4ef172cfb0ecbffd9e0af87122cfa66bc` starts at the
accepted server source and adds exactly the attributed 0038/0039 changes in two
files. Reverse patch checks pass; all other server source is unchanged. It uses
the existing object store, not a download or history rewrite. The separate
worktree preserves both accepted sources. Original config `889d836f…`, compiler
image `bdb4bbda…` and kernel build contract are reused. A new built-in kernel is
now justified by the demonstrated dependency, not by host-only failures.

Private preparation/controller: `rog5-v7-server-modules-20260906.Ibl4iPCz`.
Kernel preflight/build outcomes must be read from its process and result files,
not inferred from this preparation note. New outputs are locked and input-bound;
no copied mismatched cache, BTF bypass or weak modpost. Budget is 8 GiB for
sequential twin outputs plus a 3 GiB free-space reserve; no artifacts deleted.
There is no candidate, signing, admission, boot, staging or phone control write.

### Bounded workflow correction and H03 outcome resumption

Continued the dirty `3cbbb35014a0096adba6d6d8e46367aecf6dd367` checkpoint;
no reset, cleanup, restarted build, phone contact or competing goal.
Current state was 442 lines and is now about 130. Completed narratives already
exist in this dated incident; all 50 artifact/commit identity tokens in the
previous committed handoff remain here or in compact current state. No private
evidence or artifact was deleted. ROADMAP's obsolete completion/display-first
claim was corrected to the existing mandatory headless acceptance scope.

Project systematic-debugging is now 75 lines, explicit-only throughout:
focused correction for proven defects; bounded full investigation for repeated,
unexplained or cross-component failures; hypothesis reassessment rather than
automatic architecture verdict. Bounded labelled mitigations are permitted.
Upstream examples/creation records remain historical, not compulsory phases.
Both project skills validate; their scope was checked against proven BusyBox
failure, an unrelated unknown incident, two non-discriminating USB failures,
bounded mitigation and ordinary accepted-release reboot scenarios. No global
skills/configuration were changed. The global kernel skill's unconditional
devm/API preferences are generic guidance, not authority for a kernel rewrite;
there is no blocking global instruction conflict for this checkpoint.

Development now freezes the existing matrix as done, keeps unrelated work in
the existing backlog, batches meaningful publications and separates experimental
COMMIT/ambiguity from normal accepted-release boots and automatic fallback.
No runtime claim/selector mechanism or required publication gate changed.
Installed old boot B remains an actual qualification prerequisite.

H03 no longer blocks simply on unsupported writable charge-limit attributes.
The source-traced SM8350 firmware Full/current/counter/input path supports a
predeclared full-maintenance observation without claiming programmable CC/CV
settings. The 600 s / 10 s / 660 s contract now states polarity, neutral-current
band, zero negative-mean/counter-drift tolerance, counter plausibility, state,
power and timing conditions before any new measurements. No thresholds or
charging controls were written. Historical net-positive evidence supports
protocol interpretation, not a new release PASS.

The small Full-branch evaluator resumes mandatory H03 work. New tests first
failed because the implementation was absent, then all 33 acceptance tests
passed in normal/optimized Python: **2.117 / 1.934 s** wall. Missing data,
nonfinite/stale/late samples, unsupported states, unsafe readings, lost input,
net discharge and impossible counters refuse. Balanced small current with
unchanged counter reports maintenance, never net charging. The evaluator
always reports `h03_qualified=false`; actual supervised identity/firmware/H02
binding and a complete live series are still required. It adds no device runner,
automatic boot, arbitrary evidence import or general framework.

The already-running full local CI for the builder fix passed **589.229 s**
(previous 498.829 s). Later observer/workflow edits are not falsely labelled
part of that earlier frozen code check. First workflow active check was
**28.630 s** versus prior 21.207 s under different concurrent build load;
no speedup claim. Final active **PASS 28.337 s** includes the new H03 tests and
link checks. Final focused/active results belong in the same private
`rog5-v7-server-modules-20260906.Ibl4iPCz` directory.
The original bounded sequential kernel twins continue without input changes.
Neither clean twin outcome, final A01 nor physical H03 is inferred from progress.

### Combined build OOM recovery and identified capture-read race

At `1ad38a4ecba0bbdc29e17a0f1ba19bdcf312ea90`, all four GitHub jobs PASS
run 34040091326. The original build controller was authoritatively terminal:
A failed after **1600.559 s**, B had not compiled. Host journal identifies
CONSTRAINT_MEMCG and killed pahole at 3,115,168 KiB anonymous RSS, matching
the container's 3 GiB/no-swap cap. This is R6 host resource failure, not a
kernel/BTF source defect. The earlier successful build used 6 GiB.

Preserved failure/result/log, source, config, object tree and output lock.
The private resume controller changes only the runtime memory cap to 6 GiB
with no swap; exact-state checks and compiler inputs are unchanged. A resumed
in **176.750 s**, BTF and all 19 modules intact. Image
`ece47c7d52627d390bccdbcdab23295fe795820c66174d8de41cbc221cbac74e`,
vmlinux `bd7652a0d88c5809a2de87db985ccb0fe96288eebd4d8694ff3ca354d967b69e`,
symvers `b1856e308370c9b9678f5ae4d00d1b2d54d54e3dfd1c3e50b24a4962f5d0cd08`.
A allocates **2.9 GiB**; independent clean B is still running. No twin PASS
or assembled release is claimed. Recipes/logs remain in the same private
`rog5-v7-server-modules-20260906.Ibl4iPCz` directory.

Fresh exact V7 read-only health PASS **0.291 s**: same boot, uptime 15373.21 s,
29.9°C/8.594 V, zero current, Good/USB online, P24 RO, no failed units. No
radio activation, charging write, restart or persistent storage mutation.

H01 investigation reproduced a specific failing boundary offline: after exact
USB anchor resolution, removing the fixture device during idVendor read raises
ENODEV, then discovery confirms absence. Old code permanently marked it failed.
The new typed read exception plus phase logging distinguish only this expected
pre-target enumeration interruption. It neither resets lifetime nor closes the
listener, grants authority or retries execution. Unknown errors, unresolved
identity, network/binding failures and errors after target observation remain
fatal, even before the first frame; previous failure cannot be cleared.

The original V7 untagged exception fixture still yields FAIL. Its precise
historical syscall is unknowable from retained evidence; this correction does
not retroactively qualify V7. Receiver **21 tests PASS 0.343/0.287 s** normal/
optimized, including the fail-first actual filesystem-read/removal fixture.
The startup consumer rejects malformed or post-target pending events; its
seven new invalid subcases failed before correction. Consumer **19 tests PASS
0.362/0.418 s** normal/optimized. One mistyped consumer-test filename failed
before execution; corrected invocation is retained, not a test failure hidden
as success. One full local CI **PASS 630.297 s** for the frozen shared capture
changes; the unchanged earlier full suite was not rerun as a substitute.

The first derived module kit omitted `arch/arm64/include/generated`; the
existing Wi-Fi builder failed at `asm/types.h` before a module completed
(10.867 s). This is a separate demonstrated kit-composition omission, not a
kernel source defect. Added only the exact generated header subtree from A;
AArch64 preprocessing and subtree comparison PASS. Existing outputs/logs
remain. Corrected module A **PASS 223.630 s** with unchanged kernel/config/BTF
base; module B and activation twins are still running. No new kernel checkout,
kernel rebuild, source change, claim, signature or phone boot for that fix.

### Completed combined twins and resumed A01 core component

Published `d18182c13ce4a35584fef4d4bc5b16e513c8b244`: exact-head,
merge-compat, qemu-system and candidate-publication PASS, run 34041670810.
No additional full local run on unchanged source.

The preserved exact-state resume completed: A **176.750 s**, independently
clean B **1715.396 s**; all **24** checked kernel/config/symvers/vmlinux/module
artifacts are byte-identical. Radio twins **223.630 / 214.831 s**, activation
twins **22.019 / 21.919 s**, PMIC twins **4.275 / 4.124 s**. The QEMU-only
helper fixture was built in **3.874 s** and separately validated against the
actual vmlinux-produced Image. No host or phone module insertion occurred.

Using existing standalone composition code, unsigned core target twins were
assembled in **6.289 / 6.192 s**, hash
`0241a611818638d2e3a6ff399ebea4d63fe6bbefc09a64d5e324d600a6415cb9`.
The accepted derived PDR BTF-packaging exception is unchanged; raw kernel
outputs remain intact. No ASUS wrapper compilation, signature or new claim.

Existing A01 component routines ran the exact new Image and all 19 core
modules against the current retained P24 snapshot, mounted RO/noload with
disposable tmpfs upper. **PASS 81.283 s**, including artifact checks before and
after; VM **19.611 s**. Firmware staging, module insertion, Arch preparation,
exitrd containment, systemd execution, SSH policy, unit verification and
timing/stage composition passed. Root bytes and source identity were unchanged.
This is explicitly **not full A01 or release qualification**: radio/primary
archive, signed wrapper/selector, H02/H03 and physical recovery remain open.

Private result: `rog5-v7-server-modules-20260906.Ibl4iPCz/core-component/result.json`;
kernel/radio/aux terminal records and failed original outputs remain there.
Directory allocation is **8.9 GiB** (not a measured peak); free host space
**5.5 GiB**, reserve **3 GiB**. No build data was deleted. Next work reuses
these verified twins to complete the coherent server archive and final A01.

### Matching full server archive and signed selector package

From `92449973a7adb6adc30a4717fb9203c07605063f`, existing builders refreshed
the accepted persistent server with the exact combined ABI. All retained
firmware and radio userspace bytes are preserved; the nested module manifest
and outer boot manifest were regenerated. Target twins match:
`6f9199f5413e6d59bce6cb7973593ef1afa858630af7541c3aa2f0a5a3e73e07`,
**73.336 s**. Complete 37-module software load/firmware staging, separate
board-safe refusals, consumer BTF relocation/refusal, Arch/systemd/SSH/unit and
timing preparation **PASS 105.604 s**, VM **38.939 s**. Not physical activation.
Active tier **PASS 23.188 s**. These results remain in the same private build
directory (`server-assembly-result.json`, `server-component/result.json`).

Proposed `headless-server-selector-v2` signed-package twins **PASS 6.084 s**.
ASUS kernel was reused, and the recovery wrapper is byte-identical to the
retained selector wrapper `dcc487f1…`, not another kernel build. The target
manifest is `3a02a526e98dc8987cdede58f5124c0430034092cdb0a6fb6edfc164476f9155`;
selector `353b7a88f56733fe39ee31707981bccd3dd15b6b1d47822ca369b26bab779f99`.
One canonical exact-record row was added; no runtime/admission mechanism
changed and no real claim was created. Existing dynamic tamper/permanent
consumption tests cover the new row: **19 PASS**, normal **0.293 s**, optimized
**0.322 s**. Acceptance contract tests **33 PASS 1.274 s**. Admission-only data
uses these isolated checks per development policy; publication gates remain.

Disk reserve prevented a second disk-backed root copy. A disposable private
copy was made under host `/run` tmpfs with explicit RAM/headroom gates. A
pre-copy metadata gate caught an old 20 KiB padding assumption before any
credential or write; the preparation now derives size from the verified
capture result (34,359,717,888 bytes), not that copied constant. Copy/hash proof
**PASS 57.332 s**, initially 3,633,270,784 allocated bytes. Existing project
credential workflow only created the private host directory; no phone access.

Only the disposable copy received the new bundle/selector using bounded
debugfs writes and exact read-back. Preview **PASS 23.832 s**, hash
`8f4afbcceed4b2112981392127deaf5a057a9c1d193cb325ef55791810e792c5`.
It is prospective staging evidence, not the deployed phone root. Original
snapshot, fallback and actual phone selector/trial are untouched. Full signed
A01, exact-head publication and all physical acceptance remain to be proved.

### Full selector-v2 A01 and publication completed

At `7899c961d4b6687e73162abd4064705ee42d51b9`, full signed **A01 PASS
96.525 s**: wrapper, signed target, archive, root runtime, module load,
firmware and timing/transport all PASS. Result is retained in private
`rog5-v7-server-modules-20260906.Ibl4iPCz/selector-v2-a01/result.json`.
It explicitly remains offline evidence against the prospective P24 copy,
not deployment, physical charging or recovery qualification.

Dynamic B01 admission closure **33 tests PASS**, normal **4.495 s**, optimized
**4.885 s**. All four remote jobs **PASS**, run **34043424542** (head-exact,
merge-compat, qemu-system and candidate-publication). No additional full local
suite for the data-only record; shared consumer behavior is unchanged. Draft
PR1 was updated without rewriting its retained historical section.

Fresh read-only same-boot V7 continuity **PASS 0.344 s**: uptime 19005.75 s,
29.9°C, 8.592 V, zero current, original boot UUID, safe RO P24, no failed units.
No radio activation, reboot, charging-control or phone-storage write occurred.

The prospective root remains volatile under `/run`. Compressing it hit the
predeclared 1.5 GiB output cap after **30.842 s** (SIGXFSZ), rather than consuming
the host reserve. Only the incomplete new compressed duplicate was removed
after confirming both the original snapshot and full RAM preview remained;
logs and retention note are kept. No verified build, source, credential,
backup or original evidence was deleted. Host free space returned to 4.8 GiB.
Do not claim the preview is durably archived or automatically reusable after
a host reboot. Preserve it pending staging or an explicit retention solution.

Next mandatory work is executable H03 collection, then matching radio-inactive
rescue H01/H02/H03. The existing H02 checker deliberately accepts only the
coherent radio-free rescue composition and verifies no loaded ath11k/PHY;
the full radio-bearing selector-v2 server cannot silently substitute for it.
Keep these first-milestone and later server outcomes explicit instead of
turning unrelated artifacts into one green release.

### Executable H03 collection checkpoint

Continued `462e7fccb360a854a6d9f2336e5d8fa0e21426da` and its dirty H03
implementation; no reset, kernel rebuild, phone contact, claim, admission,
charging-control or phone-storage write. The earlier bounded workflow cleanup
is retained, not redone. The existing mandatory acceptance matrix remains done;
display is optional and historical investigations stay linked, not reloaded.

`check-charging-regulation.py` now runs the predeclared firmware-Full branch:
fresh H02 qualification, same boot/source/artifacts, exact runtime and 29-file
firmware agreement, 61 actual samples over 600 seconds, and final revalidation.
Missing prerequisites are BLOCKED; missing/stale/unsafe readings or transport
loss during observation are FAIL. No automatic retry or charging-control write.
The math-only helper remains non-qualifying. Raw replies, errors, target/host
times, sample counts and content hashes are retained outside Git. Charge-limit
sysfs absence is not a requirement; required outcome measurements still are.

Fail-first regressions demonstrated two defects during implementation:
nonzero SSH replies lost their partial output, and the initial dispatcher could
accept contradictory failed H02 metadata with a true qualification flag. Fixed
both, retaining bounded failure bytes without retry and requiring matching
successful H02 proof. Exit zero, wrong source/artifacts, missing samples, false
qualification and failed prerequisites cannot produce H03 PASS. Required power
checks are evaluated immediately rather than after the complete window.

Focused collector checks **11 PASS 2.843 s**, including explicitly selected
sealed ARM64 BusyBox execution with present/absent/read-error simulated sysfs.
Archive `0241a611818638d2e3a6ff399ebea4d63fe6bbefc09a64d5e324d600a6415cb9`;
probe `322996dc21e534e08da74b680c7fca0084048a45bcf92b7eff3bce44e5b8cc03`.
This establishes applet/firmware composition compatibility, not hardware charging.
Acceptance regressions **35 PASS 1.571 s**, optimized Python **35 PASS 1.581 s**
(wall 1.716 s). Optimized collector replay **10 PASS**, with the explicit sealed
integration not selected in that invocation, not counted as another pass.

Frozen integration: active tier **PASS 20.197 s**; full local CI **PASS 498.170 s**,
run once. No new 3–6 second or faster-full-CI claim: the optimization is focused
iteration and batched shared-behavior validation, not removing required checks.
Private logs: `rog5-h03-collector-20260906.IW5bi9HR`. Detailed report/current-state
updates after CI do not change tested executable inputs. Remote exact-head/merge
publication is the next integration gate. No ASUS wrapper/cache invalidation or
large build output; host free space remains approximately 4.8 GiB.

The next physical question is whether a matching radio-inactive rescue clears
H01/H02 and sustains the predeclared H03 outcome. Consumed V7's historical H01
failure remains FAIL; neither it nor server-selector-v2's radio-bearing archive
can silently substitute for this rescue qualification. The original goal remains
active; H03 and complete release qualification are not claimed from offline tests.

### Matched radio-free rescue V8 prepared

H03 implementation `4b22a9f670c1db44c55fc8fa98e2c6896c6ab6ba` passed all four
remote jobs in **34045925726**. During CI, one pinned read-only V7 check passed
in **0.265 s**: unchanged boot UUID, 29.9°C, 8.591 V, zero current, Good/USB
online, P24 RO and no failed units. This is continuity, not H03 regulation.

The next primary question remains matching rescue H01/H02 and predeclared
firmware-Full H03. Original V7 capture failure remains **R7 / FAIL**; its
anchored sysfs-read/removal correction has source replay and published CI.
No kernel redesign was made for that host-side failure.

One private recipe prepared `headless-acceptance-rescue-v8`, reusing the combined
kernel/core archive twins and the radio-free V11 DTB `4f6518b3…6c76b8`.
The server DTB's extra WCN/PCIe/S12 board nodes are not introduced into this
radio-inactive rescue. Verified all 24 retained kernel artifacts against both
builds and the exact 19-module core closure before signing. Existing signer,
recovery builder and boot-v3 repacker produced identical twins **PASS 20.599 s**.
No ASUS kernel rebuild, phone write, admission, live claim or execution.

Private inputs/logs/results: `rog5-rescue-h03-20260906.CayoqOsI`.

- Manifest: `2b565dbea7b14ffa90dd7100700f8db2b7554f9ac9f8eb8149d28dde02070e9f`.
- Boot AVB: `1592fedf499f3eba0351c0d3af28a616400b4e00bdd4ccd08f54a04bb79e4687`.
- Recovery: `33b0743cc87ad9081b4d1466b860d908f84617b97041d52a86ef7509c69b88dc`.
- Kernel/core archive are unchanged `ece47c7d…bc74e` / `0241a611…15cb9`.

Only a 20-line literal canonical artifact record was generated; no claim
consumer/lifecycle implementation changed. Registration commit
`fcfd15db51c225a67ea1d4c02a85c5d637cb3abb`: claim tests **19 PASS 0.174 s**,
optimized **19 PASS 0.169 s**, admission closure **33 PASS 3.569 s**.
Full assembled **A01 PASS 83.860 s**, all seven checks, exact source/artifacts,
using the unchanged retained P24 snapshot. Not deployed or physical evidence.
The full local implementation suite is reused unchanged from the H03 checkpoint;
this is artifact/data-only work, not justification for another identical suite.

The existing live adapter still requires successful remote CI for its exact
publication head. Current PR selection conservatively uses the full branch
diff, including on registry-only checkpoints; no unchecked waiver was added.
Addressing that overhead requires an explicit tested selection-policy change,
not labelling previous-head checks as current-head checks. It is not a kernel
defect or a reason to alter boot/one-use behavior.

Next: validate the retained live adapters against the new recipe, then a
coordinated, non-retryable RAM attempt after publication and connected preflight.
Keep current V7 running until that transition is ready. Host free disk is about
4.2 GiB; the 3 GiB reserve and volatile server-root preview remain preserved.

### V8 live rescue and H03 Full maintenance qualified

Continued clean published `d23304c04bc201c7ffb25fbac49b86b187969b31`;
all four jobs passed in run 34046603853. Frozen source and active coordinator
inputs were not edited during execution or qualification. Existing packaging,
full CI and exact-head checks were reused, not rebuilt/repeated.
Private evidence remains under `rog5-rescue-h03-20260906.CayoqOsI`.

V7 exited via the already-tested RAM-only exitrd action with normal storage
teardown: exact fastboot PASS 10.223 s, product lahaina, slot B, 8604 mV,
battery-soc-ok yes. No flash or partition-layout write. One V8 claim was
consumed; execution returned zero in 15.903 s (fastboot 12.813 s).
Pinned SSH became ready in 59.785 s. The original receiver completed its
1380-second capture window, returned zero and restored host setup.
Do not retry consumed V7 or V8.

Exact V8 identity:
- boot UUID `015153cc-86f0-440c-b49f-95a1733316b9`;
- kernel `7.1.4-gf17befd4ef17`;
- Image `ece47c7d52627d390bccdbcdab23295fe795820c66174d8de41cbc221cbac74e`;
- target archive `0241a611818638d2e3a6ff399ebea4d63fe6bbefc09a64d5e324d600a6415cb9`;
- signed boot `1592fedf499f3eba0351c0d3af28a616400b4e00bdd4ccd08f54a04bb79e4687`;
- recovery archive `33b0743cc87ad9081b4d1466b860d908f84617b97041d52a86ef7509c69b88dc`;
- manifest `2b565dbea7b14ffa90dd7100700f8db2b7554f9ac9f8eb8149d28dde02070e9f`.

The private adapter's preboot regression covered privileged capture evidence
ownership: fixed no-follow files are handed to the acceptance reader only
after receiver exit, with 0600 modes and unchanged bytes. Ten adapter tests
passed in 0.684 s. A separate closed smoke summary needed the same bounded
ownership handoff; its bytes stayed
`a42fef0942547b9169c6f9a5a12c723859c6cedfc1e97eb2b3f4e50867235a81`.
No live input or phone data was changed to correct this host-only issue.
Future coordinator maintenance should include that closed summary; no successor
is needed. Historical failed capture evidence was not relabelled PASS.

The existing acceptance dispatcher ran H01 and H03; H03 itself freshly
qualified H02, avoiding a duplicate H02 call. Results are
`qualification-r1/results.json`, with nested `H03/h02/result.json`.
H01 PASS 0.416 s. H02 PASS on the same boot, including deployed bytes,
radio inactivity, power and the actual current-boot watchdog acknowledgement.
H03 PASS 604.523 s at the dispatcher (collector 604.338 s):
61 raw samples span 600.265 s, with source/artifact/firmware/runtime/boot
checks before and after. Full/100%, Good, 29.8°C and 8.590 V throughout;
battery current 0 µA and counter 5,106,000 µAh unchanged.
USB input 172–447 mA at 4.983–5.053 V remained below its 500 mA limit.
This qualifies the predeclared **firmware Full-maintenance branch only**,
not sub-full charging, programmable limits or a complete server release.
There were no charging-control writes or missing-field substitutions.

Independent offline work used the exact V8 kernel/archive, not older g601
proofs. `c01-exact-r1/result.json`: nine watchdog/root-handover cases PASS
138.299 s. `f01-exact-r1/result.json`: disposable journal recovery and
corruption rejection PASS 75.432 s; protected inputs/root hashes unchanged.
These are offline component results, not physical reset/UFS qualification.

`c02-exact-r1/result.json` remains **FAIL**: 151.045 s exceeds the unchanged
120 s contract, although both real Arch/systemd/SSH cases passed and the
retained root stayed unchanged. A bounded diagnostic replay wrapped only
existing hash calls with timing, retained in `time-c02.py`,
`c02-timing-r2.log` and `c02-timing-r2/result.json`.
It completed in 114.037 s: root hashes 29.627/29.670 s, guests
30.581/22.916 s. The wrapper changed no hashes, guest behavior, timeout or
production source. This demonstrates host verification overhead but does not
prove why the first run was slower. Keep it labelled diagnostic, not an
erasure of the initial failure or a stable timing guarantee. No kernel fix,
threshold relaxation or physical boot is justified by this host timing result.

The bounded workflow correction remains complete: compact current state,
explicit-only proportionate debugging, frozen mandatory scope, distinct
experimental/accepted-release operations and supported H03 telemetry.
No global instruction edits, history deletion, new framework or build cleanup.
Next: resolve C02 timing robustness and installed autonomous recovery, then
advance the existing persistent-server matrix. R01, Wi-Fi, repeated ordinary
boots, powered-off start, durability and soak remain unqualified.

Evidence-only handoff update: current-state is 114 lines. Markdown targets and
`git diff --check` PASS; the existing active tier PASS after the update, with
per-test durations printed (no aggregate wall duration captured for this run).
No unchanged full local or remote suite was rerun for these documentation edits.

### C02 isolated-guest timing correction

Started clean `3f1c38ecb72c3dd5c4cc8e2ea89f9a3507b0fc15`. The prior goal turn
made progress (H01/H02/H03 qualified); it was not a stopped or retriable boot.
Question: can the exact C02 behavior meet its existing 120 s contract without
discarding root hashes or altering target/watchdog semantics?

The two C02 guests have independent initramfs, logs, RAM overlays, loopback
credentials and networkless containers; shared kernel/root inputs are read-only.
The runner now overlaps only these two guests. C01 and other supporting modes
remain sequential. Each guest retains its 40 s QEMU/50 s subprocess limit,
2 CPU/1 GiB container cap; timeout errors propagate without retry. Both complete
root hashes, ordered per-case proof and the unchanged 120 s row limit remain.
This is host test-harness code only, not kernel, initramfs, claim or recovery code.

New overlap/sequential/timeout tests first failed with missing implementation.
The full 17-test artifact/harness suite then PASS 1.084 s, including an actual
barrier in mocked complete C02 core and Wi-Fi runs, separate logs and retained
read-only arguments. Active tier PASS 20.595 s; exact log
`rog5-rescue-h03-20260906.CayoqOsI/c02-parallel-active.log`.
Implementation committed as `c2539e3c27b4478e901f3058ad9b01de593fdb84`,
then frozen for real exact-artifact qualification. No rebuild or phone boot.

`c02-parallel-r3/results.json` under the same private directory is the actual
existing acceptance dispatcher result: **C02 PASS 91.570 s**, versus the retained
151.045 s failure. Input-receipt hashing outside the timed row took 30.146 s;
it is reported separately, not hidden. The runner itself took 91.452 s with
two workers; healthy SSH restart 30.482 s, stale-identity reset 23.366 s.
Kernel/archive/root hashes match the V8 receipt, the retained root is unchanged,
and complete proof passed the existing consumer. No prior FAIL was overwritten.
The 114.037 s instrumented replay remains diagnostic only. This reduces serial
guest overhead; it does not claim the old variable host delay's cause is proven
or guarantee timing under arbitrary host load.

Fresh same-boot H02 PASS 1.269 s, private `h02-c02-checkpoint/result.json`:
exact V8 identity, runtime, Good power/thermal bounds, pinned SSH and actual
900.048 s watchdog ACK. Wi-Fi remains intentionally inactive. This is continuity,
not another H03 interval or whole-server qualification. Installed autonomous
recovery, server radio/local persistent operation and remaining release rows
remain the next work. The source demotion fix already exists; qualify deployed
composition rather than reopening the same historical review. No global
instruction, charging control, phone storage or installed boot image changed.

### Server V2 staged from the qualified V8 rescue

Continued clean `60482471f6c0dcc327edf79fbeadfe8ef9597135`; the preceding
turn made progress (C02 correction), not a stopped/retriable device execution.
All four exact-head/merge/QEMU/publication jobs PASS run 34049602683.
No repository implementation or active artifact input changed during this cycle.

Existing acceptance dispatcher **server C02 PASS 77.233 s**, with the exact
37-module server archive and prospective root already qualified by A01.
Input verification outside the row took 35.201 s. Both actual Arch guest cases
passed: healthy late SSH/Wi-Fi-timer restart retained access; stale Wi-Fi health
caused rollback. Root hash unchanged; no physical radio activation is inferred.
Private `rog5-v7-server-modules-20260906.Ibl4iPCz/server-c02-r1` retains the
full receipt/results. This is server-specific evidence, not imported rescue C02.

Read-only phone staging inspection PASS **0.634 s** on unchanged V8 boot
`015153cc-86f0-440c-b49f-95a1733316b9`. It verified exact host/device topology,
kernel/boot, P24/P23 sources/UUIDs/sizes, 117-node write scope, existing selector
and healthy trial metadata/hashes, existing overlay identity, safe power,
five V11 fallback hashes and absent staging destinations. No mutation occurred
in that inspection. The existing tested transaction was instantiated with
canonical V2 data; only identities/scalars/payload hashes changed, not its
write/relock algorithm. Shell syntax and no-effect read-only cleanup passed.
Three coordinator ordering tests PASS 0.005 s: default inspection cannot
transfer, failed backup prevents transfer/entry, and local refusal precedes
device/credential use. There is no new repository lifecycle framework.

Immediately before staging, the exact authenticated recovery's sealed verifier
revalidated both primary/fallback signatures and payloads from the paired
root preview; all five transfer files, including manifest signature, matched
those verified bytes. Canonical artifact hashes, clean source and successful
remote CI were checked again. No signing key was needed. Candidate claim,
entry and global consumed marker were absent.

**Bounded staging PASS 2.073 s.** New five-file V2 bundle installed on P24;
old selector copied/verified before atomic selector replacement, P24 remounted
RO and block-locked, then old healthy trial archived on P23. Old records were
first preserved/hash-verified/fsynced on the host. No trial state was fabricated.
The independent 180 s relock guard and single non-retryable transaction remained.
No flash, GPT, protected partition, overlay/service-state contents, reboot or
boot-claim operation occurred. Old primary, V11 fallback and stock A remain.

Private `server-stage-v2/STAGING-ENTERED.json`, `STAGING-RESULT.json`,
`execution-r1` backups/logs and `proposal.json` retain exact commands, source,
coordinator/template/script hashes, authorized file-write scope and interruption
limits. Staging script SHA:
`2ce92efb639e72cdf68a274101f3979eda53550ca03a3d4670c24ca5ee290b1d`.
Active selector:
`353b7a88f56733fe39ee31707981bccd3dd15b6b1d47822ca369b26bab779f99`.
Old selector:
`c15c77824e3cecf128288f2c273c6bd7f93825e837568c669d8288145541d904`.
Archived healthy trial:
`6705ccb23b337cce074eb28cc1f5556ef84b183b63bf3552f5a1e97858fb184d`.
On-device preserved paths are `selector.rollback-headless-server-selector-v2`
under `/boot/rog5-linux` on P24 and
`wifi-trial-state.accepted-server-v1-6705ccb23b337cce074eb28cc1f5556ef84b183b63bf3552f5a1e97858fb184d`
under `/rog5/boot` on P23. Their host copies are `execution-r1/old-selector`
and `old-trial`. Cross-filesystem interruption requires inspecting these exact
records; never blindly rerun staging or synthesize a healthy trial.

Independent postcheck **PASS 0.532 s** rehashed all staged files and preserved
records, checked owner/mode/link metadata, absent active trial, exact V8 boot,
Good/online power and P24 RO with only `sda sda23` writable. The original P24
snapshot and RAM preview remain unchanged on the host; their raw-image hashes
must not be presented as the now-modified physical P24 hash. Physical readback
proves the staged files, not a complete post-staging raw snapshot.

V8 remains running. A final read-only claim-store check confirms all V2 claim,
entered and consumed markers absent. Next: adapt/test the existing coordinator,
capture and V8-to-fastboot transition, then one admitted RAM-only V2 trial.
Do not perform an ordinary reboot into the staged unissued selector or reuse
V8's consumed claim. Installed autonomous recovery and full-server qualification
remain outstanding. Source/recovery/kernel rebuilds are not needed for staging.

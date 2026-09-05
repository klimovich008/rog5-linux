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

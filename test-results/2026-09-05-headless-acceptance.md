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

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

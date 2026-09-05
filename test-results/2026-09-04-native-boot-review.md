# Native boot review and interrupted-update correction

Starting HEAD: `8e7373cb2400399f394fcd6364cabb8c05983348` (clean).
Question: can interruption between systemd's two update-marker writes make
otherwise valid persistent Arch state unbootable?
Layer: initramfs/userspace validation; R3/R8 runtime/recovery assumptions.

## Evidence and limits

Before the code-only review, one ordinary exact-device fastboot reboot was
sent at 22:52:42 local, with slot B, 7671 mV and battery-soc-ok yes verified.
The host saw recovery at 22:53:02, target at 22:53:17 and disconnect at 22:53:39.
Recovery/target enumeration then repeated at roughly 54-second intervals.
No target SSH or diagnostic stages were obtained. Identical target USB strings
do not identify V10 versus fallback V11. No new candidate was executed.
Observers were stopped when the user requested code-first investigation.

The reviewed V10 kernel is `7.1.4-g1eea8970e87f`, Image SHA-256
`2649a272eb2a6814db6302630a585fcab3d4422802e774ec55a55cc489f629e1`.
Its retained initramfs SHA-256 is
`cf3f8e6f36e33121ec4e7b83c1aff4814261b88927fcd27f1dc01e140a27f833`.
The Arch release lower was inspected read-only; its expected init/SSH policy
was present. This does not establish current writable-overlay health.

Other review findings remain open, not silently fixed in this patch:

- The retained ARM trial selector repeats an already-healthy primary after
  subsequent decisions without a fresh health acknowledgment. Four offline
  decisions reproduced this; it may sustain a loop but not explain its start.
- Exact UFS source/module composition disables auto-Hibern8 but leaves the
  separate software clock-gating/Hibern8 worker enabled. A containment gap,
  not proof of today's loss of USB.
- Initramfs rejects nonempty internal overlay workdirs before Linux's cleanup
  path, and rejects successful journal replay on the writable userdata parent.
  Neither recovered on-phone condition has yet been observed for this incident.
- The power helper's 20-second readiness deadline plus two-second failure
  delay resembles the target window. Without stage evidence this is a
  timing hypothesis, not a diagnosis. Ramoops support without a matching
  reserved-memory node does not provide independent crash evidence.

## Proven marker defect and minimal fix

The retained lower uses systemd 260.2. Its
[update-done implementation](https://raw.githubusercontent.com/systemd/systemd/v260.2/src/update-done/update-done.c)
atomically saves each marker separately, `/etc/.updated` before `/var/.updated`.
No cross-file transaction exists. Our boot validator required both markers to
be empty or carry identical timestamps, rejecting valid interrupted states.

The fix removes only cross-subtree equality. Each marker still requires exact
format, bounded size, regular non-symlink/root-owned mode-0644 single-link
metadata and equal merged/upper content. Lower markers remain prohibited;
volatile-root timestamp checks and cache/SSH-unit checks are unchanged.
Validation runs in a subshell as before, preserving shell variable isolation.
Existing marker contents are not rewritten to manufacture equality.

## Tests and measurements

- Added interruption cases: unequal valid timestamps, only `/etc` updated,
  only `/var` updated. All three failed before the runtime fix (0.291 s).
- Full focused storage-resolution suite: 24 tests passed (1.803 s).
- Persistent-overlay runtime suite passed (0.250 s).
- Expanded invalid-marker cases: bad comment, invalid timestamp, merged/upper
  content disagreement, symlink and wrong mode all rejected.
- Six systemd-state tests ran with the exact retained ARM BusyBox/applets and
  libraries in an isolated extracted V10 root: passed in 11.494 s including
  extraction (10.820 s tests). Disposable fixtures emulate merged/upper paths;
  no actual OverlayFS mount or phone storage is exposed. The first fixture
  run lacked `/dev/null`; supplying bubblewrap's private minimal `/dev` fixed
  the harness, not the target. The final source also preserves the original
  subshell boundary and receives the frozen-tree checks below.

Full local CI and publication results are recorded with this checkpoint's
commit/PR checks after source freeze. No kernel or wrapper rebuild is needed
for this correction; eventual deployment requires a new verified initramfs.

No phone contact, signing, candidate issuance, flashing, slot selection or
phone-storage writes occurred during the review/correction. The installed
server, stock slot A and signed fallback are unchanged. Do not interpret the
offline fix as recovery of SSH or resolution of the initial blackout.

## Accepted-primary re-arm correction (source checkpoint after `338c598c`)

Question: does an accepted primary that later fails before a fresh health
acknowledgment select the signed fallback on the next loader invocation?
Layer: persistent trial-state helper/recovery composition; R8. Experimental
claims, target COMMIT and signed fallback bytes are not changed.

Previously every `decide` seeing `healthy` returned primary without changing
state. New code uses the existing temporary-file/fsync/rename/inode-check
replacement to persist `pending`, re-reads it, then returns primary. A later
decision without a fresh health acknowledgment returns fallback. A lost reply
also leaves pending. A temporary collision prevents primary publication; it
does not prohibit safely selecting fallback from an already-pending record.
No source change is needed in the target health service.

Four new host regressions failed before the fix: repeated accepted boots,
concurrent decisions, failure writing the result to `/dev/full`, and an
existing ambiguous temporary. All passed after the fix. Immediate repeated
health acknowledgment remains idempotent. The suite also verifies one canonical
helper selection and source/builder/output digest agreement.

The accepted `artifacts/persistent-trial-state-v1` directory is unchanged.
New artifact v2 has SHA-256
`c1aab57b43d32d14714af96f3ee1feb936c363c8a86b4ac0b312ea5d08f69d0d`
and size 67520 bytes. Two pinned Alpine GCC 15.2.0 ARM builds matched exactly
(5.107 s and 4.876 s); independent twin rebuild verification passed in 9.765 s.
Only the helper and recovery initramfs composition changed, not the ASUS kernel.

`configs/persistent-trial-helper.path` is the single active artifact selection.
Builders/tests resolve its checksum record instead of repeating version/hash
literals. Identity-only successor composition still refuses a helper swap;
this change does not silently modify any archived or signed target bundle.

Focused tests passed: host helper 13 tests in 2.689 s before adding the
ARM-only mixed-version case; health service 8 tests in 2.059 s; Wi-Fi
composition 19 tests in 1.329 s; slot-B loader 8.936 s; recovery composer
2.181 s, including matching twin archives and exact embedded helper bytes.
Final exact ARM replay: all 14 tests passed in 0.920 s, including concurrency,
lost reply and v2 recovery/v1 target-health interoperability. Reproduce with:

```sh
ROG5_TRIAL_TEST_ARM64=1 python3 scripts/host/test-persistent-trial-state.py
```

This maps only disposable fixture state at the helper's two fixed paths inside
bubblewrap; the release binary is executed by qualified static QEMU. No phone,
network or host block devices are exposed. Native CI runs the same behavioral
fixtures against freshly compiled source; ARM replay is explicit on capable
hosts. An independent read-only review found no blocking issue in the proposed
transition; its scope clarification about temporary collisions is incorporated.

Frozen-tree full CI and publication results belong to this checkpoint's PR
comment/checks. No phone contact, boot, signing, candidate issuance, flashing
or phone-storage writes occurred. Deployment still requires a separately
verified RAM-only recovery composition and the existing live gates. This
prevents one source of repeated primary selection; it does not prove either
the current phone failure cause or a successful fallback boot on hardware.

## Service reliability and test-selection follow-up

Starting HEAD: `338c598c18acff9e27840b643d1e3b7daafc1744`; preserved the
unpublished helper-v2 checkpoint above. Question: can accepted service activity
reactivate rollback or stall health monitoring? Layers: target userspace,
initramfs composition and shared test selection. Failure classes R2/R8/R9.

- SSH retains a Requires edge to the boot rollback timer. A later start can
  re-arm an elapsed OnBootSec deadline. The rollback service now calls a runtime
  action that suppresses reboot only for the exact root-owned, single-link,
  mode-0444 healthy record matching this boot, descriptor and sole cmdline
  bundle token. Missing, partial, oversized, malformed or stale evidence still
  requests ordinary reboot. This is not ongoing health monitoring, nor a
  replacement for pre-systemd watchdog coverage. No deadline was enlarged.
- Fresh persistent composition replaces both runtime and rollback service and
  regenerates member checksums. The previous composer retained the old
  unconditional service. Identity-only successor composition intentionally
  remains unchanged; it is not a way to deploy this correction to old bundles.
- Healthd now closes completed HTTP connections and applies a one-second idle
  socket timeout. This is not a total-request deadline or general resistance
  to deliberately trickled requests. JSON, credentials-free surface and the
  service sandbox remain unchanged.
- Probe selection now includes the previously omitted battery/host diagnostic
  and reporter-builder suites. A closure regression covers every probe-allowed
  path. The existing ARM helper behavior replay is called by normal full CI
  when private QEMU/bubblewrap are available, independently of twin-build tools;
  unavailable environments report an explicit skip. No CI environment is
  falsely claimed to execute the production ARM binary.

Before fixes: three real socket regressions failed in 6.124 s; late healthy
rollback failed in 0.225 s; stale-unit composition failed in 0.087 s; probe
coverage failed in 0.115 s; ARM replay registration failed in 0.277 s.
After fixes: healthd 7 tests/2.438 s; Wi-Fi health 12 tests/3.634 s; composition
19 tests/1.343 s; tier selection 28 tests/0.724 s; exact ARM helper 14
tests/0.911 s. Active tier passed in 6.574 s (previous checkpoint 5.433 s).
Healthd's private temporary files and ephemeral loopback ports permit its
explicit isolated parallel registration; shared-state tests stay sequential.

Exact sealed-shell replay used the retained V10 archive identified above,
its BusyBox/applets and libraries, isolated /dev and disposable fixture paths:
12 tests passed in 30.147 s, 30.925 s including extraction. The shell-runner
hook is `ROG5_WIFI_TEST_SHELL`; filesystem contents are not borrowed from the
host. Two initial harness setups failed before shell execution because their
mount destinations were in the read-only root; private /tmp mountpoints fixed
the harness without changing target code. Timer events and ownership are
fixture-modeled, not proof of real systemd transactions or live deployment.

Full frozen-tree local CI and exact-head remote results are recorded at the
publication checkpoint. No kernel/wrapper rebuild, phone contact, signing,
candidate consumption or storage write occurred. The fallback-copy ordering,
watchdog handover, WPA restart and display-isolation findings remain open.

The first integration run stopped after 109.466 s at a newly exercised ARM
test assumption: concurrent decisions were required to return exactly one
primary. Direct replay reproduced zero primary outputs with only explicit
lock refusals and signed-fallback outputs; state remained pending and the next
decision returned fallback. Source inspection confirms that a fallback reader
can lock the newly replaced inode before the publisher's required revalidation.
This is safe refusal, not a lost at-most-once guarantee. The test now requires
at most one primary, only recognized concurrency refusals, a lock refusal when
zero primaries occur, durable pending state, and subsequent fallback. Serial
re-arm tests still require exactly one primary. No helper source/artifact or
locking behavior changed. Focused ARM/host suites passed in 0.884/2.837 s;
full CI is rerun only after this changed regression and a new source freeze.

## Signed fallback independence and actual switch_root evidence (September 5)

Starting HEAD: `545f2118bc3dd96768b73824bad6fb6273ce4380`; preserved the
pending loader/test changes. Previous checkpoint full local CI passed in
478.163 s; published exact-head, merge, candidate-publication and QEMU checks
passed in [run 33923905287](https://github.com/klimovich008/rog5-linux/actions/runs/33923905287).
Question: can recovery retain an intact signed fallback when only primary
bytes are damaged, and what survives the actual initramfs handover? Layer:
recovery/initramfs; R8. No new hardware cycle is justified by these tests alone.

The loader previously copied and verified primary before reaching fallback
selection. It now copies/verifies fallback first and classifies a primary-only
copy or verification failure. That path selects the exact verified fallback
without opening the trial-state write window. It still requires successful
root unmount and the existing all-storage read-only relock. Invalid fallback,
unmount/relock failure, selector identity and crypto checks remain fatal.
Both-valid behavior still calls the existing trial helper exactly once.

The added replay executes the real copy/unmount/verify/select flow with real
temporary copy fixtures and a clearly simulated crypto boundary. Primary
missing/symlink/corruption/partial-copy cases now reach fallback; fallback
damage, cleanup failure and invalid selection do not publish a plan. Initial
primary-damage regressions failed before the fix (0.119 s). Four focused tests
passed in 0.179 s on September 5. The existing full loader-focused suite passed
in 9.116 s; exact sealed recovery BusyBox replay passed in 1.334 s including
extraction. No phone filesystem was exposed. Handoff and overlay suites passed
in 0.064 s and 0.288 s, but their mocks do not prove real switch_root recovery.

`scripts/host/test-qemu-watchdog-handoff.py` reuses the accepted Image and only
BusyBox/interpreter bytes from the V10 archive identified above. A verified
public systemd 260.2 closure supplies PID 1. All guest filesystems are RAM-only;
there is no disk, phone passthrough, network or credential. An existing local
QEMU container is resolved to its content identity without pulling. The output
receipt records kernel/archive/container identity and each bounded case.

Results: systemd startup 17.049 s; hanging successor init 14.594 s; failed init
execution/panic 5.827 s. All three passed. The first two show the sleeper waking
after rootfs deletion, its console FD still valid, `/bin/busybox` absent from
its old root, and a helper pathname reachable relative to pinned `/run` cwd.
Systemd places the surviving process in `/init.scope`. This is a deliberately
retained watchdog mechanism experiment, not execution of the current disarming
production handoff or proof of an acknowledgment protocol.

Failed successor exec causes a kernel panic before the sleeper deadline. The
fixture uses `panic=2` and QEMU `-no-reboot`; this must not be described as a
userspace watchdog recovery. Likewise a visible relative helper is not proof
its interpreter remains executable; production should use the already retained
syscall-only helper, and test that exact execution path. Next fix must keep
watchdog ownership until the successor rollback timer is demonstrably armed,
preserve an executable reset path, and retain panic handling as a separate layer.

The continuing read-only review also reproduced malformed descriptor acceptance
under Python `-O` (composer assertions disappear) and healthd starvation by a
client sending bytes every 0.2 s (second client timeout 2.002 s). Neither is
fixed here. Current Wi-Fi composition tests passed 19 cases in 1.457 s, without
covering restartability or optional-display failure isolation.

Anchored host sysfs still reported the persistent-Linux USB descriptor during
this checkpoint, with changing device numbers. No fresh target health evidence
was obtained. No phone reboot, candidate signing/issuance, flash, slot operation
or phone-storage access occurred. Source stays separate from installed state.
Full frozen-tree integration results are attached to the publication checkpoint.

## Passive early-boot capture after publication

Checkpoint `87eea4ae96cf11c335a0676743f86daba5de4ad2` passed full local CI
in 476.297 s on tree `88be98d1c718dd5440aaae2b2e28e1feab99e1ab` and was
pushed. No production source changed during that run. The following evidence
arrived afterward; these are documentation-only updates, not another boot fix.

The retained target sends early stage records to `169.254.77.1:8079`, whereas
the active host shared profile had only `10.77.0.1/30`. No listener existed.
Its `nm-shared` firewall zone allowed DHCP/DNS/SSH then rejected other traffic,
so a listening socket alone was insufficient. A temporary receive-only
collector bound to the anchored interface finally captured 12 bounded records
after temporarily assigning both addresses in manual mode and allowing only
TCP from `169.254.77.2` to `169.254.77.1:8079` for 60 seconds. The rich rule
was explicitly removed and verified absent; the interface disappeared and its
saved profile remained `shared`, `10.77.0.1/30`, automatic zone. No boot command,
phone storage request, candidate execution or slot change was sent.

Host-only capture setup first failed on three assumptions: shared mode uses
the first configured address; nmcli joins multiple values with ` | `; and an
empty field may be a newline-only result during asynchronous activation. The
bounded independent review identified the formatter issue; local read-only
route output confirmed it. The exact parser passed empty, newline-only, single
and joined-address fixtures before the successful capture. These observations
must become reusable capture fixtures before any new candidate is built.
Reference: [NetworkManager 1.52.1 source](https://raw.githubusercontent.com/NetworkManager/NetworkManager/1.52.1/src/core/devices/nm-device.c).

For boot ID `344113fb-8e7b-45de-8cbd-0ab63400a452`, release
`7.1.4-g1eea8970e87f`, host timestamps (Unix seconds) are:

| Evidence | Host timestamp |
|---|---:|
| Target USB device 49, persistent-root descriptor | 1788561837.273404 |
| First received stage, ufs-ready ENTER, sequence 2 | 1788561838.813728 |
| Overlay ENTER, sequence 18 | 1788561845.852025 |
| Switch-root ENTER, sequence 24 | 1788561847.863578 |
| Switch-root PASS, sequence 25 | 1788561849.849527 |
| USB device 49 disconnect | 1788561857.510400 |

The observed disconnect is 7.661 s after the final PASS record. Stage records
are unauthenticated diagnostic input, not admission proof; they identify neither
primary V10 nor fallback V11. PASS is emitted before watchdog disarm/exec, so
it proves neither systemd startup nor a completed switch_root. It does show
the reporting target progressed beyond earlier storage/overlay validation.
No terminal FAIL was captured. Kernel panic, explicit rollback and transport
loss remain distinguishable hypotheses, not conclusions. Pinned SSH remained
unavailable; the later attempt outlasted the short network window and is not
evidence of a specific target SSH failure.

Raw capture SHA-256:
`3d9e5c49462c3b0f050334f63fea39f43763a5272414928ed893fc68e23c436b`.
The records, private receive-only collector, QEMU logs and full local CI log
are retained outside Git. Next hardware question is what happens between the
pre-exec PASS record and usable systemd/SSH. Do not redesign UFS or charging
to explain this newly narrowed boundary without evidence.

## Production watchdog handover correction (September 5)

Starting HEAD: `87eea4ae96cf11c335a0676743f86daba5de4ad2`; preserved the
unpublished passive-capture documentation above. Question: does the actual boot
watchdog retain a usable reset path until the successor's core startup checks
pass? Layer: initramfs/runtime rollback, R3/R8. No kernel/DT/wrapper change.

Removed pre-exec watchdog disarming. The existing sleeper pins `/run` as cwd
and retains kmsg/SysRq descriptors. At the unchanged deadline it validates the
existing atomic P2-ready record: root-owned regular non-symlink single-link
mode-0444 file, positive size bounded at 4096 bytes, unique PASS status and
unique current-boot `attested_boot_id`. The distinct field avoids collision
with historical collectors' independently sampled `boot_id`. Validation uses
the retained musl loader/BusyBox, not deleted old-root interpreter paths.

Absent/invalid acknowledgment tries the retained syscall-only reboot helper,
then the old absolute helper if still available, then the already-open SysRq
FD. Optional logging follows reset requests. No new timer, service, claim,
persistent record or PID-kill protocol was introduced. Native SSH's existing
rollback-timer dependency and panic handling remain separate layers. P2-ready
proves its existing boot checks, not ongoing service health or remote access.

Five focused test methods cover 16 ACK cases plus handoff ordering, attestation
publication and reset setup/fallback. Initial ordering/publication regressions
failed before the fix. Independent review exposed parent `exec` redirection
failure bypassing rollback and retained-helper failure skipping the old helper;
both received failing regressions before correction. Final host suite: 0.144 s.
The legacy initramfs composition suite passed (earlier iteration 7.719 s),
overlay suite 0.250 s, active tier 6.435 s. Source-sensitive disarm tests were
replaced, not silently left asserting the old unsafe ordering.

Final full-system replay uses production watchdog functions, the exact V10
BusyBox/interpreter/static helper and accepted Image identified above. Guest
root is RAM-only; the ACK producer is an explicit fixture, not real phone P2
attestation. Seven cases passed: valid systemd ACK 16.654 s; missing ACK
10.588 s; stale ACK 10.840 s; unexecutable helper/SysRq 10.589 s; hanging init
10.490 s; failed init/panic 5.076 s; FD-open failure/rollback 2.370 s. Reset
oracles distinguish `RESTART2("bootloader")` from SysRq and observer shutdown.
The exact BusyBox PID-1 FD-open failure returns to rollback rather than exiting.

Watchdog function digest:
`f1ca971f27ac924185dc2d9293471581c01f4d7642ad41df08ffb749ebe98b94`.
Raw QEMU results and logs remain private. Full frozen-tree CI and publication
results are recorded at the resulting commit/PR checkpoint. Nothing is deployed:
no signing, candidate issuance/consumption, boot, flash or phone-storage access.
Fresh exact fastboot telemetry was slot B, 7704 mV, SOC gate yes. This does not
establish charging current, temperature, server health or the initial failure.

The first frozen full CI stopped after 361.262 s on the storage-resolution
suite's stale literal `arm_watchdog` call. The production call intentionally
became `arm_watchdog || force_rollback`; its FD-open regression already proves
why checking the return is required. The old assertion failed independently
in 0.001 s. Only its expected call is corrected; all USB/identity/UFS ordering
assertions remain. Corrected focused storage-resolution suite: 24 passed in
1.789 s; watchdog suite: 5 passed in 0.139 s. These ran before refreezing for
full CI; the previously passing seven-case production QEMU run is unchanged.

## Retained radio power-gate finding (September 5)

Independent reinspection verified the V10 archive hash above and its sealed
radio, failure handler and unit. The radio requires `voltage_now >= 8400000`
before module activation. Unit failure invokes a handler that requests
`systemctl --no-block reboot`. Its only diagnostic transport is `/dev/ttyGS0`,
but the same archive creates only the NCM gadget. This can conceal an explicit
userspace reboot behind loss of USB reporting.

An isolated replay of the exact retained BusyBox power predicates with fixture
health Good and temperature 302 rejects 7704000 and 8399999 microvolts and
accepts 8400000 and 8500000 (0.186 s). This tests the power subsection only;
it is not a complete lifecycle or measurement of on-phone sysfs. The last
fastboot voltage, 7704 mV, is nonsimultaneous evidence. Accepted September 3
boots recorded about 8.52 V. These facts strengthen the hypothesis but do not
prove that the captured switch-root boot ran V10 or failed this predicate.

Keep the 8.4 V radio guard until an independently justified power policy exists.
The next hardware experiment must capture the actual failure or establish
the existing qualified headless charging/recovery route, not repeat display
or radio activation at an unmet gate. No kernel, power-control, artifact,
claim or phone state was changed by this audit.

## Exact-selector headless rescue preparation

Starting HEAD: `5c406e19e5e4df47928dee246183900c50bfea6b`; its frozen
tree passed full local CI in 473.624 s. Primary question: can the already
qualified signed headless fallback restore power/SSH observation without
entering V10's 8.4 V radio gate? Layer: recovery initramfs, R2/R5/R8.

The retained rescue wrapper requires an obsolete V6 selector; it would reject
the current V10/V11 selector. The shared loader now accepts one explicit
`existing-recovery-fallback SELECTOR_SHA256` invocation from a sealed executor.
It validates the ordinary V2 selector and its exact-byte SHA, then selects
only that selector's signed fallback through the existing single-bundle path.
The selector file is never changed. Primary bytes are not copied or executed,
and p23 trial state is not opened. Unmount and all-117-node read-only relock
remain mandatory before bundle verification and kexec; parent recovery and
Haven handling are unchanged. The default installed executor is unchanged.

Fail-first rescue and argument regressions failed before implementation;
a multiline-hash regression also failed before the exact-length correction.
Seven focused tests pass (0.521 s host, 6.082 s exact sealed recovery BusyBox).
They cover actual selector read/apply/copy/verify integration, changed bytes,
wrong format/mode, invalid arguments, missing/corrupt fallback, unmount/relock
failure, no primary copy and no trial write, plus the existing normal behavior.
UID/GID and crypto remain explicit fixture boundaries; real file metadata,
hashing and applet behavior are exercised. Mutating away the actual production
apply call makes the fixture choose primary, which the new assertions reject.

Independent review found no runtime bypass and identified that integration
test gap before it was corrected. The first isolated replay inherited a host
PATH lacking `/bin`, causing `cp: not found`; setting the production PATH
fixed the harness. A proposed applet-dispatch workaround did not fix it and
was removed. No production applet change or host binfmt change was needed.

Retain the existing ASUS kernel and signed V11 bytes. Fresh archive/repack and
exact admission remain required; no consumed image, phone boot, signing,
flash, slot change or phone-storage access is authorized by these tests alone.
Full frozen-tree results and subsequent composition belong to the publication
checkpoint, not a claim that the phone is already recovered.

## Paired boot composition correction (September 5)

Preserved rescue checkpoint `c005ddff435fab3164a6815be653f3926ba415d4`:
its tree `52e70ffde1cc48f7dde6e06c5e220f5a5d38da45` passed full CI in
470.865 s. Fresh private rescue twins remain unissued and unbooted.

Question: can a fresh composition retain an old P2 producer while installing
the new watchdog consumer? Layer: target initramfs composition, R2/R4.
The complete synthetic base/radio composition reproduced that mismatch before
the fix (0.123 s command time). Init and attestation now render from one shared
set of boot-mode values. Both are replaced together, while unrelated archive
members remain exact. Template cardinality and unknown parameters fail closed.
Tests verify the refreshed producer, matching ACK field, shell syntax, preserved
firmware/module entries and byte-identical twin archive outputs.

The failure-diagnostic composer also copied the radio service's unresolved
`@OUTER_SECONDS@` placeholder. Its final-archive regression failed in 0.101 s
before correction; it now renders the canonical timeout without changing it.

Focused results: 21 composition/runtime tests, 1.273 s (1.356 s command);
five watchdog tests, 0.185 s; overlay runtime, 0.243 s; active tier, 7.459 s.
The accepted V10 archive's exact ARM BusyBox parsed both rendered scripts in
an isolated filesystem: init 0.812 s, attestation 0.685 s. These are syntax and
offline composition checks, not execution of on-phone attestation. The prior
production watchdog QEMU evidence remains separate. Bounded independent review
found no blocking issue. No kernel/recovery rebuild, signing, admission, phone
operation or storage mutation occurred for this correction. Other audit findings
remain deferred. Full frozen-tree results belong to the publication checkpoint.

## Exact rescue registration and host preparation

Composition checkpoint `8cb0f65f4b5e1f9a8a70326f4502e68ac8f54983` passed
full local CI in 491.913 s on tree `c438eb7d99c7950af8ca8fc1edaae41922ae510f`.
GitHub run 33933475707 completed successfully, including head-exact, merge,
publication and QEMU. The next edit adds one literal rescue claim record, not
a new consumer: AST comparison proves all executable statements and historical
records unchanged. The new lookup regression failed before registration;
all 17 consumer tests passed in 0.135 s (0.261 s command). Mutated artifact
fields and consumption retries are rejected. The four recorded hashes were
independently compared against the actual retained boot/archive/selector/manifest.

The retained Arch image's public authorization fingerprint matches the located
deployment key; V11's pinned host fingerprint matches its accepted live record.
No private key was printed or copied. A copy of the proven receive-only stage
collector differs only in its 1320-second observation/firewall lifetime,
covering recovery 300 + target 900 + cleanup 120. It has not been started.
The retired NFS-specific host-doctor profile is not the standalone server gate;
the actual saved shared profile and unoccupied diagnostic listener ports were
checked directly. Sudo credential validation succeeded, but its per-terminal
cache does not carry into later execution cells. No host network change,
actual claim creation/consumption, phone boot, flash or storage write occurred.

## Canonical rescue claim closure and live-preflight refusal

Starting HEAD: `979e25eb77cb163f212020086490648389afb823` (clean).
Question: does the historical admission verifier include the new RAM-only
fallback family already registered in the canonical consumer? Layer:
host admission, R1/R9. Exact-head run 33934354059 failed in head and merge
with `generic claim consumer registry is not exact`; both stopped in the
retention-admission suite. The canonical importer selected only
`execution=mainline-kexec-ram-only`, omitting
`execution=fastboot-boot-fallback-only`.

The correction extends only that existing fixed-repository lookup to the
second exact execution marker. No candidate names or hashes are copied;
whole-registry equality, candidate file hash/mode verification, alias/mutation
refusal and the generic consumer remain unchanged. Two new closure/mutated
fallback-record tests failed before correction (0.181 s command time).
All 30 admission tests passed afterward (3.447 s), and all 17 consumer tests
passed (0.250 s). The mutated fixture is rejected even when its containing
file's size/hash are repinned. Full frozen-tree results belong to the next
publication checkpoint; no passing remote result is implied here.

Connected non-consuming preflight verified serial/product/USB anchor, slot B,
7702 mV and SOC yes, but refused the failed CI before claim creation. No phone
boot, claim entry, signing, storage access or host network change occurred.

Bounded independent review verified the prepared rescue hashes, exact-selector
executor, signed fallback identity and read-only recovery loading. It also
identified a mistaken prior assumption: exact V11 checks temperature and pack
voltage before UFS, but not battery health, and disarms its older watchdog before
switch_root. Do not represent the signed archive as containing the newer source
watchdog correction. The collector's 1320-second lifetime does not guarantee
rollback continuity, and it exits on the first disconnect. Its adapter needs
fresh process identity and remaining-budget checks before any claim entry.

These findings stop this physical attempt before consumption, not the server
goal. Next work is the smallest coherent headless composition with corrected
early gates and watchdog/attestation, reusing the qualified kernel and preserving
accepted fallback/rescue bytes. Existing prepared twins remain unconsumed;
they are not to be rebuilt or silently treated as a qualified new target.

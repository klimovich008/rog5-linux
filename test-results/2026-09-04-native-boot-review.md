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

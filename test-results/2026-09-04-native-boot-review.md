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

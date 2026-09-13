# Authenticated VM service readiness timing

Offline generic ARM64 VirGL VM only. No phone, USB, reboot/power operation on
physical hardware, protected storage, signing, admission, claim or candidate
creation occurred. Phone physical rows remain NOT RUN; headless S06/R01 FAIL
and the accepted server/rescue baseline remain unchanged.

Starting sourcec66c37d6c06fa5f4b84a5019e8fd61e5a076fbb1,
tree1a93bed6a5618feff3c26340c9a63c8ae828ee56. The previous turn was progress:
font preparation and authenticated text entry were observed, while full-session
readiness remained unqualified. Source for this timing experiment:
93b35b4432c214f607e9778efcb0b5107f099f1c,
tree27f83511e1dc5ab72e8f823189d08edeaa78199c.

The actual retained util-linux2.42.3 `lsclocks` supports direct CLOCK_MONOTONIC
reads. Its isolated ARM64 user-mode invocation passed in0.036s. The first VM probe
brackets the retained20-second `systemctl --user start` with that clock,
then takes one3-second/64KiB-bounded snapshot before cleanup. Only unit identity,
state, job, bus-name, monotonic transition times and CPU time are queried.
Snapshot failure/overflow is recorded without replacing the original command
failure. A failed initial clock refuses before startup; a failed later clock
cannot mask an already failed start. Normal service-state and FUSE checks remain.

Eight actual ActivatedServices fixture tests PASS0.276s, including failed start,
missing/invalid clocks, failure only of the after-start clock, failed snapshot,
output overflow and primary-error preservation. The new observation assertions
failed against the previous implementation. Syntax and whitespace checks passed.
Clock and service facts are substituted in host tests; actual ARM64 package and
VM results are separate. No new clock binary, kernel or compositor build was needed.

The pre-command timestamp plus the configured readiness allowance is a LOWER bound on actual timeout cutoff.
Timeout arming occurs afterward. The after-command clock sample also follows
command completion. ActiveEnter inside that interval is ambiguous, not proof
that a unit missed the exact deadline. Snapshot states are later still; a unit
being active in the snapshot does not prove it was active before timeout. Systemd
microsecond timestamps and lsclocks seconds use the same CLOCK_MONOTONIC base.

The complete VM session PASS in283.696s (runner283.627s). The same-clock samples
were190.174471856s before start and209.870231680s after return:19.695759824s.
GTK portal became active at208.430143s; desktop portal at209.730825s. Both were
before the earliest possible210.174471856s cutoff. Desktop readiness had only
0.443646856s margin relative to that lower bound; the post-command sample had
0.304240176s margin. All five snapshot units were active/running, successful,
with empty Job properties. This passing run establishes little margin in this
fixture, not the precise cause of previous timeout124 failures.

The actual authenticated session delivered the expected12 focused OSK key
press/release events. Original captures were inspected and visibly show
`test → tes → test` in Mousepad with the keyboard present. Foot exited normally0,
Mousepad exited0 after owned TERM, launcher exited143 after owned TERM. Denial
reported99raster frames/99page flips with no recorded rendering errors. PAM
closed, credentials were deleted, logind removed the session, filesystems
unmounted and the VM powered down normally. This qualifies this exact VM run;
it does not erase prior failed runs or establish repeatable startup or phone
scanout/touch/GPU behavior.

The reused generic Linux7.1.4+ kernel is pinned to Linux
7a5cef0db4795d9d453a12e0f61b5b7634fc4d40 with virtual DRM/input and built-in FUSE;
Image SHA2562b1c8d95f54dda28e772df82be54af7508b2ce84183f1b0024a7f14e3d5ce0fc,
config23af1f7083bb5607f65904ab6d46a101c5d67fd73a6ae10dd868877db16870af.
Denial executable SHA25640b1fc631643d602b57db2b988eb2caf8839e1e044890f7c9aa4ad0555bb8af0;
unsigned archive1ff417307c96bac90977b64a143e1a81b535d94a03109ca967c40e9b1f269d0c.
The package closure, memory/CPU/network limits, actual editor observation and
existing inner/outer deadlines were reused. Only small VM probes and initramfs
staging were rebuilt. None of these artifacts identifies installed phone bytes.

A bounded independent source review confirmed that20s was introduced by the
manual VM fixture, not packaged unit TimeoutStartSec, the headless contract or
phone guards. Based on repeated nearby historical failures and this successful
19.70s interval, final source uses25s of readiness allowance inside unchanged
120s user/140s PAM/145s supervisor/170s service/300s VM bounds. It adds5s of
fixture scheduling headroom, not a root-cause repair or qualification of startup
reliability. The first container step took270.535s under its300s limit; overall
wrapper time includes separate preparation and is not the container deadline.
Historical failures and the20-second passing control are preserved.

Final source1a9f039b9b1a1c8b9d978122437b3758757f6808,
tree323dc33b787cc5387cdd7db05d83cb65e8b4f66a. Focused8cases PASS0.274s.

The25-second trial also PASS in268.343s (runner268.276s).
Samples174.503135024s to193.439799600s bracket18.936664576s. Desktop portal
was active at193.277111s,6.226024s before the new earliest cutoff. All five
units were active/running with successful results and empty jobs. The extra5s
allowance was not needed on this sample, so this does not prove it prevents the
historical failures. It qualifies one complete run with the final source/policy.

The exact12 focused OSK events and original test/tes/test captures passed again.
Both native clients and the launcher stopped with expected statuses, Denial
recorded99frames/99page flips and no rendering errors, and PAM/logind cleanup,
all-filesystem unmount and normal poweroff passed. No third VM was launched.

Final frozen active tier:99 PASS,0 FAIL/BLOCKED/SKIPPED,255 NOT_SELECTED,
149.200s,507.6MiB peak memory and0swap. Three declared optional subchecks are
SKIPPED. This was one active-tier execution after both VM trials and final source
freeze. No GitHub CI or phone board rebuild is claimed. Per-suite deadlines,
commands and outcomes are retained in the JSON/JUnit summaries.

Full commands, per-step timings, source/tree, input/output hashes, original VM
result, snapshots and host JSON/JUnit identities are in the
[qualification JSON](2026-09-13-service-timing-qualification.json). Raw logs and
captures remain private. Historical evidence is preserved; a new fixture set
and the existing current-artifact pointer carry this result without release
or execution authority.

Next use the existing AppSwitchObserver/AppTextObserver for launcher-driven
launch, switching and text input through this authenticated nonroot session.
Today's clients were launched directly; their success is not UI-launch proof.
Keep the measured VM readiness allowance and independent outer guards; investigate
any new timeout with the retained clock/snapshot evidence. No phone operation
is authorized. The next physical OLED/touch/Adreno question still requires the
existing exact-artifact trial process and separate authorization.

Publication checks: metadata5 PASS0.945s, mobile status8 PASS0.024s, generated
status/whitespace PASS, inventory524sets/827registered/177tracked files with68
small hashes checked. Large/private byte verification, admission and physical
qualification remain outside this inventory check. Independent comparisons
preserve all523prior sets, every unrelated pointer, both acceptance contracts,
the historical current-state body and final VM input hashes. Owned containers
are absent. Free host disk is above3GiB. Qualification SHA256:
`0c86c581c52562ca485ad3c833886578a685cc90d974fbc87df765838906d803`.

Changed files relative to starting source:

- `configs/project-status.json`
- `docs/current-state.md`
- `docs/development-lessons.md`
- `docs/development.md`
- `manifests/artifact-sets.json`
- `manifests/current-artifact.json`
- `scripts/host/test-qemu-logind-runner.py`
- `test-results/2026-09-13-service-timing-qualification.json`
- `test-results/2026-09-13-service-timing.md`
- `tools/qemu-virtio-drm/logind-denial.sh`

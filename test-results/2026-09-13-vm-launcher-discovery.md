# VM launcher discovery — 2026-09-13

The unlocked mobile launcher visibly presents Foot and Mousepad in the retained
ARM64 VirGL VM. This is launcher discovery only: neither application was clicked,
launched or switched. The first capture still shows Loading; the second shows
the home layout. Phone physical rows remain NOT RUN; S06/R01 remain FAIL.

The supplied Pro framebuffer review was already addressed by the strict selector,
Invalid-only pool dispatch and returned-descriptor guard recorded in
[allocation-contract qualification](2026-09-12-denial-allocation-contract.md).
Those changes remain in the current patch. This run advances the later mobile UI
work; it neither re-runs that original comparison nor turns VM rendering into
Adreno evidence.

## Source and implementation

Starting commit `836b9093d99f89c8f9e026cd915354633f88df95`, tree
`d6b9a0213a2c2c68f7790a0d3052133cc2717c61`. Executed source:
`b8cd837ca6dab7d74e7858587b671560c48b61e8`, tree
`8abe7a1e001c590300f86c8940474e73d28cbfc0`. The subsequent evidence commit does
not change the executed source.

The VM guest prepares RAM desktop overrides for the existing Foot and Mousepad
entries, replacing only their main Exec command. The package root is read-only.
Denial searches XDG_DATA_HOME first and keeps the first desktop ID. The wrappers
have fixed arguments, a VM-only command-line guard, one lifetime per app, PID plus
start-time identity checks, owned timeout/logger children and cleanup deadlines.
They drain client diagnostics after a 1 MiB per-app limit; the host retains its
8 MiB aggregate serial bound. The guest CLI requires its console node.

The first wrapper inherited its parent's stdout. Inspection of Denial's actual
`application_command` showed that it intentionally launches desktop commands
with stdout/stderr set to `/dev/null`. A real-helper subprocess regression with
null stdio failed because the diagnostic sink was empty. The correction redirects
only the wrapper supervisor to fixed guest `/dev/console`; fixtures inject a
private sink. All ten helper cases then pass, including original exit status,
log limit, stale owner refusal and a TERM-ignoring client. This host coverage is
separate from launching those clients inside a VM, which remains NOT RUN.

The new `--observe-mobile-launcher` mode excludes editor autolaunch and captures
two frames without pointer input. It requires both apps, desktop files and GTK
cache tooling before starting. Missing or repeated preparation/cleanup markers,
a launcher failure marker or any unexpected app launch fail discovery. Capture
transport does not assert visual semantics; direct inspection is recorded in a
separate assessment. The initial Loading image proves that presentation readiness
alone is insufficient for later app-input readiness.

Changed source files:

- `tools/qemu-virtio-drm/launcher-apps.sh` and `guest.sh`: diagnostic wrappers,
  RAM preparation and cleanup integration.
- `scripts/host/test-qemu-virtio-drm.py`: explicit discovery selection, prerequisites,
  marker validation and input hashes.
- `scripts/host/qemu-mobile-observer.py`: bounded no-input launcher capture.
- `scripts/host/test-qemu-launcher-apps.py`, `test-qemu-mobile-observer.py` and
  `test-qemu-virtio-drm-prerequisites.py`: executable host regressions.
- `configs/repository-tests.json` and `scripts/host/test-repository-linux.sh`:
  mandatory helper suite, deadline and retained public tier selection.
- `docs/development.md` and `docs/development-lessons.md`: usage and the demonstrated
  null-stdio lesson.

## Executed results and identity

| Executed check | Result | Wall seconds |
| --- | --- | ---: |
| Mobile observer, Python -O |42 PASS |2.019 |
| Runtime prerequisites/results, Python -O |25 PASS |0.215 |
| Actual guest launch helpers, Python -O |10 PASS |2.322 |
| Guest/helper Bash syntax |PASS |0.004 |
| One ARM64 VirGL VM |PASS discovery/capture;10 frames/page flips; no render errors |102.747 |
| Frozen active tier |91 PASS;0 FAIL/BLOCKED/SKIPPED;255 NOT_SELECTED |143.678 |

Three declared optional subchecks remain SKIPPED separately. The active tier
used two workers, a600-second bound,1GiB/no swap and285.4MiB peak memory.
The VM had its existing120-second host/90-second shell bounds, network disabled,
read-only runtime/payload and only the retained host render node. Guest cleanup
and container removal both passed. No QMP input event was sent.

The VM used the same native Denial, engine, corrected shell AOT, assets, package
root and generic kernel as the preceding content-sizing observation. There was
no kernel, compositor, engine or shell build this run. Current shell AOT SHA256:
`85567c81c52a375d8fa424aaaa54a152440b2fd02d73632301b857da6b230b19`.
Native Denial SHA256:
`878ff4c6155279264782523837cf7672273f333a9a45318a7db9cc9fbf7ce19a`.
Engine SHA256:
`a75c88d8f12d9ec7a24bb107ff9dc0349b6bb2d5b0f18cb4d40b9e54227e9418`.

New initramfs SHA256:
`470fb717888b5c59433255e7f0ed64db4e6aebcd225257cd8df2251f993321c7`.
Serial SHA256:
`32e1412c12195ed22877a2fd98dc94fac7b8db9578952f0ff964bc6cb01474e4`.
Settled launcher PNG SHA256:
`65be5b89c92904794d7ac972dae2a8d109a73c093bde5b7b981d5069e5dfa397`.
All exact input hashes, commands, test durations and source identities are in
[qualification JSON](2026-09-13-vm-launcher-discovery-qualification.json).
Private raw evidence is under
`/home/deck/.local/state/rog5-vm-launcher-20260913-r1`; no raw private credentials
or unit identity are published. No new GitHub CI execution is claimed.

The evidence update also changes `configs/project-status.json`, its generated
`docs/current-state.md` header, `manifests/current-artifact.json`, and appends one
fixture set to `manifests/artifact-sets.json`. Prior500 sets and the historical
current-state body are preserved. Headless/mobile acceptance contracts remain
byte-identical. No phone operation, candidate generation, signing, admission,
claim operation, protected-storage mutation or historical evidence rewrite occurred.

After the status update, `python3 -O scripts/host/test-review-metadata-checkers.py
Checkers` passes five cases in1.083 seconds wall time; `python3
scripts/host/test-mobile-status.py` passes eight cases in0.099 seconds.
`check-artifact-inventory.py` validates501 sets in0.078 seconds, and
`check-mobile-status.py` validates the generated header in0.047 seconds.
These are host metadata checks, not new build or physical evidence.

## Remaining qualification and next experiment

The visible tile centers at 540×1224 are approximately Foot (205,592) and Mousepad
(77,752). These are observed coordinates, not proof of input delivery. Next,
prepare a bounded UI interaction using these tiles and the owned wrappers: prove
the selected native toplevel is configured and buffer-backed, return home, launch
the second app, and switch while checking app identity and retained content.
Gate input on actual launcher/client readiness, not the first presentation or
unchanged loading image. Preserve all failure outcomes and the same VM bounds.

Application launch/switch, automatic caret tracking, non-root mobile privilege
and authentication remain unqualified. All phone display/touch/GPU, suspend/wake,
charging and other physical rows remain NOT RUN in this offline task. Battery
Waiting and the epoch clock in the VM are fixture output, not phone telemetry.
The reusable improvement was reproducing the launcher's stdio contract before
running apps; it avoided a VM run with invisible diagnostics and any binary rebuild.

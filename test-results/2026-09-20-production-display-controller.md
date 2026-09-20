# Production display controller components — 2026-09-20

**Offline host qualification only. No phone/VM operation, candidate, signing,
claim creation/consumption or protected-storage mutation.** The previous turn
was progress: exact archive intake. This turn implements its activation consumer,
firmware prerequisite and concrete provider readers. It does not issue an
admitted live controller or qualify physical display/GPU operation.

Starting commit `dafc820b01748be213161810c0d3fbfcee982d4e`, tree `090f68fb203e248953e1527ec410397b82db0625`.
Frozen implementation `92cb1552498a4e18816fa827dfdf5cb5c190c222`, tree `43a96e09004c9c7171451e200d135c0673fbf59a`.
Current board source remains 8f7b2f83; Linux remains
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`. The current artifact pointer and sealed historical
controller are unchanged. No new kernel/DT/module/Denial/Flutter build was needed.
The tests compile temporary host panel/core callback extracts, not a phone kernel.

## Implemented behavior and exact-source finding

The old controller loads two modules and expects Adreno before display startup.
Current production MSM is a module: `msm_drm_register()` registers Adreno inside
`msm.ko` (exact `drivers/gpu/drm/msm/msm_drv.c`). Its registration returns through
void helpers, so module insertion success alone is not binding evidence.

The successor pins all 14 qualified module bytes. It loads REFGEN/GPUCC, observes
providers, loads DRM helpers and MSM, observes Adreno, then inserts the panel
last. It rechecks providers immediately before MSM and panel consumers. The
archive's dependency order (panel before MSM) is not a hardware activation plan.
The existing helper still performs one finit_module call without fallback/retry.
Children have per-insertion bounds and are killed/reaped on failure/interruption.
Durable entry must cover 14 insertions and the 85-second component bound; no new
entry/claim is created by this work. No driver reprobe, DRM open or unload is added.

The concrete provider reader checks exact DT ancestry/compatibles, reciprocal
driver links, REFGEN's DSI-host supply, GPUCC/SMMU binding and reciprocal GPU/GMU
IOMMU groups. MSM stage adds Adreno and shared-device parameters. The pinned core
`drivers/iommu/iommu.c` configures unbound devices at provider registration;
`drivers/base/platform.c` performs their DMA configuration. Therefore group
observation does not require a DRM open or a GMU driver link. It is not DMA proof.
REFGEN supplies the DSI host; the PHY supply is separate.

The exact composed DT has REFGEN phandle 0x81 and SMMU 0x59. GPU/DSI status is okay;
REFGEN/GPUCC/SMMU/GMU omit status, meaning enabled by DT default. The reader pins
those actual representations, including stream cells and Y/N module parameters.
Panel registration can complete component binding and initiate GPU-object/GMU
and display preparation. Cleanup ownership is required before that step; the
first DRM open is not the only hardware activation boundary.

The firmware reader opens/hash-checks the three fixed A660 files, retains all
pathname edges and revalidates them plus the firmware-class path before actions.
Hashing is bounded. Caller/PID1 namespace, root inode and mount identities must
match. Exact `fs/kernel_read_file.c` uses `init_task.fs`; `init/main.c` initially
shares that FS with PID1 via CLONE_FS. PID1 matching cannot prove continued sharing
after arbitrary unshare/root changes. The current helper is a prerequisite,
not qualification of future switch-root, kernel firmware import or SCM execution.

## Regressions and personally executed tests

- Symbol-order fixture is rejected before a premature panel consumer; the
  original ordering could not reach the required MSM checkpoint.
- Missing firmware-owner regression failed before the new mandatory-owner check.
- Interrupted directory construction leaked one FD before changing its cleanup
  catch to BaseException; the regression checks real owned descriptors.
- Missing zero/framebuffer receipts each produced false success before receipt
  validation. Startup and independent cleanup now require a successful two-byte
  zero write receipt and zero readback; property-only success is rejected.
- Provider loss while loading helpers allowed MSM insertion before detection.
  The failing regression now stops before that consumer via a fresh checkpoint.

Final loader suite: 29 PASS in 6.023s; firmware: 25 PASS in 0.155s;
providers: 32 PASS in 0.364s; selector/workflow: 37 PASS in 0.692s.
The new firmware reader also accepted the actual retained firmware bytes under
explicit host root/namespace/sysfs fixtures in 0.0123s. This validates its exact
production byte pins, not kernel firmware loading. Read-only fdtget observations
of the hash-verified composed DT independently matched the provider-reader pins.
The 29 loader tests use real inert children, compiled actual panel/DRM/backlight
callbacks, and integrations with both real reader implementations. Firmware,
identity, ownership, sysfs and registration effects remain explicit fixtures.
The other fixtures exercise wrong roots/namespaces/mounts, bad firmware bytes,
replacement/mutation, missing bindings/groups, changed DT/parameters, premature
display, one-use entry refusal, errors and cleanup. No root privileges are used.

Initial loader runs:20 PASS/4.008s, 23 PASS/4.494s, 26 PASS/5.228s. After adding the fresh
preconsumer check, an older fixture expected the later child error rather than
the now-earlier checkpoint refusal: 29 tests/one assertion FAIL in 5.997s. The fixture
was corrected to require refusal before panel insertion; that failed run is
retained. Failing-before control logs are retained separately and are intentional
regressions, not overwritten by the final PASS.

Frozen active tier: **118 PASS, 0 FAIL, 0 BLOCKED, 0 SKIPPED suites**,
255 NOT_SELECTED, 209.064s.
Three declared optional historical subchecks remain skipped separately. These
are personally executed local results; no GitHub CI result is claimed.
Owner bounds: 1 GiB/no swap, 2 CPU quota, 256 tasks, 600s and two test workers.
Scratch is disk-backed; 219 GiB free was observed before work.

Focused commands were `python3 -O scripts/device/test-load-production-display.py`,
`python3 -O scripts/device/test-display-firmware.py`,
`python3 -O scripts/device/test-display-providers.py` and
`python3 -O scripts/host/test-select-repository-test-tier.py`.
The frozen integration command was `scripts/host/test-repository-linux.sh active`.
[Qualification](2026-09-20-production-display-controller-qualification.json), SHA256
`762b7e4227f04725a56d7975571cc4f831258330196c4bdccda96c1c1864a035`, records source, per-suite commands/durations and log hashes.
Private evidence: `rog5-production-controller-20260920-r1` under the host state root.

## Remaining boundaries

No matching production endpoint/boot descriptor, root-transition proof, outer
85-second lifetime/14-insertion admission contract or signed composition is issued.
The constructor's callbacks must be preinstalled and identity-bound by that future
owner; fixtures are not production authorization. A currently unbound SMMU causes
failure. Any one-use reprobe requires separate qualification and authorization.
Actual firmware import/authentication, driver binding, panel preparation and
zero-brightness behavior on the new kernel remain NOT RUN.

Next: adapt the exact endpoint/outer component identity and lifetime to these
components, testing the current board binding and one-use/independent recovery
handoff offline. Preserve the sealed controller and all consumed claims. The
smallest later physical question is whether this exact provider/panel path
prepares and accepts zero brightness; it must wait for completed offline
composition/recovery review and explicit hardware authorization. No Ready is
requested. S06/R01 and earlier Denial VM failures remain FAIL.

Changed implementation files:

- `configs/repository-tests.json`
- `patches/display-controller/README.md`
- `scripts/device/display-firmware.py`
- `scripts/device/display-providers.py`
- `scripts/device/load-production-display.py`
- `scripts/device/test-display-firmware.py`
- `scripts/device/test-display-providers.py`
- `scripts/device/test-load-production-display.py`
- `scripts/host/test-repository-linux.sh`

## Final metadata checks

- `python3 scripts/host/check-mobile-status.py`: PASS, 0.040s.
- `python3 -O scripts/host/test-mobile-status.py`: PASS, 0.083s.
- `python3 scripts/host/check-artifact-inventory.py`: PASS, 0.086s.
- `git diff --check`: PASS, 0.012s.

Eight status regressions passed. Inventory validation retained 595 sets; its
large/private-byte revalidation remains NOT RUN. The full inventory and current
artifact pointer are unchanged, as are headless/mobile acceptance, the historical
loader/draft ordering patch and the historical current-state body. The integrated
service terminated successfully; its reported peak was 302.2 MiB with zero swap.

Metadata files changed: `configs/project-status.json`, `docs/current-state.md`,
`docs/development-lessons.md`, this report and its qualification JSON.

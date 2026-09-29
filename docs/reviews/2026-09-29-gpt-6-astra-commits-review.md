# GPT-6-Astra: review of the 2026-09-29 commits

Brief: [2026-09-29-commits-review-brief.md](2026-09-29-commits-review-brief.md). Codex CLI 0.158.0, gpt-6-astra, reasoning high, read-only sandbox. Links point at local paths on the development host.

Reviewed the requested range and bootsplash commits against the r91 source. No files were modified and no phone commands were run.

Findings, ranked by severity:

1. **P1 — GPU monitoring attributes outlive the GPU object.** [0104 patch:134](/home/deck/.local/state/rog5-prod-boot-20260923/patches/linux-7.2.7/0104-drm-msm-ROG5-export-GPU-load-frequency-and-temperature.patch:134)  
   `adreno_unbind()` destroys the GPU before device-managed resources are released. Concurrent monitoring can therefore dereference freed hwmon driver data, or dereference NULL through `dev_to_gpu()` after cleanup clears it. Probe-error unwinding has the same exposure. **Fix:** explicitly unregister both exports and drain their callbacks before GPU destruction, including error paths.

2. **P1 — Temperature lookup races thermal-zone removal.** [0104 patch:110](/home/deck/.local/state/rog5-prod-boot-20260923/patches/linux-7.2.7/0104-drm-msm-ROG5-export-GPU-load-frequency-and-temperature.patch:110)  
   In r91, `thermal_zone_get_zone_by_name()` releases the registry lock without taking a device reference. TSENS unbinding can free the returned zone before `thermal_zone_get_temp()` uses it. Looking it up afresh on every read does not prevent this use-after-free. **Fix:** use a lifetime-safe thermal-core interface; the smallest local workaround is removing this attribute and using Resources’ existing thermal-sysfs fallback.

3. **P1 — Overlays above 160 GiB lose compatibility with the recorded fallback.** [persistent-root-init:41](/home/deck/.local/state/rog5-prod-boot-20260923/initramfs/persistent-root-init:41)  
   The retained [growth results](/home/deck/.local/state/rog5-prod-boot-20260923/test-results/2026-09-29-overlay-growth.md:3) identify `safe-r6` as carrying the 160 GiB limit. Growing the shared image beyond that makes this fallback reject it when a primary boot fails. This commit supplies no matching fallback update. **Fix:** rebuild and qualify both bundles with the new limit before permitting growth beyond 160 GiB. This is conditional on growth; I did not inspect installed phone state.

4. **P2 — A sample can overwrite the suspended GPU’s zero load.** [0104 patch:53](/home/deck/.local/state/rog5-prod-boot-20260923/patches/linux-7.2.7/0104-drm-msm-ROG5-export-GPU-load-frequency-and-temperature.patch:53)  
   Sampling releases `df->lock` before publishing `busy_percent`. Suspend can acquire that lock, write zero, and then have the in-flight sample overwrite it before polling stops. Monitors retain a nonzero load throughout suspension. **Fix:** publish the sample while holding `df->lock`, and use `WRITE_ONCE` for every write.

5. **P2 — The hwmon addition lacks its Kconfig dependency.** [0104 patch:136](/home/deck/.local/state/rog5-prod-boot-20260923/patches/linux-7.2.7/0104-drm-msm-ROG5-export-GPU-load-frequency-and-temperature.patch:136)  
   `DRM_MSM` now unconditionally references hwmon registration, but its Kconfig still permits `HWMON=n`, or built-in MSM with modular hwmon. These configurations fail linking/modpost. The production configuration happens to have `HWMON=y`. **Fix:** add the appropriate dependency or guard registration with `IS_REACHABLE(CONFIG_HWMON)`.

6. **P2 — Concurrent performance-mode changes can reverse trip ordering.** [rog5-perf-mode:39](/home/deck/.local/state/rog5-prod-boot-20260923/scripts/device/rog5-perf-mode:39)  
   There is no lock around reading, updating and saving the mode. A performance write of the high trip, followed by both normal writes, followed by the performance low write leaves **56/46 °C**. Subsequent temperature-based sorting can exchange the trips’ cooling-policy roles. **Fix:** serialize the entire apply-and-save transaction with a shared lock.

7. **P2 — Hardware failures become an overall pass.** [trial.py:48](/home/deck/.local/state/rog5-prod-boot-20260923/scripts/device/bench/trial.py:48)  
   `hardware()` checks only the summary’s `error` list. Missing GPU/Wi-Fi and partial audio therefore pass; empty command output also becomes `{}` and passes. Both were reproduced with in-memory fixtures. **Fix:** require a valid summary and propagate nonpassing results for the required hardware set.

8. **P2 — Display SMMU faults are suppressed throughout the boot.** [trial.py:154](/home/deck/.local/state/rog5-prod-boot-20260923/scripts/device/bench/trial.py:154)  
   The exclusion matches SIDs `0x820`/`0xc20` without checking time or boot stage. Real display faults after modesetting or resume disappear from the result. Patch 0107 also removes the original expected boot fault. **Fix:** remove the exemption for patched kernels, or restrict it to an explicitly bounded legacy handover window.

9. **P2 — A GPU timeout passes the suspend test.** [trial.py:202](/home/deck/.local/state/rog5-prod-boot-20260923/scripts/device/bench/trial.py:202)  
   `sh()` returns the nonempty string `"TIMEOUT"`, and the success condition accepts any nonempty GPU output. A hung post-resume benchmark therefore passes when the other checks succeed; reproduced in memory. **Fix:** require successful command completion and a parsed benchmark score.

10. **P2 — The standby probe suspends even when RTC arming fails.** [sx.sh:33](/home/deck/.local/state/rog5-prod-boot-20260923/tools/standby_probe/sx.sh:33)  
    The semicolon executes `systemctl suspend` regardless of `rtcwake` failure, potentially leaving an unattended experiment asleep without its promised wakeup. **Fix:** abort on RTC failure and suspend only after successful arming.

Checks that looked correct:

- Overlay byte constants, inclusive bounds, whole-MiB rule and matching loop/file sizes; boundary fixtures behaved correctly.
- MIDR implementer filtering, active-low reset interpretation, and normal panel teardown cancellation through MSM’s shutdown path.
- QoS register offsets fit the DT resources; USB retention handling matches the GDSC implementation.
- Updater IPv4, IPv6 and IPv4-mapped loopback parsing passed host fixtures; DP and stay-awake checks are correctly placed.
- Resources’ patch checksum matches its PKGBUILD; the status renderer produces valid XML identical to the checked-in SVG.

`gpu_ab.py` is absent from this branch; I reviewed its retained version on `agent/gpu-perf-exp`. Full test suites and hardware validation were not run.
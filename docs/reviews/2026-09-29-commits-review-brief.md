# Review request: bugs in today's commits (2026-09-29)

Read-only code review. Do not run anything against the phone and do not
modify files. Find real bugs: wrong logic, races, missing error handling,
security or safety regressions, portability problems (busybox sh/awk vs
GNU), wrong assumptions about the hardware, tests that don't test what they
claim. Rank by severity; for each finding give file:line, the failure
scenario, and a minimal fix. Skip style nits.

Repository: this checkout, branch agent/production-boot-20260923. Range:
`git log 8d46ce19~1..HEAD` (0103 .. 95939b44). Also branch
agent/bootsplash (commits c9e1f9be, 65028980; merged here as 45b7b750 and
4980520d). Kernel source for context: the r91 build tree
/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source.

Most important changes to check:
- Kernel patches in `patches/linux-7.2.7/`:
  - 0103 arm64 cpuinfo "model name" from MIDR;
  - 0104 drm/msm gpu_busy_percent + msm_gpu hwmon (freq1/temp1) registered
    from msm_devfreq_init (lifetime, locking, devm on the GPU pdev,
    READ_ONCE/WRITE_ONCE, thermal zone lookup by name at read time);
  - 0105 gcc-sm8350 usb30_prim_gdsc PWRSTS_RET_ON;
  - 0106 interconnect sm8350 QoS boxes + regmap configs for mmss/gem noc
    (register ranges, QoS programming without clocks, disp nodes);
  - 0107 arm-smmu-qcom identity default domain for qcom,sm8350-mdss;
  - 0108 ams678 panel handoff (reset GPIO requested as-is, first prepare
    skipping the reset pulse) and bl_delay_ms delayed backlight work
    (races with disable/unprepare/remove, work cancellation, module unload).
- Boot/root: `initramfs/persistent-root-init` and `persistent-root-attest`
  now accept a 16-192 GiB overlay image (was 16-160); check the arithmetic,
  whole-MiB rule, and interaction with the fallback bundle.
- Updater: `initramfs/rog5-update` new `system_idle` (remote_client via
  /proc/net/tcp{,6} awk parsing, loopback/v4-mapped handling, DRM DP
  `enabled`, /run/rog5-stay-awake, systemd-inhibit shutdown blockers) and its
  tests in `scripts/device/test-rog5-update.py`.
- Sleep: `scripts/device/rog5-sleep-policy` (USB devices opt-in blocker),
  `scripts/device/rog5-usb-sleep` (systemd-sleep hook that rebinds an xHCI
  that lost its devices), tests.
- `scripts/device/rog5-perf-mode` + `configs/systemd/rog5-perf-mode.service`
  (writing skin thermal trip points; ordering; restoring; boot apply).
- `configs/NetworkManager/conf.d/60-rog5-stable-mac.conf`,
  `configs/systemd/rog5-tailscaled.service.d/60-slow-retry.conf`.
- Bench/tools: `scripts/device/bench/trial.py`, `gpu_ab.py`,
  `tools/status-map/render.py`, `packages/resources/*` (Resources patch).

Output: a markdown list of findings (severity, file:line, scenario, fix) and
a short list of things you checked and consider correct.

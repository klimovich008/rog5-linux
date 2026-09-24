# 2026-09-24: bench harness, GPU recovery, Denial smoothness

Default kernel `production-7.2.7-r13`, Denial r1 bundle, Mesa 26.2.3 freedreno
(A660, GMU v3.1.10). All numbers from `scripts/host/rog5-bench.py`; JSON in
`test-results/bench/`.

## Harness

| command | what it does |
|---|---|
| `rog5-bench.py hw` | read-only non-cellular hardware matrix (`bench/hwcheck.py`) |
| `rog5-bench.py gpu nop\|fault\|hang\|cycle N` | `gpu-recovery-probe.py`: raw msm submits, no Mesa |
| `rog5-bench.py shot [png]` | screenshot of the scanned-out buffer; UBWC is decoded by EGL dma-buf import + `glReadPixels` (`bench/scanout-read.c`, built with gcc on the phone) |
| `rog5-bench.py gesture png swipe …\|tap …` | one virtual-touch gesture, then a screenshot |
| `rog5-bench.py smooth [--repeat N] [--scenarios …]` | gestures through a uinput touchscreen cloned from the FTS3658U; tracefs `dpu_crtc_complete_flip` cadence, GPU jobs, GMU power cycles, display glitches; diff against the previous run |

Scenarios were checked by screenshot to start and end on the home screen:
quick settings open/close (close drags the handle at y≈1155), slow drag of the
same, the keyboard (the bottom swipe on the home screen opens it), and the two
home pages. The earlier "home gesture" and "edge panel" swipes both opened the
keyboard and left it up, so their first numbers were invalid.

## GPU recovery

- The 11:16:54 crash (r13, DRM debug on): `Timeout waiting for GMU OOB set
  GPU_SET` came first, then a CP read of iova 0, `hangcheck recover`, and
  `GMU firmware initialization timed out`; the GPU stayed dead and deniald
  hung in D state in `msm_gem_close`, which blocked shutdown for good (the
  watchdog never fired because systemd kept petting it; physical reset).
- The same fault injected on a healthy GPU recovers in 0.09-0.11 s (5/5), a
  hangcheck lockup in 1.9 s, and 300 slumber/cold-boot cycles show no error
  (wake 4-6 ms). Kernel recovery works; the open question is what wedged the
  GMU before the fault. Not reproduced since the console fix below.
- 5 s display wake: `console=ttyMSM0,115200 loglevel=8 ignore_loglevel` in the
  loader's signed command line printed every message synchronously; with DRM
  debug on, ~525 lines stretched each wake to ~5 s and user taps landed as
  Denial's double-tap lock gesture. The platform kit now clears
  `ignore_loglevel` and sets console level 4 first thing (r14 onwards).

## Smoothness

Baseline (r13, Denial r1): home pages 0 dropped (p95 16.8 ms), keyboard 25,
quick settings 48 (p95 40 ms, p99 86 ms), slow drag 118 dropped in 18 gestures.
Build 0.3-1 ms per frame; raster spikes 36-94 ms. perf on the raster thread:
63 % kernel, mostly shmem page allocation, clearing and cache maintenance for
new GEM buffers pinned at submit.

Denial's Impeller fork disabled `GL_EXT_multisampled_render_to_texture` on
GLES 3, so every MSAA layer got an explicit 4x renderbuffer. Patch
`patches/denial-engine/0001` restores the upstream choice; engine rebuilt
incrementally (1 object) and deployed as `/opt/denial/lib/libflutter_engine.so`
(old one kept as `.r1`). Result: quick settings 48 → 5 dropped (p95 40 → 18
ms), keyboard 25 → 7, home pages latency 49 → 25 ms, screenshots unchanged.

Still open: the slow shade drag (p95 31-68 ms, p99 ~140 ms). A kprobe on
`msm_ioctl_gem_new` counted 307 new buffers (~1.26 GB) in two drags: the layer,
stencil and blur targets change size every frame as the panel slides under
the screen edge, Impeller's `RenderTargetCache` only reuses exact sizes, and
the freedreno BO cache misses them. Next: size-stable offscreen targets or
deferred release in the engine.

## Hardware found and fixed

- Power key and volume-down: the base DTB already enables PON pwrkey/resin;
  `qcom_pon` was never loaded. Loading it created `pmic_pwrkey`/`pmic_resin`;
  it is in the boot list from r14.
- Denial battery tile ("-- mA, Waiting"): it reads denia-powerd's
  `/run/denia-powerd/battery_discharge.tsv`; `rog5-battery-log.service` now
  writes it from `qcom-battmgr-bat` (live mA, W, V and graph confirmed).
- uinput: `CONFIG_INPUT_UINPUT=m` from r14 (built out of tree for r13).
- CPU idle: no cpuidle state. The board DT drops CPU power-domain and
  idle-state references on purpose (ASUS firmware reset on OSI enable after
  kexec). RAM trial t13 with `ARM_PSCI_CPUIDLE_DOMAIN=y` switched the firmware
  to OSI mode without a reset over a 3-minute soak, but used no state;
  production keeps it off until idle states are qualified separately.
- Brightness: USB current is the same at backlight 1023 and 0 (498/501 mA):
  writes still do not reach the panel.
- Bluetooth: QCA6490 on QUP SE18 (`uart18`, 0x890000, 4-wire), BT_EN GPIO 65,
  SW_CTRL GPIO 153 (stock lahaina.dtsi); no DT node, modules or firmware yet.

## Wi-Fi and dual Wi-Fi (r15/r16)

- Link: 5540 MHz, 160 MHz HE (Wi-Fi 6), PHY 1.7-2.2 Gbit/s, -45 dBm. No
  6 GHz band on this WCN6855 hw1.1. Regulatory domain is the world domain
  `00` (passive scan, 20 dBm on 5 GHz) until a country is set.
- Throughput from Hetzner fsn1: one stream 490-680 Mbit/s (noisy), four
  streams 688 Mbit/s; the laptop gets 668 on the same network. RPS on the big
  cores made no measurable difference; the ath11k DP MSIs sit behind the
  DesignWare PCIe MSI demux and have no settable affinity.
- Dual Wi-Fi: the firmware offers `#{managed} <= 2, total <= 3, #channels <= 2`.
  A second managed interface (wlp1s1) on the router's 2.4 GHz radio while
  wlp1s0 stayed on 5 GHz: both associated with their own DHCP leases. Alone:
  5 GHz 492, 2.4 GHz 146 Mbit/s; together 313 + 133 = 446 Mbit/s. An idle
  associated second link does not cost 5 GHz throughput (565/544 vs 569).

## Console spinner (fixed in r16)

The ramdisk's stage reporter was never stopped; after switch_root its nc and
sleep were gone and the orphaned /init subshell printed errors to the
115200-baud console nonstop: ~11 KB/s, ~210 UART interrupts/s, 6.5 % CPU on
every boot. r16 stops it after the final switch-root report: UART 0 B/s,
idle system load 0.2-0.5 %.

# GPU performance: governor, thermal limits and undervolt (2026-09-29)

Bundle production-7.2.7-r185 (kernel r86), Mesa 26.2.3 (turnip), phone on
the USB-C hub (charging), screen off for every run, 5 min cool-down plus
GPU < 38 C before each run. Tool: `scripts/device/bench/gpu_ab.py` (headless
vkmark x2 + Geekbench 6 Vulkan, sampling GPU clock/load/temperature, skin
temperature and throttling cooling devices every 0.2 s). The Geekbench
links are the uploaded results.

| Run | GB6 Vulkan | GPU clock while busy | Throttled samples | Max GPU / skin |
|---|---|---|---|---|
| stock (simple_ondemand) | 4670 ([6919179](https://browser.geekbench.com/v6/compute/6919179)) | 719 MHz | 100 % | 78.7 C / - |
| min_freq 840 MHz | 4781 ([6919195](https://browser.geekbench.com/v6/compute/6919195)) | 716 MHz | 100 % | 78.4 C / - |
| **skin trips 56/57 C (stock PERF profile)** | **5405** ([6919213](https://browser.geekbench.com/v6/compute/6919213)) | **840 MHz** | 0.3 % (CPU only) | 94.2 C / 48.5 C |
| undervolt -1 corner (all OPPs) | 4269 ([6919230](https://browser.geekbench.com/v6/compute/6919230)) | 716 MHz | 100 % | 76.4 C / 44.8 C |
| undervolt -2 corners | 2908 ([6919252](https://browser.geekbench.com/v6/compute/6919252)) | 801 MHz | 39 % | 64.1 C / 42.6 C |
| stock again (drift check) | 4658 ([6919276](https://browser.geekbench.com/v6/compute/6919276)) | 716 MHz | 100 % | 80.0 C / 45.7 C |

Typical Android SD888 (Adreno 660) Geekbench 6 Vulkan: ~4509
(91mobiles). vkmark (headless, 800x600) moves little (9000-9900): it is
mostly CPU/submission bound.

## Findings

1. **The limit is the skin thermal policy, not the GPU.** The skin zone
   (msm_therm, `sm8350-asus-rog-phone5-skin-thermal.dtso`) throttles the
   GPU and both big clusters from 42 C (step_wise) and 46 C. On the charger
   the case idles at ~40 C, so the GPU is capped at 676-778 MHz for the whole
   Geekbench run, while its junction stays at ~80 C (own trip 95 C).
   A min_freq floor does nothing against it.
2. **Stock's own profiles:** `vendor/etc/thermal-engine.conf` on the
   virtual-therm (= msm_therm) sensor: NORMAL caps from 36 C, GAME from
   39 C, **PERF only from 56 C** (778 MHz), 57 C (738 MHz); shutdown
   ladder 58/63/65 C. With the PERF thresholds (trip_point writes at
   runtime; trips are writable) the GPU holds 840 MHz: **+16 % (5405)**,
   skin 48.5 C, GPU junction touching its 95 C trip briefly.
3. **Undervolting is counterproductive.** The GPU's ACD (adaptive clock
   distribution, enabled from stock's bin-0 table) answers a lower GX corner
   by stretching the clock internally: -1 corner = -9 %, -2 corners = -38 %
   at the same or higher *reported* clock. It does lower temperature
   (-2: 64 C GPU), so it only makes sense with ACD off, which needs the full
   voltage margin by design; not pursued. The knob (`msm.gpu_corner_offsets`)
   stays for experiments; it resets at boot.
4. **Governor:** simple_ondemand does drop to 315 MHz between Geekbench's
   short kernels (~18 % of samples in every run), but pinning 840 MHz under
   the normal thermal policy gave only +2 % because the thermal cap
   dominated. Worth re-checking together with the PERF thermal profile.

## Candidates still open

- A user-selectable performance mode (skin trips 56/57 C, like stock X
  Mode's PERF profile) with the normal policy as default.
- Kernel experiment r186 (`agent/gpu-perf-exp`, patch 0107): LLCC GPU slice
  write-allocate (downstream `wse = 1`, mainline table leaves it off).
  Built and packaged, not yet booted.
- The drirc `tu_restrict_subgroup_size_64` workaround applies to all apps;
  it could be limited to Geekbench.

## r186: LLCC GPU slice write-allocate (0107 on agent/gpu-perf-exp)

Same method. PERF thermal limits (840 MHz held, the fair comparison):
GB6 Vulkan 5448 ([6919340](https://browser.geekbench.com/v6/compute/6919340))
vs 5405 on r185 (+0.8 %, noise). Normal limits: 4950
([6919325](https://browser.geekbench.com/v6/compute/6919325)), but that run
started 3 C cooler and was throttled 64 % of the time instead of 100 %, so it
is not comparable. No measurable benefit: not carried into production.

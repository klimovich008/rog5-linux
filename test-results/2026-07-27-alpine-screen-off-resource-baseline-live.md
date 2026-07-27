# Alpine screen-off server resource attribution — live read-only result

Date: 2026-07-27

Result: **PASS for redacted RAM attribution and a short screen-off
CPU/thermal stability baseline on the persistent Alpine fallback. This is
not battery-depletion, Linux 7.1, accelerated rendering, or Arch/KRDP
acceptance.**

The phone remained on installed Alpine 3.24.0 and kernel
`5.4.134-qgki-perf-00001-g6c308144c23e`. The two repository collectors were
streamed to `sh -s` over the existing pinned SSH connection; neither script
was installed or written to phone storage. No service, process, screen,
driver, module, network configuration, account, credential, NFS state,
reboot, or boot state changed.

## Why a second collector was needed

The accepted `collect-baseline.sh` intentionally aggregates only selected
Plasma processes. The earlier remote-GUI checkpoint therefore measured the
whole desktop/browser memory delta but could not attribute it between:

- Plasma/KWin desktop processes;
- Chromium's multi-process tree; and
- Xvnc/noVNC/ttyd remote transport.

Changing the accepted collector would invalidate the byte-exact successor
v1–v3 root evidence. The new `collect-component-pss.sh` is separate,
read-only, and not staged into any accepted root. It reads only process names
from `/proc/*/status` and proportional set size from
`/proc/*/smaps_rollup`.

Its fixed categories are:

- desktop: KWin, Plasma shell, KDE daemons/activity/session helpers, KScreen,
  and desktop portals;
- browser: Chromium/Chrome and crashpad helpers; and
- remote: Xvnc/TigerVNC, KRDP, Openbox, ttyd, websockify, and x11vnc.

It reports process count, readable-PSS count, category PSS, and total managed
PSS. If any matching process lacks readable PSS, that category and the
managed total report `unavailable` rather than an incomplete number.
Arguments, environments, descriptors, addresses, MACs, SSIDs, serials, and
credentials are never read.

## Current screen-off snapshot

The accepted baseline collector reported:

```text
memory_total_kib=11583016
memory_available_kib=10565128
memory_used_kib=1017888
swap_total_kib=3145724
swap_used_kib=0
thermal_zone_count=73
thermal_max_millidegree_c=39800
screen_state=off
backlight_brightness=0
dsi_status=connected
gpu_model=Adreno660v2
gpu_reset_count=0
gpu_fault_count=0
```

The physical panel remained off while the nested remote desktop and browser
services stayed available.

## Component PSS attribution

All selected processes had readable `smaps_rollup` data:

| Component | Processes | PSS KiB | Approx. MiB |
|---|---:|---:|---:|
| KDE desktop | 6 | 399,347 | 390.0 |
| Chromium | 11 | 353,265 | 345.0 |
| remote transport | 4 | 68,306 | 66.7 |
| total managed stack | 21 | 820,918 | 801.7 |

Plasma plus Chromium therefore account for about 752,612 KiB, or 91.7% of
the measured managed GUI stack. This supports the existing design: keep
headless server mode as the default and start the compositor/browser only
when their capabilities are needed.

## Stability samples

A full-collector 30-second comparison remained stable:

```text
memory_available_kib=10564980 -> 10565012
swap_used_kib=0 -> 0
thermal_max_millidegree_c=40100 -> 40100
screen_state=off -> off
backlight_brightness=0 -> 0
desktop_pss_kib=399354 -> 399376
browser_pss_kib=353267 -> 353265
remote_pss_kib=68308 -> 68328
managed_pss_kib=820929 -> 820969
```

That interval's 2.23% CPU result was rejected because it included four
expensive process/PSS scans. A separate single-session sample read only
aggregate CPU counters around a 30-second sleep:

```text
cpu_busy_percent=0.78
load_1m=3.56 -> 3.34
screen_state=off -> off
backlight_brightness=0 -> 0
```

## Load-average explanation

The high load with low CPU came from three vendor-kernel threads in
uninterruptible state:

| Thread | Wait function |
|---|---|
| `soc:qcom,svm_ne` | `protocol_block_server_thread` |
| `hdcp_2x` | `sde_hdcp_2x_main` |
| `dp_hdcp2p2` | `dp_hdcp2p2_main` |

Each thread accumulated exactly zero scheduler runtime nanoseconds and zero
timeslices during a separate 15-second sample. They explain the load-average
floor but did not consume scheduled CPU in that interval. This does not prove
zero hardware power impact, so disabling HDCP or secure-VM functionality
based only on load average would be unjustified.

## Measured optimization decision

No service or package removal is justified on this 11 GiB device:

- approximately 10.1 GiB remained available;
- swap use stayed zero;
- PSS and available memory were stable; and
- low-overhead aggregate CPU remained below 1% for the short interval.

The useful reversible controls are already the intended target policy:

1. headless server mode by default;
2. stop Chromium when browser automation is not needed, avoiding roughly
   345 MiB PSS in this baseline;
3. stop the nested/physical Plasma session when no GUI is needed, avoiding
   roughly 390 MiB PSS in this baseline; and
4. retain the smaller remote shell/transport path independently.

These Alpine numbers are not limits for Arch and must be remeasured with
physical KWin/DRM, KRDP, hardware rendering, and representative automation
workloads.

## Battery limitation

The installed 5.4.134 fallback exposes no Battery-class power-supply node:

```text
battery_present=no
```

Its module tree does not match the separate 5.4.210 charger/ADSP modules.
Those modules must never be force-loaded into this kernel. Battery current,
charging behavior, and depletion remain unaccepted until a matching kernel
provides audited telemetry. Thermal and CPU evidence cannot substitute for
wall-power or battery measurements.

## Test and source identities

The fail-first test commit is `d30a626`; it initially returned:

```text
FAIL missing executable component PSS collector
```

Implementation commit `3b9f9b6` adds the separate collector and delegates
its fixture to the full Linux-rootfs aggregate.

| Input | SHA-256 |
|---|---|
| accepted baseline collector, unchanged | `2726ffda517aa13d97da4c9b04712524ccded2ba6ac25f2021f337a10523b946` |
| component PSS collector | `c0413eb430949f95f7250d6fca9c93b0de0b7300a88e5b77cd0efd554873aee5` |
| component fixture test | `50d95d84267028275bcc30fdbc11a7529ea3f7be86bb74cc59ae25913c82ad40` |
| aggregate Linux-rootfs test | `54eec377dbc5d800ebf68465b58e8b231b919d85711f09476b5c4193724faef8` |

Validation returned:

```text
PASS redacted component PSS collector attributes desktop, browser, and remote-stack memory without process arguments
PASS Linux rootfs tools pin signed input, preserve metadata, and avoid phone writes
```

POSIX syntax, ShellCheck at warning severity, missing-PSS fail-closed
behavior, relative-root rejection, forbidden-source scanning, exact accepted
collector hash, live streamed execution, and `git diff --check` pass.

## Remaining acceptance

- Repeat component PSS and low-overhead CPU samples on successor v3 after a
  separately authorized boot.
- Compare headless, Plasma, KRDP, Chromium, panel-on, and panel-off states
  under fixed workloads.
- Measure battery or wall power only with matching audited charger telemetry.
- Correlate refresh-rate profiles, Wi-Fi/VPN hotspot load, charging, and
  sustained GPU/AI workloads with thermals and energy use.
- Do not infer Linux 7.1 GPU, display, power-button, KRDP, VPN, or hotspot
  acceptance from this vendor-Alpine baseline.

# DP link policy power on the MSI monitor (r206, 2026-09-30 19:20-19:46)

Phone on bundle production-7.2.7-r206 (kernel r109 with 0145), GNOME desktop mode on the MSI (3840x1080@60, 10 bpc), idle desktop, phone on hub power in bypass (battery idle), power measured at the USB input. `rog5-dp-power-measure matrix --label=r206-msi-3840x1080-idle --power=input`, 3 rounds, rotated order, 45 s settle + 120 s per window, retrain by GNOME DPMS off/on.

```
rog5-dp-power-measure 20260930T172002Z  power=input  load=idle

config      link                            n  W mean     sd      d vs max     MMCX  cpu%  skin C   xo C
max         4x540M 30bpp 46.3%              3   2.072  0.031             -      192   0.9    34.2   35.1
narrow      2x540M 30bpp 92.5%              3   2.010  0.012    -62+-19 mW      192   0.8    34.0   34.9
efficient   4x270M 30bpp 92.5%              3   2.024  0.026    -48+-30 mW      128   0.8    34.0   34.9

d = mean of per-round differences to the first config (+- sd over rounds,
descriptive, not a confidence interval); a difference smaller than ~2 sd is not
resolved. MMCX: 128 svs, 192 svs_l1, 256 nom.
results: /var/lib/rog5-dp-power-measure/20260930T172002Z

[exited with code 0]
```

Result: both reduced links save ~50-60 mW (~3 % of the phone's total) vs the old max link; narrow (2xHBR2) and efficient (4xHBR) are not resolved from each other. Efficient lowers MMCX from SVS_L1 to SVS. No measurable temperature difference (skin 34 C). Kept msm.dp_link_policy=1 (efficient) as the default. Raw data on the phone: /var/lib/rog5-dp-power-measure/20260930T172002Z.

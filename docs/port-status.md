# Subsystem port status

| Subsystem | 5.4.210 baseline | Linux 7.1 upstream base | ASUS work remaining |
|---|---|---|---|
| reversible boot | passing | v18 staging/rollback and v3 retained-exitrd normal reboot pass | repeat clean cycles and retain the same boundary for each new DTB tier |
| UFS root | passing baseline only | no-mount discovery passes; network-root v3 boots and reboots normally with UFS compiled out | design persistent storage only after explicit approval and recovery retest |
| USB NCM/SSH | passing | Linux 7.1 normal-coldplug NCM/NFS and persistent client/server SSH identities pass twice | convert the attended PC-backed transport into an independent deployment path |
| battery/charging | passing | guarded read-only SM8350 battery/USB/wireless telemetry passes through audited ADSP QRTR/PDR and battery-only PMIC GLINK | repeat physical-state/current-direction checks, dual-cell topology, then separately review charging; controls remain disabled |
| thermals/CPUfreq | passing | 33 thermal zones are readable and sane in two normal network-root boots | cooling maps, cpufreq policy checks, sustained-load characterization |
| OLED/DPU/DSI | passing with vendor DRM | DPU/DSI present | AMS678 ER2 plus missing Pixelworks Iris/i6 bridge path |
| touch/power button | passing | input framework present | exact FocalTech main/rear controllers and GPIO/pinctrl |
| GPU | rejected: KGSL second-open fault | GPUCC-only v13 proves the new GPUCC orphan completes, records the existing DISPCC pixel-clock provider as runtime-suspended, and enters its `get_parent()` callback without returning; v14 reproducibly brackets the callback's one existing RCG regmap read and passes offline only; A660 DRM/MSM remains untested | run one attended zero-storage v14 diagnostic with independent rollback, then design any PM/lock fix separately before continuing power-domain/clock/regulator/IOMMU/GMU/firmware and full Tier 5 validation |
| Wi-Fi/hotspot | passing | ath11k modules and fail-closed VPN routing test pass offline | board PCIe/power/calibration/firmware and device routing tests |
| modem/DSPs | passing with delayed startup | ASUS reserved-memory contract and ADSP-only PAS/SCM startup pass | CDSP/modem/SLPI firmware names and one-processor-at-a-time validation |
| audio | basic services present | Qualcomm audio frameworks present | codecs, routing, speakers, microphones, headset safety |
| cameras/sensors | not a server requirement | partial generic frameworks | deferred until core server release |
| BTF/eBPF | BPF present, BTF absent | BTF generated and verified in 7.1 build | boot-time verifier/load tests, then optional GodShell systemd service |
| KDE remote UI | software-rendered | userspace-independent | switch to hardware only after GPU gate passes |

“Present upstream” means the SoC framework exists, not that the phone is supported. No row becomes passing until its device test succeeds without new kernel warnings, resets, or recovery loss.

The historical v2 staging root was writable physical UFS and its target DTB
enabled UFS and QMP/SuperSpeed. Its former zero-storage/USB2-only classifications
are withdrawn; v2 is superseded and must not be booted. Nothing was flashed.

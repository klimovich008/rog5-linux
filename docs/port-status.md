# Subsystem port status

| Subsystem | 5.4.210 baseline | Linux 7.1 upstream base | ASUS work remaining |
|---|---|---|---|
| reversible boot | passing | v18 staging passes twice; Linux 7.1 target and rollback pass once | retain the same boundary for each new DTB tier |
| UFS root | passing baseline only | Linux 7.1 recovery kept UFS disabled and exposed zero physical devices | build a separate no-mount read-only UFS discovery tier |
| USB NCM/SSH | passing | Linux 7.1 credential-free ACM/NCM pass; v17 keyed SSH passed | retain ACM/NCM through UFS discovery; keep SSH key-only and explicit |
| battery/charging | passing | PMIC GLINK/power supply framework present | dual-battery/charger topology and current-direction validation |
| thermals/CPUfreq | passing | SM8350 thermal/cpufreq infrastructure present | board zones, cooling maps, sustained-load characterization |
| OLED/DPU/DSI | passing with vendor DRM | DPU/DSI present | AMS678 ER2 plus missing Pixelworks Iris/i6 bridge path |
| touch/power button | passing | input framework present | exact FocalTech main/rear controllers and GPIO/pinctrl |
| GPU | rejected: KGSL second-open fault | A660 DRM/MSM present | firmware/IOMMU/GMU DTS and full Tier 5 validation |
| Wi-Fi/hotspot | passing | ath11k modules and fail-closed VPN routing test pass offline | board PCIe/power/calibration/firmware and device routing tests |
| modem/DSPs | passing with delayed startup | Qualcomm remoteproc present | reserved memory, firmware names, one-processor-at-a-time validation |
| audio | basic services present | Qualcomm audio frameworks present | codecs, routing, speakers, microphones, headset safety |
| cameras/sensors | not a server requirement | partial generic frameworks | deferred until core server release |
| BTF/eBPF | BPF present, BTF absent | BTF generated and verified in 7.1 build | boot-time verifier/load tests, then optional GodShell systemd service |
| KDE remote UI | software-rendered | userspace-independent | switch to hardware only after GPU gate passes |

“Present upstream” means the SoC framework exists, not that the phone is supported. No row becomes passing until its device test succeeds without new kernel warnings, resets, or recovery loss.

The historical v2 staging root was writable physical UFS and its target DTB
enabled UFS and QMP/SuperSpeed. Its former zero-storage/USB2-only classifications
are withdrawn; v2 is superseded and must not be booted. Nothing was flashed.

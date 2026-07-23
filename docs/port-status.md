# Subsystem port status

| Subsystem | 5.4.210 baseline | Linux 7.1 upstream base | ASUS work remaining |
|---|---|---|---|
| reversible boot | passing | image, modules, and serial skeleton cross-build pass | recovery DTS hardware, packaging, and temporary boot image |
| UFS root | passing | controller/PHY rails and reset translated but kept disabled | recovery packaging, read-only temporary-boot enablement |
| USB NCM/SSH | passing | left-side USB1 controller/PHY rails mapped but disabled | gadget initramfs and temporary-boot test |
| battery/charging | passing | PMIC GLINK/power supply framework present | dual-battery/charger topology and current-direction validation |
| thermals/CPUfreq | passing | SM8350 thermal/cpufreq infrastructure present | board zones, cooling maps, sustained-load characterization |
| OLED/DPU/DSI | passing with vendor DRM | DPU/DSI present | AMS678 ER2 plus missing Pixelworks Iris/i6 bridge path |
| touch/power button | passing | input framework present | exact FocalTech main/rear controllers and GPIO/pinctrl |
| GPU | rejected: KGSL second-open fault | A660 DRM/MSM present | firmware/IOMMU/GMU DTS and full Tier 5 validation |
| Wi-Fi/hotspot | passing | ath11k modules and fail-closed VPN routing test pass offline | board PCIe/power/calibration/firmware and device routing tests |
| modem/DSPs | passing with delayed startup | Qualcomm remoteproc present | reserved memory, firmware names, one-processor-at-a-time validation |
| audio | basic services present | Qualcomm audio frameworks present | codecs, routing, speakers, microphones, headset safety |
| cameras/sensors | not a server requirement | partial generic frameworks | deferred until core server release |
| BTF/eBPF | BPF present, BTF absent | BTF generated and verified in 7.1 build | boot-time verifier/load tests, then optional GodShell/OpenRC port |
| KDE remote UI | software-rendered | userspace-independent | switch to hardware only after GPU gate passes |

“Present upstream” means the SoC framework exists, not that the phone is supported. No row becomes passing until its device test succeeds without new kernel warnings, resets, or recovery loss.

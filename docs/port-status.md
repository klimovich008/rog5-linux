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
| GPU | exact firmware requests and rollback-safe ucode allocation pass; v8 GMU entry reached but userspace oracle rejected safely; corrected v9 runtime, protected root, runner, and local GO controls pass offline | v3 accepts registration and v4 exact SQE/GMU requests; v5/v6 are consumed oracle diagnoses; v7 accepts raw-size-pinned allocation/rollback and equal settled GEM state; v8 reached exact GMU entry/rollback, then safely rejected zero-extended returns and an unscoped generic-PM count and is consumed; the [v9 offline runtime](../test-results/2026-07-26-a660-gmu-resume-entry-v9-runtime-offline.md) keeps the exact v8 module, normalizes signed 32-bit returns, matches one GPU-device PM event among 21 generic events, reproduces controls, and rejects twelve mutations; the [v9 protected root](../test-results/2026-07-26-a660-gmu-resume-entry-v9-root-offline.md) preserves the unchanged kernel/seven-module/two-firmware payload and credentials behind an exact-delta verifier and compound target gate; the [v9 pre-live HOLD](../test-results/2026-07-26-a660-gmu-resume-entry-v9-prelive-hold.md) adds a strict no-retry runner and credential/root checks; the [GO review HOLD](../test-results/2026-07-26-a660-gmu-resume-entry-v9-prelive-go-hold.md) adds a verifier-first server case and exact package audit but stops before NFS because no phone is present | connect exact persistent fallback and rerun its identity-pinned health preflight plus every GO gate; no live v9 or GMU power authority yet; only after acceptance isolate GMU power, HFI, and ZAP/SCM before successful open, submission, or rendering |
| Wi-Fi/hotspot | passing | ath11k modules plus namespace packet tests for VPN-only forwarding, IPv4/IPv6 leak blocking, unsolicited isolation, VPN loss, and cleanup pass offline | board PCIe/power/calibration/firmware, real WireGuard handshake, AP/DHCP/DNS, and device packet/thermal tests |
| modem/DSPs | passing with delayed startup | ASUS reserved-memory contract and ADSP-only PAS/SCM startup pass | CDSP/modem/SLPI firmware names and one-processor-at-a-time validation |
| audio | basic services present | Qualcomm audio frameworks present | codecs, routing, speakers, microphones, headset safety |
| cameras/sensors | not a server requirement | partial generic frameworks | deferred until core server release |
| BTF/eBPF | BPF present, BTF absent | BTF generated and verified in 7.1 build | boot-time verifier/load tests, then optional GodShell systemd service |
| KDE remote UI | software-rendered | userspace-independent | switch to hardware only after GPU gate passes |

“Present upstream” means the SoC framework exists, not that the phone is supported. No row becomes passing until its device test succeeds without new kernel warnings, resets, or recovery loss.

The historical v2 staging root was writable physical UFS and its target DTB
enabled UFS and QMP/SuperSpeed. Its former zero-storage/USB2-only classifications
are withdrawn; v2 is superseded and must not be booted. Nothing was flashed.

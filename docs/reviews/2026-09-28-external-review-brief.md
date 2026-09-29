# Review request: ROG Phone 5 mainline Linux, week of 2026-09-22

Please review the code and the reasoning below and point out gaps, wrong
assumptions, risky changes, missed simpler solutions and anything that looks
fragile. Read-only review: do not run commands against the phone and do not
change files; answer in text.

## Goal
ASUS ROG Phone 5 (Qualcomm SM8350, Haven/Gunyah hypervisor) as a fully usable
Linux phone (Arch Linux ARM + Phosh) that also works as a Linux server with
USB hubs, is reliable, fast when needed and efficient in standby.

## Where things are
- Repo (branch agent/production-boot-20260923):
  ~/.local/state/rog5-prod-boot-20260923
  - Kernel patches for 7.2.7: patches/linux-7.2.7/ (series.production,
    series.diagnostic); build: scripts/host/build-rog5-production-kernel.py
  - Device-tree overlays: dts/qcom/*.dtso, composed by
    scripts/device/compose-production-dtb.sh (feature list argument)
  - Boot ramdisk: initramfs/persistent-root-init, persistent-root-attest,
    rog5-update (unattended updater)
  - Device scripts/services: scripts/device/, configs/systemd/, configs/*
  - Test evidence: test-results/ (2026-09-27-phosh-suspend.md,
    2026-09-28-haven-watchdog-0088.md, 2026-09-28-bottom-usb-port.md)
- Patched kernel tree (read-only): ~/.local/state/rog5-kernel-7.2.7-build-r71/source
- Stock ASUS 5.4 kernel/DT for reference:
  ~/.local/state/rog5-kernel-compare-20260927/stock,
  ~/.local/state/rog5-stock-payload-20260927/dtbo/dtbo0.dts
- `git log --since=2026-09-22` in the repo: ~300 commits with reasons.

## What changed this week (current default: r167 = kernel r70 + DTB platform-cpucap-dtb-r1)
1. Battery/charging: battmgr fixes (0078), charge limit / bypass through ASUS
   OEM glink messages (0082).
2. Audio: 24-bit speakers (0079), built-in microphones (VA macro, 0083).
3. Display: DPU top-down allocation for DP (0080); DP alt mode still broken
   (see open items).
4. Power: geni serial powers down in suspend (0081, releases XO); PCIe L0s
   off (0077); UFS switched to mainline power management (containment
   dropped); GPU ACD, L3 scaling, skin thermal zones (DT features).
5. Reliability: Haven hypervisor watchdog enabled (0088: qcom_scm registers
   gunyah-wdt on this machine despite SMCCC 1.0; bark 3 s before bite; kernel
   pets it from probe; PID 1 keeps softdog). Verified: hard hang -> reset in
   ~40 s. Phosh auto-restart after crashes.
6. Bottom USB-C port as a USB 2.0 host (0089: 5 V source through a battmgr
   OEM message + PM8350C GPIO4 fixed regulator; 0090: usb30_sec_gdsc
   RET_ON; rog5-usb-bottom on/off tool).
7. Performance: CPU capacity + energy model from stock DT (cpucap feature)
   plus a uclamp.min=400 floor for the graphical session
   (scripts/device/rog5-session-boost) -> single-thread lands on the X1.
8. Server: nftables input firewall (configs/firewall), kernel netfilter
   options for Tailscale/containers, NetworkManager manages USB Ethernet,
   journal capped at 200 MB (the updater snapshots the whole overlay upper).

## Open problems where a second opinion helps most
A. Deep sleep never reached: AOP sys-PM violator log (CXPC mode) shows only
   DDR_AUX=5 while suspended; cxsd/aosd/ddr LPM counters stay 0; DDR at
   200 MHz in suspend with ~14 up-transitions/min. Ruled out: HLOS XO/CX
   votes, display RSC and the whole display/GPU stack, LLCC table, USB cable
   (real unplug), bwmon/input boost, IPA ipa_pc, SLPI stop, smp2p sleepstate
   bit, wrapper-started subsystems. APSS reaches the deepest cluster state.
   Notes: test-results/2026-09-27-phosh-suspend.md, memory of experiments in
   scratchpad. What is missed?
B. DP alt mode through a USB-C HDMI hub: see
   <session-scratchpad>/dp-research/COMBINED.md
   (orientation not applied to the SBU mux/PHY; msm_dp PUSH_IDLE on a dead
   link hangs the SoC, fixed by 0091; open: dark monitor in the good
   orientation — reconnect helper, 10-bit colour vs HDMI converter, or 3D
   merge route).
C. The 16 GiB overlay image (/ is overlay(lower p24 ro, upper = fixed 16 GiB
   ext4 image on userdata)). Plan to allow 16-256 GiB in persistent-root-init
   and -attest, rebuild default and fallback ramdisks, then grow online.
   Is the plan sound; what could brick the boot?
D. uclamp/EAS approach (item 7): power cost and failure modes.
E. Anything in the 0088 watchdog approach that could cause spurious resets.

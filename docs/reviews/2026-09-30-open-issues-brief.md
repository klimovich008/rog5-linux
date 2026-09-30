# Brief: what should we research and test next? (2026-09-30 evening)

Goal (user): a fully usable Linux phone (ASUS ROG Phone 5, SM8350) that also works as a Linux server with USB hubs; reliable; maximum performance when needed; power-efficient standby.

Running now: bundle production-7.2.7-r204 = kernel r108 (patch series patches/linux-7.2.7/series.production up to 0144) + DTB r9 (compose feature list touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,audio,slpi,usbotg,osi,aoss,qupicc,dp,l3,skin,acd,cpucap,usbbtm,mic,usbbtmtc,memx). Fallback entry safe-r7. Phosh default shell, GNOME desktop mode on an external monitor (switcher in manual mode), native arm64 Steam with FEX for x86 games.

Done/verified today:
- DPU/DSPP blue-screen fix (0130-0135); GNOME without the DPU clock pin.
- Speaker loudness: PipeWire S16LE (q6asm 24-bit front end was 48 dB low); 0125-0127 fix the 24-bit path (V4 Q23) but not yet A/B tested; CS35L45 protection DSP running.
- 4-lane DP (0136-0139): on r202 verified 4 x HBR2 both orientations after a replug; boot with monitor attached had no DP notification from the ADSP (UCSI came up ~1.8 s earlier than older boots) - suspected ADSP boot race; not yet retested on r204.
- Bottom USB-C stage B (RT1715 + TCPM) works on r204 thanks to 0144 (PDC SPI edge/level register); CX-collapse retention of that register unproven.
- Ifetch-only external aborts on phys 0x34b4xxxxx/0x34bcxxxxx (ASUS wrapper's QTEE shmbridge left registered R/W no-X): DT no-map 0x34a000000+64M (memx) + rog5-sea-retire service.
- Turnip 8-bit storage on A660 (packages/mesa) installed: DXVK 3.x works for native ARM64 Proton; x86 Proton (FEX's x86 Mesa) still unpatched. BioShock runs on Proton 9.
- Steam title-bar drag via LD_PRELOAD shim (build-id pinned).
- Host disk cleanup.

Known open items (see docs/current-state.md, docs/status/components.json, docs/whats-left*.md, docs/user-irritations*.md, test-results/, docs/reviews/ for detail):
- Standby: ~79 mA suspended vs ~100 mA idle; no CX/DDR collapse reached; standby bisect kit exists (scripts/device/compose-standby-bisect-dtb.sh, rog5-standby-bisect-measure).
- Side-port USB error -71 intermittently on replug.
- Desktop-mode switcher back to automatic needs a supervised boot test.
- 5120x1440@60 and 3840x1080@100 need msm.dpu_mode_clk_check=halved tests; HBR3 opt-in untested.
- Speaker robustness (20 start/stops, s2idle, reboot, 5-min loud); the r202 boot showed "cs35l45 Failed to set mailbox cmd 1 / SPK DSP1 event failed -42" on every stop (0 on r204 so far).
- q6asm 0126 cleanup P2 (Sol); inherited msm native-HPD teardown P1 (not reached on ROG5).
- Flash drive present at boot isn't auto-mounted.
- HDR later. Cameras, modem/cellular, GPS, fingerprint status: check components.json.

Please (read-only): read the repo docs above, then give a prioritised list (P0/P1/P2) of (a) research questions, (b) phone tests the user should run next with exact pass criteria, and (c) engineering gaps against the goal (server use with hubs, reliability, performance, standby power) that nobody is tracking. Be concrete: file paths, commands, expected log lines. Flag anything in today's changes (0144 PDC writes to every PDC IRQ's SPI config, memx, stage B, the shim, the Mesa package) that could bite later (suspend/resume, updates, fallback boot, trial boots through the 128 MiB RAM wrapper).

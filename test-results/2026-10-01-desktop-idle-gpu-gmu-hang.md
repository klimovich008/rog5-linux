# Desktop-mode idle hand-back killed Steam's shader compilation; GMU stopped answering and msm deadlocked (main-k111-d10-261001b, 2026-10-01 13:22-13:39)

Evidence: `journalctl -b <732f119b>` on the phone (boot 12:51:02-13:39:25).

## Timeline

- 13:22:25 Steam (native arm64 client, GNOME desktop mode on the MSI MPG 491C) starts
  Fossilize ("processing Vulkan shaders"). No input after this.
- 13:32:25 `rog5-desktop-mode: GNOME idle -> Phosh`: exactly GNOME's 600 s idle-delay
  after the last input. GNOME and with it Steam/fossilize are stopped;
  gnome-shell does not stop within 5 s and is SIGKILLed at 13:32:31.
- 13:32:31-36 Phosh/phoc start (DSI + DP modeset at 5120x1440).
- 13:32:37.656 `a6xx_gmu_set_oob: Timeout waiting for GMU OOB set GPU_SET: 0x0` (hw_init
  of phoc's first submit after a GPU resume; the GMU booted but never acknowledged).
- 13:32:37.722 hang IRQ `gpu fault ring 0 fence 31818 ... rb 0000/0fb9 ib1 0/0 ib2 0/0`,
  .723 `hangcheck recover!`, .747 offending task phoc, .748
  `*** gpu fault: iova=0 dir=READ type=TRANSLATION source=CP`, .768 a6xx_recover's dump.
- 13:32:39 `GMU watchdog expired`. Then no GPU message at all; Phosh restart loop
  (13:35:35 killed, counter 3 at 13:38:36), phone frozen, sshd MaxStartups drops.
  Hard reboot by the user.

`rog5-gmu-bind 3d6a000.gmu:` in these lines is only the GMU device's driver name
(tools/gmu_bind binds an empty driver for fw_devlink); the messages and the GMU IRQ
handlers are msm's (a6xx_gmu.c). msm.gpu_corner_offsets (0102) was empty: no undervolt.
First GMU OOB timeout in the ~30 boots in the journal.

## Root causes

1. Desktop mode: the idle hand-back counted only input (GNOME IdleHint). Steam's shader
   compilation, a game played with a pad, music or a download have no input.
2. msm (upstream too, v7.3-rc5 / msm-next unchanged):
   - `msm_gpu_submit()` ignores `msm_gpu_hw_init()`'s error: after the unanswered OOB
     request the ring of an uninitialised CP was written; the CP fetched from iova 0
     (rptr 0, ib1/ib2 0) and phoc's innocent submit was blamed.
   - Deadlock: the stalled SMMU fault re-armed `fault_coredump_done` and waited for
     `gpu->lock` (devcoredump); the recover worker held `gpu->lock` and, in
     a6xx_recover -> runtime suspend -> a6xx_gmu_shutdown (needs_hw_init still set),
     asked the dead GMU for GPU_SET again, then waited for `fault_coredump_done` without
     limit. No second OOB timeout was ever printed; every GPU client blocked.
   - A failed hw_init at the end of a6xx_recover was ignored too (replay writes the rings).
3. No watchdog covered it: the persistent-root emergency-reset watchdog is a boot
   watchdog (disarmed at 13:06:44 once P2 and the SSH identity were published), PID 1
   kept petting softdog, the Haven watchdog bites only stuck CPUs.

Why the GMU stopped answering is not known (firmware and HFI start succeeded; GX
power-up for GPU_SET never acknowledged; its own watchdog bit 1.5 s later).

## Fixes (branch agent/gpu-recovery-desktop-idle-20261001)

- `rog5-desktop-mode`: work in progress (fossilize_replay / SteamLaunch processes, audio,
  logind idle inhibitors, a focused fullscreen Xwayland window, GNOME's own idle
  inhibitors when idle) holds a GNOME idle inhibitor (gnome-session-inhibit) and blocks the
  idle hand-back. GNOME lock still hands back at once; the start path is unchanged.
  `rog5-gnome.service`: `ROG5_DESKTOP_IDLE_DELAY` (600 s, 0 = never).
- Kernel 0152: no ring writes after a failed hw_init; the submit and all later ones are
  deferred and the recover worker restarts GMU and GPU and replays them in order (no
  submit blamed); retry via the hangcheck timer while it keeps failing; 2 s bound on the
  GMU/HFI waits for a fault devcoredump; read-only `msm.gpu_init_failures`,
  `msm.gpu_recovering`, `msm.gpu_recoveries`, `msm.gpu_inits_ok`. Compiled (whole
  drivers/gpu/drm/msm) with the k111 config, W=1, KCFLAGS=-Werror.
- `rog5-gpu-watchdog` (new service): blocking read of the kernel log; 60 s after a GPU/GMU
  error it samples the parameters, again 10 s later; dead = inits failing at both samples
  with no successful init between, or the same recovery running at both. Then sysrq w,
  a transient fallback unit without shutdown dependencies (sysrq s/u/b after 120 s), and
  `systemctl reboot`. Exits on a kernel without 0152.

Offline tests: test-rog5-desktop-mode-events.sh (11 new cases), test-rog5-gpu-watchdog.sh
(12 cases). Reviewed by GPT-6.1-Sol in three rounds (findings fixed: deferred-submit order also after a failed recovery, closed contexts in the replay,
hangcheck after replay, fallback unit outliving the shutdown (Type=exec, SurviveFinalKillSignal), two-sample incident identity,
pre-idle work check, kmsg read failure, value validation; kernel part CONFIRMED in round 3). Phone checks (read-only): the work queries take 0.14 s; the kmsg reader sees
only new records on the real /dev/kmsg.

## Still to do on the phone

1. Build a kernel with 0152 (k112), boot it in a bundle, check `grep .
   /sys/module/msm/parameters/gpu_{init_failures,recovering,recoveries,inits_ok}`
   (0, N, 0, growing).
2. Install userspace (`rog5-install-userspace`), `systemctl enable --now
   rog5-gpu-watchdog`, `systemctl restart rog5-desktop-mode`.
3. Desktop mode: start Steam's shader processing (or `systemd-inhibit --what=idle sleep
   900`, or play audio), no input for > 10 min: GNOME must stay, journal shows
   "work in progress (...)"; afterwards GNOME idles and hands back to the PIN screen.
4. GPU: a hang test (e.g. a Vulkan app that hangs) must log "hangcheck recover!" and
   "GPU recovered" from the watchdog, no reboot.

# Brief: sleep policy, perf mode, USB storage (2026-09-30)

Review, read-only, for correctness bugs and safety holes. The changes are
uncommitted in this worktree (`git diff HEAD -- scripts/device/rog5-sleep-policy
scripts/device/test-rog5-sleep-policy.sh scripts/device/rog5-perf-mode
scripts/device/test-rog5-perf-mode.sh` plus the new files listed below).
Context: items 5 and 9 and the gap table of
docs/reviews/2026-09-30-gpt-6.1-sol-open-issues-evening.md.

1. scripts/device/rog5-sleep-policy (loop every 5 s; suspends with
   `systemctl suspend --check-inhibitors=no` because rog5-server-inhibit,
   packaging/arch/rog5-server-inhibit.service, holds a permanent
   `sleep:handle-power-key` block): new reasons to stay awake on battery with
   the screen off: ALSA playback substream RUNNING/DRAINING
   (/proc/asound/card*/pcm*p/sub*/status), a logind block-mode inhibitor whose
   WHAT includes sleep from anyone except WHO rog5-server (busctl
   ListInhibitors parsed in awk), and external power beyond
   qcom-battmgr-usb/online: any other online USB/Mains/Wireless power_supply
   (UCSI connector psy online = partner sources VBUS), or charge_behaviour not
   [auto] while /sys/class/typec/port*-partner exists (force-discharge makes
   battmgr-usb read online 0 with the charger attached; see
   scripts/device/rog5-charge-policy, untracked, another agent's work).
2. scripts/device/rog5-perf-mode: auto_mode gains /etc/rog5/perf-mode
   perf_on_power=display (default, unchanged behaviour) | always | never.
3. New: scripts/device/rog5-usb-storage, configs/systemd/rog5-usb-storage@.service,
   configs/udev/94-rog5-usb-storage.rules, configs/rog5/usb-storage,
   scripts/device/test-rog5-usb-storage.sh. Goal: mount a configured USB
   filesystem (by UUID/LABEL) at boot or on plug, independent of login, never
   before the boot gate (initramfs/persistent-root-attest run by
   rog5-p2-ready.service, generated in initramfs/persistent-root-init ~line
   2709, fails the boot on any unexpected block-backed mount;
   initramfs/persistent-service-state counts block mounts at start), never the
   UFS, and never let writes land in an empty mountpoint while the disk is
   absent. Keep /run/media/phone/ROG5-USB (Steam library, today mounted by
   gvfs/udisks).

Questions: can any path mount before rog5-p2-ready/rog5-persistent-state
finish (udev coldplug, Requisite semantics, restart)? Can a stale
charge_behaviour or a sourcing hub hold the phone awake on battery forever?
Any always-RUNNING playback PCM or permanent block sleep inhibitor on a
Phosh/GNOME session that would stop suspend entirely? Shell/awk bugs
(busctl quoting, set -u, subshell exits), udev/systemd unit mistakes
(SYSTEMD_WANTS on change events, BindsTo on removal, shutdown ordering)?
Answer with concrete findings (file:line), most serious first.

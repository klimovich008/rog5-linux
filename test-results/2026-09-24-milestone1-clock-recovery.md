# Milestone 1: clock and self-recovery — September 23–24

Default kernel `production-7.2.7-r6` (build r6, platform DTB `cc39d79e…`,
installed with `install-default-kernel.py`, two ordinary boots committed
healthy). Evidence: `~/.local/state/rog5-production-boot-20260923/`
(`trial-727-t4..t6-session`, `default-7.2.7-r6`).

## Results

| Part | Result |
|---|---|
| RTC | `rtc-pm8xxx` registers the PMK8350 RTC read-only. It is a counter since some PMIC reset (27958 s at the first read), and it kept counting across RAM-trial reboots (Δ1264 s both ways). |
| Clock at boot | After the first NTP sync the offset is saved to `/persist/var/lib/rog5-clock`. Next boot: `rog5-rtc-time: restored 2026-09-23T22:28:09Z from RTC 30507` at 28 s, before any NTP, within 1 s of the host. |
| Watchdog | systemd drives `softdog` (`Using hardware watchdog /dev/watchdog0: 'Software Watchdog'… hardware timeout of 2min`), `soft_panic=1`. |
| Panic | `echo c > /proc/sysrq-trigger` on the default boot: USB absent at 4 s, the loader at 24 s, r6 back in 35 s, committed healthy, clock restored. No crash-dump screen. |
| pstore | ramoops at `0x9b800000` with the ASUS 5.4 wrapper kernel's exact layout keeps that loader's full console (up to kexec "Bye!") readable as `console-ramoops-0`. A mainline panic record does **not** survive: see below. |

## Limits found on the phone

- `CONFIG_RTC_HCTOSYS=y` runs for a modular RTC too: loading rtc-pm8xxx set the
  clock to 1970 (t4). It is off now.
- The loader's bundle verifier forbids overlapping reserved-memory tuples,
  disabled or not, so ramoops reuses the disabled rmtfs node in place.
- The 5.4 wrapper kernel boots first after every reset with its own ramoops
  command line at `0x9b800000`; any other layout gets reinitialized (t5).
- Every reboot and panic is a PMIC **HARD_RESET** (PON log: `Reset Trigger:
  PS_HOLD`, `Warm Reset Count: 0`), which power-cycles DDR, so no mainline
  panic record survives.
- A warm reset (`/sys/kernel/reboot/mode` = warm, PSCI SYSTEM_RESET2) **hangs in
  firmware**: the phone went through shutdown and never reset; the USB link
  stayed frozen until a manual R1. Never request a warm reboot.
- `rog5-rtc-time-save.path` re-triggered its oneshot while the file existed and
  hit the start limit; the save service now stays active (RemainAfterExit).

A panic therefore still self-recovers (reboot to the same default in 35 s,
with the RTC clock restored), but its log is lost. Keeping it would need a
panic-time writer to storage, which is out of scope for this milestone.

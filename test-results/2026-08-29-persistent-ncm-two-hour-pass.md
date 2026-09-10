# Persistent slot-B v8 NCM liveness — PASS

- Primary question: does the accepted v8 side-port NCM/SSH path reproduce the
  earlier isolated host `NETDEV WATCHDOG` after about 47 minutes?
- Changed layer: observer/userspace only. No kernel, DTB, initramfs, recovery,
  trust, admission, or phone-storage composition changed.
- Boot ID: `bf9aa234-327f-4b50-acaa-40e98a94c421`.
- The sealed target observer completed 7,200 one-second samples and exited
  successfully. Its final sample was at 7,831.20 seconds target uptime.
- Every sample retained carrier, exact UDC state `configured`, high-speed USB,
  active DWC runtime, zero RX/TX errors, and one pre-existing target TX drop.
- The host observer completed 670 ten-second checks. Every ping and strict
  pinned-SSH probe passed, consecutive failures remained zero, host TX errors
  remained zero, and the USB device stayed at the same anchored device number.
- The exact host kernel journal interval contained no `cdc_ncm`, NETDEV
  watchdog, TX-timeout, USB-anchor, or xHCI error.
- Systemd remained `running` with zero failed units. At collection end the
  battery reported `Full`, 8.682 V and 30.1 C; side USB was online at +309 mA.
- Adjacent discriminators also passed on this boot before the long run: a
  256 MiB transfer in each direction, a 180-second no-traffic interval, and a
  10-minute no-traffic interval.
- Private target log SHA-256:
  `32f60ad2bf99e2ecad540f69601d1c444358779c1341e6731c2fd1480c2acb15`.
- Private host log SHA-256:
  `d8d24e3b3881f459de62d96283a0b7919c1105ff19d20c0dbb49da5b89cec8d6`.
- Focused observer test and the active repository tier passed before the live
  run; the active tier took 72 seconds. Full CI was not repeated because this
  was an observer-only change and the tested source was unchanged.
- Result: PASS. The prior 47-minute failure was not reproduced and is not a
  deterministic uptime timeout. Its root cause remains unproven, so no USB
  kernel/DT change is justified by this cycle. Preserve the observer for a
  future first-failure capture while proceeding with the accepted v8 baseline.

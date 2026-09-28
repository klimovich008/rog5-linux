# Haven hypervisor watchdog (patch 0088), 2026-09-28

Goal: a hung phone should reset itself. Until now only softdog existed, and
softdog (an hrtimer) cannot fire when every CPU spins with interrupts off.

## Findings (7.2.7 r62 / r155 default, test modules)

- The Haven vWDT answers the Gunyah watchdog SMCCC calls (vendor-hyp
  0x0005 control, 0x0006 status, 0x0007 pet, 0x0008 set bark/bite ms), the
  same interface as the stock `hh_virt_wdt.c`. STATUS a1 bit 0 = enabled,
  bit 31 = expired, a2 = ms since the last pet.
- qcom_scm never registered `gunyah-wdt`: `arm_smccc_1_1_get_conduit()` is
  NONE (the firmware reports SMCCC 1.0), so the Gunyah UID query returns
  NOT_SUPPORTED. Direct `arm_smccc_1_1_smc()` calls work.
- The ASUS wrapper leaves it disabled (a2 frozen near 34 s).
- Haven counts busy time only: with the watchdog enabled and the phone idle
  for 30 s, a2 stayed near 0 and nothing bit. It catches spinning CPUs and
  stalled bus accesses, not an all-idle deadlock (softdog stays for that).
- A bite is a clean PMIC reset: the phone booted the slot-B default by itself
  about 70 s later (no crashdump screen, no button press). Five bites today,
  all the same.
- bark == bite sets the expired bit at enable. One such test (driver path,
  idle phone for about 2 min) ended with the watchdog disabled and no bite;
  bark < bite never showed that. 0088 uses bite = bark + 3 s like stock.

## Patch 0088 and wiring

- qcom_scm registers `gunyah-wdt` on `asus,rog-phone5` even without the UID;
  the driver's probe still needs a working STATUS call.
- gunyah_wdt: bark = timeout - 3 s; on this machine it starts at probe with
  WDOG_HW_RUNNING, so the watchdog core pets it (every ~16 s, 32 s bite)
  from boot on; stopped and restarted across system suspend.
- The kernel keeps petting it; PID 1 keeps softdog. persistent-root-init
  adds `WatchdogDevice=/dev/watchdog1` when a hardware watchdog0 registered
  before user space.

## Results

| Test | Result |
|---|---|
| Module build of the patched driver on r62, 45 s full load | kept petted, max 15.4 s between pets |
| stop_machine() with IRQs off on all CPUs, 60 s (module test) | reset after ~41 s, default booted |
| r156 RAM trial (kernel r66) | watchdog0 = gunyah-wdt, enabled from boot; systemd uses watchdog1 'Software Watchdog' |
| r156 s2idle cycle | stopped in suspend, enabled again after resume |
| r156 hard hang, 90 s | reset after ~42 s, default booted |
| r156 default install | two ordinary boots committed healthy (calltraces=2, the usual DSI PHY clk warnings) |

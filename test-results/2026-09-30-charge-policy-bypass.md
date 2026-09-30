# 2026-09-30: bypass ("direct power") charging and rog5-charge-policy

Kernel: r204 bundle, i.e. kernel r108 with 0082 (qcom_battmgr ROG5 charge limit and bypass).
Phone: side port on the user's USB-C hub (214b:7260), battery Full at 100 %, 578 cycles, SOH 89 %.
Policy: `scripts/device/rog5-charge-policy`, committed but not installed on the phone.

## What the firmware does (stock source and ADSP strings)

- Stock bypass is Armoury Crate `persist.sys.bypasscharging`. init writes it to
  `/sys/class/asuslib/bypass_stop_charging` (init.asus.rc:916-919), and the kernel sends one
  message on the OEM channel (owner 32782): `SET_CHG_LIMIT_MODE2` 0x2117 `{mode 0x8, value 0|1}`
  (asus_battery_charger.c:821-839, 1718-1735, 2854-2862).
- The same message implements `persist.sys.stopcharging`, the scheduled/smart charge stop.
- Stock never sends USBIN suspend (0x2105) for bypass. It uses 0x2105 only for the 60 % demo and
  ultra-battery-life caps and for USB thermal alerts.
- The stock kernel checks nothing before bypass: no charger type, wattage, adapter ID, SOC or
  temperature. There is no HLOS message that chooses a PD voltage. The ADSP negotiates PD itself;
  the only input knob is mode2 0x1 (slow charge, a watt cap of 9-65 W).
- ADSP firmware strings ("side-way charging, set 9v2a", "side-way, pause charging") suggest the
  ADSP moves a PD adapter to 9 V / 2 A in bypass. That was not observed here: see PD below.
- Our 0082 sends exactly that message for `inhibit-charge` and for the end threshold, and 0x2105
  for `force-discharge`. This firmware acks 0x2117 with the older 0x2110 reply (r143 finding,
  handled since r144).

## Measurements (r204, 5 s samples, /var/tmp/rog5-chgexp.log on the phone)

| Phase | behaviour | battery | USB (qcom-battmgr-usb) |
|---|---|---|---|
| 17:21 baseline | auto | Full 100 %, 0 mA | online 1, 5.03-5.10 V, 0.22-0.40 A |
| 17:22 bypass | inhibit-charge | Full 100 %, 0 mA | online 1, 5.06-5.10 V, 0.22-0.41 A: the adapter carries the load |
| 17:23 | auto | Full, 0 mA | online 1, 5.06-5.09 V, 0.22-0.38 A |
| 17:23:42 | force-discharge | -113..-170 mA awake (-1.1 W), cells 4364 -> 4344 mV; status Discharging after ~90 s | online 0, 0 A at 5.13-5.18 V; the UCSI psy stays online 1 |
| 18:11 (restored) | auto | Full 100 %, 0 mA | online 1 within 10 s, 5.04 V, 0.45 A |

- At 100 % auto and inhibit-charge cannot be told apart: the charger is already idle. The
  below-full evidence is from r144 (2026-09-28-battmgr-charge-limit-0082.md): at 99 %, auto
  charged at +94..151 mA and inhibit-charge held 0 mA with USB online.
- This run did not reach the below-full phase. force-discharge makes qcom-battmgr-usb read
  offline, so rog5-sleep-policy counted the phone as on battery and suspended it 60 s after the
  screen went off (17:26, s2idle; after the user's power key at 18:11 it resumed still in
  force-discharge at 100 %).
- The script then restored auto and 0/100. The fix on the sleep-policy side is 10cc4116: a
  non-auto charge_behaviour with a sink partner counts as external power.
- Kernel log: no "failed to pause/resume/suspend" warnings from 0082.
- Thresholds, checked at 18:13 and then restored:
  - writing end 80 reads back start=75 end=80;
  - then start 70 reads back 70/80;
  - the battery stayed Full at 0 mA and USB stayed online;
  - end 10, end 101 and start 100 are rejected (EINVAL).
  Afterwards: [auto], 0/100.
- The kernel keeps these values in memory only and starts every boot in auto with 0/100.

## PD (read-only UCSI GET_CONNECTOR_STATUS 0x10012)

- RDO 0x1304b12c the whole time (17:25-18:12): object position 1 (5 V), 3 A operating and
  maximum, no capability mismatch, USB comm capable, power operation mode "USB default".
- This held through force-discharge (USB input suspended), Full-with-auto, and the bypass phase
  (USB 5.07 V; the RDO was not sampled in that phase).
- The hub offers 5 V/3 A, 9 V/2.45 A, 15 V/2.87 A and 20 V/2.75 A. The phone's sink PDOs are
  5 V/3 A, 9 V/3 A, PPS 3.3-11 V/5 A and PPS 3.3-16 V/5 A. The main session read these.
- With the battery full the ADSP has no reason to leave 5 V. Whether it moves to 9 V/2.45 A
  while charging below full, or in bypass, is open and needs a below-full test.
- The 9 V/3 A sink PDO against a 2.45 A offer should not block 9 V: a PD sink may request less
  than its own PDO. The ADSP's selection rule is unknown.
- 5 V/3 A is 15 W, enough for bypass under a normal load. Linux has no knob to ask for 9 V:
  UCSI has no sink-PDO selection here, and stock has none either apart from debug overrides
  0x2113/0x2114.

## The policy (rog5-charge-policy)

Configuration lives in `/etc/rog5/charge-policy` (sample: `configs/rog5/charge-policy`). The
unit is `rog5-charge-policy.service`, which polls every 30 s and runs `stop` as ExecStopPost.

- Default `mode=limit start=70 end=80`: the kernel pauses (bypass) at 80 % and resumes at 70 %.
  The other modes are `full`, `bypass` and `off`. `rog5-charge-policy full` charges to 100 %
  once, until the battery reports Full, the charger is unplugged, or `full_hours` passes.
- inhibit-charge on external power while rog5-perf-mode is in performance, or while the battery
  is at 40 C or above (released at 37 C). It is never used below 30 %.
- Load fallback: if the battery still discharges faster than 200 mA for 120 s, the adapter
  can't carry the load. The policy returns to auto for 900 s; the limit window stays.
- Opt-in `drain=1`: force-discharge from end+3 % down to end, with a 50 % floor. It stops when
  the Type-C partner goes away or when performance mode or heat applies.
- Any unreadable value, failed write or unknown mode ends in auto 0/100. Thresholds are only
  written when they change, because each write clears the kernel's hold.

Test: `scripts/device/test-rog5-charge-policy.sh`, offline with a fake sysfs.
Review: GPT-6.1-Sol. Its seven findings are fixed and covered by the test.
It replaces `rog5-charge-limit` and `rog5-charge-limit.service`, which were installed on the
phone but idle because there was no /etc/rog5/charge-limit.

Install (not done yet):

```
scp scripts/device/rog5-charge-policy root@PHONE:/usr/local/sbin/
scp configs/systemd/rog5-charge-policy.service root@PHONE:/etc/systemd/system/
scp configs/rog5/charge-policy root@PHONE:/etc/rog5/charge-policy
ssh root@PHONE 'systemctl disable --now rog5-charge-limit.service;
  rm -f /usr/local/sbin/rog5-charge-limit /etc/systemd/system/rog5-charge-limit.service;
  systemctl daemon-reload; systemctl enable --now rog5-charge-policy; rog5-charge-policy status'
```

## Test with a high-power PD charger (open)

B=/sys/class/power_supply/qcom-battmgr-bat, U=/sys/class/power_supply/qcom-battmgr-usb.
Start below about 90 % (bypass is only visible below full) with the charger on the side port.
Keep the screen on or keep an SSH session open. Sample every 5 s:
`$U/{voltage_now,current_now}`, `$B/{current_now,status,temp,capacity}`, and the UCSI RDO
(`echo 0x10012 > /sys/kernel/debug/usb/ucsi/pmic_glink.ucsi.0/command; cat .../response`).

1. auto, 2 min. Expected: battery current_now clearly positive (charging). Note the USB voltage
   (9 V or 5 V) and the RDO position.
2. `echo inhibit-charge > $B/charge_behaviour`, 3 min idle, then 3 min under load (a GPU
   benchmark). Pass:
   - battery current_now within ±50 mA idle, and not below -200 mA under load;
   - status "Not charging" (or Discharging only under load), USB online 1;
   - USB current rises with the load;
   - battery temp does not rise (it rose in step 1);
   - no "failed to pause" in dmesg.
   Also note whether the ADSP switches the RDO to 9 V in bypass.
3. `echo auto > $B/charge_behaviour`: charging resumes within about 60 s.
4. With the policy installed and `rog5-perf-mode performance`, `rog5-charge-policy status`
   shows `inhibit-charge ... performance` within 30 s. On a weak 5 V/0.5 A port under load, it
   shows `...-backoff` after 2 min.
5. Limit: `rog5-charge-policy limit 80` below 80 % charges and stops at 80 % with current_now
   about 0 and USB carrying the load. Below 75 % it charges again.

Never leave force-discharge set by hand; `echo auto > $B/charge_behaviour` undoes everything.

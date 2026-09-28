# 2026-09-28: qcom_battmgr ROG5 charge limit and bypass (patch 0082)

Scope: source and compile only. No kernel build, no boot, nothing sent to the phone.
Follows item #4 of `2026-09-27-compare-battery-charging.md`.

## Change

`patches/linux-7.2.7/0082-power-supply-qcom_battmgr-ROG5-charge-limit-and-bypass.patch`,
appended to `series.production` after 0081. It applies only when the ASUS OEM client
from 0018 exists (`asus,cell-voltage-readonly`).

- `qcom-battmgr-bat` gains `charge_behaviour` (auto / inhibit-charge /
  force-discharge) and writable `charge_control_start_threshold` /
  `charge_control_end_threshold`. The values live in memory only. Defaults are
  auto and 0/100, which means nothing is sent to the ADSP.
- A work item (deferrable, on `system_freezable_wq`) pauses charging with OEM
  0x2117 `{mode=0x8 BYPASS, value=1}` for inhibit-charge, or when capacity is at
  or above end. It resumes with value 0 when capacity is at or below start.
  Force-discharge sends OEM 0x2105 `{enable=1}` (USBIN suspend).
- Triggers: BAT/USB notifications, sysfs writes, BC and OEM PDR up, system
  resume, the stock OEM notification 0x2112 VBUS-attached, and a 60 s poll while
  a limit or behaviour is set.
- Sending: a message goes out on each state change. An active pause or USBIN
  suspend is also re-sent after PDR up, resume, VBUS attach (0x2112 or a
  USB_ONLINE 0 to 1 edge), and every 60 s while USB is online.
- Nothing is sent while the OEM channel is poisoned. Errors go through
  `dev_warn_ratelimited`.
- Unbind and `.shutdown` send resume and unsuspend before the pmic_glink clients
  are released. This matters for kexec.
- OEM request path: 0018's request code is now a shared locked helper. The ack
  is matched against the pending opcode and length (cell voltage 16 B, mode2
  20 B, USBIN 16 B). OEM `PMIC_GLINK_NOTIFY` messages, such as ADSP event logs,
  no longer complete a pending request with -EPROTO.

## Compile check (r52 flags, r52 tree untouched)

- Method: `scratchpad/kc82/cc.py`. It takes the exact `savedcmd` of
  `objects/drivers/power/supply/.qcom_battmgr.o.cmd` from
  `rog5-kernel-7.2.7-build-r52` (clang 20.1.8, W=1-level `-Wall -Wextra
  -Wmissing-prototypes ...`), drops ccache, and redirects the source, `-o` and the
  `-MMD` depfile into scratch. It runs with cwd = r52 objects.
- Baseline (r52 source file): rc 0, no diagnostics.
- Patched: rc 0, no diagnostics (0-byte log).
- `find r52 -newer stamp` shows 0 files changed.
- New undefined symbols (`disable_delayed_work_sync`, `mod_delayed_work_on`,
  `queue_delayed_work_on`, `system_freezable_wq`, `delayed_work_timer_fn`,
  `timer_init_key`, `___ratelimit`, `jiffies`) are all exported by the r52 vmlinux
  (`Module.symvers`).
- `patch -p1 --dry-run` and `git apply --check` both pass on a copy of the r52
  file. The applied result is byte-identical to the compiled file.

## Usage

```
B=/sys/class/power_supply/qcom-battmgr-bat
echo 80 > $B/charge_control_end_threshold    # start becomes 75 if it was unset
echo 70 > $B/charge_control_start_threshold  # optional, resume at <= 70 %
echo inhibit-charge > $B/charge_behaviour    # pause now, run from VBUS
echo force-discharge > $B/charge_behaviour   # USBIN suspended, runs from battery
echo auto > $B/charge_behaviour
echo 100 > $B/charge_control_end_threshold   # no limit
```

Valid ranges are end 20..100 and start 0..99; anything else returns EINVAL.
Writing start >= end moves end to start + 5.

## Hardware checks still open

1. The mode2 and USBIN acks arrive with the expected lengths. No
   "failed to ... : -71/-90/-110" warnings appear, and `cell_voltages` still works.
2. Inhibit-charge with the charger attached: `current_now` goes to about 0 or a
   small discharge, `status` reports Not charging, and usb `online` stays 1. The
   phone stays up.
3. Force-discharge: the battery discharges with the adapter attached, and auto
   restores charging.
4. With end=80, crossing 80 % pauses charging, and it resumes at or below start.
5. Unplug and replug while paused: does the firmware keep the mode? Check the
   0x2112 VBUS event and the re-send.
6. PDR/ADSP restart, suspend/resume, and module unload all restore auto.
7. Idle power: the 60 s re-send is one glink message per minute, and only while
   paused on USB.

## Hardware results (2026-09-28)
- r142 (kernel r54): force-discharge (USBIN suspend 0x2105) worked; every
  mode2 pause failed with -71. r143 logged the reply: owner 32782, type 1,
  opcode 0x2110 (SET_CHG_LIMIT_MODE), 16 bytes: this ADSP firmware acks
  SET_CHG_LIMIT_MODE2 with the older MODE reply. r144 (kernel r56) accepts
  that reply as the MODE2 ack.
- r144, side port on the Steam Deck: initial Full 100 %, -8 mA;
  force-discharge 4 min -> 99 %, -89 mA, usb online 0; auto -> +94..+151 mA
  (Charging); inhibit-charge -> 0 mA, usb online 1 (runs from VBUS, cells
  rest); no OEM errors. Installed as the default (two ordinary boots).
- rog5-charge-limit (scripts/device) + rog5-charge-limit.service: set END
  [START] / bypass / off / status; saved in /etc/rog5/charge-limit and
  applied at boot. Verified on the phone; no limit is set by default.

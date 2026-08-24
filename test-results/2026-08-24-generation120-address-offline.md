# Generation 120 usb0 address-state discriminator

Date: 2026-08-24

Result: **CONSUMED; `address-show-failed` SELECTED.** Never retry or flash.

Generation 119 proved that `ip address add 169.254.77.2/30 dev usb0` returned
nonzero after ConfigFS, UDC binding, `usb0`, and link-up passed. Generation 120
changes only that boundary and classifies five outcomes with fixed 70–90 second
delays: address-show/interface failure, exact address already present,
conflicting address, first-add failure, or first-add success.

It stops before carrier, power/USB, UFS, userdata, SSH, installer, or any
storage surface. Clean-twin target initramfs SHA-256 is
`697c5750fe7d4a95fc6908be2e362e7feaa7a7ef5086755c76925e0169f6d278`;
signed bundle manifest is
`fda8afcc23cdb35c782b72bc91c1975138dd8f7404acb40c7744badc03825678`;
Generation-120 recovery is
`6bd965cf81d976d76f27b90b43d102a4e6d514285d89fdf5ec8664a17897a621`.

The host USB journal records recovery departure at `11:23:42.502504` and
slot-A fastboot at `11:24:59.547513`, an interval of 77.045009 seconds. After
subtracting the 6.903-second immediate-return baseline, the result selects the
70-second `address-show-failed` branch.

The exact sealed BusyBox `ip -4 -o address show` syntax passes in an isolated
network namespace. Therefore the live `usb0` interface disappeared or became
unqueryable immediately after `ip link set usb0 up` returned success. No target
USB product reached the host. The mature working path runs `mdev -s` before UDC
selection/bind and never after binding; the failing staging path did the
opposite. Moving that one scan before binding is the next root-cause fix.

No carrier, power/USB loader, UFS, userdata, SSH, installer, or storage-write
path ran. Exact fastboot fallback and durable `FALLBACK_RETURNED` resolution
passed at 8.710 V with `battery-soc-ok=yes`.

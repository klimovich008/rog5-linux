# Persistent health service and IRQ/UFS recovery

Result: **PASS**.

Commit `dd9b69fde84312d52f666f3e86fe6558532b7361` adds one
credential-free Python health endpoint and a dynamic-user systemd unit. The
focused four-test suite passed in 0.39 seconds, the active repository tier
passed in 4.28 seconds, and exact PR run `33639870772` passed.

The first deployment was correctly stopped before install when executing
`/usr/bin/python3` returned `EIO`. RAM-resident diagnostics proved:

- PMIC-arb parent IRQ 118 was firing with `bad_chained_irq` and millions of
  suppressed callbacks;
- exact UFS reads at physical sector 24382312 failed;
- p23 and its overlay loop entered `emergency_ro`;
- p24 remained read-only and no healthd destination file had been installed.

A fresh, distinct RAM-only V11 recovery wrapper used raw payload SHA-256
`1236b9e5…c25888` and AVB SHA-256 `891d3a76…ad718`. V11 reported zero current
UFS errors. Read-only fsck proved outer p23 clean; the overlay image required
only journal replay and bitmap/orphan reconciliation. The guarded repair
changed overlay SHA-256 from `71ad9845…90e6` to `0c11f618…e5931`, after which
read-only fsck passed. The previously failing physical block returned one
stable SHA-256, `cd51d88d…61c37`, in 20/20 aligned direct reads.

A receive-only target monitor then enabled dynamic debug only for
`spmi-pmic-arb.c`, watched IRQ errors and `emergency_ro`, and retained fallback
authority. Its terminal record covered 10,800 samples from uptime 218.96 to
3002.80 seconds:

- `result=SOAK_PASS`;
- `irq_err_count=0`;
- `emergency_ro=0`;
- no UFS/I/O or PMIC-bad signature;
- evidence SHA-256 `b4c7d921…793eb`.

Because the storm did not recur well beyond the prior 2,018-second onset, no
speculative kernel or DT patch was applied.

The workload was then installed with exact hashes:

- `/usr/local/libexec/rog5-healthd`: `019418fa…b1e51`;
- `/etc/systemd/system/rog5-healthd.service`: `f5c95744…a7ab3`.

It runs as a dynamic user with no capabilities, strict filesystem/kernel
protections, a 64 MiB memory limit, and only TCP port 8787 allowed. The fixed
JSON `/healthz` response passed locally, over NCM and over native Wi-Fi. After
an ordinary reboot through installed `boot_b`, V10 boot
`389acb49-2cc0-46da-9997-e67e548a77ee` retained the exact files, enabled unit,
zero restarts and healthy endpoint. Full acceptance also passed:

- exact 163-package inventory;
- systemd, Wi-Fi, Tailscale and strict key-only SSH;
- p24 read-only and only `sda,sda23` writable;
- `journal=0/0` and no UFS/IRQ/emergency-RO errors;
- battery Full/Good at 30.2 C with USB online.

Slot A, `boot_b`, p24, GPT and protected partitions were unchanged.

## Powered-off startup

The accepted target exitrd previously converted every systemd action into
`reboot -f`, so `systemctl poweroff` could not test cold startup. A RAM-only
variant changed only the terminal dispatch: `poweroff` used sealed BusyBox
`poweroff -f`; reboot and kexec fallback behavior remained unchanged. The exact
BusyBox applet and poweroff/reboot/kexec dispatch paths passed offline tests.

With battery Full/Good and connected power, exact USB-path observation recorded:

- V10 USB departed at `+29.581s`;
- recovery returned at `+49.328s`, after 19.747 seconds absent;
- recovery departed at `+60.558s`;
- persistent-root USB returned at `+63.120s`, after 2.562 seconds absent.

The observer's original derived duration reused the first return across the
second disconnect and was rejected; its raw timestamps are authoritative and
the fixture is corrected. Cold-start V10 boot
`9a4dce86-229f-4193-a216-aedb06dbd5ff` restored systemd, Wi-Fi
`192.168.1.239/24`, Tailscale `100.68.169.83/32`, key-only SSH and healthd.
Full acceptance passed with the exact package inventory, `journal=0/0`, only
`sda,sda23` writable, no IRQ/UFS/emergency-RO errors, and Full/Good battery at
30.0 C. Healthd passed from the host over both NCM and Wi-Fi.

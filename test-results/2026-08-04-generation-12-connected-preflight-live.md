# Generation-12 connected preflight — live result

Date: 2026-08-04

Result: **PASS connected preflight — the exact Generation-12 diagnostic
recovery, signed bundle, non-fixture deployment-key chain, installed host
surfaces, and one physical ASUS `lahaina` fastboot device passed. No
Generation-12 boot claim, recovery boot, payload transfer, target SSH, project
server, flash, mount, wipe, slot operation, or intentional phone-storage write
occurred.**

## Published prerequisite

The preflight ran from clean pushed commit
`328b33c623d1d39492c253d3fc1fc566536af7cf`. Complete local Linux `ci` and
independent standards/security and specification/documentation reviews passed.
Exact-head GitHub Actions run `30942517411` passed recovery-core in 4m10s and
QEMU in 52s.

Central policy admits exactly one RAM-only lifecycle for Generation-12 AVB
`615d7498e85be499b80473aa0fd6c0cb341dbd13ef5006d6464b389fedd72cf6`.
The artifact remains exact `unbooted`, issuance `authority=none`, `tracked=no`,
and never-flash.

## Connected sequence

The phone initially exposed the exact Alpine fallback USB composite identity
`1d6b:0104`, serial `ROG5LINUX`, and fixed NCM path. Strict key-pinned fallback
SSH proved the accepted ASUS 5.4 kernel, BusyBox init, `qcom,lahaina-mtp`, ext4
root, empty project-module/pstore state, readable nonfatal kernel log, and safe
thermal telemetry. The bootloader serial was recovered privately from the
single exact kernel command-line field. The anchored helper then sent
`RESTART2("bootloader")` and verified disconnect, same-port ASUS fastboot
VID/PID and serial, and one exact product `lahaina` device.

Local admission matched the dedicated Ed25519 key to the caller-owned
non-fixture v3 package, exact `headless-netroot-early-diag-v1` candidate, and
runtime manifest
`4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76`.

The first lifecycle preflight refused before phone access because Steam's
enabled, active `steam-web-debug-portforward.socket` owned wildcard TCP 8081.
After its exact enabled/listening state was recorded, the socket was stopped
for the bounded preflight and restored immediately afterward to enabled,
active, and wildcard-listening. The terminal marker was:

```text
PASS headless-netroot-early-diag-v1 lifecycle preflight is clean; the deployment key was admitted locally, and no phone boot, payload transfer, SSH connection, or privileged server was started
```

Final observation found one exact fastboot device, the restored Steam socket,
and no Generation-12 `.record` or `.record.entered` boot claim. The private
preflight evidence directory remains outside Git and contains no lifecycle
output because preflight creates none.

## Integrity chain

- temporary-boot policy:
  `839a5f45306cb7c1ea23f88363e1eba740feac2e271f785141b6d73e61f2c69b`;
- artifact inventory:
  `ae8b7da3531578106ec4f79e770a333afe3704a80d880ce0d6cd7e89e028476d`;
- minimal profile:
  `6574c528a98e3ad3f3de564f06f59b91e9cd38c922beb88576154b12ac35140f`;
  and
- source/DT outer profile:
  `9b7bff49b44e6442c925054aa06ec6f33d646d09af442bde9786dcb5bd20ac6c`.

## Boundary

This pass establishes the connected-preflight prerequisite only. It does not
consume the candidate or authorize flashing. The next permitted increment is
to publish this evidence, pass exact-head CI, and then invoke the sole
Generation-12 RAM-only diagnostic lifecycle through the controller. Any later
failure after durable claim entry burns the candidate without retry; only a
distinct successor generation may recover from that outcome.

The strict fallback reads retain only the already accepted bounded
BusyBox-history and read-induced ext4-atime effects. No credential or private
device serial is stored in Git.

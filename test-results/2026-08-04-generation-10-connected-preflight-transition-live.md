# Generation-10 connected-preflight transition — live result

Date: 2026-08-04

Result: **transition attempted and failed before connected preflight; manual
fastboot entry required**. No recovery image, payload, boot command, boot claim,
NFS export, privileged server, target execution, or artifact consumption
occurred.

## Published prerequisite

The exact one-shot Generation-10 admission is commit
`a9c012cbb36f4529cfe570224a311d0fcc9b553d`. Complete local CI and constrained
tool-free Opus review passed. Exact-head GitHub Actions run `30870594823` then
passed `recovery-core` in 3m58s and QEMU in 35s.

## Observed transition

The phone began in the exact Alpine fallback USB personality:

- one `1d6b:0104` `ROG_Phone_5_Linux_Server` composite gadget;
- fallback NCM at host address `169.254.77.1/30`; and
- fallback ACM at `/dev/ttyACM1` on the expected physical USB path.

The dedicated mode-`0600` SSH key and pinned known-hosts file passed the fixed
fallback health helper. The remote check verified the exact fallback kernel,
BusyBox PID 1, `qcom,lahaina-mtp` compatibility, ext4 root, empty diagnostic
module and pstore state, readable kernel log without a fatal signature, and
bounded thermal telemetry.

The helper then emitted both authenticated markers before issuing the fixed
AArch64 `RESTART2("bootloader")` syscall:

```text
PASS authenticated fallback reboot session
PASS guarded fallback RESTART2 bootloader request sent
```

The fallback gadget disconnected, but no USB personality re-enumerated on the
anchored port during the helper's fixed 45-second observation. A separate
30-second read-only fastboot check also found no device, and the subsequent
USB inventory still contained no phone. The terminal classification was:

```text
FAIL fallback USB disconnected but no anchored-port USB re-enumeration was observed
```

This is a failed transport transition, not an attempted Generation-10 boot.
Central policy retains the one-shot admission, Generation 10 remains unbooted,
and no durable `BOOT_CLAIMED` record exists. The next action is manual fastboot
entry followed by a fresh `diagnostic-preflight`; do not send `diagnostic-run`
until that separate connected preflight passes and is recorded.

Private serial, credential, and host evidence paths remain outside Git. The
bounded fallback SSH history/atime effects were covered by standing operator
authorization.

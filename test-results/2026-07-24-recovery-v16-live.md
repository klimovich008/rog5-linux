# Recovery v16 live result

Status: **PARTIAL PASS; superseded by v18** after one reversible temporary
boot. Exact recovery USB, NCM, and automatic rollback passed, but ACM returned
no shell data. Nothing was flashed and kexec was not loaded or executed.

## Result

- Manifest-pinned AVB SHA-256:
  `019e62ee07b8d2c1bad3d47ae0730dad741df4af14a4a31858fedabdd6200b08`.
- The real preflight found exactly one `lahaina` fastboot target.
- `fastboot boot` accepted and started the image.
- The exact normalized `ROG5_recovery` product appeared at 06:33:13 local
  time, about 20 seconds after the guarded command began.
- The NCM interface came up and `169.254.77.2` answered ICMP.
- Repeated ACM opens and delayed command writes returned no bytes.
- The exact fallback product returned at 06:36:30.
- The fallback boot identity changed, proving a real automatic reboot.

V16 therefore fixed the earlier wake-lock return and reached the staging
gadget, but it did not satisfy the credential-free recovery-console gate.
The independent rollback remained armed and recovered the phone without host
intervention.

The separately authorized v17 keyed diagnostic reproduced the same init path
and identified the missing `/dev/ttyGS0` node. See the
[v17 diagnostic](2026-07-24-recovery-v17-ssh-diagnostic.md).

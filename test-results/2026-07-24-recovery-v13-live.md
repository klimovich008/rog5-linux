# Recovery v13 live result

Status: **REJECTED** after one reversible temporary-boot attempt. Recovery
identity was never reached on USB. Nothing was flashed and kexec was not
loaded or executed.

## Candidate and action

- Manifest-pinned unsigned AVB image SHA-256:
  `ba25c2b765e92c23d048e0aab7cc4722e448dd97f3c9bd05df7102f34ef15e15`.
- The real Linux host preflight passed with exactly one fastboot target.
- `fastboot boot` accepted and started the 96 MiB image.
- No `fastboot flash`, partition write, slot change, or filesystem operation
  was issued.

## USB timeline and identity

- Fastboot disconnected at 05:08:27 local time.
- At 05:08:48, the known Alpine fallback gadget enumerated.
- The kernel USB journal contains no intervening `ROG5 recovery` product.
- The fallback boot ID changed, confirming a complete return through reboot.

The first host detector used only `1d6b:0104`, which both recovery and the
fallback server intentionally share. It therefore reported a false recovery
ACM success. Immediate console inspection disproved that result: the endpoint
reported fallback kernel `5.4.134`, its existing ext4 root, no recovery marker,
and its existing SSH service. Those fallback readings are not v13 recovery
state and do not count as a recovery storage failure or pass.

The host workflow now also requires the exact normalized USB product
`ROG5_recovery` and fails explicitly if another ROG5 ACM gadget returns first.

## Diagnostic boundary

- Standard pstore exposed no previous-console record.
- The available historical ramoops module had exact kernel vermagic but
  predated the repository's device-compatible guard, so it was not loaded.
- The current fallback exposes live kernel headers but not the matching build
  tree and symbol-version data needed to reproduce the guarded module.
- The exact early reset cause is therefore not claimed.

The approved recovery SSH key was copied only to a mode-0600 host tmpfs
directory and used for read-only fallback inspection. No key or account
material was included in v13.

## Follow-up

V13's policy targeted all 149 fallback-visible block objects, including 16
loop devices, 16 RAM disks, and zram. That policy is broader than the storage
threat: seven UFS LUNs and their 109 partitions are the persistent objects.
Recovery v14 keeps the pre-USB block-backed-mount rejection but locks and
verifies only physical disks and their partitions. This is a reasoned
hypothesis for the early v13 return, not a proven root cause until v14 reaches
its exact recovery USB identity.

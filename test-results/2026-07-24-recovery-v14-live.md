# Recovery v14 live result

Status: **REJECTED** after one reversible temporary-boot attempt. Nothing was
flashed, recovery USB did not enumerate, and kexec was not loaded or executed.

## Result

- Manifest-pinned image SHA-256:
  `9cd6f875b3a32293eda7805ed0d68c09aa7d6b93fc98e096e34328900632a86d`.
- The real preflight found exactly one fastboot target.
- `fastboot boot` accepted and started the image.
- Fastboot disconnected at 05:49:15 local time.
- The known Alpine fallback gadget enumerated at 05:49:36.
- No exact `ROG5 recovery` USB product appeared between them.
- The corrected host detector rejected the fallback immediately instead of
  reporting a false recovery success.

The 21-second disconnect-to-fallback interval is identical to v13. V14's
physical-storage-only selection therefore did not solve the early return.
That change remains a safer policy, but the reset occurs on a path shared by
both candidates or before recovery `/init`.

Standard pstore still provides no retained previous-console record. No
unguarded diagnostic module was loaded. Recovery v15 uses a USB-closed,
bounded timing side channel to distinguish reset before `/init`, PM wake-lock
failure, block-backed mount rejection, and physical-device lock failure.

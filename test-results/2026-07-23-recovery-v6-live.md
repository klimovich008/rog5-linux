# Recovery v6 live result

Status: rejected after a reversible temporary boot.

## Candidate

- Clean ASUS 5.4 Image SHA-256:
  `afd27f912e1efe9c8abe2b1df3380e37b3a51397c88869f81cb826da68189529`
- The Image and config matched across two fresh source/build volumes.
- AVB boot image SHA-256:
  `d88123f2738006d96751483a8a4e85abb6b6a9fd61734b3310cc416a60cd7f1c`
- The complete offline recovery verifier passed before boot.

## Live observations

- `fastboot boot` completed; no partition was flashed.
- Windows enumerated one ACM serial interface and one NCM network interface.
- NCM reached the recovery SSH port without authentication.
- Every ACM write failed in the Windows USB-serial driver with a semaphore
  timeout.
- The inherited command line carried one valid but longer-than-documented
  rollback timeout. The gadget remained present beyond that wall-clock
  interval, so automatic rollback did not pass.

## Boundaries

- No SSH key or other credential was read or used.
- Staging identity, RAM-only mounts, payload, and UFS-disable live gates were
  not run and are not claimed.
- Kexec was not loaded or executed.
- Storage was not intentionally mounted or modified, but live zero-storage
  proof is absent.

## Follow-up

- The repacker now replaces command-line keys and the verifier requires
  exactly one 180-second rollback timeout.
- The recovery init now holds a timed wake lock and fails closed to repeated
  forced-reboot/SysRq attempts.
- The ACM shell is supervised and restarted across gadget hangups.
- Linux 7.1 now requires built-in ACM serial support and timed wake locks.

All follow-up changes require a newly rebuilt and reverified candidate before
another temporary boot.

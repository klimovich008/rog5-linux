# Persistent-root P2 early-entry v1 live rejection

Date: 2026-07-28

Result: **REJECTED SAFELY; package consumed; never retry or flash**

The first and only attended early-entry v1 cycle did not expose a stable
`ROG5_P2_entry_oracle` ACM identity. The exact target marker was therefore not
observed and target `/init` entry is not accepted. Automatic rollback returned
the phone to the exact Alpine fallback, the staged Arch root remained
unchanged and `UNBOOTED`, and the corrected screen service started
automatically with the panel off.

## Preconditions

- Git was clean and synchronized locally and remotely at
  `6d28a431488dac91ff60a3b6490cad01b05a895a`.
- The manifest-pinned temporary boot image was
  `5489638517ebd83684702e6197ea459d890c6274b328cc6a3373b65a05442b3e`.
- The complete entry-v1 bundle, receive-only ACM, live-runner, OpenRC screen
  lifecycle, shell/static, link and private-material suites passed.
- The exact fallback health preflight passed after the phone cooled to
  46.1 C.
- The sealed root identity was exact, promotion state was `UNBOOTED`, both
  selectors and the partial root were absent, and the screen service was
  active with brightness zero.

## One-shot sequence

1. The guarded AArch64 `RESTART2("bootloader")` helper reached exactly one
   fastboot device.
2. `recovery-linux.sh` verified the exact AVB image and used `fastboot boot`;
   nothing was flashed.
3. Exact recovery ACM enumerated. The initial load marker was missed, so the
   accepted transport performed its one permitted identical, read-safe load
   replay after rediscovery.
4. Payload hashes passed. Staging verified 116 physical block nodes read-only,
   zero writable physical nodes, zero block-backed mounts, and one loaded
   target.
5. The host transmitted exactly one `kexec -e`. It did not retry the target
   execute.
6. The receive-only target reader waited for the exact USB identity but
   returned `P2 entry ACM identity did not remain stable`.
7. An automatic reset returned the phone to Alpine. The available evidence
   does not classify which reset path fired. No target shell, target SSH
   identity, storage mount, root selection, promotion or flash was used.

## Rollback closure

The runner's first generic fallback preflight rejected only the thermal gate:
the immediate post-reset maximum was 61.4 C, above the fixed 60 C ceiling.
This did not authorize a retry. After passive cooling, the same exact preflight
passed, followed by a complete read-only attestation:

- exact fallback kernel, BusyBox init, compatible and ext4 root;
- empty pstore, zero project modules and zero current fatal signatures;
- 70 readable thermal zones with a final 43.5 C maximum;
- exact root seal and tree identity with `promotion_state=UNBOOTED`;
- `/rog5/state/good`, `/rog5/state/next` and `arch-a.partial` absent;
- exact hashes and mode `0755` for the screen toggle, daemon, OpenRC starter,
  phone-start wrapper, preserved original launcher and OpenRC service;
- OpenRC initialized and the service enabled and active;
- one dynamically discovered `qpnp_pon` input, one daemon, one matching
  `evtest`, no unexpected reader and one event FIFO; and
- screen state `off`, one or more backlights present, and every brightness
  value zero.

This is the first real target-cycle rollback that proves the fallback screen
correction persists across boot without a host-side screen action.
ModemManager was restored to active and no fastboot device remained.

## Private evidence

The two caller-owned evidence logs remain outside Git with mode `0600`.

| Log | Bytes | SHA-256 |
|---|---:|---|
| target marker reader | 49 | `920bcd50b19bf3e62c39f91c46f81401804db72259deac8e2c186341b48e418c` |
| first fallback preflight | 72 | `fa6c269da2280be3ef141a5641a7d0efaad424d9a52a8e72e3f528b1889d46cf` |

The target log contains only the unstable-identity rejection. The fallback log
contains only the thermal rejection. Neither log contains credentials,
personal data or a device serial.

## Interpretation

The result proves:

- exact recovery and staging still work;
- target execution happened exactly once;
- automatic rollback works, without classifying which reset path caused it;
- the persistent Arch root remains untouched and unselected; and
- fallback OpenRC screen-off persistence is accepted.

It does **not** prove whether the target reached `/init`, wrote its tmpfs
marker, armed the fixed watchdog, configured the UDC, or reset before/after
USB setup. A missing stable ACM identity cannot distinguish those branches,
and the reset interval must not be used as a substitute.

Entry-v1 is consumed and must not be booted again. P2 remains HOLD and P3
remains prohibited.

## Next offline gate

Before another live candidate:

1. inspect version-matched stock `boot`, `vendor_boot`, DTBO and runtime USB
   facts using the private
   [stock-image analysis runbook](../docs/stock-image-analysis.md);
2. source-audit the Linux 7.1 USB2 gadget/UDC path and identify an
   independently recoverable marker channel;
3. prefer a marker retained in an already reserved RAM region or another
   read-only post-reset oracle so USB failure is distinguishable;
4. write fail-first transport, reset, corruption and no-storage tests;
5. reproduce target, stage, wrapper and boot package twice; and
6. require a new clean synchronized checkpoint and separate live review.

Do not weaken the watchdog, thermal limit, zero-storage boundary, one-execute
rule or exact fallback acceptance.

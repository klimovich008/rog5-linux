# Persistent-root P2 early-entry v1 offline acceptance

Date: 2026-07-28

Result: **offline PASS; live HOLD**

The seventh P2 package replaces timing inference with a fixed marker emitted
from the first RAM-only target init. It has not been live-booted at this
checkpoint.

## Boundary

The target mounts only procfs, sysfs, devtmpfs, devpts, tmpfs and configfs.
It does not mount, query, read or write a userland block device. Before USB
setup it:

1. arms a fixed 120-second SysRq reset;
2. reads `/proc/sys/kernel/osrelease` with the shell builtin;
3. counts exact command-line tokens;
4. counts block-backed mounts;
5. writes a mode-`0444` marker in tmpfs; and
6. exposes that marker repeatedly over a receive-only ACM function.

The host opens the exact `ROG5_P2_entry_oracle` ACM identity read-only and
transmits zero bytes. A complete marker must report:

- exact kernel `7.1.4-gcfd385a1c754`;
- one each of `rog5.persistent_ro=1`, `rog5.ufs_discovery=1` and
  `rog5.p2_entry_diag=1`;
- zero invalid token-family members;
- zero block-backed mounts; and
- the still-armed 120-second watchdog.

USB failure does not disable rollback.

## Reproducibility

Two independently retained ASUS source/build volumes produced byte-identical
wrapper outputs. Duplicate target initramfs, staging initramfs, wrapper, raw
boot image and AVB image also match their canonical copies.

| Canonical artifact | Bytes | SHA-256 |
|---|---:|---|
| `rog5-persistent-root-entry-initramfs.cpio.gz` | 5,839,811 | `09f7e69daf270c584b1947f41872a9af512c47e26fb2e8a30d3cdfb2fcc5d7a5` |
| `rog5-persistent-root-entry-kexec-stage.cpio.gz` | 26,674,329 | `3360abb8b47cdc5ffd5be59664b979fad186611442bd8224ced225084a4ecc73` |
| `Image-5.4.210-persistent-root-entry-wrapper` | 69,372,416 | `5171ab75e55dc2de330f126dbffc42fc380a4fc04f623368e775375d48cc8fbc` |
| `config-5.4.210-persistent-root-entry-wrapper` | 185,763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| `build-meta-5.4.210-persistent-root-entry-wrapper.txt` | 442 | `36ef17a26a65f9a78a72469f7b44391da0d3a1b77491c5dcb96f662ba5a1f0c6` |
| `boot-5.4.210-persistent-root-entry.raw.img` | 96,055,296 | `36455b88ac36bc88b449893096bba839ac12fe229065b4a23d55687a3b9c8079` |
| `boot-5.4.210-persistent-root-entry.avb.img` | 100,663,296 | `5489638517ebd83684702e6197ea459d890c6274b328cc6a3373b65a05442b3e` |

The bundle verifier checks manifest identity and mode, duplicate equality,
nested payloads, the exact wrapper command line, target-only token exclusion
from the wrapper, header-v3 unpacking, unsigned AVB structure, credential
absence, and all focused tests.

## Host control

`run-persistent-root-entry-live-gate.sh` is guard-first and requires a clean
branch equal to its remote-tracking checkpoint, exactly one fastboot device,
three explicit live guards, private caller-owned credentials/evidence, and the
manifest-pinned AVB image. Its mock suite proves:

- temporary boot only and no flash path;
- one load, one staging preflight and exactly one non-retryable execute;
- receive-only marker handling;
- rollback verification after both accepted and rejected/missing markers;
- exact sealed root identity with `UNBOOTED` and selectors absent;
- fallback screen-off and supervised power-button service acceptance; and
- ModemManager restoration.

## Fallback screen lifecycle

The persistent Alpine fallback previously launched an unmanaged shell daemon
and restored the panel on after target resets. A tested OpenRC service,
idempotent hardware-aware toggle, child-reaping event daemon, volatile OpenRC
starter and fail-safe phone-launcher wrapper are now installed. Live
start/stop/start testing passed with one daemon, one `evtest`, no orphan or
stale FIFO, and brightness remaining zero. The original phone launcher is
preserved separately and still supplies the manual daemon fallback if OpenRC
cannot start.

Cold/reboot persistence is not claimed yet. The first P2 entry live cycle must
prove that the wrapper starts the service after automatic rollback without a
corrective host action.

## Live gate

Before any live run:

1. commit and push a clean synchronized checkpoint;
2. re-run the complete bundle, screen-service and live-runner tests;
3. require exact healthy fallback and safe thermals;
4. enter fastboot through the guarded fallback helper; and
5. run one attended temporary boot only.

The package is consumed after that one cycle regardless of result. Never
flash it and never retry it.

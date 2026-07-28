# Recovery runtime bundle contract

Status: **standalone native verifier implemented and tested offline;
responder and initramfs integration pending**

Live authority: **none**

Last reviewed: 2026-07-28

This is the source of truth for the first signed runtime-bundle format accepted
by stable recovery. The implementation is
`tools/recovery_control/rog5-bundle-verify.c`. Its host fault suite is
`scripts/host/test-recovery-bundle-native.py`; its pinned AArch64 static build
and QEMU aggregate are `scripts/device/build-recovery-bundle-verifier.sh` and
`scripts/host/test-recovery-bundle-aarch64.sh`. The timestamped no-cache
builder bootstrap is
`scripts/host/build-recovery-bundle-verifier-image.sh`.

The verifier is not yet called by the recovery responder, is not present in an
initramfs, and cannot authorize a phone action. A production signing key does
not exist. Tests generate an ephemeral Ed25519 key under a temporary directory
and delete it when the test exits.

## Fixed paths and inventory

Production accepts exactly:

```text
/run/rog5-bundles/<bundle-id>/
    manifest
    manifest.sig
    Image
    board.dtb
    initramfs.cpio.gz
```

Its raw 32-byte Ed25519 public key is fixed at:

```text
/etc/rog5/recovery-bundle-ed25519.pub
```

The production binary has no path-override option. Test builds expose
`--bundle-root` and `--trust-key`, and the production build proves those
strings are absent.

The bundle root and selected bundle directory must be real directories owned
by the verifier's effective user, with no group or other write bit. Every
inventory item must be a real regular file with the same owner, no group or
other write bit, and link count one. Symbolic links, hard links, missing
entries, and extra entries fail closed. Recovery must create and finalize the
bundle before invoking the verifier; no process may mutate it afterward.

`<bundle-id>` is 1–64 lowercase ASCII letters, digits, `.`, `_`, or `-`. Its
first byte is alphanumeric; it cannot contain `..` or equal `none`.

## Canonical manifest

`manifest` is a newline-terminated printable-ASCII record of at most 4096
bytes. It has exactly these fields in this order, with no blanks, duplicates,
comments, unknown fields, carriage returns, or leading-zero numbers:

```text
format=rog5-recovery-bundle-v1
bundle=<bundle-id>
profile=<fixed-profile>
kernel_size=<decimal>
kernel_sha256=<64 lowercase hex>
dtb_size=<decimal>
dtb_sha256=<64 lowercase hex>
initramfs_size=<decimal>
initramfs_sha256=<64 lowercase hex>
target_id=<fixed-safe-identity>
target_release=<fixed-safe-identity>
rollback_timeout=<decimal-seconds>
target_timeout=<decimal-seconds>
```

Permitted profiles are:

- `diagnostic-initramfs-v1`;
- `network-root-v1`;
- `persistent-root-ro-v1`.

Target identities contain only ASCII letters, digits, `.`, `_`, `+`, and `-`;
they cannot begin with `.`, contain `..`, or be empty. `target_id` is bounded
to 64 bytes and `target_release` to 96 bytes. Artifact hashes cannot be the
all-zero unset value.

Size policy is:

| Artifact | Minimum | Maximum |
|---|---:|---:|
| `Image` | 64 bytes | 128 MiB |
| `board.dtb` | 40 bytes | 2 MiB |
| compressed initramfs | 2 bytes | 256 MiB |
| expanded initramfs | newc header | 128 MiB |

Rollback timeout is 60–900 seconds, target timeout is 30–600 seconds, and the
target timeout must leave at least 30 seconds of rollback margin.
`persistent-root-ro-v1` requires at least 300 seconds of rollback time.

`manifest.sig` is exactly 64 raw Ed25519 signature bytes over the exact
manifest bytes. The caller also supplies the expected manifest SHA-256. The
verifier requires both the requested hash and the signature before accepting
the bundle.

## Artifact policy

The three manifest sizes must equal the opened file sizes and all three
SHA-256 values must match.

`Image` must have a Linux arm64 Image header:

- `ARM\x64` magic at offset 56;
- memory image size at least the file size and at most 256 MiB;
- no flag outside the low four defined bits;
- all three reserved 64-bit header words zero.

`initramfs.cpio.gz` must be one complete gzip member with no trailing or
concatenated data. Verification inflates it through a fixed 64 KiB streaming
buffer and rejects expansion beyond 128 MiB. The streaming newc parser checks
every header and hexadecimal field, pathname and alignment, optional CRC,
strictly sorted unique entries, bounded entry count, zero padding, one
executable regular `init`, one final `TRAILER!!!`, and only zero archive
padding after the trailer. It does not allocate the expanded archive.

`board.dtb` must be one bounded FDT v17 structure compatible with v16 and
must satisfy all of these:

- root model is exactly `ASUS ROG Phone 5`;
- root compatibility contains both `asus,rog-phone5` and `qcom,sm8350`;
- no `bootargs` property exists anywhere;
- there is one root and one root-level `reserved-memory` node;
- reserved-memory contains exactly one `#address-cells = <2>`, one
  `#size-cells = <2>`, and one empty `ranges` before any child;
- every immediate child `reg` tuple is nonzero and non-overflowing;
- reserved-memory tuples do not overlap;
- one tuple is exactly `0x9b800000` plus `0x400000` for the fixed ramoops
  reservation;
- the FDT reservation map is empty;
- header, structure, and strings blocks use the canonical contiguous v17
  layout with no trailing structure or file data.

The FDT walk is bounded to 64 node levels and 128 reserved-memory tuples. The
newc walk is bounded to 8192 entries with pathnames of at most 4096 bytes.
The generated command line is bounded to 1023 bytes plus its terminator.

## Generated command line

The manifest never carries free-form command-line text. The verifier generates
one fixed command line from constants, the validated bundle ID, and bounded
rollback timeout.

The common prefix is:

```text
console=ttyMSM0,115200n8 rdinit=/init panic=10 oops=panic loglevel=8
ignore_loglevel printk.always_kmsg_dump=Y
```

The profile contributes exactly one of:

```text
rog5.diagnostic=1
rog5.netroot=1
rog5.ufs_discovery=1 rog5.persistent_ro=1
```

All profiles then receive:

```text
ramoops.mem_address=0x9b800000 ramoops.mem_size=0x400000
ramoops.record_size=0x100000 ramoops.console_size=0x300000
ramoops.pmsg_size=0 ramoops.ftrace_size=0 ramoops.dump_oops=1
rog5.bundle=<bundle-id> rog5.recovery_timeout=<rollback-timeout>
```

Successful verification prints one canonical
`rog5-verified-plan-v1` record containing only fixed artifact basenames,
target identity, target timeout, generated command line, and its SHA-256. It
never prints a caller-supplied pathname.

## Reproducible AArch64 build

The production verifier is a stripped static-PIE AArch64 binary. Its builder
uses:

- Alpine 3.24 arm64 base digest
  `sha256:e7a1a92a5bfeee40966aea60f0796b0e7917cc35591542701834f03a68fa3d18`;
- GCC 15.2.0;
- OpenSSL 3.5.7 static `libcrypto`;
- zlib 1.3.2 static library;
- fixed `SOURCE_DATE_EPOCH=1681862400`;
- no ELF build ID, interpreter, writable executable stack, test path, or test
  environment interface. No key material enters the build context.

The aggregate builds production twice, requires byte equality, then executes
the same signed mutation suite against a separate static AArch64 test binary
under `qemu-aarch64-static`. Two independent no-cache builder bootstraps also
produce the same pinned image ID and digest; volatile container hostname,
hosts, and APK-log content are normalized in the Dockerfile.

The current offline checkpoint produced:

```text
source_sha256=2ceb59beb8807543f29ee1f3cd4348f3a356ad989cd808c94d39f33f87813612
binary_sha256=aabef30cf7800a70942036d7f19515272272c3d6f8a0d21cf7b9fb64ced36ef1
builder_id=e2e90f8ad3cfc4f9b7660ee8828fcae008792f05567fb9b4efd3ab0102063d8e
builder_digest=sha256:b4946b74324785d005aa3067dd18788f90cc65215a519c8735dce03aa01d1268
```

These identities are checkpoint evidence, not a live allowlist. Any source
change requires a fresh two-build/QEMU result and updated pins.

## Remaining integration gates

Before the responder may return `PREPARED`:

1. fetch all five files from the fixed NCM host into a private temporary
   directory;
2. publish one finalized owner-private bundle directory;
3. run this verifier with the requested bundle and manifest hash;
4. parse only the exact canonical verified-plan record;
5. perform one bounded `kexec -l` without a shell and without reopening an
   attacker-controlled path;
6. persist `PREPARED` only after the load succeeds;
7. retain the watchdog throughout fetch, verification, and load;
8. add crash, timeout, malformed-plan, verifier-failure, and load-failure
   tests;
9. independently review the combined responder/verifier boundary;
10. create or use a production signing key only after separate user
    confirmation.

Initramfs integration, shell removal, wrapper rebuild, image verification,
staging-only live promotion, and any payload execution remain later,
separately reviewed gates.

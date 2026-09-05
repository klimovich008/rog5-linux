# Recovery runtime-bundle verifier offline result

Date: 2026-07-28

Result: **PASS OFFLINE; NOT INTEGRATED; NO LIVE AUTHORITY**

The standalone native verifier in
`tools/recovery_control/rog5-bundle-verify.c` now enforces the exact contract
in `docs/recovery-bundle-contract.md`. It verifies a canonical manifest and
raw Ed25519 signature, requested manifest hash, private exact inventory,
artifact sizes and hashes, arm64 Image header, ROG Phone 5 DTB policy,
complete bounded gzip/newc initramfs, and a generated fixed command line.

It is not called by the recovery responder, does not run `kexec`, is not in an
initramfs, and cannot authorize a phone action. The production responder still
rejects every `PREPARE`.

## Test coverage

The host and real static AArch64/QEMU runs each pass 18 test methods containing
80 signed success and mutation scenarios. Tests generate an ephemeral Ed25519
key in a temporary directory and delete it afterward. No production signing
credential exists.

Coverage includes:

- exact output for all three fixed profiles and the generated command-line
  SHA-256;
- changed-after-signing manifests, wrong requested hashes, corrupted
  signatures, untrusted keys, all-zero hashes, field reorder, duplication,
  unknown fields, non-ASCII bytes, carriage returns, embedded NUL, leading
  zeros, unsafe identities, profile mismatch, and timeout bounds;
- content, size, hash, and compressed-size limits for all artifacts;
- exact inventory, extra entries, file and key symlinks, hard links,
  group-write modes, unsafe bundle/root directories, and bundle-ID traversal;
- arm64 Image magic, memory size, flags, and reserved words;
- bounded streaming gzip verification, trailing data rejection, 129 MiB
  expansion rejection, complete newc headers, hexadecimal fields, zero
  alignment, sorted unique safe paths, executable regular `init`, checksum,
  final trailer, and archive padding;
- FDT canonical layout, exact root identity, no `bootargs`, empty reservation
  map, explicit unique two-cell reserved-memory geometry before children,
  one `reg` per child, exact ramoops reservation, no overlaps, and malformed
  header/string-list/raw duplicate-property rejection;
- absence of production path overrides, plus an intentionally contaminated
  AArch64 source that the production builder must reject; and
- real compatibility with the accepted v18 recovery DTB, Linux 7.1.4 Image,
  and v18 recovery initramfs under a temporary signed manifest.

## Known-artifact compatibility probe

The verifier was also run against one temporary diagnostic-profile bundle
made from these existing, independently pinned v18 artifacts:

| Artifact | Size | SHA-256 |
|---|---:|---|
| `Image-7.1.4` | 38,406,656 | `4d6f3ecaa8d2af0b1e1fddd0655af469e867d596f8f3eae0a20583b058fbe697` |
| `sm8350-asus-rog-phone5-recovery.dtb` | 102,774 | `255c5ac199b0412c499aae39bb596507b934e71c003396040d4952f0c5ffabe6` |
| `rog5-recovery-initramfs.cpio.gz` | 5,838,973 | `852b02a2cbcb2dfd43598269ff1b2b10cb1542e90ab7a7aa32d1a26c7cc645fc` |

An ephemeral Ed25519 key signed only the temporary manifest. Verification
returned the exact `rog5-verified-plan-v1` header, bundle
`recovery-v18-artifacts`, and profile `diagnostic-initramfs-v1`. The temporary
bundle and key were outside the repository and are not live inputs.

GCC `-Wall -Wextra -Werror -fanalyzer`, Python compilation, shell syntax, and
`git diff --check` pass. ASan/UBSan execution was not available because this
host lacks their runtime libraries; real AArch64 execution under QEMU and the
GCC analyzer are the recorded compensating checks.

## Reproducibility

`scripts/host/build-recovery-bundle-verifier-image.sh` performs a timestamped
no-cache arm64 builder bootstrap. Volatile container hostname, hosts, and APK
log files are normalized. Two independent no-cache builds produced the same
image ID and digest.

`scripts/host/test-recovery-bundle-aarch64.sh` then builds production twice,
requires byte equality, verifies ELF hardening and production-only strings,
builds a separate test binary, and runs the full signed mutation suite through
`qemu-aarch64-static`.

| Item | Identity |
|---|---|
| builder image ID | `e2e90f8ad3cfc4f9b7660ee8828fcae008792f05567fb9b4efd3ab0102063d8e` |
| builder image digest | `sha256:b4946b74324785d005aa3067dd18788f90cc65215a519c8735dce03aa01d1268` |
| verifier source SHA-256 | `2ceb59beb8807543f29ee1f3cd4348f3a356ad989cd808c94d39f33f87813612` |
| production AArch64 binary SHA-256 | `aabef30cf7800a70942036d7f19515272272c3d6f8a0d21cf7b9fb64ced36ef1` |

The production output is a stripped static-PIE AArch64 ELF with RELRO, no
interpreter, no build ID, a non-executable stack, and mode `0755`.

## Commands

```text
scripts/host/build-recovery-bundle-verifier-image.sh
python3 scripts/host/test-recovery-bundle-native.py
scripts/host/test-recovery-bundle-aarch64.sh
scripts/host/test-repository-linux.sh quick
git diff --check
```

## Independent review and remaining boundary

Independent security, specification, and standards reviews identified and
closed ineffective negative build assertions, partial CPIO validation,
ambiguous FDT critical properties, unchecked plan output, non-fail-closed
directory enumeration, missing adversarial cases, and volatile builder-image
inputs.

One P1 integration requirement remains deliberately open: `PREPARE` must load
the same open artifact objects that were verified. Closing these descriptors,
printing basenames, and reopening paths would permit a post-verification
replacement race. Integration must pass the verified descriptors directly to
the fixed `kexec -l` operation, or make the verifier perform that load itself;
rehashing and reopening a pathname is not accepted.

Fetch, same-descriptor load, watchdog monitoring, exact verified-plan parsing,
responder fault injection, initramfs integration, shell removal, wrapper
rebuild, and staging-only promotion remain later gates. No phone was booted,
rebooted, or flashed, and no allowlist, recovery image, or production
credential changed.

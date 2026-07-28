# Persistent Arch P2 kernel-config timing live attempt

Date: 2026-07-28

Result: **REJECTED BEFORE TARGET USB; FALLBACK PASS; NO FLASH.**

The attended command temporarily booted the corrected ASUS wrapper, reached
recovery ACM, loaded and preflighted the exact Linux 7.1.4 payload, and
issued exactly one `kexec -e`. The target did not expose its USB or SSH
identity. Exact Alpine fallback appeared 37 seconds after execute, selecting
the broad 10-second runtime kernel-config branch from the previous timing
map.

## Rejected input

| Input | Size | SHA-256 |
|---|---:|---|
| raw header-v3 wrapper | 96,067,584 | `5c9e0391f1be68f1257c3402eea4105508066b2b6afd26c450c4725e3ae1aba9` |
| temporary unsigned AVB wrapper | 100,663,296 | `f4f33bae1e69c8499527be159d409b53cea424e09eefc7e25c73157516d54249` |
| ASUS wrapper Image | 69,372,416 | `b133ebcee9c2b0a99876da1dd20615c9f569c67e7e91a089d9de5a54e6ad8d17` |
| nested staging initramfs | 26,687,246 | `b14c2a54eb413f1dbb2b808691b5c6b77614b7a502cd4ff7eb5a34d9bac0c54e` |
| target initramfs | 5,853,871 | `f69d31c78bd8ce154516e701f0166760d2934b009152242a752795249b1103f2` |
| Linux 7.1.4 target Image | 38,607,360 | `832757fc6b97554813a14049123667bc6f5b225e6204ca048d73c3a36c76469f` |
| Linux 7.1.4 target config | 242,248 | `8a7fabffa076a65d09529ef1004c315e1296e547a02d08c362031d0363ba63c3` |

The image was used only with `fastboot boot`. No partition was flashed,
formatted, repaired, repartitioned, selected, or promoted.

## Observed sequence

1. The clean synchronized branch and manifest/image preflight passed.
2. Fastboot transferred and accepted the temporary image.
3. Exact `ROG5_recovery` ACM appeared.
4. The fixed load action succeeded after one bounded identical retry caused
   by the initial serial-open race.
5. Recovery independently verified every nested payload hash, all 116
   physical block nodes read-only, zero block-backed mounts, and a loaded
   kexec image.
6. Exactly one non-retryable execute action issued `kexec -e`.
7. The target exposed neither its USB gadget nor strict SSH identity.
8. Exact Alpine fallback was detected after 37 seconds.
9. Fallback passed exact kernel, init, compatible, ext4 root, empty pstore,
   zero project modules, safe thermals, unchanged persistent-root seal,
   `UNBOOTED` state, absent selectors, and screen-off checks.
10. ModemManager was restored to its initial active state.

The private mode-0600 rejection marker is caller-owned outside the repository
and has SHA-256
`c72bf59ff2f28f33932790da88f2cdcea5147bc3bdef8d066f877c8f39bdbc61`.
It contains only the rejection class and elapsed seconds, with no serial,
credential, or host path.

## Classification

The first immediate target rejection established an approximately 26-second
execute-to-fallback baseline. The previous map added 10 seconds for one
combined kernel-config branch; its expected interval was therefore about
36 seconds. The observed 37 seconds is the baseline plus that bounded delay
within USB-enumeration and scheduler resolution. It selects the
kernel-config branch but does not distinguish a missing config file, decode
failure, or failed setting comparison.

Offline inspection rules out a target Image/config mismatch:

- the target Image contains one embedded IKCONFIG stream;
- its decoded SHA-256 is exactly
  `8a7fabffa076a65d09529ef1004c315e1296e547a02d08c362031d0363ba63c3`,
  identical to the pinned configuration; and
- that configuration enables `CONFIG_IKCONFIG`,
  `CONFIG_IKCONFIG_PROC`, `CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY`,
  `CONFIG_EXT4_FS`, and `CONFIG_OVERLAY_FS`.

The old target decompressed `/proc/config.gz` three times in separate
negated pipelines and grouped all outcomes under one marker. A one-pass
identity check is both a stronger attestation and a narrower diagnostic.

## Fail-first correction

The initramfs test was first changed to require the exact full config hash,
one RAM-only decoded file, and separate failure stages; it failed against the
old implementation. The target now:

1. requires readable `/proc/config.gz`;
2. decodes it once to mode-0400 `/run/rog5-kernel.config`;
3. requires the full decoded file SHA-256 to equal the pinned build config;
4. leaves physical storage untouched; and
5. assigns unique bounded delays to file, decode, identity, and every later
   pre-USB branch.

| Stage | Added delay |
|---|---:|
| invalid command line | 5 s |
| missing runtime config | 10 s |
| runtime config decode | 15 s |
| runtime config identity | 20 s |
| UFS discovery | 35 s |
| UFS power containment | 50 s |
| physical storage lock | 65 s |
| exact userdata identity | 80 s |
| UFS inventory | 95 s |
| USB setup | 110 s |

Two independent builds at every changed packaging layer are byte-identical:

| Corrected product | Size | SHA-256 |
|---|---:|---|
| target initramfs | 5,854,487 | `bb3a57d5bb5a2fd62a52832efe624ef4a7bb23ee66de0fc89f9995028394fab6` |
| nested staging initramfs | 26,688,238 | `1dc79b683f4040543ed59c94e2cea9dbb1ada38dffbd936d146b39fc13021fdc` |
| ASUS wrapper Image | 69,372,416 | `0fa8a9d7aaa27f43467ad31048ad6efaca95369d3334ff600feeca1ace673029` |
| ASUS wrapper metadata | 410 | `05ec9d0a80af2d2ef10f09a3a035e8d9166b9c2e2c6665ab742b9890acfdf010` |
| raw header-v3 image | 96,067,584 | `3a77f1cb50def26ac6ab6e8e8a7b7e75e5d5be150ae73eead0d9c9c538045859` |
| unsigned AVB image | 100,663,296 | `033f4c15fdfc1ffeb015028cce0eb4ca621f5909df4b6d3cf113c38f249839e8` |

The target Image, decoded config, DTB, verifier, root seal, read-only UFS
policy, watchdog, and wrapper config are unchanged. A clean final repack with
the pinned `avbtool 1.4.0` SHA-256
`6418646bb5bf3c57c3c702bfd1e157917e59f9ce25c3c81bcce79d85655e56ff`
reproduces the raw and AVB products exactly.

## Decision

The rejected timing package is consumed and must not be retried or flashed.
P2 remains HOLD and P3 remains prohibited. After the one-pass package passes
the complete offline suite and its source, manifest, and report are committed
and pushed, it may receive one attended non-flashing diagnostic boot. Only
complete target acceptance plus exact automatic fallback can pass P2.

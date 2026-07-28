# Persistent Arch P2 config-identity live attempt

Date: 2026-07-28

Result: **REJECTED BEFORE TARGET USB; EXACT FALLBACK PASS; NO FLASH.**

The attended command temporarily booted the manifest-pinned ASUS wrapper,
reached exact recovery ACM, loaded and preflighted the exact Linux 7.1.4
payload, and issued exactly one `kexec -e`. The target exposed neither its
USB gadget nor strict SSH identity. Exact Alpine fallback appeared 37 seconds
after execute. This consumes and rejects the one-pass runtime-config package;
it does not establish P2 target acceptance.

## Rejected input

| Input | Size | SHA-256 |
|---|---:|---|
| raw header-v3 wrapper | 96,067,584 | `3a77f1cb50def26ac6ab6e8e8a7b7e75e5d5be150ae73eead0d9c9c538045859` |
| temporary unsigned AVB wrapper | 100,663,296 | `033f4c15fdfc1ffeb015028cce0eb4ca621f5909df4b6d3cf113c38f249839e8` |
| ASUS wrapper Image | 69,372,416 | `0fa8a9d7aaa27f43467ad31048ad6efaca95369d3334ff600feeca1ace673029` |
| nested staging initramfs | 26,688,238 | `1dc79b683f4040543ed59c94e2cea9dbb1ada38dffbd936d146b39fc13021fdc` |
| target initramfs | 5,854,487 | `bb3a57d5bb5a2fd62a52832efe624ef4a7bb23ee66de0fc89f9995028394fab6` |
| Linux 7.1.4 target Image | 38,607,360 | `832757fc6b97554813a14049123667bc6f5b225e6204ca048d73c3a36c76469f` |
| Linux 7.1.4 target config | 242,248 | `8a7fabffa076a65d09529ef1004c315e1296e547a02d08c362031d0363ba63c3` |

The image was used only with `fastboot boot`. No partition was flashed,
formatted, repaired, repartitioned, selected, promoted, or mounted by the
host.

## Observed sequence

1. The synchronized branch and manifest/image preflight passed.
2. Fastboot transferred and accepted the 100,663,296-byte temporary image.
3. Exact recovery ACM appeared.
4. The first fixed load-marker read lost the serial-open race; one bounded,
   byte-identical load retry succeeded. No execute action was retried.
5. Recovery verified every nested payload hash, all 116 physical block nodes
   read-only, zero block-backed mounts, and a loaded kexec image.
6. Exactly one non-retryable execute action issued `kexec -e`.
7. The target exposed neither its expected USB gadget nor strict SSH identity.
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

The package assigned 5, 10, 15, and 20 seconds to command-line,
`/proc/config.gz` availability, decode, and full identity failures,
respectively. The repeated 37-second fallback selects the early runtime
proc-config path, most closely the 20-second identity marker, within baseline
USB-enumeration and scheduling resolution. This is a bounded classification,
not proof of why procfs did not satisfy the check.

Offline evidence establishes that the intended Image and configuration are
coherent:

- the exact target Image contains one `IKCFG_ST`/`IKCFG_ED` stream;
- decompression reproduces the pinned config byte-for-byte;
- the config enables `CONFIG_IKCONFIG`, `CONFIG_IKCONFIG_PROC`,
  `CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY`, `CONFIG_EXT4_FS`, and
  `CONFIG_OVERLAY_FS`; and
- duplicate System maps expose the expected IKCONFIG symbols.

The recovery stage already verifies the exact target Image hash before
kexec. Depending again on a live procfs representation before USB therefore
adds an early failure dependency without strengthening the exact-image
identity.

## Fail-first successor

The initramfs test was first changed to require the exact running release and
to reject any `/proc/config.gz` dependency; it failed against the rejected
implementation. The boot-contract test was extended independently to extract
the target Image's IKCONFIG stream and require byte identity with the pinned
config and all safety-critical settings.

The successor target now:

1. enters only from the recovery-hashed target Image;
2. requires exact `uname -r` value `7.1.4-gcfd385a1c754` before arming the
   watchdog or inspecting storage;
3. has no live `/proc/config.gz` dependency;
4. retains offline byte-for-byte Image/config attestation; and
5. preserves unique bounded delays for every remaining pre-USB branch.

| Stage | Added delay |
|---|---:|
| invalid command line | 5 s |
| running kernel release | 20 s |
| UFS discovery | 35 s |
| UFS power containment | 50 s |
| physical storage lock | 65 s |
| exact userdata identity | 80 s |
| UFS inventory | 95 s |
| USB setup | 110 s |

Two independent builds at every changed packaging layer are byte-identical:

| Corrected product | Size | SHA-256 |
|---|---:|---|
| target initramfs | 5,853,822 | `e2b58d50fae31509b8cd87ed01afbf25c90d49500e3d9d9691ecd77643fd434e` |
| nested staging initramfs | 26,688,093 | `438aaf1c99455e23ff27f758738e779b0fd318e68c58467eeae7b77c55a87520` |
| ASUS wrapper Image | 69,372,416 | `cfd65186afd75435d34cb33a36c76c4a80a861d0360bec13495c0b445836b7c2` |
| ASUS wrapper metadata | 410 | `9ff24786682d447b185fd69f1d88334585efa6f84cc3fd4333f7a87c95fe576c` |
| raw header-v3 image | 96,067,584 | `7a0293daaf14939bd2dc6b6264fcdef955d8fb6c654deaf4ffe394e9b2c8bc31` |
| unsigned AVB image | 100,663,296 | `3c0355be52ebb005371b26e73a97a9899efaf9569c79442cc9f063779faf475b` |

The final duplicate wrapper builds use separate immutable source volumes and
match in Image, config, metadata, and their one embedded staging archive.
Two header-v3 repacks and `avbtool 1.4.0` AVB products also match exactly.
Outputs from two earlier duplicate attempts that exhausted host resources
were rejected; a fresh full build on the spacious home filesystem produced
the accepted matching result.

## Decision

The one-pass proc-config package is consumed and must not be retried or
flashed. Its successor subsequently received its sole attended boot and
[returned safely to exact fallback after 36 seconds without target
USB](2026-07-28-persistent-root-p2-kernel-release-live-rejected.md). That
kernel-release package is also consumed. P2 remains HOLD and P3 remains
prohibited. The next fail-first successor reads
`/proc/sys/kernel/osrelease` directly and separates file/read failure from
identity mismatch. Only complete target acceptance plus exact automatic
fallback can pass P2.

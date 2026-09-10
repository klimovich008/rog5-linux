# Headless recovery dependency closure — 2026-07-30

## Result

**PASS — every pruned input required to rebuild the corrected headless
recovery candidate is either exactly reconstructed, immutably bootstrapped,
or bound to a qualified local builder.**

This is hardware-free evidence. No phone, ADB, fastboot, SSH credential, root
password, persistent signing key, private workload input, or external service
was used. It grants no boot, flash, signing, storage, or deployment authority.

## Reconstructed recovery lineage

The historical v18 recovery archive had been pruned, but two independently
retained P2 archives still contained enough exact lineage to recover a stable
successor base. `scripts/host/reconstruct-recovery-base-v18r.sh` verifies both
parent identities, extracts them separately, reconstructs the archive twice,
compares the trees and bytes, and publishes only the following no-replace
output:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `rog5-recovery-base-v18r.cpio.gz` | 5,838,975 | `da573d089cd617e088624b6d6bf711e193a4df5367843293e2e5ba543556e51d` |
| reconstruction provenance | 921 | `768bf860fefc94af5620506df0e398a4bf5ff1eb0c0961692c5e0efb7d5a2448` |

The successor deliberately has its own identity. It does not claim to be the
missing historical v18 archive.

## Exact network-root v3 recovery

The accepted network-root v3 initramfs was recovered in two historical
transitions:

1. remove the empty `usr/local/sbin` directory introduced by the P2 tooling
   and restore the exact UFS-era `recovery-init`; and
2. replace that init plus shutdown helper with the exact network-root versions
   from commit `adb50a98fe5fe79453d9adfb0b49f0c5bad4f617`.

The intermediate UFS-v2 archive reproduced as 5,841,750 bytes with SHA-256
`df1d0cdb95513d7ef6d772a3a6165d37b3b226682d92e30a2143409341bbefb1`.
The final accepted archive reproduced exactly:

```text
bytes:   5,840,728
sha256:  4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac
```

`scripts/host/test-reconstruct-network-root-v3.sh` performs two independent
reconstructions and rejects parent, source-blob, intermediate, final,
symlink, mode, and existing-output changes.

## Exact headless target initramfs

The qualified ARM64 verifier builder reproduced the static whole-tree
verifier:

```text
bytes:   326,920
sha256:  bc7d5c9e5a7a0ff4d46f9fc9dc1680f0d9a960bcd9b01d11fb327d407fa4ba58
```

Two isolated compositions from the recovered network-root base then matched
the frozen headless target byte-for-byte:

```text
bytes:   5,978,369
sha256:  819bdf88c920057a5d8b511cb13e3adc0f7d8d9cf1a92a7fac087697889bb9b5
```

The build uses the private rootless ARM64 runner and an isolated cpio-only
command path, avoiding both host `binfmt_misc` state and the earlier gzip-shim
recursion. Builder identities and limits are recorded in the
[ARM64 recovery-builder qualification](2026-07-30-steam-deck-recovery-builders-qualified.md).

## Android boot tools

The accepted packaging bytes were traced to immutable Android Open Source
Project Git blobs. `scripts/host/fetch-android-boot-tools.sh` verifies the
repositories, commits, blobs, source bytes, historical CRLF normalization,
final hashes, executable modes, and `avbtool 1.4.0` before atomic no-replace
publication.

| Tool | Bytes | SHA-256 |
|---|---:|---|
| `mkbootimg.py` | 27,333 | `d99136f30bda966e8820c8ae53a82c659ca36e6d1aaf49a4cd63ae4795a6845a` |
| `unpack_bootimg.py` | 23,786 | `7012fe91c4032446f23f3bd6f86fe1bc274517eb4e7aef923ed8396a5b619aef` |
| `generate_gki_certificate.py` | 3,082 | `367858be999c3013d44450a91bde0067f0530857b5a95fbf5858c62477bcaf36` |
| `avbtool.py` | 247,851 | `6418646bb5bf3c57c3c702bfd1e157917e59f9ce25c3c81bcce79d85655e56ff` |

The fetch step is the only networked reconstruction step. All candidate
building and verification after publication run with container networking
disabled.

## Compact canonical boot template

The missing 96 MiB historical wrapper template is no longer a successor-build
dependency. `scripts/host/build-canonical-boot-v3-template.sh` independently
creates two compact Android boot-v3 metadata templates, verifies the parsed
header/cmdline policy, compares them byte-for-byte, and publishes:

```text
bytes:   12,288
sha256:  95be17d48ec61d00a4e8c92be754c8a8345f93685ce05d412a6d3a6aceba6e02
```

It preserves Android 11/2022-02 metadata and the accepted ramoops/rollback
command line while excluding recovery CIDR and target-only UFS tokens. It is
metadata input only and must never be booted directly.

## ASUS wrapper successor

The historical wrapper builder remains byte-frozen:

```text
scripts/device/build-asus-kexec-stage.sh
sha256:
aaaa423aefc9b90dd30738bf42a0209574437599da2062b9dd8cc685d6e15b94
```

The successor entry point uses the accepted v18 output config as its exact
seed:

```text
profile:  accepted-wrapper-v18-v1
bytes:    185,763
sha256:   df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
```

This avoids inventing the pruned historical running-config input while
preserving the already accepted effective wrapper configuration. The
successor profile separately pins the qualified Steam Deck ASUS source,
builder, config, template, and Android tools.

## Contracts and limits

The canonical repository gate includes hostile contracts for:

- dual-lineage recovery reconstruction;
- network-root v3 parent and source transitions;
- exact headless target twin composition;
- private rootless ARM64 execution and builder qualification;
- authoritative AOSP tool bootstrapping;
- canonical boot-v3 metadata/template reconstruction; and
- accepted-config ASUS wrapper successor behavior without changing the
  frozen historical builder.

This closure proves rebuildability and exact bytes, not hardware behavior.
USB/NCM, Linux target boot, SSH, buttons/indicator, charging, thermal control,
suspend, sensors, audio, display, radio, and GPU remain separate attended
live gates behind fresh authorization.

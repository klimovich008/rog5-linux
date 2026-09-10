# Steam Deck ASUS 5.4 builder qualification — 2026-07-30

## Result

**PASS — qualified for host-only ASUS 5.4 kernel work on the current Steam
Deck host class.**

Two independently fetched builder root filesystems matched, and two fresh,
network-disabled ASUS kernel builds were byte-identical to each other and to
the historical P2 `Image` oracle. The historical 2026-07-29 profile remains
unchanged.

This result grants no signing, phone access, boot, flash, wipe, storage, or
deployment authority. No phone or credential was used.

## Host and inputs

```text
host:                     Steam Deck x86_64
SteamOS:                  3.8.24 build 20260716.2
host kernel:              6.16.12-drmexec7-valve24.5-1-neptune-616-drm-exec-gf253f5da553e
Podman:                   5.5.2, rootless
builder recipe sha256:    28dca69fd5c7f0fb1cf3418fd5a8bc5d2d8d04cdd1cf09919667e32faefb54bd
package lock sha256:      9dce7979f2b55e0f56c6dd803986d127107e5a7ead15cd69e780aebaccacc101
Ubuntu snapshot:          20260728T000000Z
source tree sha256:       592aefb37589f9f9483b43677e29702ed927fc56a251616e33e81f2645e9c35a
config sha256:            df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
initramfs sha256:         438aaf1c99455e23ff27f758738e779b0fd318e68c58467eeae7b77c55a87520
```

The source was mounted read-only. Each kernel build used a new empty output
directory, container networking was disabled, and build user/host/version/
timestamp, architecture, toolchain, project, and compiler flags were fixed.

## Rootfs reproduction

The current Deck image had a normalized rootfs identity different from the
historical host:

```text
historical rootfs: 2eb07c8a9a4895530ab092ed43e8a953b428f7cd2315c63fa08cf1f9a83f13af
Deck rootfs:       a82749a50365d864714594cc40ce27a28af4f132ef0e540946338b4681bf1fda
```

The historical run retained only its final digest, so a file-level
classification of that old-host difference is impossible. The historical
profile and cache identities were therefore not changed or broadened.

`bootstrap-kernel-builder.sh reproduce` then performed two no-layer-cache
builds with distinct APT cache namespaces. Both independently fetched the
pinned snapshot and produced the Deck identity:

```text
first image ID:  8f7129af3a8e7d4d3b5a735d32fc9aaad02c1ba3a280bbf321fb41b91b14be4f
second image ID: f15d77ec5fb04e8d261629d560128671ba3c2a3c05d5cc8285bab14de5b0aba0
rootfs identity: a82749a50365d864714594cc40ce27a28af4f132ef0e540946338b4681bf1fda
```

Distinct OCI IDs are expected because the cache namespace is recorded in
image history; OCI metadata is diagnostic, not the acceptance identity.

The exact 24,145-line normalized stream is tracked at
[`artifacts/kernel-builder-steamdeck-v1/rootfs-manifest.tsv.gz`](../artifacts/kernel-builder-steamdeck-v1/rootfs-manifest.tsv.gz):

```text
uncompressed sha256: a82749a50365d864714594cc40ce27a28af4f132ef0e540946338b4681bf1fda
gzip sha256:         7680447aa94ed11de4313347face7b7b2168d73c92b243f733eeb656cf6bd94b
```

Future rootfs mismatches can now be diffed directly.

## ASUS kernel oracle

Both clean Deck builds produced a 69,372,416-byte `Image`:

```text
first Deck build: cfd65186afd75435d34cb33a36c76c4a80a861d0360bec13495c0b445836b7c2
twin Deck build:  cfd65186afd75435d34cb33a36c76c4a80a861d0360bec13495c0b445836b7c2
historical P2:    cfd65186afd75435d34cb33a36c76c4a80a861d0360bec13495c0b445836b7c2
```

`cmp` confirmed byte-for-byte equality among all three files. Existing
source warnings and CFI/ThinLTO linker warnings were the same non-fatal
vendor-tree class; neither build failed.

## Accepted profile and limits

The separate qualified profile is
[`configs/kernel-builder/steam-deck-asus-5.4-v1.json`](../configs/kernel-builder/steam-deck-asus-5.4-v1.json).
`verify-steam-deck-builder.sh` pins that profile, bootstrap implementation,
recipe, package closure, rootfs-manifest implementation, tracked manifest,
tool versions, and live rootfs identity.

Qualification is intentionally narrow:

- it covers the exact ASUS 5.4 oracle build on this Steam Deck host class;
- the old builder profile remains frozen;
- a distinct-host reproduction remains desirable before broadening the
  profile to unrelated outputs or hosts; and
- live phone work remains a separate attended gate.

## Claude advisory review

A targeted, tool-free Opus review classified output-level equivalence plus
independent current builds as suitable evidence for a separately named
successor profile, while rejecting an OR-list, dropping rootfs verification,
or rewriting the historical cache identity. That advice was applied only
after the local proofs above; Claude made no changes and received no
credentials or private inputs.

Two final self-contained Opus reviews separately covered the source/import
boundary and builder/profile boundary. Both returned `NO_BLOCKERS`; tools,
session persistence, credentials, private inputs, and write access remained
disabled.

## Post-proof storage cleanup

After all hashes and byte comparisons passed, one unique compact P2 OS
`Image`, config, and metadata file were retained. Three stale historical
object trees and the two new clean-output trees were then removed; the
legacy migration image and the two temporary reproduction image tags were
also removed. The local project shrank from about 27 GiB to 8 GiB. Accepted
source, the official source archive, stock-private inputs, boot images,
validation evidence, qualified builder, source volume, and public rootfs
manifest were retained.

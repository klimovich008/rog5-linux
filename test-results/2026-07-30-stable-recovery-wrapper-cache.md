# Stable-recovery wrapper cache

Date: 2026-07-30

Result: **PASS offline; exact accepted output; no compile on materialization;
authority=none; no phone or credential action**

## Outcome

A content-addressed cache entry was published from the retained accepted
corrected-headless twin build. The source was sealed twice with the new
host-metadata-independent implementation and produced the same identity:

```text
format:        rog5-kernel-source-tree-v1
entries:       79030
regular files: 73717
directories:   5272
symlinks:      41
bytes:         1182067858
tree sha256:   592aefb37589f9f9483b43677e29702ed927fc56a251616e33e81f2645e9c35a
tool sha256:   b5ed3261a858680b05a3a7247e2d7948e722f71be812fcdc66972594d22c097a
```

The profile additionally pins the accepted source archive and marker,
reference and output configs, builder ID/digest, compiler, build/repack tools,
boot template, Android image tools, AVB tool, partition size, and command-line
policy.

## Cache identity

```text
profile sha256:
c6b06b44561506d3adfd7c3d49ef5d3476356d8aa0061fc3dec11bbf8496a4c7

input key:
85bad5a91be2195ccde08df1ebb6c3a96749001286f2ad5fa3955067db983f38

entry ID:
05865d1cdbc7de08606d064316a7bd3e64d0ba6f9ba7218e17c73932f9e48333
```

The entry occupies about 208 MiB. The cache root and index directories are
mode `0700`, the entry directory is mode `0500`, and every manifest/payload/
binding file is owned by the invoking user, single-link, and mode `0400`.

## Exact outputs

| Product | Size | SHA-256 |
|---|---:|---|
| manifest | 2427 | `05865d1cdbc7de08606d064316a7bd3e64d0ba6f9ba7218e17c73932f9e48333` |
| stable-recovery initramfs | 7593276 | `6927d91d5c590ada1f6cae44cfa126c15470008f79949ca3256a45ee3edc4fff` |
| wrapper config | 185763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| wrapper Image | 50498048 | `cf8c2aced08010a193b60f3dbc6099f6a24cebbe7473fb13be0e18a7015fd4ad` |
| build metadata | 442 | `610391a3d218620bc83b8f5c4ae17716edcf044c92b6590f6197977a60f98dce` |
| raw boot-v3 image | 58097664 | `0489b6522a8bae12138e20630cc8d7a4005e82b687a9dd52fa4a874ded480e9f` |
| unsigned AVB test image | 100663296 | `fe0046e342b9aad0ecbfda3d4e8851a2ab261dfd70db8773d817a55f73030531` |

Every output hash matches the accepted 2026-07-29 twin-build report.

## Independent materialization proof

The pinned materializer recomputed the source seal and every input/cache hash,
then copied the exact entry to a new no-replace directory:

```text
elapsed:     3.10 seconds
maximum RSS: 230400 KiB
kernel build: none
authority:    none
```

Independent Android tooling unpacked the raw image as header version 3 with
the expected 50,498,048-byte kernel and 7,593,276-byte ramdisk. Both matched
the materialized files byte-for-byte. `avbtool verify_image` verified the
footer, `NONE` vbmeta structure, and SHA-256 `boot` descriptor against the raw
image.

## Hostile tests

Five source-seal tests and ten cache tests cover:

- deterministic output and timestamp-independent reconstruction;
- file content/mode, symlink target, added path, special file, and linked-root
  rejection;
- twin mismatch and pre/post source mutation;
- profile duplicate/noncanonical fields and dependency mutation;
- wrong expected entry, input drift, and conflicting same-input output;
- cache content, inventory, symlink, permissions, and manifest mutation;
- existing destination no-replace behavior;
- build metadata and exactly-one embedded initramfs enforcement.

The static contract also requires source sealing before the two builds and
publication only after both AVB checks and the post-build seal. It excludes
phone, privilege, storage, process, and network transports from the cache
path.

## Advisory review

A constrained Claude Opus review received the complete patch and, in a
follow-up, the full unchanged twin-build gate it requested. The wrapper used
safe mode, no tools, no session persistence, no permission prompts, and a
fixed timeout. Claude returned:

```text
BLOCKERS: NONE
```

Claude had no repository write access. The complete repository `ci` tier also
passed after the cache and source-seal tests were added to both canonical test
lists.

## Trust boundary

The cached initramfs contains the historical test public key. Its disposable
private key was destroyed by the accepted twin build, so this cache cannot
sign a new runtime candidate. No credential was created, opened, or used in
this work. The cache does not authorize a phone boot.

The broad A/B kernel object trees are reconstructible from the pinned source,
builder, config, scripts, initramfs, and retained cache output. After the
proof, Claude review, complete CI, committed clean-tree CI, and a final
byte-for-byte comparison against the cache, these exact generated paths were
removed:

```text
build/corrected-headless-candidate-20260729-a/wrapper/wrapper-a
build/corrected-headless-candidate-20260729-a/wrapper/wrapper-b
build/stable-recovery-wrapper-cache-materialized-05865d1c
build/stable-recovery-wrapper-cache-proof-20260730
```

They represented 9,665,237,171 apparent bytes. Btrfs availability increased
from 596,596,088,832 to 600,291,504,128 bytes, a physical gain of
3,695,415,296 bytes. The 208 MiB cache and 662 MiB compact corrected-headless
candidate/repack evidence remain. The deleted directories are not directly
recoverable; the broad object trees can be rebuilt and every accepted wrapper
output remains in the exact cache entry.

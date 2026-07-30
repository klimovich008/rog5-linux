# Linux 7.1.4 network-root ref-state reconstruction — 2026-07-30

## Result

**PASS — all five frozen `network-root-v1` kernel artifacts were recovered in
two independent, byte-identical, network-disabled builds.**

This was PC-only work. No phone, fastboot, ADB, SSH credential, signing key,
root password, private input, or external service was used. It grants no boot,
flash, signing, storage, or deployment authority.

## Root cause

The migrated Linux source retained a local annotated tag ref,
`refs/tags/v7.1.4`. Linux `scripts/setlocalversion` observes local refs, so
that checkout produced release `7.1.4`. The historical build had fetched the
annotated tag into `FETCH_HEAD`, checked out its peeled commit on
`rog5-build`, and retained no local tag ref; its release was
`7.1.4-g7a5cef0db479`.

The source commit, tree, and final config were otherwise identical. The
release difference changed the embedded kernel version, module installation
path, module archive, and compressed outputs. A reconstructed historical
builder reproduced the wrong identities while the local tag ref remained,
then reproduced every frozen identity after the exact no-local-tag state was
restored. This disproved the initial glibc/toolchain explanation for the
mismatch.

The rejected tag-retaining build included:

```text
release:          7.1.4
config sha256:    68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f
Image sha256:     3485358d8b25ef0a046535940b1d9985781a65abd5bf7130f4ef25e2e4a776e2
Image.gz sha256:  b5938fdb3160214053c9067fb0ecd19e0ecd8762f1e634f81ad5cfae37f80c5e
modules sha256:   ce4876b5723f9028e2fa7e2fcc91bfb7a141436bdc400645920252995d07ad66
metadata sha256:  44e755817be6c94d3321ab22549d72e4ecda80d125ec274837dfcc39a167d3de
```

## Exact source and builder

```text
remote:                    https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
annotated tag object:      114456a9c542d933387517bb22561668c25a5b59
peeled commit:             7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
tree:                      2ea2be38c5e4dc9aafffbbc0db5aae0f6513a1d9
branch:                    rog5-build
checkout:                  shallow
local refs/tags/v7.1.4:    absent
release:                   7.1.4-g7a5cef0db479
Ubuntu snapshot:           20260724T020000Z
builder package closure:   9310a47eab66545b98d69d5522313d064bfad17c80e1716f73e01119b83d4e22
builder recipe sha256:     312fe54127b282fe6ece395b024b5ab9150e9e606d8b40d3ed5144dea8941556
reconstructed image ID:    b01d1a9ea3b76323fe0202db86b6bdcbe58f29e80504a3174ea33cb2caf61f7d
reconstructed image digest: sha256:7ba7b8a707b8b8922f2c2145e60728685463b185e229f3938783819f9ce4fe11
```

The reconstructed OCI ID and digest differ from the original historical
image because image metadata is not the acceptance identity. The recipe,
snapshot, installed package closure, tool versions, and network-disabled
runtime checks are pinned and pass independently.

## Twin-build evidence

Build A used a separately reconstructed no-local-tag source state. Build B
used a new source directory created by
`scripts/host/fetch-linux-stable-v7.1.4.sh`. Both mounted source and repository
read-only, used separate empty output directories, disabled container
networking, fixed build identity/timestamp/hash/BTF inputs, and used six jobs.

The independent final verifier passed for each build. `cmp` then proved
byte-for-byte identity for all five outputs:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `.config` | 239,677 | `68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f` |
| `Image` | 40,049,152 | `349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf` |
| `Image.gz` | 14,751,785 | `a1756e36f42a57c90bd85ef33d68aa1424768a45f272cc0514c2992ace0ae6e5` |
| `modules.tar.gz` | 300,439,504 | `5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9` |
| `build-meta.txt` | 629 | `1cd315745755394ffceea7a2124800c63f8f67ca776fe4bdf47f9b296e1a4ecf` |

These values exactly match `manifests/artifacts.tsv`. Publication refuses to
overwrite a different file and independently compares the destination bytes.

## Fail-closed controls

- the source fetcher pins remote, tag object, peeled commit, tree, branch,
  shallow state, clean worktree, absent local tag ref, and exact release;
- the builder verifier pins historical snapshot, recipe, package closure,
  architecture, tool versions, and normalized image state;
- the build checks source and installed module releases before publication;
- deterministic tar ordering, ownership, modes, mtimes, and `gzip -n` bind
  the module archive;
- the compatibility verifier checks the config, Image version, sole module
  ABI/path, `modules.dep`, artifact metadata, and minimal-headless oracle;
- the contract suite hostile-rejects the incorrect `7.1.4` ABI; and
- publication requires independent A/B equality plus every frozen size/hash.

## Review and limits

Claude CLI authentication and the no-tools/no-persistence security wrapper
were healthy. One broad selected-patch review returned only a narrated action
and no verdict, so it was excluded from acceptance evidence. A second,
narrowed Sonnet review covered the source fetcher, historical builder
verification, deterministic build/verifier pair, publication/cleanup gates,
contract test, and CI wiring. It returned `NO_BLOCKERS` with tools disabled,
no session persistence, no credentials, and no write access.

The complete hardware-free repository CI tier passed after the recovery
manifest update was propagated through the compatibility-profile identity.
Local exact checks, hostile regressions, independent verification, and byte
comparison remain authoritative; the Claude result is advisory.

## Post-proof storage cleanup

After publication, independent verification, twin comparison, full CI, and
review passed, five 6.8 GiB object trees and the 2.0 GiB hand-reconstructed
source copy were removed by exact validated path. `/home` decreased from
315 GiB used to 279 GiB used, reclaiming about 36 GiB.

The canonical no-local-tag source checkout, reconstructed historical builder,
all five compact accepted artifacts, manifest identities, this report, and
the 839-byte failed-build host/builder record were retained. No broad glob,
host storage device, Podman image, phone path, or credential location was
deleted.

This result does not prove ROG Phone hardware behavior, DTB correctness,
mainline boot, charging, thermal control, suspend, input, sensors, audio,
wireless, display, or GPU. Those remain separate measured live gates behind
fresh authorization.

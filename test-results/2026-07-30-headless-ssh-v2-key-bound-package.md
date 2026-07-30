# Headless SSH v2 key-bound package

Date: 2026-07-30
Status: **PASS offline; fixture-only; unbooted; no live authority**

## Outcome

The credential-clean minimal Arch root now has a new, non-historical identity:

- root build profile: `headless-ssh-v2`;
- network-root identity/package format: v3;
- wire profile: unchanged `network-root-v1`;
- SSH key type: one canonical `ssh-ed25519` record;
- key identity: SHA-256 fingerprint recomputed from the decoded SSH blob; and
- effective OpenSSH key path: `/root/.ssh/authorized_keys` only.

Historical v1 and v2 parsers and package/profile pairings remain exact. No
phone, private SSH key, signing key, root password, network package repository,
or host-global binfmt registration was used.

## Source-root reproduction

The build used:

```text
project commit:
9739abe1eb138d301bcae988ac9cb859cc9e3f0a

Arch base:
size:   818293654
sha256: 3cf5764fb6fec7bffdff98787e52ccd15d5d6390a2496c7028d7c4950404c56a

modules:
size:   300439504
sha256: 5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9

kernel:
7.1.4-g7a5cef0db479
```

Two fresh rootless builds ran inside the hash-pinned private AArch64 binfmt
namespace. Both passed in-root and clean-extraction verification and produced
identical bytes:

```text
size:   536750378
sha256: 2abe8c533179da598c37939ff8ebb4667a243bd8140c2d497237e41fbea72e6a
entries admitted by source-archive policy: 37734
```

The host `/proc/sys/fs/binfmt_misc` table remained unchanged. The duplicate
A/B output was deleted after `cmp`, size, and hash equality; one read-only
canonical artifact remains.

## Authorized-key binding

The build fixture is public-only. Its private half was destroyed previously.
Staging strips comments and writes exactly:

```text
ssh-ed25519 <canonical-base64>
```

The verifier requires `/root` to be a real, non-writable directory,
`/root/.ssh` to be root-owned mode `0700`, and `authorized_keys` to be one
root-owned mode-`0600`, link-count-one file. The Python parser strictly
decodes Base64, verifies its canonical re-encoding, parses both SSH
length-prefixed fields, requires an internal `ssh-ed25519` algorithm and a
32-byte public key, rejects trailing blob bytes, and computes the standard
OpenSSH SHA-256 fingerprint.

That fingerprint must agree in:

1. the installed canonical key;
2. `/etc/rog5/build`;
3. v3 identity;
4. v3 package manifest; and
5. the complete sealed root tree.

The v2-only SSH policy fixes `AuthorizedKeysFile` to the bound file and is
checked through `sshd -T`.

## Sealed package

The first recursive archive diagnostic failed closed because 11 directory
allocation sizes changed after extraction. File contents, paths, ownership,
modes, links, mtimes, and xattrs were equal. The historical tree seal includes
directory `st_size`, so the v3 packager now uses a sorted NUL member list with
`--no-recursion`; historical v1/v2 packaging remains unchanged.

The fixed-contract path then reproduced and independently verified:

```text
source:
artifacts/arch/rog5-arch-headless-ssh-v2-7.1.4.tar.gz

sealed root:
artifacts/arch/rog5-arch-headless-ssh-v2-network-root-7.1.4/root.tar.gz
size:   536747283
sha256: 60fed48c8714a3f3b2082f95a04e913f32dfc74ed4c262e5b3d6e924a39a9c3b

package manifest:
size:   731
sha256: 1173f96851e8e2df01fdc02e68fcc805ab3a2e7a8141ca0a76eda9954619cd98

tree entries: 37735
tree sha256:  6f8a8f11bfb581bb52ca7d590141ce465b8d48d8f9f4577a076b7a37604a2fd5
seal sha256:  f443a47c456b33d670e6efd4a2e20cff2bc72061e7661472694acfbba45c8d5a
```

The contract is tracked at
`configs/network-roots/headless-ssh-network-root-v3.package`.

## Tests and review

Focused tests pass:

```text
PASS minimal SSH-only Arch root contract
PASS successor headless-core root adds only the sealed native key indicator
13 Python network-root tests: OK
```

The complete phone-free repository `ci` tier passes.

A bounded Claude advisory review correctly found an invalid Bash assumption
about Ed25519 Base64 length, the no-final-newline `read` edge case, and a weak
multi-file assertion. Those were fixed and regression-tested. One claimed
unknown `sshd` directive was not present in the reviewed file and was rejected
after direct inspection; advisory output is not treated as authority.

## Cleanup and remaining boundary

The rejected recursive package, duplicate source build, diagnostic package,
and three disposable expanded-root volumes were deleted. Approximately 6 GiB
was reclaimed.

The distinct fixture-only `headless-ssh-network-root-v3` recovery candidate
now passes its complete hardware-free gate. It does not grant live authority;
see the
[candidate result](2026-07-30-headless-ssh-v2-candidate-offline.md).
Before any credential-bearing or connected preflight:

1. derive the public key from the caller's private key with `ssh-keygen -y`;
2. reject the public fixture fingerprint;
3. rebuild and require exact v3/profile/package/candidate pairing; and
4. obtain fresh authorization for host promotion, credential use, and any
   temporary phone boot.

# Headless-root credential and reproducibility hardening

Date: 2026-07-30

Status: **PASS — credential-clean source archive is byte-reproducible;
successor package/profile identity remains pending**

## Outcome

The retained corrected recovery successor remains a valid, authority-free
recovery artifact, but it is not currently a runnable live candidate. Its
expected NFS root archive is absent, and the historical recipe did not
reconstruct that archive byte-for-byte.

The reconstruction attempt also found a release-blocking security defect: the
historical root archive embedded a newly generated Pacman local signing
private key, its revocation certificate, and mutable trust state. The archive
was rejected and moved to the desktop Trash. It was not packaged, promoted,
installed, or sent to the phone.

## Reproduction evidence

The official Arch Linux ARM base input was recovered from an official mirror
and matched the existing manifest:

```text
path:   artifacts/arch/ArchLinuxARM-aarch64-latest.tar.gz
size:   818293654
sha256: 3cf5764fb6fec7bffdff98787e52ccd15d5d6390a2496c7028d7c4950404c56a
mode:   0444
```

The retained module and indicator inputs also matched their tracked
identities. A clean detached worktree at historical staging commit
`6a8090e936bfbc2a8e93b430671a216593d11ca9` completed both in-root and
clean-extraction verifiers, but produced:

```text
rebuilt size:    535672329
rebuilt sha256:  63a052238443a2b430c8a43306d7bacc0b8e62c713f2c3b9bea219705d6db44f
expected size:   535163814
expected sha256: f52bd75f023ab6209a04f842881356e5a224e1e1845f1d5732ab71da7d36e66b
```

Inspection found, among other generated trust files:

```text
etc/pacman.d/gnupg/private-keys-v1.d/*.key
etc/pacman.d/gnupg/openpgp-revocs.d/*
```

The mismatch is therefore not accepted as harmless rolling-package drift.
The old process generated deployment-irrelevant secret material during the
build and could not satisfy a clean reproducibility boundary.

## Corrected staging contract

The minimal headless stage now:

- runs with networking disabled;
- requires `attr`, `diffutils`, and `openssh` to exist in the exact
  manifest-pinned base archive;
- performs no Pacman database sync, system update, key initialization, or
  package download;
- removes only the generic kernel and firmware packages;
- kills any inherited GPG process and leaves `/etc/pacman.d/gnupg` as an
  empty root-owned mode-`0755` directory;
- truncates the timestamped Pacman transaction log and removes ldconfig's
  disposable auxiliary cache;
- normalizes all output mtimes to one fixed source epoch;
- archives a byte-sorted, non-recursive member list in pax-restricted format
  with sparse-file reading disabled; and
- uses timestamp-free gzip output.

The archive admission tool now allows the required empty Pacman GnuPG
directory but rejects every child beneath it. Hostile tests cover a key file,
an exact secret-directory entry, a revocation file, and a trust database. The
staged-root verifier also rejects any remaining Pacman trust or signing entry.

## Validation completed

```text
PASS minimal SSH-only Arch root contract
PASS persistent Arch staging is identity-pinned, path-safe,
     metadata-preserving, credential-clean, interruption-safe, sealed,
     and atomic
6 headless-network-root tests: OK
PASS repository Linux ci tier
```

These are source and fixture gates. They do not prove that the corrected root
archive is reproducible yet.

## First corrected A/B attempt

Two fresh builds from commit `93052cf1843b37abafd09955285fbe210ae78d4f`
both passed the in-root and clean-extraction verifiers but correctly failed
the byte-identity gate:

```text
A size:   536762060
A sha256: 39e628a134a7f1edbe15a1ccb9be4e1bf9038d68b7ef857696e1dc8f190fa7d7
B size:   536762094
B sha256: 13ea6d8b4d00490ea8082dd1fa1775ba5cf21b613377b35c180ea4ecd4a2904f
```

A complete 37,735-entry metadata and content inventory found exactly two
differences:

```text
var/log/pacman.log
var/cache/ldconfig/aux-cache
```

The first contains Pacman transaction timestamps; the second is a disposable
ldconfig optimization cache. No path, type, ownership, mode, mtime, link,
xattr, or other file-content difference was present. Neither output is
accepted. The stage now canonicalizes those two members, and a second fresh
A/B attempt was run from the resulting clean commit.

## Successful corrected A/B result

Two new builds from commit
`ffe8dda35e8c97e7d0474a6f945b23b1d97aba05`, separate fresh stage and verify
volumes, and the same public-only fixture key produced identical archives:

```text
A size:   536755705
A sha256: d81d91fca1968eeb889155a8bf8077d0604812dd43e4055abfa64a1adb87c6a9
B size:   536755705
B sha256: d81d91fca1968eeb889155a8bf8077d0604812dd43e4055abfa64a1adb87c6a9
cmp:      identical
entries:  37734
```

Independent archive admission and member inspection confirmed:

- exact base SHA-256
  `3cf5764fb6fec7bffdff98787e52ccd15d5d6390a2496c7028d7c4950404c56a`;
- exact module SHA-256
  `5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9`;
- kernel release `7.1.4-g7a5cef0db479`;
- only the empty `/etc/pacman.d/gnupg` directory;
- an empty root-owned mode-`0644` `/var/log/pacman.log`;
- no `/var/cache/ldconfig/aux-cache`; and
- the public fixture fingerprint
  `SHA256:ylv66wbMSxVEAMiOFvMQOztcvtSB5wSbVe9FXePMLN0`.

This proves the corrected source archive is reproducible. The public fixture
has no retained private half and grants no deployment access. The archive is
not yet assigned a successor package identity and is not a live candidate.

## Remaining release gates

1. Introduce a new package/build-profile identity; do not overwrite or
   relabel the historical `headless-core-v2` identity.
2. Bind the deployment public-key fingerprint into the successor package and
   require a matching client key only at a separately authorized credential
   preflight.
3. Rebuild and re-admit the recovery candidate before requesting any phone
   boot authorization.

No phone action, privileged host action, signing credential, SSH private key,
or personal data was used in this investigation.

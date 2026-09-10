# Persistent Arch staging live result

Date: 2026-07-27

Result: **PASS for Gate P1 persistent root staging. The Arch generation is
published but deliberately unselected and unbooted.**

## Scope

This run copied the already accepted successor-v3 Arch archive to the running
vendor-Alpine fallback, verified it on the phone, and staged it below
`userdata:/rog5`. It did not repartition, format, mount a boot partition,
select a generation, write `state/good` or `state/next`, kexec, reboot, or
flash.

The Alpine root, SSH service, screen-off desktop, noVNC, ttyd, and Chromium
remained online throughout.

## Accepted inputs

| Input | Size | SHA-256 |
|---|---:|---|
| `rog5-arch-plasma-network-root-7.1.4-successor-v3.tar.gz` | 2,007,033,670 | `a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7` |
| `libarchive-tools-3.8.7-r0.apk` | 674,658 | `033049f6d53ff0d267341087adfe142d3e4abe8d3fcec6853e2ed7c95ce2d41e` |

Only the signed package's `bsdtar` executable was placed in volatile `/run`.
It linked against the fallback's existing libraries and reported libarchive
3.8.7. No APK was installed.

## Live preflight

The production layout inspector returned:

```text
PASS persistent layout mode=live slot=_b protected_slot=_b root=/dev/sda23 filesystem=ext4 userdata_bytes=243766472704 free_kib=197263032 plan=no-repartition
```

Before transfer, `/rog5` was absent and approximately 189 GiB was free. The
phone-side archive then independently matched both the pinned byte count and
SHA-256 before staging was armed.

## Publication

The detached production stager completed:

```text
PASS persistent Arch root staged generation=arch-a entries=181242 tree_sha256=b71eccbe5275f8d125a6d3251fff166b57f196c23984b845e31666ecaaea9a8c publication=atomic-unbooted
```

It extracted into `/rog5/roots/arch-a.partial`, generated and verified the
whole-tree seal, then published through one same-filesystem rename to
`/rog5/roots/arch-a`. No partial directory remained.

## Independent post-publication verification

A separate full-tree verification after publication passed:

```text
PASS persistent root tree matches its complete seal
seal_format=rog5-persistent-root-v1
generation=arch-a
source_archive_size=2007033670
source_archive_sha256=a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7
promotion_state=UNBOOTED
tree_format=rog5-persistent-tree-v1
tree_entries=181242
tree_regular_files=132422
tree_directories=10150
tree_symlinks=38670
tree_bytes=5594331332
tree_xattrs=8
tree_sha256=b71eccbe5275f8d125a6d3251fff166b57f196c23984b845e31666ecaaea9a8c
```

Both `/rog5/state/good` and `/rog5/state/next` were absent. The redundant
2,007,033,670-byte transfer copy under `/var/tmp` was removed only after this
verification; the pinned host archive remains available.

## Fallback health

After publication:

- the active root remained vendor kernel
  `5.4.134-qgki-perf-00001-g6c308144c23e` on `/dev/sda23`;
- the panel brightness and logical screen state both remained off;
- SSH, Xvnc, KWin, noVNC, ttyd, and Chromium remained running;
- local noVNC and ttyd tunnel endpoints both returned HTTP 200;
- the host tunnel service was active and enabled; and
- 183 GiB remained free on userdata.

## Decision

Gate P1 is accepted live. Gate P2 remains separate: no current evidence says
that the mainline read-only UFS kernel can safely mount and boot this root.
The next authorized phone cycle must keep `arch-a` read-only, use it only as
an OverlayFS lower, retain the independent fallback watchdog, and return to
Alpine automatically.

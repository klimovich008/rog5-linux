# Generation-8 recovery ACM stability — live

Date: 2026-08-03

Result: **REJECTED safely; consumed; never retry or flash**. The sole admitted
Generation-8 RAM-only recovery boot reached verified recovery ACM/NCM and
transferred the complete signed diagnostic bundle, but the control client
rejected before PREPARE because recovery ACM identity did not remain stable.
No COMMIT intent existed and no target ran. The exact Alpine fallback returned.

## Admission and connected preflight

The admission checkpoint was published at commit
`c6677184946758b12d2328abbc3ecd4cecc971c4`. Complete local CI passed, and
GitHub Actions run `30832269180` passed both `qemu-system` and
`recovery-core` at that exact head.

An initial connected preflight stopped before boot because the phone was in
the Alpine fallback rather than fastboot. The pinned strict-SSH fallback
helper then verified the stock kernel/init/board/ext4/thermal state, issued
one acknowledged `RESTART2("bootloader")`, and proved the same physical USB
port returned as exact ASUS `0b05:4daf`, product `lahaina`. A fresh connected
preflight then passed without a phone boot, payload transfer, target SSH
connection, or privileged server.

## Sole RAM-only result

The one-shot lifecycle used AVB image
`f102d53c3b64ac8407ebe81b06213899c5907666bd9ed79b149dc91ec69f2415`.
Private evidence records:

- fastboot accepted one 100,663,296-byte temporary boot image;
- verified recovery ACM appeared on the anchored physical USB port and
  rollback remained armed;
- the fixed one-transfer bundle service sent exactly 46,163,787 bytes:
  manifest, signature, Image, board DTB, and diagnostic initramfs;
- the NFSv4.2 server reached its pre-COMMIT ready state;
- recovery control terminated with
  `FAIL recovery ACM identity did not remain stable` before PREPARE;
- the independent receive-only diagnostic collector rejected its exact
  ACM-stability preflight with zero valid target frames and no dropped USB
  events; and
- no PREPARED record, COMMIT intent, kexec, target execution, or phone-storage
  access occurred.

The lifecycle made no retry. It cancelled the NFS window, restored the exact
Alpine NetworkManager profile, and proved strict-SSH fallback on the anchored
USB port.

## Final host cleanup classification

The automated final cleanup proof reported
`cannot inspect host NFS exports`. This is a host-verifier defect, not observed
NFS residue: after `exportfs` cleanup, `/var/lib/nfs/etab` was an empty
root-owned mode-`0600` regular file, so the unprivileged lifecycle could stat
but not open it. Independent read-only checks found:

- no NFS, recovery-host, or network-root service active;
- no TCP/UDP listener on the bounded NFS or bundle ports;
- no `/run/rog5-network-root-nfs-ready`, server-state, or export-mount marker;
- no mounted export and no active kernel NFS thread file; and
- exact Alpine USB/NCM profile `169.254.77.1/30` restored.

The subsequent host-only correction moves the final export-table read through
the fixed privileged broker for both allowed root-owned modes (`0600` and
`0644`). The argument-free operation opens only the fixed path with
`O_NOFOLLOW`, bounds and revalidates the inode, requires an exact zero-byte
table, and does not alter its permissions or contents. Service, listener,
mount, interface, firewall, kernel-thread, and lifecycle-marker checks remain
independent in the unprivileged controller. No phone action is part of that
correction.

## Disposition and next diagnostic

Generation 8 is removed from `manifests/temporary-boot-images.tsv`, recorded
as consumed in `manifests/artifacts.tsv`, and must never be retried or flashed.
Its private evidence remains outside Git.

The consumed compatibility chain pins artifact-manifest SHA-256
`c3b2430c778b1d0acfc78e123160b9a33c9a3764f5fb9f1e520e56d396c55689`,
minimal-headless profile SHA-256
`fc5f87a341b384f53408c3aa0d41fa5b322ce49cb167ea2bf9f9580e75e4d4ed`,
and core source/DTB profile SHA-256
`25dcfb040f7ad035c25e70521c4afa4bc1a18b07e951fd248a633b9faae4415f`.

The next recovery successor must add bounded, non-sensitive classification of
the recovery ACM stability failure before another admission. It should record
the observed exact product/interface/driver/location counts and transition
class without serials or raw USB text. A successor is not justified by merely
reissuing the same raw recovery or extending a timeout.

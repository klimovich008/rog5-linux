# Generation 52 fast local-root live result

Date: 2026-08-13

Result: **consumed; read-only UFS, userdata, root admission, and handoff entry
passed; key-only SSH did not appear; exact Alpine fallback passed. Never retry
Generation 52.**

The one-use `persistent-root-ufs-fast-admission-v31` candidate retained the
Generation 51 kernel, DTB, four deferred UFS modules, storage read-only lock,
`ro,noload` userdata mount, tmpfs OverlayFS, and 600-second rollback. It changed
only the legacy 181,242-entry boot-time rehash into exact checks of the prior
seal and boot-critical files.

The recovery controller transferred all 45,806,987 bytes and committed the
single target execution. Mainline boot ID
`9ae0bd72-cdcb-429c-bd43-ff3087a6dcc7` produced these host-received stages:

| Host monotonic time | Relative to UFS entry | Sequence | Stage |
|---:|---:|---:|---|
| 138775.124740 | 0.000 s | 2 | `ufs-ready ENTER` |
| 138780.155691 | 5.031 s | 4 | `storage-locked ENTER` |
| 138781.161953 | 6.037 s | 6 | `userdata-resolved ENTER` |
| 138782.168225 | 7.043 s | 8 | `userdata-mount ENTER` |
| 138784.181589 | 9.057 s | 10 | `root-verify ENTER` |
| 138786.193351 | 11.069 s | 20 | `switch-root ENTER` |

The target remained the exact `ROG5 persistent root` NCM gadget and remained
pingable, but TCP/22 never exposed an Ed25519 host key during the bounded
450-second wait. This proves that the Generation 51 hashing delay was removed
and that Generation 52 entered the handoff; it does not prove which unchecked
mount move, `switch_root`, systemd step, entropy boundary, or sshd step failed.

The target watchdog returned the phone to fallback boot ID
`6f194272-a573-4750-9f83-4978c6237514`. Strict fallback identity, host cleanup,
intent resolution as `FALLBACK_RETURNED`, and restoration of the Steam socket
all passed. The formal fallback postmortem found `pstore_state=UNAVAILABLE`,
PMIC `PS_HOLD`/`HARD_RESET`, and no watchdog token. That absence remains
inconclusive and is not evidence that no target crash occurred.

No local image existed, and no phone-storage write occurred during this live
cycle. The successor work adds checked mount handoff/rollback and moves the
minimal deployment-key-bound headless Arch tree into the bounded image path.

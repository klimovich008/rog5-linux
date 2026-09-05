# Generation 68 host-departure live result

Date: 2026-08-14

Result: **TARGET PASS RECOVERED; FORMAL LIFECYCLE FAIL.** Generation 68 is
consumed, revoked, and must never be retried or flashed.

The sole RAM-only cycle passed the corrected post-`CLAIMED` recovery departure
classification. The unchanged v45 target then passed exact four-module UFS
discovery, read-only userdata and 16 GiB local-image mounts, persisted marker
verification, tmpfs OverlayFS, systemd startup, early key-only `sshd`, and P2
storage attestation. The target boot ID was
`9eb2b170-24d8-45a2-9185-eaccfaa2c084`.

The formal runner failed because its first cold authenticated SSH invocation
exited after the fixed 10-second connection deadline. The USB-NCM address and
route remained reachable. Read-only same-boot salvage showed
`rog5-early-sshd.service` active with zero restarts and six completed preauth
connections; a later strict key-only session passed the exact runtime contract
at 474.59 seconds uptime. The recovered runtime record SHA-256 is
`0d4fa030a4814ebf9dcf07d39f8935c18bb440355fd649d9b4414c11c238efcb`.

The target then performed a normal `systemctl reboot`. Exact Alpine fallback,
host cleanup, and lifecycle intent resolution passed. The correlated fallback
record identified `PS_HOLD` / `HARD_RESET`, no watchdog signal, and no fatal
tokens; pstore remained unavailable and therefore inconclusive. Its file
SHA-256 is
`4313e13997ac9815cc504d4774728dd8add2f832478b0b171907c2c4df50b3ba`.

The demonstrated defect is host-side: TCP/22 and `sshd` availability did not
guarantee that one complete cold authenticated session would finish inside ten
seconds. The next candidate must retain the unchanged target bytes and add one
bounded, harmless authenticated-SSH rendezvous before collecting the runtime
record exactly once.

# Generation 50 read-only local-root live result

Status: **consumed; exact Alpine fallback returned; never retry or flash**.

The sole Generation 50 RAM-only cycle accepted its exact signed bundle and
executed Linux `7.1.4-gae717d919f87`. The `ROG5 persistent root` USB-NCM gadget
appeared and remained continuously present for approximately 599 seconds. The
strict target SSH host key did not appear before the bounded target watchdog
reset. Exact Alpine fallback, strict fallback identity, host-profile
restoration, durable `FALLBACK_RETURNED` intent resolution, and final cleanup
passed.

This result proves that the target entered the mainline USB/UFS path and kept
the NCM transport stable for the bounded window. It does not show whether the
earliest failure was the read-only userdata mount, the 181,242-entry seal
verification, OverlayFS preparation, `switch_root`, systemd, or sshd because
Generation 50 emitted no stage records. Empty pstore and fallback PMIC warm
reset count zero are inconclusive and are not treated as proof that no target
fault occurred.

Exact identities:

- repository checkpoint: `97e49ce6ccc27500237870896e22b3babb5b3fd1`
- target manifest SHA-256: `ae22914906d63accc893157b51c683f24a3a7e933bba84e13661e664764b9cc6`
- temporary recovery SHA-256: `26d2d9b7a230268d9bd3e82497aab3e8126aefcf951b2e1fcf0a4c7fc5d6df28`
- fallback boot ID: `842f33e2-20e7-4e96-8ff3-651c798341ee`
- retained private evidence: `rog5-generation50-live-20260813.DIHw1CZZ`

Generation 51 keeps the storage behavior unchanged and adds fixed,
outbound-only, volatile stage heartbeats while the host waits for key-only
SSH. No persistent phone write occurred in Generation 50.

# Generation 69 authenticated-SSH rendezvous live result

Date: 2026-08-14

Result: **TARGET PASS RECOVERED; FORMAL LIFECYCLE FAIL.** Generation 69 is
consumed, revoked, and must never be retried or flashed.

The sole RAM-only cycle passed recovery `PREPARED` and `CLAIMED`, exact UFS and
local-image stages, both `ro,noload` ext4 layers, tmpfs OverlayFS, P2 storage
attestation, stable NCM, and key-only `sshd`. The bounded authenticated-SSH
rendezvous received one status-zero response within 150 seconds. The host then
rejected the response because it contained extra startup output in addition to
the expected marker, so it did not invoke the runtime command. The old runner
did not retain that response; its exact bytes are therefore unavailable.

The same running boot was inspected without reusing the candidate. Exact
runtime passed at target uptime 378.07 seconds with kernel
`7.1.4-gae717d919f87`, 116 block nodes, two block-backed read-only mounts, the
16-GiB local image, tmpfs OverlayFS, zero blocked storage queries, zero UFS
errors, and strict key-only SSH. Diagnostics reported systemd startup of
3 minutes 50.457 seconds and no target-side storage failure.

Normal `systemctl reboot` returned the exact Alpine fallback. The fallback
boot ID differed from the target boot ID, PMIC lineage reported
`PS_HOLD`/`HARD_RESET`, no watchdog signal or fatal token was present, pstore
was unavailable and remains inconclusive, and host profile restoration passed.

Private evidence remains outside Git under the retained Generation 69 evidence
directory. Public evidence identities are:

- runtime record SHA-256:
  `3c28a40a01af948e0d988c407382ed8533c4579778930bc9f3005a4121070586`;
- diagnostics SHA-256:
  `37dbcac1cd273398c1e5ef2edb0cda6331bd19dcd3fe295387849ac33e649632`;
- fallback postmortem file SHA-256:
  `228c3333ead9b9de1e9b56af8b60544129d3d5fe25153e7a364fece31941bdbe`;
- fallback postmortem record SHA-256:
  `b2e465c35510721dda52d7742c89a17c940fe6063a52c1bcaf7fbce49ff23113`;
- boot-claim SHA-256:
  `a2f365a2ef7434a1635daaf155c249a5b23592651b86ba3effd743478026d297`.

The concrete defect is host-side marker parsing, not target readiness: a valid
authenticated command can emit bounded startup text before its exact marker.
Generation 70 accepts that case only when the bounded stream contains exactly
one marker line, while retaining one runtime command and one-use semantics.

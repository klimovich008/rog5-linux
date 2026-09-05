# Generation 70 bounded startup-output live result

Date: 2026-08-14

Result: **PASS.** Generation 70 is consumed, revoked, and must never be retried
or flashed.

The sole RAM-only cycle passed exact fastboot identity, recovery `PREPARED` and
`CLAIMED`, the unchanged signed v45 target bundle, and the Linux
`7.1.4-gae717d919f87` target. Target stages passed four-module UFS discovery,
the 116-node storage lock, dynamic userdata resolution, both `ro,noload` ext4
mounts, the 16-GiB local image, bounded root verification, final storage
attestation, and `switch-root`.

NCM remained stable. The volatile Ed25519 host key was uniquely pinned. SSH
attempts 1–5 returned `exit-255`, attempt 6 reached its 20-second bound, and
attempt 7 returned status zero with 175 bytes. Those bytes contained exactly
one authenticated marker line, so the corrected host accepted the session.
The one exact runtime command then passed at target uptime 243.46 seconds:

- 116 physical block nodes and exactly two block-backed mounts;
- userdata and local image both `ro,noload`;
- local-image write probe `PASS`;
- root `local-ext4-overlay-tmpfs`;
- zero blocked device queries and SCSI commands;
- zero journal-recovery and UFS-error events; and
- strict key-only SSH on dynamically resolved `/dev/sda23`.

The authenticated rendezvous took 121.995 seconds and formal end-to-end
accepted SSH took 326.300 seconds. That is 53.700 seconds, or 14.1%, faster
than the Generation 20 380-second reference. Target systemd reported 46.602
seconds in the kernel plus 3 minutes 11.411 seconds in userspace.

Normal `systemctl reboot` returned the exact Alpine fallback. Target and
fallback boot IDs differ. PMIC evidence reports `PS_HOLD`/`HARD_RESET`, no
watchdog signal, and zero fatal tokens. Pstore was unavailable and remains
inconclusive. Exact fallback identity, profile restoration, postmortem capture,
intent resolution to `TARGET_ACCEPTED`, final host cleanup, and Steam's restored
port-8081 socket all passed.

Private evidence remains outside Git. Public evidence identities are:

- claim SHA-256:
  `ce9967cd2d0df83b7f77639cdde6eaefebb358ce750d2a484bf99895b8a7c6bf`;
- recovery-control SHA-256:
  `8b024334f7e641cff00fd824e039351af817f3cf9f5b515bdeccb7a0427a36ac`;
- stage evidence SHA-256:
  `6738a3db98d6eecdea5cb1ea661cec4b545d3757333f19ad60b6b716b620224c`;
- SSH-readiness SHA-256:
  `6975efe05ea2cf391b9d9be7cc464b9ea9ffa43e9ca1ae5eeeb8eb35620f6458`;
- runtime SHA-256:
  `c15616d54f5119b8ed7740c1406d23ebe663f2f7e8d74aca96041878ed0a3a2e`;
- diagnostics SHA-256:
  `4c8554fe95671aec6366b4d2baf367c04def5953ce9dbb587610fc81d4f19011`;
- timing SHA-256:
  `31c2a3e2e587a0bd9ad287b097629ace04dcd513ab963baa4b2b19f90cfd308e`;
- fallback postmortem file SHA-256:
  `82c2f691aea3b341967c251090e8fa125ea957213f9ca5fcd0ce01d4bb63fab6`;
- fallback postmortem record SHA-256:
  `48211839d9c787c389f7d64b173e22ada303104e62fa612db3c6879d094ae0fd`;
- intent-resolution SHA-256:
  `e0535372df2cd29dc6313c6aef336d612fb01a1caf66ef5276bd416ed78bb536`.

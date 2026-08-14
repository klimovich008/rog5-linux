# Generation 67 early-SSH live result

Date: 2026-08-14

Result: **TARGET PASS, LIFECYCLE CONTROL FAILURE. The sole RAM-only
Generation 67 cycle reached exact read-only UFS, local-image Arch, early strict
key-only SSH, and full storage attestation. Recovery delivered the canonical
`CLAIMED` response, then ACM closed before the follow-up STATUS response.
Generation 67
is consumed, revoked, and must never be retried or flashed.**

The cycle ran from exact reviewed repository head
`35c26e749d1fc1899c7b6b776df7f1dd0fd51e42`. Local repository CI passed in
483.051 seconds. Exact-head, merge-compatibility, QEMU, and candidate-
publication CI passed in [GitHub run 31806954178](https://github.com/klimovich008/rog5-linux/actions/runs/31806954178)
before the boot.

The one-use claim was consumed at 18:05:09 local time. Recovery transferred
the exact 45,810,825-byte bundle and returned the canonical `CLAIMED` response.
Its ACM endpoint then closed before the controller received the follow-up STATUS response. A
single sysfs teardown-race sample returned `inspect-error`, so the host's
overly strict departure classifier refused target acceptance. The same already-running
target—not a retry—was recovered by activating the exact existing host NCM
profile, pinning the target's volatile Ed25519 host key through the recovery
anchor, and connecting with the dedicated key.

The target boot ID was `8cba055b-f301-4f43-8d08-9a3a2947b8e3`. Read-only
runtime evidence reported:

- Linux `7.1.4-gae717d919f87`;
- all 116 physical block nodes and exactly two block-backed mounts;
- userdata and the 16 GiB local image mounted `ro,noload`;
- the persisted Generation 64 marker and local-image write probe passed;
- tmpfs-backed OverlayFS root;
- zero blocked block queries, blocked SCSI commands, journal-recovery events,
  and UFS errors; and
- strict key-only SSH with no backlight device.

The first salvaged runtime collection had a host-side shell-quoting error and
is retained as failed evidence. The corrected collection passed at target
uptime 279.24 seconds. Systemd's target-side timestamps provide the useful
critical-path result independent of the delayed host salvage:

- kernel: 47.656 seconds;
- early strict SSH active: approximately 94.147 seconds target uptime;
- storage attestation started: 94.17 seconds;
- local-image write probe passed: 100.36 seconds;
- both mount checks passed: 117.53 seconds;
- physical read-only proof passed: 117.76 seconds;
- UFS health passed: 119.33 seconds;
- SSH policy passed: 126.89 seconds; and
- complete attestation PASS: 130.056802 seconds target uptime.

The attested target path is therefore approximately 249.491 seconds faster
than Generation 20's 379.548-second NFS-root acceptance marker. That comparison
uses target uptime; it is not interchangeable with Generation 66's
328.363-second host lifecycle duration. Full systemd startup fell from
Generation 66's 228.983 seconds to 214.284 seconds. The unchanged P2 attestation
still used 35.916 seconds, including 12.177 seconds for the one Ed25519 key.

No flash, slot, GPT, partition, erase, format, raw-storage operation, or new
phone-storage write occurred. Both ext4 layers stayed `ro,noload`; the root
overlay stayed in tmpfs. Maximum sampled target temperature was 45.1 C.

A normal `systemctl reboot` returned exact Alpine with boot ID
`6c7049c3-a81e-471a-b419-beacde456b8a`. The postmortem recorded exact
`PS_HOLD` / `HARD_RESET`, no watchdog signal, and zero fatal tokens. Pstore was
unavailable and remains inconclusive. The exact fallback profile and unrelated
Steam debug socket were restored. The formal runner reported failure because
the post-claim response was absent and the manual NCM activation necessarily
violated its expected pre-fallback cleanup state; neither changes the exact
target or fallback evidence.

Private evidence remains outside Git at
`/home/deck/.local/state/rog5-generation67-early-ssh-live-20260814.D4iQWuwX`.
Selected identities are:

- recovery control log:
  `3f07ba5d00e11a131995c091189a80403f7f79c376341d7338811bfdc1e980f5`;
- boot-claim log:
  `8ca955031cf8aaed7d7bc23924e86eb9cb326027ea1c1c6becc69b3320c70ccf`;
- corrected runtime salvage:
  `67bc79ad5b6cb424e6644793fe93fda7d64763fc68dd765e05528db3aee8754c`;
- diagnostics:
  `9c31ca6297abf5a4c8ad7d35c7c358ff868fde0b119848f602be6567f4170338`;
- thermal record:
  `703af76c0a4d34f0d4834ca4d31b71997ed23f9bca253b6503f8ed5894574c8c`;
- fallback identity:
  `aeb806550fa494541ee245a7717332059c001559c82813141ebe2d2abb199732`;
- intent resolution:
  `f600bbed758798c1af8da83aa6d39590ec5cff2f3883a986939e2e0a5c396e1a`;
  and
- signed fallback postmortem:
  `0850489f449fc6e1feb61e5f55f6bb8ee2aac15252d3a474e9970c984a10554c`.

The next candidate must not alter the proven target storage or early-SSH path.
The bounded host correction may resample only transient `inspect-error` for at
most two seconds after a lost post-claim STATUS; it must never resend
`COMMIT_EXEC` or accept an exactly present recovery responder.
The host should tolerate only a bounded transient inspection race while proving
that recovery ACM departed after `CLAIMED`; it must still reject a present
recovery responder. The successor then needs its own identity, claim, and sole
RAM-only cycle.

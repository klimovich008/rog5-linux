# Generation-11 NCM progress host integration — offline

Date: 2026-08-04

## Result

PASS, hardware-free. The receive-only recovery NCM progress channel now spans
the device responder, exact production network namespace, privileged host
broker/controller, root-to-operator collector runtime, private lifecycle
evidence, and post-COMMIT correlation. The channel remains advisory and every
capture or assessment states `authority=NONE`.

No Generation-11 image was built, admitted, or booted. No phone command,
connected preflight, signing operation, flash, storage write, or credential use
occurred.

## Implemented boundary

- The device opens at most one nonblocking 25 ms connection from `usb0` and
  `169.254.77.2` to `169.254.77.1:8081`; failure cannot change PREPARE.
- The fixed host controller owns the exact interface, `/30`, source-restricted
  firewall rule, and unique IPv4 listener. Absence is advisory; a conflicting
  or mis-owned IPv4/IPv6 listener fails closed.
- The root helper opens the listener and private output-directory descriptor,
  clears capabilities/groups/root identities, proves root cannot be regained,
  and creates one mode-`0600` no-follow/no-replace capture after the drop.
- Parent death is armed before interpreter execution and re-armed after the
  UID/GID transition, closing Linux's credential-change `PDEATHSIG` reset.
- A correlated PREPARED record requests stream stop, but buffered bytes and
  clean EOF are drained first. The stop file remains until terminal lifecycle
  cleanup.
- Missing listener/capture, malformed or mismatched evidence, collector exit,
  and post-transfer EOF-marker failure cannot authorize or block a completed
  bundle transfer. The lifecycle evaluates evidence only after durable COMMIT.

## Exact source hashes

- `packaging/host/rog5-recovery-progress-collector.py`:
  `8b15aaac28d54ac0acf93411dc2dbb77d9a9b7b5dfc8e2cc591609f7a23ed20a`
- `tools/recovery_control/__init__.py`:
  `22364e5f8e8e18744fc9e1aabb069acf2e7020251f40c64202f4d30227b38175`
- `tools/recovery_control/reference.py`:
  `82497ccf98ddf67fbaeccf6173c8ce5531029977d28c7015e191d940de84a4da`
- `tools/recovery_control/host_progress_collector.py`:
  `5c5ee9480fa49448e204f30f97679dc8108c60687627a0f94ca3c812322ee5a8`

The controller pins these values; the installer and launch preflight verify
the installed root-owned metadata and exact bytes.

## Verification

- recovery progress runtime: 8/8 PASS;
- recovery progress collector: 21/21 PASS;
- privileged recovery host controller: 34/34 PASS;
- recovery host broker/socket: 18/18 PASS;
- recovery timeout lattice: 1/1 PASS;
- native recovery control: 63/63 PASS;
- minimal-headless lifecycle: 69/69 PASS; and
- `scripts/host/test-repository-linux.sh ci`: PASS; and
- `scripts/host/test-repository-linux.sh quick`: PASS.

The provisioned `quick` run used an auto-cleaned transient user service with a
delegated cgroup and an ephemeral Vulkan sysroot. Exact SteamOS
`vulkan-headers 1:1.4.321.0-1` and
`vulkan-icd-loader 1.4.321.0-1` package signatures verified against RSA key
`889B5EBDDD505A683621900DAF1D2199EF0A3CCF`; no package was installed into the
host root filesystem. The first transient run exposed a locale-dependent AVB
test ordering assumption, not an artifact difference. The inventory sort is
now fixed to the C locale, mismatch diagnostics print both inventories, and
the exact issuer test plus the complete `quick` tier pass under
`en_US.UTF-8`.

The native suite's dedicated rootless user/network-namespace test exercises
the real production `usb0` source bind/connect path, a wrong host interface,
and an unresolved peer. Other testing builds require explicit opt-in before
they can touch that path.

GitHub exact-head run `30886635962` passed the QEMU job but exposed one runner
policy difference in that namespace gate: Ubuntu's hosted runner rejected the
unprivileged `/proc/self/uid_map` write before the test entered its isolated
network namespace. The gate now recognizes only that exact setup refusal and
reruns only the single namespace test through noninteractive passwordless
`sudo`; ordinary local execution remains rootless, all product binaries remain
unchanged, and every other failure still propagates. The focused test and the
complete local `ci` tier pass after this correction. A replacement exact-head
GitHub run is still required before installed-host preflight.

## Independent review

A constrained, stdin-only Claude Opus review first identified five concrete
issues: post-transfer marker failure could gate success, the collector lacked
parent-death containment, the stop record was removed too early, stop could
discard buffered terminal evidence, and ordinary testing builds could enter
the production network path. All five were corrected and regression-tested.

A later oversized verification review timed out and one split response
simulated a tool transcript; neither was accepted as evidence. A final narrow
review completed, but its proposed changes contradicted the explicit
fail-closed listener-integrity contract or misread the collector/watchdog
deadlines and 100 ms stop polling. No additional valid defect was adopted.

A final two-axis Codex review then found six release-blocking gaps: a stalled
collector could consume the controller watchdog, an exited collector could
hide a replacement listener, malformed streams lost their observed byte hash,
legacy launcher actions unnecessarily required progress files, impossible
zero-byte complete captures were accepted, and healthy slow collector startup
had only one observation. All six were corrected with hostile regressions.

The post-fix constrained Claude review was attempted twice. The first response
again simulated unavailable tools and was rejected. The second reviewed only
the supplied diff and found two more valid edge cases: records with zero
correlation identities and a stop-drain path that did not reapply the absolute
deadline. Both are fixed and tested. Its request to duplicate capture bytes and
hash into the summary assessment was rejected because the private capture is
the canonical evidence and malformed summaries must not echo untrusted fields;
its fixed-interface-name suggestion was rejected because the root controller
already pins the dynamically named interface to the exact recovery NCM device
before the helper applies `SO_BINDTODEVICE`.

## Decision

The host integration is ready for publication and installed-host preflight,
not for a phone boot. Before any Generation-11 issuance, require green
exact-head GitHub CI, install and verify the exact privileged files, rerun the
final AArch64 gate, twin-build an offline-only wrapper, and review the complete
artifact/profile/rollback chain. Generation 10 remains consumed and cannot be
reused.

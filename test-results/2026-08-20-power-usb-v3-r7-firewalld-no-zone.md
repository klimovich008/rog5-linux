# Power/USB v3 incident: firewalld `no zone`

ID/date: power-usb-v3 / 2026-08-20
Primary question of the cycle: Can the existing mainline kernel sustain side-port NCM/SSH while exposing verifiable charging telemetry, then return to exact stock slot A?
Earliest failed stage: recovery NCM host classification, before bundle transfer.
Observed evidence: exact recovery USB `1d6b:0104` and `ID_MODEL=ROG5_recovery` appeared on `enp4s0f3u1u2`; `firewall-cmd --get-zone-of-interface=enp4s0f3u1u2` returned the canonical line `no zone`; the lifecycle rejected the embedded space as an invalid zone.
Root cause (proven / probable): proven host parser defect.
Failure class: R7.
Was the candidate consumed?: wrapper claim consumed; no PREPARE, COMMIT, transfer, or target execution occurred.
Was phone storage modified?: no.
Why existing host tests missed it: the firewall fixture returned an empty line or a named zone, never firewalld's real `no zone` text.
New regression fixture/test: `test_firewalld_no_zone_is_canonical_absence`.
Systemic prevention change: preserve real host outputs and replay them before candidate build; generate active candidate identity and policy from one manifest.
Successor prerequisites: every item in `docs/development-lessons.md`'s mandatory pre-build checklist must pass; no kernel redesign.

## Pre-build checklist status

- [x] Objective and acceptance test are one sentence above.
- [x] Cheapest disproof passes: canonical `no zone` regression.
- [ ] Source tree is frozen and immutable to the build.
- [x] Candidate exists once in the canonical power/USB source; active consumers use generated locks.
- [x] Generated policy/allowlists/lockfile regenerate without a diff.
- [x] Recovery, target and stock-slot-A fallback capability verifiers are bound by the canonical source; the exact built archive remains a post-build gate.
- [x] Central timeout-lattice assertions pass.
- [x] Real-output replay and complete lifecycle simulation pass.
- [x] Host doctor and planned deployment receipt prove build headroom and clean mutable state without phone contact.
- [x] Existing mainline kernel reuse was selected; no kernel rebuild is required.

Candidate issuance remains blocked until all unchecked items pass.

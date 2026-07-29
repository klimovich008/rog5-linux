# Host storage tier-1 preflight

Date: 2026-07-29

## Outcome

The guarded, non-destructive Podman preflight passed. No volume or other host
state was removed.

- Repository commit:
  `c6f88105f8e9490c5ff909c3bf1b2b901dd359a8`
- Candidate count: 88
- Candidate-set SHA-256:
  `e3418635d4db9e40b0306095c3aa846f0a5510b1468d2532a59ab115f3662a40`
- Candidate allocated size: 375,432,364,032 bytes (about 349.65 GiB)
- Private plan SHA-256:
  `d5a688818943d03f75e6f3eea0b7b38b264a4629a771fc3778374479ebec42ab`
- Preflight status: `ready`

The private plan is intentionally not committed. It expires after 15 minutes
and is evidence only, not deletion authority.

## Safety closure

The exact live rootless Podman store matched the plan. The preflight confirmed:

- zero Podman containers;
- the complete current volume-name set;
- every candidate has the reserved `rog5-*` prefix;
- zero candidate mount counts;
- local driver and scope with empty options;
- unchanged creation identity and exact local mountpoint containment;
- unchanged allocated and apparent byte counts;
- a clean repository at the exact plan commit; and
- no inherited remote Podman connection selector.

The delete path is separately guarded by the exact plan hash, candidate count,
candidate-set hash, a short plan lifetime, and an environment value equal to
the plan hash. It uses `podman volume rm` without `--force` and never removes a
filesystem path directly.

## Verification

The complete repository Linux CI tier passed locally, including all ten
destructive-executor fixture tests. An initial constrained Claude Opus review
identified identity, local-store, TOCTOU, and partial-failure hardening gaps;
those were corrected. A second constrained, tool-free review returned
`NO_BLOCKERS`.

Before any approved deletion, regenerate the private plan, repeat the
preflight, and require the candidate-set SHA-256 above to remain unchanged.

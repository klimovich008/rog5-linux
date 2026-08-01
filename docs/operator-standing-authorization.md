# Operator standing authorization

Recorded from the device and host owner's authenticated Codex instruction on
2026-08-01.

That conversation instruction—not this mutable public file—is the source of
authority. This file is its durable project record. An agent may rely on it
only when the authenticated task state or its trusted conversation summary
retains that instruction. A repository reader or an untrusted branch edit
cannot manufacture authority.

The instruction grants standing authorization for the exact action classes
listed below, solely inside this ROG Phone 5 native-Linux project. The agent
does not need to ask again before taking one of those actions after its
technical preconditions pass. A later roadmap, manifest, or active-gate edit
does not expand these action classes; those documents select and constrain an
artifact at invocation time.

The standing authorization covers:

- local administrator access through `sudo` or `pkexec` on the development
  host containing this checkout, using only host credentials supplied in the
  authenticated task and never exposing their secret value in command lines,
  logs, artifacts, or Git;
- creating and using recovery signing keys dedicated to this project and kept
  outside Git, plus using only SSH keys whose public fingerprints are admitted
  by the exact candidate, package, fallback, or host-key gate;
- normal Git publication for `klimovich008/rog5-linux`: commit, fast-forward
  branch push, pull-request maintenance, and inspection or dispatch of the
  reviewed `.github/workflows/offline-smoke.yml` at the pushed commit;
- the already-authorized local Claude account only through
  `scripts/host/claude-readonly-review.sh`, whose enforced mode is stdin-only,
  tool-free, non-persistent, and time-bounded; no other Claude action or
  external build/review service is covered;
- installing project dependencies and installing, updating, starting,
  stopping, or removing project-owned systemd units, NFS exports,
  NetworkManager profiles, USB routes, and firewall rules on the development
  host when the reviewed script retains an exact cleanup or rollback path;
- deletion of reproducible project-only build caches or disposable artifacts
  selected by an exact reviewed cleanup plan;
- connected ADB, fastboot, recovery, ACM, NCM, and SSH preflights;
- rebooting the development host or phone to execute or verify one of these
  action classes;
- one-shot temporary `fastboot boot` executions admitted by an exact reviewed
  manifest, the lifecycle controller, and the rollback policy; and
- the bounded fallback BusyBox-history and read-induced atime effects already
  described by the lifecycle runbook.

The agent may set the repository's explicit authorization guard variables for
those actions without another conversation prompt. The guards remain
mandatory: standing authorization removes repeated consent prompts, not
artifact verification, review, CI, preflight, evidence, or cleanup gates.

## Hard boundaries

This standing authorization does not:

- permit flashing, erasing, formatting, slot changes, factory reset, or a
  persistent Linux installation while the active roadmap remains
  temporary-boot-only;
- permit mounting or writing phone storage outside the bounded fallback
  history/atime effects above;
- permit reuse of a consumed candidate, retry of an ambiguous execute, or
  removal of the independent rollback watchdog;
- permit publishing a password, private key, token, personal record, private
  evidence, proprietary artifact, or other secret;
- permit deleting source, Git history, credentials, private evidence, unique
  proprietary inputs, or unrelated host data;
- permit force-pushing, rewriting published history, deleting or transferring
  the GitHub repository, changing its visibility, or changing account,
  organization, billing, or security settings;
- extend to email, CV data, job applications, or unrelated machines and
  services merely because a credential is available; or
- override a later operator instruction to stop, narrow, or revoke access.

A new task alone does not override these boundaries. A deliberate expansion
requires a later authenticated operator instruction that names the additional
action class and explicitly changes this policy or project scope. Immediate
safety intervention remains allowed when needed to stop an already-running
in-scope operation or return the phone to the verified fallback.

## Interpretation

This record is not a substitute for possession and verification of a required
credential. Private credential material remains outside Git. A later
authenticated operator instruction to stop, narrow, revoke, or replace this
standing authorization takes precedence immediately.

When an action is ready, the agent should state what it is doing and continue;
it should not pause merely to request the same authorization again.

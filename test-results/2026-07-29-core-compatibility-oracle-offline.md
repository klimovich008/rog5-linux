# Core compatibility oracle — offline result

Date: 2026-07-29

Result: **PASS hardware-free; authority=none; no phone action**

## Outcome

The repository now has one fail-closed machine-readable compatibility
contract joining:

- the proven ASUS 5.4.210 core and USB behavior;
- the accepted Linux 7.1.4 network-root v3 CPU/RAM, storage-isolation, NCM,
  systemd, key-only SSH, thermal, and reboot evidence;
- the accepted Linux 7.1 Image/config identities;
- the corrected isolated DTB and headless initramfs ancestry; and
- the complete active/future headless hardware roadmap.

This checkpoint does not claim that the corrected candidate booted. Its state
is still `live-pending`, its candidate remains `offline`, and its authority is
`none`.

## Positive checks

The verifier passed:

```text
profile=minimal-headless-v1
active_capabilities=6
future_capabilities=6
kernel_config=verified
new_root_state=live-pending
authority=none
status=ready
```

That result was reproduced with:

- the committed minimal active-config fixture; and
- the retained accepted
  `artifacts/network-root-v3/config-7.1.4-network-root`.

Explicit metadata-only mode also passed and reported
`kernel_config=metadata-only` plus `status=metadata-only`.

The complete `scripts/host/test-repository-linux.sh ci` tier passed after
integration. It includes the builder bootstrap, corrected candidate, exact
DTB semantic delta, board-neutral QEMU, recovery protocol, native responder,
bundle verification, fetch/server/controller, rootfs, init policy, rollback,
and repository checks.

## Mutation coverage

Thirty-three focused tests passed. They reject:

- missing required Kconfig, enabled forbidden Kconfig, and an integer below
  the minimum;
- cross-capability config contradictions and negative values encoded as
  positive requirements;
- evidence hash drift, absent markers, and duplicate markers;
- artifact-manifest hash or row drift;
- unequal, duplicate, malformed, or unknown artifact identities;
- weakened candidate identity and changed candidate artifact ancestry;
- narrowed capability coverage, rewired integration, and an active gate not
  present as an exact CI entry;
- malformed capability list members without leaking `TypeError`;
- duplicate JSON through both the helper and real loader;
- duplicate Kconfig symbols and non-LF separator smuggling;
- symlinked input;
- implicit CLI mode; and
- a verifier failure incorrectly translated into a zero process exit.

A committed golden config supplies the primary hardware-free positive case.
The synthetic config remains a separate profile-consistency fixture.

## Claude advisory review

The constrained Opus verifier review returned `BLOCKERS: NONE`. Its useful
hardening suggestions were implemented:

- the artifact manifest is directly hash-pinned;
- metadata-only verification is explicit and distinguishable;
- manifest and Kconfig parsing require canonical LF records;
- cross-capability config conflicts fail at profile validation;
- CI gates and the build-verifier invocation use exact lines;
- input reads use one bounded `O_NOFOLLOW` descriptor; and
- manifest integer text and general profile strings are canonical.

The first profile-review response claimed it would inspect external files
despite having no tools, then stopped without a verdict. It was discarded.
A smaller self-contained retry returned `BLOCKERS: NONE` and confirmed that
the table does not promote a new boot. Its terminology findings were applied:
future button and battery states now say `baseline-diagnostic-*`, and the
schema documentation makes roadmap phase distinct from candidate acceptance.

The test review found four blockers: one vacuous exception assertion, no
end-to-end CLI failure, duplicate JSON tested only at helper level, and
unguarded symlink creation. All four were corrected. Secondary exactness
coverage was also added before this result was accepted.

## Boundary

The oracle proves profile integrity, historical evidence provenance, artifact
identity ancestry, active Kconfig compatibility, and CI/build integration.
It does not prove that every ignored historical binary is present in a fresh
clone, that a new Image behaves like the accepted Image, or that a changed
Image/DTB/initramfs/root combination works on hardware.

No signing key, credential, host network mutation, fastboot command, reboot,
flash, phone-storage access, or phone action occurred.

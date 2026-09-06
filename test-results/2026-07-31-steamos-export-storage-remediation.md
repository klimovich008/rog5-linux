# SteamOS deployment-export storage remediation

Date: 2026-07-31

## Scope

This is host-only evidence for the first non-fixture v3 deployment-export
attempt and its remediation. It grants no phone authority. The phone was not
contacted, no temporary boot was consumed, and no phone storage was written
or mounted.

## Accepted inputs

- runtime bundle:
  `headless-ssh-network-root-v3`;
- runtime manifest SHA-256:
  `457273993a9ce3cb0a9c735ef29e96101c1303720cafefc774aed12972a6926e`;
- package SHA-256:
  `9eb60d6e4254986dc8e017fc1dd9d76d699e8d35cb3716d8fdef72ca6df1199d`;
- sealed archive size: 536,746,495 bytes;
- uncompressed tar size: 1,643,038,720 bytes.

The fixed controller was installed from pushed commit `bdf8719`. Its installed
files matched the reviewed repository bytes and metadata. The signed runtime
bundle was atomically prepared below
`/var/lib/rog5-recovery-bundles`, matched the twin-built reference byte for
byte, and passed the native verifier. Private key, package, candidate, and
runtime-manifest admission also passed before privilege.

## Observed refusal

SteamOS mounts `/var` as a separate 230 MiB filesystem. It had 128 MiB free,
while `/home` had 627 GiB free. The root-owned export installer therefore
stopped with `ENOSPC` while copying the admitted archive into its anonymous
`O_TMPFILE`. It had not created the deterministic extraction stage or final
destination, so no export was published and there was nothing to remove.

The refusal handler then exposed a host-version compatibility defect:
Python 3.13 no longer provides `pwd.error`, so evaluating the exception tuple
raised `AttributeError` after the safe storage refusal.

## Remediation

- move only the deployment export to the fixed
  `/home/rog5-linux/exports/headless-ssh-network-root-v3` store;
- keep the small signed recovery bundle in
  `/var/lib/rog5-recovery-bundles`;
- create `/home/rog5-linux` and its `exports` child as root-owned mode-`0700`
  directories during fixed-host installation;
- require canonical root-owned, non-writable, non-symlinked export ancestry;
- re-attest that ancestry immediately before the NFS bind mount and verify the
  already bound read-only tree before starting NFS;
- retain anonymous snapshotting, archive inspection, complete-tree
  verification, fsync, and `renameat2(RENAME_NOREPLACE)` publication; and
- catch the documented `KeyError` from `pwd.getpwuid` without referencing the
  removed `pwd.error` alias.

## Focused regression result

The following pass with this remediation:

- 13 deployment-export installer tests;
- 12 recovery host-controller tests;
- 14 headless network-root tests;
- 8 export-launcher tests;
- 17 one-shot lifecycle tests;
- 13 stable-recovery control tests; and
- the shell host/NFS contract test.

The new tests cover the fixed destination, unsafe writable ancestry,
symlinked ancestry, and the Python 3.13 caller-lookup refusal.

## Remaining gate

The final diff passes full local CI. Independent Standards and Spec reviews
both report `NO_BLOCKERS`; a separate Claude Opus closure review also reports
no blocker. A clean pushed checkpoint and GitHub Actions still precede fixed
host-component reinstallation or export-publication retry. Fallback SSH proof
and connected fastboot preflight still precede the one separately authorized
temporary boot.

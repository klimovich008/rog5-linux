# Observation-only recovery wrapper — offline

Date: 2026-08-09
Starting repository SHA: `6abd71a00180668d11821e3b1e79aa3b19f35915`
Recommendation: **HOLD**

## Outcome

The observation-only recovery identity now has a deterministic outer ASUS
5.4 wrapper. Two fresh, network-disabled builds reproduce the config, kernel
`Image`, embedded observer initramfs, raw boot-v3 image, unsigned AVB image,
and sealed source state byte-for-byte. The inspected image contains the exact
4 MiB ramoops reservation and built-in pstore support.

This closes only the offline composition gap. It does not prove ramoops bytes
survive target → bootloader → recovery, does not establish that the modeled
host-readiness race caused Generation 12, and does not create a candidate or
boot authority. No phone, credential, signing key, policy row, manifest
candidate, flash, wipe, slot operation, phone storage, or boot action was
used.

## Concrete defects and patches

The observer archive previously stopped before its outer wrapper, while the
preceding report incorrectly suggested the old full-recovery kernel could be
reused. The ASUS 5.4 config embeds the initramfs in `Image`, so reuse would
retain the wrong payload identity. The fix performs two fresh builds and
requires the observer input, both embedded copies, and the unpacked ramdisk to
be identical.

- `scripts/host/build-observation-recovery-wrapper-offline.sh` verifies both
  observation archives, invokes the existing qualified clean-twin wrapper
  gate with eight safe jobs, and publishes evidence only after the dedicated
  verifier passes.
- `scripts/host/verify-observation-recovery-wrapper.py` parses the gzip/newc
  archive without extraction, requires exact observer mode and metadata,
  forbids kexec and bundle paths, verifies every twin/product relationship,
  pins the accepted config/source/builder contracts, checks the exact ramoops
  command line, and requires unsigned AVB `Algorithm: NONE` with rollback
  index zero.
- `scripts/host/test-observation-recovery-wrapper.py` provides eight test
  methods: one positive composition, ten hostile mutation/refusal subcases,
  and one static orchestration/registration contract. They cover full mode,
  injected kexec, twin and embedded-initramfs divergence,
  command-line/config drift, signed AVB, AVB/raw divergence despite unchanged
  sidecars, source mutation, and symlinked products.
- `scripts/host/test-repository-linux.sh` runs that suite in the shared test
  list. The unrelated VCNL36866 working-tree additions remain preserved and
  isolated.

The fail-first suite stopped in 0.08 seconds because no verifier existed. The
first fixed focused run passed seven tests in 1.55 seconds; the retained-output
rerun passed in 1.63 seconds. Independent review then found that detached
inspection sidecars could certify synthetic non-boot data. After replacing
that fixture and re-verifying the artifacts directly, eight focused tests
passed in 8.33 seconds and the retained real wrapper passed direct reinspection
in 2.41 seconds.

## Reproduced identity

The qualified builder used sealed ASUS source identity
`3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8`,
accepted config profile `accepted-wrapper-v18-v1`, and Clang 18.1.3. The
complete source seal before and after both builds is
`4c4958385b9d0f270c368642c484c84e4c60ea23d18f68c00e37ca67a8637344`.

| Product | Size | SHA-256 |
|---|---:|---|
| observer initramfs A/B | 5,371,780 | `613d6e3e61d7818693c0d26b0b7c252479941cc25c98e897ef6aa30469e770db` |
| accepted config A/B | 185,763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| observer kernel Image A/B | 48,400,896 | `efcc4db8a5ad6abbd27a7489bb7f9ae202ab93662e5b7953e77621671e27a6ab` |
| raw boot-v3 A/B | 53,780,480 | `fdcf9b85951fe696afb56f1b3d3c9e6581ce040fdcce1e51f8ed37d23d4fa163` |
| unsigned AVB A/B | 100,663,296 | `63fc0a1a6827941d51edb7033fa501ae74dd8c192fad65d84f7816e3caf743b1` |

The config has `CONFIG_PSTORE=y`, `CONFIG_PSTORE_CONSOLE=y`,
`CONFIG_PSTORE_PMSG=y`, and `CONFIG_PSTORE_RAM=y`. The exact command line
reserves `0x400000` bytes at `0x9b800000`, split into a 1 MiB record and 3 MiB
console region, with pmsg and ftrace regions disabled and `dump_oops=1`.
The wrapper retains the separate 180-second recovery rollback token. AVB is
explicitly unsigned and has rollback index zero.

## Critical-path disposition

The earlier
[critical network-root review](2026-08-09-critical-network-root-readiness-review-offline.md)
remains authoritative: a host/target readiness window was reproduced in a
hardware-free ordering model, with final exact host readiness at 1,210 ms,
but this is not proof of Generation 12's cause. Diagnostic mode now waits
boundedly for exact source-bound TCP/2049 acceptance before its sole NFS mount
attempt. `timeo=30,retrans=2` gives a nine-second first major RPC window and
fits inside the 600-second userspace rollback deadline, although the NFSv4
mount does not have a strict nine-second outer bound.

The actual network-root target config has `CONFIG_QCOM_WDT=m`; its initramfs
has neither the module nor a module tree, no matching DT node exists, and no
hardware watchdog is loaded or opened early. The reviewed userspace rollback
timer remains the active layer. This wrapper's pstore observer improves the
independent postmortem path, but physical retention and current-cycle lineage
still require a separately admitted experiment. Missing pstore is never proof
of no crash. The uncommitted VCNL36866 set remains incomplete, isolated, and
untouched.

## Timing, retention, and remaining uncertainty

- two clean wrappers, repack, AVB inspection, source reseal, and dedicated
  observer verification: PASS in 2,075.91 seconds (34m35.91s);
- retained ignored evidence: 9.2 GiB below
  `build/observation-recovery-wrapper-offline-20260809-r1/`;
- free space after the build: approximately 413 GiB;
- no build process or output lock remained after completion;
- complete repository Linux `ci` before independent review hardening: PASS in
  502.79 seconds; this run exposed no failure but is not the final checkpoint
  because the detached-sidecar verifier finding was fixed afterward;
- final hardened complete repository Linux `ci`: PASS in 480.29 seconds
  (`user` 149.91, `sys` 151.53), including the eight observer tests in
  8.344 seconds.

Offline reproducibility cannot prove firmware preserves the reserved DRAM,
that recovery reads the same physical bytes after the exact transition, or
that the lineage marker belongs to the current failed target without the
already-designed correlation checks. The correct recommendation remains
**HOLD**. Candidate issuance, signing, authorization, and hardware execution
must remain separate decisions.

# Development consolidation — 2026-09-04

Starting checkpoint: `c5ff2e327b1e2754db49e602576032c406ae43b1`.
Full-suite checkpoint: `3444e32b394a398033050a2d9a967c2c97e02dd1`.
Final implementation checkpoint: `9128379944a5a5450dba17a56ec401e1ee54addc`.
No target was signed with the production key, admitted, booted or flashed.
No phone network, slot, storage, firmware or installed service was changed.

## Confirmed corrections

- **R6: receipt verification ignored fresh resource failures.** A clean captured
  host-doctor receipt could validate despite current disk/inode exhaustion or
  a newly running builder. Three reproductions failed before the correction;
  validation now applies the live gates before comparing immutable fields.
- **CI selection:** main pushes ignored changed paths; all Markdown was assumed
  harmless; rename detection could hide a removed runtime path; merge tests
  selected from PR paths rather than the checked-out merge. Before/head and
  merge-base selection, explicit documentation paths, no-renames diffs and
  conservative missing/unknown-history handling fix these cases. Scheduled and
  manual regression validation remains broad. Required check names and exact
  head/merge verification remain intact.
- **R10: contradictory active instructions.** README/roadmap described completed
  migration as future work; current state named two installed recoveries. One
  current entry point now owns accepted state; historical instructions have an
  immutable archive index. The 79-line prose-pinning test was removed: it had
  required duplicated historical wording without detecting contradictions.
  Shared document/link validation remains.

## Reusable development path

`scripts/host/rog5-dev` delegates to the existing test, selector, initramfs and
packaging implementations. The packager now accepts a single JSON recipe for
its 15 non-credential fields; keys/outputs are separate and derived artifact
hashes remain computed. Unknown/duplicate fields and overrides are rejected.
No new policy engine or signing/admission bypass was introduced.

The isolated BusyBox runner uses the actual archive plus QEMU in a private
filesystem/network namespace. It reproduced missing `modules.dep` and then
returned `qcom_pon` after explicitly simulating the existing runtime's empty
index. The shipped runtime syntax check also passed. Missing-module paths can
exit zero without output, so callers must check content, not just exit status.
This does not emulate hardware, run init, or validate systemd protections.

Real retained Image, DTB and V14 archive were packaged with an ephemeral test
key. New recipe twins and the original CLI produced identical payload,
manifest and signature hashes. Both new bundles passed the native verifier.
These test-key packages are not phone-trusted candidates. Wrapper/kernel
rebuild count was zero; accepted bytes were reused.

## Measurements

| Measurement | Before | After |
|---|---:|---:|
| README + roadmap + current + active words | 11,501 | 1,033 |
| Current + active words | 1,772 | 606 |
| Project fast-loop skill words | 561 | 413 |
| Active local tier | 4.871 s | 4.750 s final (5.246 s earlier sample) |
| Runtime packaging including hashes | 0.455 s original CLI | 0.447 / 0.672 s recipe twins |
| Exact archived BusyBox name check | No reusable isolated entry point | 0.736 s positive probe |
| Old full GitHub head/merge test steps | 317 / 314 s | See publication run |

Active timing varies between samples; the final run is slightly faster, not
proof of a significant speedup. Packaging speed is essentially unchanged. The gains are reduced context,
eliminated copied signing scripts, subsecond offline capability checks and
avoided full/QEMU work for docs-only main pushes. This is a selection result,
not an invented measured remote latency saving. Historical head checkout alone
took 40 s; full integration remains the major test cost.

Two retained rehearsal bundles used 189,448,192 allocated bytes in total.
No instrumented high-water measurement of short-lived packaging staging was
taken; this is retained output size, not claimed peak usage.

## Recoverable cleanup

Inventory covered 1,088 scripts, 678 reports, 214 configs, 169 manifests and
four detached historical worktrees. Build output was about 164.18 GiB. Five
obsolete wrapper trees totaling 45.56 GiB had 60/60 final-artifact comparisons
matching retained cache entries. Only the oldest V1 tree was reclaimed here.

Its 9,800,404,992 allocated bytes became a 2,941,504,613-byte private zstd/tar
archive: approximately 6.39 GiB reclaimed. Full archive comparison passed;
kernel configuration and cache-publication sample restoration passed `cmp`.
The archive preserves symlinks without dereferencing them. Its digest,
original path and restore commands are retained outside Git. Cache, other
builds/worktrees, unique evidence, keys, backups and rescue artifacts remain.
The four detached worktrees total only 143.70 MiB and contain historical inputs;
they were left intact. No repository history was rewritten.

## Review limits and remaining risks

Reviewed native RAM loader/transaction, pre-switch Wi-Fi/module setup,
power-readiness loader, overlay/service-state teardown, one-use kexec exitrd,
package/native-verifier boundary, wrapper cache and host/test/CI selection.
Existing focused and integration tests cover these paths; this was not an
exhaustive driver audit or hardware reliability proof.

The possible display-service sandbox write restriction remains unproven:
rootless namespace/systemd probes did not consistently enforce the packaged
restrictions. No speculative service fix was made. A faithful namespace-capable
VM or attended hardware observation is still needed before declaring toggles
working. The historical PMIC/UFS transient remains unexplained.

The old generated power/USB lock is explicitly documented as the NFS observer
track, not installed native-server authority. Historical profiles remain
regression/recovery data; wholesale lifecycle replacement was not attempted.
Local packaging needs no fresh remote green commit, but existing live gates
that require remote evidence were not bypassed. Global skills were untouched.

The anchored USB descriptor identified persistent Linux, but pinned SSH at
`10.77.0.2` returned “No route to host”. Therefore fresh phone health is not
claimed. Next device work is read-only transport/health recovery, followed by
the operator-attended screen test. V15 stayed unsigned/unconsumed throughout.

## Final local validation

- Full `scripts/host/test-repository-linux.sh ci`: **234 suites PASS,
  468.107 s** at the full-suite checkpoint. There is no comparable retained
  pre-change local full-run measurement; the 317/314-second baselines above
  are from GitHub runners and must not be compared as the same machine.
- Subsequent changes were confined to test tooling and guidance. A new real
  archived-app test caught inherited host UID/GID 1000; explicit namespace
  mapping fixed it. The test failed before the fix and passed afterward;
  the display archive now reports module metadata `0:0:644:1` in 0.701 s.
- Final active tier PASS in **4.750 s**. Packager 10 tests PASS, receipt 4 tests
  PASS, selector 27 tests PASS, cache 13 tests PASS, runner contract PASS,
  generator/no-diff and revoked historical-track closure PASS. Both updated
  project skills validate. All local links and diff whitespace checks pass.
- The published commit receives full GitHub head and merge validation plus
  QEMU through [PR checks](https://github.com/klimovich008/rog5-linux/pull/1/checks).
  Remote run timing/conclusion is reported in the PR and final handoff rather
  than creating a new code commit solely to record its own CI result.

No additional hardware cycle is needed for these host/tooling corrections.
A future cycle is justified only by the outstanding physical display or new
hardware question after the existing server's transport health is confirmed.

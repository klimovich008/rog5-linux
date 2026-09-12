# Native ARM64 package snapshot, 2026-09-12

Captured and authenticated a coherent selected set of **315 native-mobile package
inputs**. All archive sizes/hashes, detached signatures and signed `.PKGINFO`
name/version/architecture/dependencies/providers pass. The cache contains 630
archive/signature files, 279,543,157 bytes. This closes archive availability for
this snapshot, not Denial runtime, ABI, mobile UX or phone qualification.

The old 312-package graph and its 14-PASS/298-BLOCKED audit remain unchanged.
Several pins had disappeared from the live mirror: bounded checks found the old
foot, systemd and Mesa archives absent. A fresh snapshot updates 36 versions,
adds liburing and numactl through dependency resolution, and explicitly adds
archlinuxarm-keyring. Mesa and both selected Vulkan Mesa packages advance together
to `1:26.2.2-1`. Fifteen identical archives were reused; 300 were fetched, including
the separate ARM keyring addition. No package was installed or activated.

The first resolved set had 314 packages and 1419 edges. Pacman's print-only
transaction preparation independently matched every name/version. Adding the
ARM keyring produces 315 packages, 1421 edges and 29 root requests; libalpm again
matches exactly. The general Arch keyring alone does not supply the ARM signing
key. Source declaration of `signature_verified: false` records the graph's
unauthenticated metadata stage; the separate audit receipt proves authentication
of the exact graph hash. The whole runtime status remains BLOCKED.

[Upstream signing policy](https://archlinuxarm.org/about/package-signing) signs
packages and deliberately leaves repository databases unsigned. Missing database
signatures are therefore not an obtainable prerequisite. We retain HTTPS source
URLs, fetch times, exact raw database hashes and package signatures. This binds
the selected input set, not cryptographic repository freshness/anti-rollback or
signed mobile-update authority. The fresh extra.db still contains one malformed,
unselected `findnewest-0.3-4` record. It is retained and quarantined, not silently
repaired or used. Whole-repository integrity remains unqualified.

Current upstream keyring Git HEAD was observed as
`91e6b11698f8df66042d56aaa56fbe9c9263847d`; its public key/trust/revocation files
were fetched at that revision. They differ from the current signed
`archlinuxarm-keyring-20240419-2` package. The package's build-key bytes and
direct-signer file match the prior retained build key. Its signer is the build
system fingerprint published by Arch Linux ARM:
`68B3537F39A313B3E574D06777193F152BDBE6A6`. The verifier uses an explicit primary
signer allowlist; it does not implement pacman's web-of-trust setup. Canonical
Git master-key trust files, packaged files and the selected verifier inputs are
retained separately. No host or phone trust store was modified.

An initial keyring-only preparation read `desc` without its separate `depends`
record. The verifier correctly rejected the resulting missing `pacman`
dependency. That FAIL is retained; collecting the complete record passes without
relaxing the verifier. No failed input was promoted. The signed package and Git
keyring differences are recorded facts, not an inferred upstream bug.

Added `--graph` to the existing checker so the current snapshot can be selected
explicitly while preserving the historical default command. The new regression
fails on old source because explicit graph selection is absent; it then proves
that the requested graph is validated even when the default graph is invalid,
and rejects a missing dependency in the requested graph. Metadata-only output
now describes its scope instead of claiming archive authentication is missing
after a separate successful audit.

Starting commit `70cef098a5d0a1c35fd2c8ae65a79dc54417d306`, tree
`82214898e31153f582555c8e10989f391859bb14`. Frozen source
`d21180c0f78e075c5d858a2455d48b2a2892298a`, tree
`3e93004c1cfa7da310fe30220a317782d86ea611`. Later changes record qualification
only. Final commit/tree and clean state are in private completion evidence.

| Executed check | Result | Seconds |
|---|---|---:|
| New explicit-graph test against old source | Expected FAIL: unsupported graph argument | 0.071 |
| Explicit valid/invalid graph selection | PASS | 0.303 |
| Focused metadata/archive suite, 19 groups | PASS under Python optimization | 1.802 |
| 314-package libalpm print-only preparation | PASS, exact set | 0.269 |
| 315-package libalpm print-only preparation | PASS, exact set including ARM keyring | 0.270 |
| Initial full archive authentication | 315 PASS, no FAIL/BLOCKED | 28.374 |
| Frozen public graph + database + archive check | 315 PASS; runtime BLOCKED | 28.485 |
| Full offline CI | {'PASS': 306, 'FAIL': 0, 'BLOCKED': 0, 'SKIPPED': 3, 'NOT_SELECTED': 30} | 612.291 |

The three whole-suite skips are declared optional historical suites. There are
also 39 declared optional skipped subchecks; exact-source sections are enumerated
in JSON/JUnit. No new board build or real-phone result is inferred. GitHub CI
was NOT RUN. Final archive audit SHA256: `473536ffc62acc44180d929bf4b80a23fe5c86c78c5b9d97c07889120566104c`.
The graph SHA256 is `b5fa5dac0ea87a34126ced885a2da139b48f22ec26f3ec2e32484506e3da08e1`.


The exact commands, full audit and per-suite JSON/JUnit are bound by the
[qualification JSON](2026-09-12-mobile-package-snapshot-qualification.json).
Private cache and raw evidence are in
`/home/deck/.local/state/rog5-mobile-snapshot-evidence-20260912-r1` (`E`).
`python3 E/run-qualification.py` records the final public `--graph` audit and
full `ci` invocation. Audit and fetch processes use at most 1 GiB; CI uses two
workers, 3 GiB and no swap. More than 3 GiB free disk is preserved. Large package
archives stay outside Git; their exact identities are retained in the source
graph, archive index and artifact-set manifest. No new target candidate exists.

Changed source/data: `scripts/host/check-mobile-package-closure.py`,
`scripts/host/test-review-metadata-checkers.py`,
`packaging/arch/mobile-package-snapshot-20260912.json`, `docs/development.md`.
Qualification: `configs/project-status.json`, `docs/current-state.md` (generated
header only), `docs/development-lessons.md`, `manifests/current-artifact.json`
(package-audit field only), `manifests/artifact-sets.json` (one new input set),
this report and its JSON. All 462 previous artifact sets, the old graph and
non-package pointer fields remain unchanged. Existing CI results are not
presented as newly executed GitHub CI.

Remaining work: materialize and check the ARM64 ABI/runtime composition from
these exact inputs; provide matching Denial engine, AOT/ICU and shell assets;
then qualify a real native mobile session through the authorized process. The
old engine-sync container no longer exists, and its later stop receipt overrides
the old running checkpoint. It was not restarted. Capacity for its engine build
remains unresolved. Cryptographic update freshness/security review also remain
separate from this archive-authentication result.

All mobile physical rows remain **NOT RUN**, and S06/R01 remain **FAIL**. Board,
GPU/touch, signed/installed artifacts and fallback are unchanged. No phone
contact, boot, power control, production signing, claim/admission operation or
protected-storage mutation occurred. The next smallest physical question remains
separately authorized corrected-display scanout and blank cleanup. No session is
armed and this package work grants no device-operation authority.

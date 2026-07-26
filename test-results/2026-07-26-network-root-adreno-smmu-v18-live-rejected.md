# Network-root v18 Adreno SMMU — safe live rejection and v19 correction

Date: 2026-07-26

Result: **v18 stopped safely at its read-only baseline because of a verifier
false positive; v18 must not be retried. The corrected v19 external control
plane passes offline acceptance. No SMMU bind, GPU/GMU enablement, firmware
request, DRM/render node, acceleration, flash, or storage write occurred.**

## Attended v18 boundary

The exact manifest-pinned 100,663,296-byte v18 AVB image was used once through
temporary `fastboot boot`; it was never flashed. The staging recovery reached
ACM, the existing atomic `confirm-gpucc` transport entered
`7.1.4-g7a5cef0db479`, and the exact USB/NFS network root reached running
systemd with zero failed units. A known missing-marker race caused the single
permitted identical-load replay in staging. Execute remained non-retryable and
was transmitted once.

The one-shot compound SMMU gate was invoked once. Its first read-only baseline
returned:

`FAIL IOMMU fault signature exists`

The only matching kernel line was the normal boot message:

`iommu: Default domain type: Translated`

The case-insensitive expression matched `fault` inside the word `Default`.
This was a verifier defect, not an IOMMU fault.

The baseline failed before any state-changing target step:

- the original rollback watchdog remained alive and armed;
- the transition watchdog was not armed and no watchdog was disarmed;
- the external GPUCC module was not loaded;
- the Adreno SMMU device remained unbound;
- GPU and GMU remained disabled;
- no firmware or render node appeared; and
- systemd still had zero failed units.

The cycle was not retried. A normal target reboot returned the phone to the
exact persistent Alpine fallback. The bounded NFS server observed USB
departure and removed its export, listener, mount daemon, bind mount, address,
temporary sysctl, and runtime firewall state. ModemManager and the ordinary
firewall state were restored.

The complete output is retained outside Git in a caller-owned mode-`0600`
private evidence file. Device serials, MAC addresses, boot IDs, credentials,
and private evidence are not included here.

## Fallback-verifier correction

The fallback-to-fastboot helper also rejected two benign strings during the
post-cycle check:

- a `dynamic_debug` line contained the substring `BUG:`; and
- a DRM configuration line contained `panic:1`.

Neither line was a crash. Tests now require token-delimited fatal signatures
such as `Kernel panic`, `Oops:`, `BUG:`, `watchdog bite`, `Kernel fault`,
`Unable to handle kernel`, or `Synchronous External Abort`. Regression inputs
prove that the two benign lines are rejected while real fatal examples still
match. The helper retains strict fallback identity, exact read-only health
checks, guarded `RESTART2("bootloader")`, SSH keepalives, and one-fastboot
verification.

## v19 test-first control plane

The SMMU fault detector now requires either:

- `IOMMU` or `arm-smmu`, followed by a token-delimited `fault`; or
- a token-delimited `context fault` or `global fault`.

Tests reject `Default domain type: Translated` and accept representative real
context, page, and global fault lines. The same detector is pinned in the
SMMU baseline, SMMU probe, compound gate, and later A660 registration
baseline/probe contracts.

Because the v18 live contract permits no retry, the corrected external
control plane is named v19. It deliberately reuses the unchanged,
reproduced, RAM-only v18 kernel, DTB, initramfs, GPUCC module, ASUS wrapper,
and AVB image. Only the host/device verifiers, source locks, export seal, and
exact NFS allowlist changed.

| Corrected input | SHA-256 |
|---|---|
| SMMU baseline | `db75fb268167a13b3f22b7fcdb73d17247d29e3551fcff5f3105022ca95fe402` |
| SMMU baseline test | `b3d3862edf829986b3f10f6edc37d533b11a7bbbe4e28aa2d6c6abe2ff4ee7e5` |
| SMMU probe | `c005963f206a7c325bdb08eaab4f7adc45e6d2ee1d5f9be5b1dc86f3c5317df6` |
| SMMU probe test | `2f740349528837e73cd6a0bbfdcd841703b9fd2066fdafe70ce8fbb712891504` |
| compound gate | `0604e5a1d86a3ca5beaa79421bf487f9a75cbb28d33382ceeac1859501bd33c7` |
| compound-gate test | `381355e9be5dd3bf054574465f67931aea11c368a0dc63642e33b788d1248c54` |
| fallback reboot helper | `5ea9290748bb6de5a34bf50da3888941b3d1cdf58b69633461e0a7865d897e30` |
| fallback helper test | `a60c38f2d8a4a2ecbd78c5dfa25d0605b1061b5cbc2f2282e07707cbf5263b4f` |

The corrected static suites pass, including the later A660 registration
detector regressions. The full exact artifact verifier was rerun and returned:

`PASS exact v18 GPUCC plus Adreno SMMU bundle; consumer-disabled, firmware-free, zero-storage, reproducible, and offline-only`

This wording retains the binary artifact's v18 identity; it does not authorize
another v18 control-plane run.

## Isolated v19 export

The new exact source directory is
`/var/lib/rog5-network-root-adreno-smmu-v19`. It was created beside the
preserved v18 root, not over it. Independent privileged verification proves:

- 1,008 module files match the accepted base;
- all three exact A660 firmware files are absent;
- SSH credentials and host identity are preserved without exposing them;
- unchanged metadata and file hashes match the accepted base; and
- the accepted base remains unchanged.

The export carries the exact read-only
`/etc/rog5/adreno-smmu-v19-export` seal. The runtime NFS server now accepts the
general v1 root and this v19 sibling only; the historical v18 sibling cannot
be served. NFS remained inactive with no export mount, listener, or mount
daemon after preparation and verification.

## Next gate

V19 is eligible for review as one new attended external-control candidate.
If run, it must use the same temporary-boot-only binary, a new private evidence
directory, the original and transition watchdogs, one compound invocation,
and immediate normal fallback. Acceptance still requires one GPUCC bind, one
exact runtime-suspended SMMU bind, and zero GPU/GMU clients, firmware, render
nodes, storage, warnings, faults, unsafe thermals, failed units, or cleanup
failures.

A v19 PASS would accept only the idle SMMU prerequisite. A660 registration,
first DRM open, GPU firmware/authentication, Mesa/Freedreno, display,
suspend, battery tuning, and accelerated desktop remain separate tiers.

# Linux 7.1 devices-level suspend callback candidate — offline result

Date: 2026-08-09

Starting repository SHA:
`78594a2a713959410af3a653397c7ba693dfd424`.

Result: **PASS for reproducible compile-only `pm_test=devices` diagnostics;
no phone boot and no real suspend.**

## Defect fixed

The accepted network-root kernel has suspend support but disables
`CONFIG_PM_DEBUG`, so `/sys/power/pm_test` is absent.  Entering real suspend
would cross the platform, CPU, and PSCI boundary before device callback
survival, USB/NFS continuity, or wake sources have been isolated.

The new feature fragment exposes only a devices-level callback checkpoint and
a bounded DPM watchdog.  The exact pinned-source oracle proves that Linux
returns from `TEST_DEVICES` after device suspend callbacks and before
`suspend_enter()` and the later PSCI `SYSTEM_SUSPEND` path.  The one-shot
target gate refuses real suspend, consumes its same-boot claim before the sole
state write, selects `pm_test=devices`, writes `mem` exactly once, restores
`pm_test=none`, and classifies post-return UDC, binding, interface, carrier,
address, and route loss separately.

The first clean twin build exposed a second defect in the initial
implementation: fragment metadata recorded `CONFIG_DPM_WATCHDOG=y`, but the
resolved `.config` silently dropped it because upstream also requires
`CONFIG_EXPERT`.  Both first-pass builds were therefore rejected and are not
candidate evidence.  The corrected fragment enables that exact prerequisite,
pins the newly exposed unrelated `RESET_SIMPLE` driver off, and the verifier
compares every effective config assignment.  It permits only the requested PM
symbols, unavoidable arm64 capability/default markers, and disappearance of
the now-inexpressible media-menu visibility marker; every other enabled,
module, integer, or string assignment must equal the accepted config.

## Hostile regression evidence

The three new suites failed before their implementations existed:

```text
source contract: 86 ms, missing verifier
candidate contract: 9 ms, missing verifier
runtime gate: 150 ms, missing gate
```

The initial implemented suites passed in 211 ms, 355 ms, and 1,373 ms.  After
the Kconfig dependency correction, the final focused results were:

```text
source/source-mutation oracle: 5 tests PASS, 327 ms
candidate/config hostile contract: PASS, 576 ms
one-shot runtime hostile gate: 6 methods PASS, 1,606 ms
core compatibility oracle: 39 tests PASS, 591 ms
repository runner contract: PASS, 6,132 ms
core source/DTB hostile oracle: 77 tests PASS, 13,209 ms
```

The first full-CI checkpoint stopped after 38,438 ms because the core
source/DTB contract still pinned the pre-change compatibility-profile hash.
Its 97 hostile mutations consequently failed at the common profile identity
gate instead of reaching their intended classifications.  Updating that one
repository-owned hash to the reviewed profile identity restores the existing
fail-closed test ordering; it does not change source, DTB, or hardware claims.
The focused 77-test source/DTB rerun then passed in 13,209 ms.

The final repository-wide Linux CI tier passed in 460,174 ms.  The prior
accepted checkpoint took 446,022 ms, so this checkpoint is 14,152 ms slower
(3.17%).  Per-suite durations remain emitted by the shared runner, including
the new source, candidate, and runtime gates.

The runtime suite covers successful one-attempt return, irreversible retry
refusal, missing guard before claim/write, wrong kernel/system/NFS/storage/
watchdog/USB/config state, state-write failure with disarm, exact post-return
link-loss classifications, and missing return evidence.  The candidate suite
rejects missing `EXPERT`, unexpected active config, `RESET_SIMPLE`, watchdog
timeout drift, boot-time RTC suspend, wrong feature metadata, and an unsafe
source path.  Source mutations cover the devices intercept, PM dependency,
DPM panic, and PSCI boundary.

## Clean-build discovery and corrected twins

Two first-pass clean builds were byte-identical but invalid:

```text
first A: 2,237,836 ms
first B: 2,231,301 ms
specialized verifier: FAIL, resolved CONFIG_DPM_WATCHDOG absent
```

This failure occurred before packaging, signing, issuance, credentials, or
phone access.  A config-only Kconfig probe then proved that the corrected
fragment retains every accepted effective assignment outside the exact
allowlist.

The corrected twins used:

- source commit `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`;
- source tree `2ea2be38c5e4dc9aafffbbc0db5aae0f6513a1d9`;
- release `7.1.4-g7a5cef0db479`;
- historical builder image ID
  `b01d1a9ea3b76323fe0202db86b6bdcbe58f29e80504a3174ea33cb2caf61f7d`;
- builder digest
  `sha256:7ba7b8a707b8b8922f2c2145e60728685463b185e229f3938783819f9ce4fe11`;
- Clang 18.1.3, network disabled, `JOBS=8`, `INCREMENTAL_BUILD=0`,
  and `KBUILD_CCACHE=0`;
- distinct fresh output directories.

Corrected clean-build timings:

```text
final A: 2,240,986 ms (37m20.986s)
final B: 2,245,897 ms (37m25.897s)
specialized verifier A: 11,996 ms (post-review rerun)
specialized verifier B: 11,907 ms (post-review rerun)
direct five-file comparison: 1,017 ms, byte-identical
```

Exact twin identities:

| Artifact | Size | SHA-256 |
|---|---:|---|
| `.config` | 248,182 | `a4be1ae900706886ffee23c8d3066d6309fceb33905aeb67b27756ef713943ec` |
| `Image` | 40,116,736 | `93e00f68ae7265f71b41b94f8e109aa10e2417c88aaad3aac77fd0cf606704e0` |
| `Image.gz` | 14,761,175 | `6c724d46ed405f6c6db3916490743242de7e4ae7bef5a10fb99e9e7167e1774c` |
| `modules.tar.gz` | 300,415,034 | `f650f51f4027a9e7568906e654d71794ac562c3a52e46120c17804e700099315` |
| `build-meta.txt` | 718 | `55faab238de9812270b67ed92599779aa09461324b8b84dc63c2d4060c0635ca` |

The final feature fragment is
`7c9ae6970c908d5658eb4324b9eba7f19182eeb9bbbb90d021a83117b46ae5b5`.

## Boundary and next step

No artifact was packaged as a boot image, signed, issued, published, or used
on a phone.  No fastboot, ADB, SSH, credential, signing key, GitHub mutation,
or phone storage access occurred.  Real suspend, PSCI entry, wake sources,
panel power, SSH continuity, and battery impact remain unproven.  A missing
pstore record must never be interpreted as proof that no crash occurred.

A later attended temporary target may run exactly one separately admitted
`pm_test=devices` pass.  Real `mem` suspend with `pm_test=none` remains
forbidden until callback survival and at least two physical wake sources have
independent evidence.  Generation 12 remains consumed and must never be
retried; the active stage-75/current-cycle-postmortem successor remains
unissued with no boot authority.

# Network-root thermal-PMIC compile candidate

Date: 2026-08-09

Starting repository SHA:
`1c91e53b865cac8e587453888819f65d5a946fa6`.

## Defect

The accepted Linux 7.1.4 network-root config built
`CONFIG_QCOM_SPMI_TEMP_ALARM=m`. The PMIC critical-trip IRQ path therefore
depended on userspace loading a module after boot. A retained experimental
tree had the intended built-in object, but it lacked `modules.tar.gz` and
`build-meta.txt`; partial objects were not candidate evidence. The active
network-root builder also had no exact, optional feature-layer input, so a
one-line candidate could not use incremental reuse without escaping the build
contract.

## Correction

- `build-mainline-network-root.sh` accepts one optional canonical regular
  `FEATURE_FRAGMENT`, merges it last, and binds its path and content hash into
  the private exact-state record.
- Empty-feature builds preserve the prior release-metadata format. Feature
  builds add only the feature SHA-256 to release metadata; acceleration mode
  remains excluded.
- `configs/kernel/rog5-thermal-pmic-critical.fragment` changes the PMIC alarm
  driver to built-in and explicitly preserves emergency delay zero.
- The dedicated verifier requires an exact one-line config transition,
  `modules.builtin` membership, no loadable PMIC module, and probe/IRQ/init
  symbols in `vmlinux`. It reports `compatible-not-accepted`,
  `hardware_acceptance=unproven`, and `authority=none`.

## Regression evidence

The builder regression failed before implementation in 1,373 ms with:

```text
FAIL optional feature fragment was not merged into the final config
```

The candidate-verifier regression failed before implementation in 8 ms with:

```text
FAIL missing executable thermal-PMIC candidate verifier
```

After correction:

- feature layering/reuse/invalidation/locking/ccache/identity suite: PASS,
  1,653 ms;
- hostile thermal-PMIC candidate suite: PASS, 480 ms;
- network-root rebuild contract: PASS, 135 ms;
- core compatibility oracle: 39 tests PASS, 525 ms.

Hostile cases reject config drift, a premature emergency-delay change, wrong
feature metadata/state, absent built-in membership, a remaining loadable PMIC
module, missing `vmlinux` symbols, linked feature input, feature mutation, and
concurrent output ownership.

## Real clean build

The build used the exact clean, tag-free source:

- commit: `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`;
- tree: `2ea2be38c5e4dc9aafffbbc0db5aae0f6513a1d9`;
- release: `7.1.4-g7a5cef0db479`;
- builder: `localhost/rog5-kernel-builder:ubuntu-24.04`;
- network: disabled;
- jobs: 8;
- output: ignored host build directory;
- clean-build elapsed time: 3,139,813 ms (52m19.8s).

An exact-state incremental rerun completed in 87,917 ms (1m27.9s), a 35.7x
wall-time reduction. It preserved every recorded release identity. This
measures development reuse only; it is not a clean-twin result.

Artifact SHA-256 values:

- `.config`:
  `33bd5f352eaf140a56591124419e6c0e4f433b9fa2c676d35cf611cfffe513fe`;
- `Image`:
  `35f86a12bea7037130148a5eca4fd2a9bf28ee916f0db91fa18a9b771dbfa75a`;
- `Image.gz`:
  `1281143d3de7ea6bd9a8755d0361ea7b95562113a8b2f92d1b8ff6a444ec11c8`;
- `vmlinux`:
  `e534c8278de03ca669abf227ef50705b3d52cc361091967026397196c3c031e7`;
- `modules.tar.gz`:
  `c5a9927f134182962ad608816b1e95247a813217b12f70d0e732878b7de70ab1`;
- `build-meta.txt`:
  `e2ee2077f7cb6cae4bd8701d1ee268e7721d6bcc102529a7e413852369bb5d08`.

The standard network-root verifier passed in 7,417 ms. The dedicated
thermal-PMIC verifier passed in 11,367 ms.

## Boundary

This is one complete clean compile plus an exact-state development rerun, not
the two distinct clean builds required for candidate issuance. No candidate
was packaged, signed, issued, or booted. PMIC registration, interrupt
delivery, thermal trips, cooling response, shutdown, emergency fallback, and
rollback behavior remain unproven. The emergency fallback delay remains zero.

No phone, fastboot/ADB operation, credential, signing key, GitHub mutation,
or phone storage was used. Generation 12 remains consumed and must never be
retried. The active stage-75/current-cycle-postmortem successor remains
unissued and has no boot authority.

# Mobile DT and provider qualification, 2026-09-12

Starting source: `1e963ee0789314ee1d249adee42123d5b8664146`, tree
`80c9a097e578f4f5b36eaa5e07ee5674c16398e3`, branch
`agent/review-correctness-20260912`. The original dirty checkout and other
worktrees remain untouched. This continues the [correctness repair](2026-09-12-offline-correctness-repair.md)
and [RPMh/touch qualification](2026-09-12-touch-kernel-readiness.md).

## Confirmed and fixed

The previously qualified standalone board DT lacked `/__symbols__`; the real
production display overlay could not apply. The production builder now adds
`-@` only for this board. Actual compiled comparisons preserve every existing
hardware property, reservation and boot CPU while adding 366 labels and 186
phandles. The previous no-symbols result is retained as a failing regression.

Composing display, GPU and inert touch exposed two additional schema errors.
The current display overlay replaces two unsupported `input-enable` properties
with `output-disable`. Exact pinned generic pinconf and Qualcomm pinctrl source
prove both clear the same OE bit. The r2/r3 decoded comparison permits only those
two property substitutions; all 373 phandles and other properties are identical.
The historical verifier keeps its old default; the current builder selects the
new spelling explicitly and validates TLMM as well as the panel binding.

The private FTS3658U compatible now has a local, disabled-only binding. Fifteen
real-DTB fixtures check address, native axes, GPIO/IRQ polarity, supplies and
unsupported activation/transform/wake requests. The validator CLI suppresses
some missing-required errors on disabled nodes; direct schema-library checks
cover those without enabling the device. Exact composed-property checks also
require the complete inert node.

The production board gate now requires ordered display/GPU/inert-touch
composition, full-schema validation and the touch-provider contract. It records
all consumed CPP inputs and tool identities. External binding staging cannot
replace an upstream file. CI selects these inputs and retains nested composition
receipts. No production kernel C code or resolved config changed.

The first integrated run failed after 19.356 seconds: a cleanup assertion raced
with reaping of `/proc/PID/stat`. The first focused correction exposed the second
valid disappearance error, ESRCH. Both failures remain recorded. A single read
now accepts only ENOENT/ESRCH or a zombie; deterministic tests still reject a live
child and permission errors. Thirteen cases pass in 0.610 seconds. Production
termination, deadlines and cleanup were unchanged.

## Executed evidence

[Machine-readable test records](2026-09-12-mobile-dt-tests.json) contain exact
commands, durations, source-dependent sections, statuses and private receipt
hashes. [Board qualification](2026-09-12-mobile-dt-qualification.json) binds the
compiled DTs and inherited kernel build separately.

- Full processed schema: 5,593 input files, 70.795 seconds; PASS.
- Ordered and repeated real DT composition: 12.119 seconds; PASS, zero schema
  diagnostics, seven hostile mutations rejected.
- Final source/delta binding: 0.189 seconds; 37 CPP inputs, including 33 exact
  pinned-kernel Git blobs, and only the two intended pinctrl changes.
- Ten production-builder tests: 0.108 seconds; PASS. Real display builder,
  historical/current semantic contracts and publication checks: 1.309 seconds;
  PASS (schema-tool boundaries are fixtures in this cheap suite).
- GENI source comparison and executable fixture: 1.207 seconds; PASS. Five
  actual Linux extracts cover 11 protocol/provider paths, five DMA-buffer cases
  and five rejected mutations. Full probe/adapter/IRQ execution is not implied.
- Inert provider check against the final composed DT, actual config and module
  metadata: 0.071 seconds; PASS. Hostile fixtures cover 25 DT mutations plus
  config and module-metadata failures.
- Exact retained Image, config, Module.symvers and all 1,031 modules verified in
  0.346 seconds. No Image/module source changed, so their previous real compiler,
  modpost and depmod evidence is reused; no cold rebuild was performed.

Frozen integration source: `d482f3a468072cb64f1b6496a994436e19f4d23e`, tree
`5b59264664c7c06d76b970b78a0346f664a02955`. The complete host CI tier passed in 603.870 seconds:
**303 PASS, 0 FAIL, 0 BLOCKED, 3 declared optional SKIPPED, 30 NOT_SELECTED**.
Two workers ran in a 3 GiB/no-swap scope. `ROG5_LINUX_SOURCE` was unset for
that host tier; exact-source and real-schema runs above are recorded separately.
The initial failed integration remains 7 PASS, 1 FAIL, 298 BLOCKED.
The three whole-suite skips and their optional subchecks remain explicit.
Report-only changes were then checked with twelve metadata unit tests, three
validators, the existing Markdown-link check and fifteen plan test identities;
all passed. No executable build/test source changed after this CI result.

Artifact SHA-256 identities:

| Artifact | SHA-256 |
| --- | --- |
| Base with symbols | `bf7aebb449d6a7eee0c2778f13d69166ba3203bebffd1120e9c1f89357301412` |
| Composed display/GPU/inert-touch DT | `deeb77287d20393c207469c8debf441c6b451aa1aad3cd764dd4e5e4156cdc57` |
| Corrected display overlay | `f57ab227d64687f9802bae6f7e566f01da83af024b0e7c2df9e1c985fd275095` |
| Complete processed schema | `96234e48b0ff4ed706553191d909b54e803a7f7454d9118fdafb491a7c58cbfe` |
| Retained Image | `0789c10855e74c2f54caee7437864235f5872118e9f697782cc8547b286d406a` |

The composition input bytes are bound to `ec9c4e630fd4f60eeb3bc86b0005b7a0358701e8`,
tree `ec738ae37957b4a6f316af40990fb3c09038dd2f`. Raw runs occurred before that
commit and retain file hashes; the source-binding supplement does not relabel
them as a clean-checkout execution. Later test-only changes do not change the
DT producers. Linux remains v7.1.4, commit
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`; all sixteen production patches and
all kernel fragments remain unchanged. Full new board-builder orchestration
and remote CI are NOT RUN; actual component and incremental artifact results
above have their own evidence.

## Disproved assumptions and unresolved limits

An ID read is not proof of event transport. Valid GENI I2C with FIFO enabled can
serve the small ID transaction through FIFO; a 62-byte frame may select SE-DMA.
FIFO-disabled mode requires both GPI channels. Invalid protocol requires a
qualified serial-engine firmware asset; a different valid protocol is rejected.
The GPI mask selects instances dynamically, not by equating serial-engine ID4
with GPI instance4. These are exact-source findings, not runtime observations.

L3C has a BOB parent in the combined display DT; it is incorrect to describe
both touch rails as missing their parents in this composition. L8C's parent is
still absent. Schema success does not establish rail power or firmware state.

Remaining work, in severity order:

1. Physical panel preparation/scanout, brightness, blanking and recovery remain
   unqualified for these bytes. All 28 mobile physical rows stay NOT RUN;
   historical headless S06/R01 stay FAIL. The old Q6 and r1/r2 schema failures
   remain unchanged.
2. Touch is inert. L8C parent/power ownership, actual protocol/FIFO configuration,
   firmware availability, DMA/IOMMU ownership and IRQ delivery are unresolved.
   Persistent regulator-disable failure at final devres release can leave power
   outstanding. Wake/suspend are unsupported by the prototype.
3. GPU overlay composition does not prove A660 rendering, GMU operation, buffer
   sharing, or Denial usability. Full-system QEMU and physical GPU tests were
   NOT RUN. Earlier generic QEMU results retain their userspace-only scope.
4. Firmware inventory presence, full toolchain distribution closure and older
   incomplete artifact provenance remain their existing explicit blockers.

The next smallest physical question is the prepared panel trial: does the exact
corrected production composition prepare, show a stable 60 Hz pattern and blank
cleanly? It requires separate phone-operation authority and a fully prepared
candidate/session; none is created or armed here. Independent offline touch work
can establish L8C source evidence and a bounded provider observation before a
normal-mode ID56/52 trial. It need not block safe display progress.

No phone contact or operation, production signing, candidate creation, real claim
operation, protected-storage mutation, or replacement of accepted/signed bytes
occurred. Private raw evidence stays outside Git. The existing current-artifact
pointer and status model are updated; prior evidence is retained.

## Changed files

- `.github/workflows/offline-smoke.yml`
- `configs/kernel/rog5-production-build.json`
- `configs/mobile/acceptance.json`
- `configs/mobile/trial-plans.json`
- `configs/project-status.json`
- `configs/repository-tests.json`
- `docs/current-state.md`
- `docs/development-lessons.md`
- `docs/development.md`
- `docs/front-touch-prototype.md`
- `docs/licensing-provenance.md`
- `dts/qcom/sm8350-asus-rog-phone5-display-60hz-reviewed.dtso`
- `manifests/artifact-sets.json`
- `manifests/current-artifact.json`
- `scripts/device/build-display-60hz-candidate-dtb.py`
- `scripts/device/fixtures/geni-mode/buffer-select.inc`
- `scripts/device/fixtures/geni-mode/buffer.inc`
- `scripts/device/fixtures/geni-mode/cases.c`
- `scripts/device/fixtures/geni-mode/firmware.inc`
- `scripts/device/fixtures/geni-mode/protocol.inc`
- `scripts/device/fixtures/geni-mode/setup.inc`
- `scripts/device/test-display-60hz-candidate-dtb.sh`
- `scripts/device/test-mobile-dt-composition.py`
- `scripts/device/test-mobile-dt-guards.py`
- `scripts/device/test-mobile-touch-providers.py`
- `scripts/device/test-rog5-geni-mode.py`
- `scripts/device/test-rog5-touch-binding.py`
- `scripts/device/verify-display-60hz-dtb-delta.py`
- `scripts/device/verify-mobile-touch-providers.py`
- `scripts/host/build-rog5-production-kernel.py`
- `scripts/host/test-production-kernel-build.py`
- `scripts/host/test-repository-linux.sh`
- `scripts/host/test-rog5-touch-module-build.py`
- `test-results/2026-09-12-mobile-dt-qualification.json`
- `test-results/2026-09-12-mobile-dt-readiness.md`
- `test-results/2026-09-12-mobile-dt-tests.json`
- `tools/rog5-fts3658u/asus,rog5-mp2-fts3658u.yaml`

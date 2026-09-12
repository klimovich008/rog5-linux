# Touch regulator ownership repair — 2026-09-12

The touch prototype now stops ambiguous regulator retries. The actual Linux
7.1.4 accounting code demonstrates two failures missed by the earlier fixture:
a child disable can consume its vote before its parent fails, and a failed child
enable can leave a parent vote behind when unwind fails. A public error code
cannot distinguish these from a retained child vote.

The driver records NONE, HELD or UNKNOWN for each consumer. Failed enable or
disable makes ownership UNKNOWN; subsequent regulator calls on that consumer
are refused. Cleanup still releases the other known-held consumer and preserves
the original error. Later uncertain cleanup returns `-EUCLEAN`. Normal GPIO,
reset, identification, IRQ and event sequences are unchanged.

This is a scoped software fix. It does not restore an uncertain rail, survive
reprobe, or prove terminal devres cleanup. No rebind/reload or force-disable is
qualified after an uncertain result. Touch remains disabled; all physical rows
remain **NOT RUN**. No phone contact, signing, candidate creation, claim operation,
installation or protected-storage mutation occurred.

## Source and artifact identity

Starting branch: `agent/review-correctness-20260912`, clean commit
`29d302185f4808a9e4647f432949b5f782c8bd14`, tree
`bfc1261e8072f359c0e51593ddeb81e71042deac`. This successor already contains the
previous review repairs; the old audited `4bd1a817` was not restored. The original
dirty checkout and other worktrees were preserved.

Frozen source, builds and integrated tests:
`7b17a25eab542913d3b28afa35b2bf8c7462d15e`, tree
`6630ade9dfe84c9d20fa0705b1fcc20c57074b74`. Subsequent edits are documentation and
artifact/status metadata. The ending commit/tree and complete file hashes are
recorded after the metadata commit in the private `completion.json`.

- Linux base: `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` / v7.1.4.
- Driver SHA256: `9c3c1704e3462f43b710ae811c232ce0e887f3b391c4d5182f04498bbcecc386`.
- Identical 16,544-byte module twins: `34b38126a8d3a4963fda6ec9bce163b7cd126520d722ed26d5bf85c24a30a714`.
- Vermagic: `7.1.4-rog5-production SMP preempt mod_unload aarch64`.
- Config SHA256: `277bc74e104bcdec8e6eda8a345e2a4e7bb15be5118bb829741742e97d8a174c`.
- Series SHA256: `b027af87b37d0aa6d758539efefd082557fcfdd6bfda89cef220d476346eefde`.

The [qualification receipt](2026-09-12-touch-regulator-qualification.json)
records exact commands, source/build pins, tool hashes and evidence hashes.
The [current artifact pointer](../manifests/current-artifact.json) selects this
unsigned fixture explicitly. Previous prototype bytes and receipts are retained;
the inventory links them to this successor. Accepted/signed/installed image
identities are unchanged. No Image or DT rebuild was needed.

## Executed checks

| Check | Result | Wall seconds |
|---|---|---:|
| New actual-core regression against old driver | Expected FAIL: normal cycles pass, five fault cases fail | 0.299944 |
| New actual-core regression against corrected driver, development checkout | PASS: six cases, two mutation controls | 0.556704 |
| Frozen actual-core test with exact source comparison, Python `-O` | PASS | 0.565371 |
| Frozen lifecycle test with exact IRQ/input comparison, Python `-O` | PASS: 16 cases, 13 probe-failure stages, three mutations | 2.018821 |
| ARM64 external module twin A, W=1/modpost | PASS | 2.770406 |
| ARM64 external module twin B, W=1/modpost | PASS | 2.770609 |
| Twin bytes, tools, inputs and 740 consumed kit files agree | PASS | 0.001997 |
| ELF, firmware and exact ABI export check | PASS: all 30 imports resolve; unchanged import set; no firmware/dependencies | 0.043957 |
| Integrated active tier, frozen source | 81 PASS, 0 FAIL, 0 BLOCKED, 0 whole-suite SKIPPED, 256 NOT_SELECTED | 109.864637 |

After the metadata update, eight mobile-status tests passed in 0.114350 s.
Status and artifact-inventory validators passed in 0.064316 and 0.064270 s;
Markdown-link and diff checks passed. All 16 trial-test pins match. Headless and
mobile acceptance bytes, signed/runtime/fallback pointers and current board
qualification are unchanged. Exact metadata-check commands and durations are in
`metadata-checks/result.json` under the private evidence root.

Three declared optional subchecks were SKIPPED in the integrated tier. It ran
with `ROG5_LINUX_SOURCE` unset, so its source comparisons are explicitly NOT RUN;
the separate frozen checks above executed those comparisons. JSON and JUnit
summaries enumerate selected suites, durations, commands and source sections.
The earlier 303-suite CI PASS belongs to the prior frozen source, not this turn.
No remote CI or QEMU module loading was performed this turn.

Commands were run from this worktree. The retained exact source is
`/home/deck/.local/state/rog5-review-correctness-evidence-20260912-r1/board/build-r2/source`.
The commands and complete arguments are retained in `frozen-checks/result.json`,
`module-build/summary.json`, `module-build/abi-check.json` and
`active-r1-execution.json` under the private evidence root below. The integrated
command was:

```sh
systemd-run --user --scope --quiet -pMemoryMax=3G -pMemorySwapMax=0 \
  bash scripts/host/test-repository-linux.sh active
```

It used two workers and disk-backed scratch with at least 3 GiB free. The exact
module builder used the retained kit read-only. Its original Q6 schema FAIL is
preserved; the newer composed-DT/schema qualification remains in the separate
current-board pointer. Module compilation does not supersede either DT receipt.

## Remaining evidence gaps

Confirmed and fixed: unsafe regulator retries within the existing driver context;
regressions now exercise actual core bookkeeping as well as faulted API boundaries.
The existing lifecycle suite covers both IO and VDD errors, GPIO failures, IRQ
shutdown and repeated normal cycles; the separate core suite covers parent/child
accounting rather than pretending its provider callbacks are hardware.

Disproved: a regulator error reliably means the consumer still owns its vote.
Also unsupported: inferring a mainline supply connection or touch load from the
retained vendor data. The bounded vendor audit found no L3C/L8C upstream-supply
properties. Its 10,000 µA entries are mode thresholds. The additionally retained
`asus-mp2.dtb` has generic Lahaina selectors, so its filename is not MP2 provenance.
No supply, load, voltage, mode or DT property was changed on that basis.

Unresolved, in priority order:

1. Physical recovery after uncertain regulator state, including devres/reprobe.
2. Actual L8C upstream feed and electrical margins; runtime GENI protocol/FIFO,
   DMA and IOMMU ownership; real touch ID/events and GPIO behavior.
3. OLED/A660 qualification on the current candidate, suspend/wake and idle drain.
   Historical headless S06 and R01 remain FAIL and are not explained by this fix.

The next smallest hardware experiment, **only under separate authorization**, is
a bounded provider observation using the existing exact-device readback flow,
before enabling touch or asking for touches. It must resolve the available rail,
bus-mode and ownership evidence with independent return-to-known-good cleanup.
An unknown supply cannot be guessed into a candidate. Safe display progress is
independent of that touch gap. No such experiment was run or armed here.

The improvement this turn was replacing the inaccurate failure fixture with
actual accounting code and using a 2.77-second external build instead of a cold
kernel build. Relevant lessons are in the existing development documentation.

Private evidence root:
`/home/deck/.local/state/rog5-touch-provider-evidence-20260912-r1/`.
Raw historical failures and input snapshots remain there; published receipts
contain references and hashes, not credentials or raw unit evidence.

## Changed files

- `configs/mobile/trial-plans.json`
- `configs/project-status.json`
- `configs/repository-tests.json`
- `docs/current-state.md`
- `docs/development-lessons.md`
- `docs/front-touch-prototype.md`
- `manifests/artifact-sets.json`
- `manifests/current-artifact.json`
- `scripts/device/fixtures/fts3658u-regulator/cases.c`
- `scripts/device/fixtures/fts3658u-regulator/regulator-core-v7.1.4.c`
- `scripts/device/fixtures/fts3658u-regulator/stubs.h`
- `scripts/device/fixtures/fts3658u/cases.c`
- `scripts/device/fixtures/fts3658u/stubs.h`
- `scripts/device/test-rog5-touch-lifecycle.py`
- `scripts/device/test-rog5-touch-regulator-errors.py`
- `scripts/host/test-repository-linux.sh`
- `test-results/2026-09-12-touch-regulator-qualification.json`
- `test-results/2026-09-12-touch-regulator-repair.md`
- `tools/rog5-fts3658u/rog5_fts3658u.c`

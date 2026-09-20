# Default-dark AMS678 initialization — 2026-09-20

Start `de695805aa74abbcbc60968eddb740172e54489a`, tree
`b07846017f5f3e25fdf802c02018f3722a944896`. Frozen implementation
`8f7b2f83b59b37c8a7cd53b78610d0b1db0896fc`, tree `f1390c7bde4af6933ee76f880431de42d586c8a3`.
Branch agent/review-correctness-20260912. Previous goal turn was progress:
it closed the input API test gap; this turn fixes a demonstrated panel default.
No phone access, module loading, candidate, signing, admission, claim or
protected-storage mutation occurred. Physical NOT RUN; S06/R01 remain FAIL.

## Failing before, passing after

The actual panel registration supplies brightness1023. Its enable callback sends
DCS brightness0, but exact Linux DRM then calls backlight_enable(), which sends
the registered1023 value through the driver's callback. The new test reproduced
`REGISTERED_INITIAL_DBV driver_enable=0 core_backlight=1023 property=1023` and
failed its default-dark assertion. Existing16 lifecycle cases still passed.
Failure took0.813s; the original patch and
failure log are retained. This proves the software request sequence, not that
this specific transient was physically observed.

The one-line driver change sets initial brightness0. The exact same execution
now records driver0/core0. Explicit1,255,256,1023,0 requests preserve high/low
byte order. Range, preparation guard, reset timing, Iris handshake, DSC and
vendor command sequences are unchanged. A mutation restoring1023 must fail.
This policy requires the future admitted session to request brightness explicitly;
it does not automatically illuminate during registration or initial DRM enable.

The harness now executes actual backlight creation/ops plus six exact backlight
functions, four DRM lifecycle functions and the exact large-brightness helper.
Registration allocation/sysfs, device scheduling and DSI hardware remain fixtures.
The other regression proves early zero returns-EPERM without DSI traffic even
though the core records requested brightness0 before the callback fails. A zero
property therefore cannot convert that failed command into cleanup success.
The initial fixture compilation warning and its scoped signed-comparison pragma
remain recorded separately from the intentionally failing semantic regression.

## Builds and verification

| Executed check | Result | Seconds |
| --- | --- | ---: |
| Initial production preparation, missing historical archive | FAIL before application | 0.769 |
| Exact base + complete production series + config preparation | PASS | 34.848 |
| Lifecycle, exact source,18 cases and2 mutations | PASS | 1.568 |
| Actual regulator core,8 cases and3 mutations | PASS | 1.167 |
| Two affected ARM64 module builds, W=1/modpost | PASS identical | 6.279 |
|1031-module cohort, depmod -ae and dependency closure | PASS | 0.695 |
| Frozen active host tier | PASS112 tests | 205.851 |

Final active counts: `{"BLOCKED": 0, "FAIL": 0, "NOT_SELECTED": 255, "PASS": 112, "SKIPPED": 0}`;
subchecks `{"SKIPPED": 3}` are separately
declared optional historical replays. These are personally executed host checks,
not previous GitHub CI results. Exact commands, per-test durations/source sections,
JSON/JUnit identities, compiler/linker hashes, build inputs and outputs are in
[qualification](2026-09-20-panel-default-dark-qualification.json).

The first active run stopped on the unchanged fragmented-ack launcher fixture
(exit1); another concurrent test was cancelled by the runner. Its counts were
21PASS/2FAIL/89BLOCKED. One isolated recheck passed in0.691s. The full rerun uses
unchanged source and bounds; retain the initial failure and do not infer a panel
cause or claim that the intermittent launcher failure is fixed.

The historical base.tar had been removed. The first invocation correctly refused
it; the second regenerated an immutable archive from pinned Git and verified the
existing expected archive hash. No archive guard was bypassed. Preparation took
34.848s; olddefconfig matched the retained configuration. Only patch0037 changed
among production preparation inputs. Build owner limits were3GiB/no swap,2CPUs,
256 tasks and600s; preparation peaked at its3GiB limit including file cache.
The active owner used1GiB/no swap,2CPUs and600s. All scratch was disk-backed.

Panel source SHA256 `505b50f072ab073e0e283e819f51a0e97545b39a1e64276285d48933fe922553`.
Module SHA256 `79dc4d21db7726fd939acd10d35ce0f681fee07a847074734485c11008d72994`; 23128bytes;
vermagic `7.1.4-rog5-production SMP preempt mod_unload aarch64`. Dependencies unchanged:
`drm_display_helper,drm_kms_helper`; firmware requirements remain empty.
The twin builds verify every consumed kit input and exported import. The new
cohort verifies all1030 reused module byte hashes and replaces only panel bytes.
Full module metadata SHA256 `e9aeb0e80309076db1c13db4b990cd348a2a5dc3735c228ecf2684981dc5cd30`.
Production-series SHA256 `221640701b918efaa66e4399f396556631ac2eb57d8b0d648a376f19daaae1fd`.
The full cold board build and DT schema tool were NOT RUN again: Image/DT bytes
and producing config/DTS/binding inputs match the prior qualification. Those
results are explicitly inherited; they are not fresh build or phone evidence.

## Controller compatibility and next action

The retained gpu-iommu-display-r1 controller uses a different kernel release,
module hashes and module dependency assumptions. Production DRM_MSM is modular;
its complete closure cannot be replaced by the old REFGEN+panel pair. The old
loader blanks as soon as the backlight entry appears, before attach/prepare can
finish. The corrected driver can return-EPERM; its failure is correct. Default0
removes the automatic light request but does not make that observer compatible.
Do not accept a failed write merely because a subsequent property read is zero.

The source audit also found cleanup() replaces a worker's specific error with
"zero cleanup worker failure". This loses diagnostics while retaining FAIL;
no false physical scanout or darkness PASS was found. Both findings remain
explicitly unresolved in the preserved old controller. No live controller,
sealed input lock, recovery code or historical evidence was modified.

Next is a bounded offline successor-loader regression for early backlight
registration, delayed preparation, failed preparation and cleanup. Preserve
one-use insertion, exact boot/artifact identity, independent cleanup and original
errors. Only then prepare a separately authorized corrected-artifact composition.
The eventual hardware question remains stable60Hz scanout and verified blank;
no Ready request is armed. This fix does not close touch, A660, Denial, S06 or R01.

Changed source: patch0037; AMS678 fixtures stubs.h/cases.c/new backlight-v7.1.4.c;
test-ams678-lifecycle.py; existing test-ams678-panel-patch.sh identity;
configs/mobile/trial-plans.json test pin. Metadata: this report/qualification,
current artifact pointer/inventory, project status/generated current-state,
mobile-trial-plans.md and development-lessons.md. Prior qualification and current
artifact entry are retained in the new receipt; accepted/signed bytes unchanged.

Qualification SHA256 `268676f9d2994be3f4e24aa34df244ab1f9ac542bf3544dfb586bbb99faff730`.

## Final metadata verification

Artifact inventory, generated status and eight mobile-status regressions PASS.
All592 prior inventory rows, historical evidence and acceptance bytes remain
unchanged. The previous current board pointer is preserved in the qualification;
only the current unsigned panel/cohort binding advances. Other artifact pointers
and the historical current-state tail are unchanged. No root or private device
profile was read or changed. All four owning services are terminal; the final
active run peaked at345MiB with zero swap.

- `python3 scripts/host/check-artifact-inventory.py`: PASS, 0.086s.
- `python3 scripts/host/check-mobile-status.py --write`: PASS, 0.040s.
- `python3 scripts/host/check-mobile-status.py`: PASS, 0.040s.
- `python3 -O scripts/host/test-mobile-status.py`: PASS, 0.080s.
- `git diff --check`: PASS, 0.047s.

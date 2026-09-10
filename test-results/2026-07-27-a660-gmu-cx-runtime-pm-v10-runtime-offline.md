# A660 GMU/CX runtime-PM v10 — offline runtime acceptance

Date: 2026-07-27

Result: **PASS offline; HOLD for protected root, host/target controls, and live use**

## Outcome

The v10 runtime layer is now deterministic and mutation-tested. It derives
from the immutable, accepted, and permanently consumed v9 runtime controls,
then changes only the module identity, diagnostic authorization, exact
GMU/linked-CX runtime-PM oracle, suspended-state checks, and v10 evidence.

Two independent generator runs produced byte-identical baseline and probe
scripts. The semantic verifier accepted both and rejected all fourteen
mutations in the fail-first suite.

The phone remained in the persistent Alpine fallback. No candidate kernel
was booted, no module was loaded, no NFS/RPC service was started, no export
was created, and no phone storage was mounted or written.

## Accepted runtime boundary

The generated probe requires:

- a fresh, v10-only attended authorization;
- exact release `7.1.4-rog5-a660reg1`;
- the accepted v10 `msm.ko` as the sole kernel/module delta;
- `gmu_cx_runtime_pm_only=Y` with predecessor diagnostics disabled and every
  diagnostic parameter mode `0400`;
- exact GMU consumer `3d6a000.gmu`;
- exact linked CX supplier `genpd:0:3d6a000.gmu`;
- explicit rejection of GX supplier `genpd:1:3d6a000.gmu`;
- PID-filtered entry and return probes for `__pm_runtime_resume()` and
  `__pm_runtime_suspend()`;
- built-in `rpm_resume` and `rpm_suspend` device-name events;
- exactly one GMU resume/suspend and one linked-CX resume/suspend in the
  diagnostic window;
- signed/zero-extended 32-bit `EUCLEAN` propagation through the GMU, GMU PM,
  Adreno runtime-PM, and outer GPU paths;
- GMU and linked CX back in `suspended` state after settling;
- the accepted logical `4/4` allocation rollback and equal pre/post GEM
  snapshots; and
- zero GX, clock, secure, MMIO, IRQ, firmware-start, HFI, hardware, ZAP/SCM,
  storage, retained-DRM-FD, warning, and fault evidence.

The two SQE/GMU firmware file requests used to prepare software state remain
required and balanced. `firmware_start=0` means the runtime boundary does not
start GMU firmware; it does not incorrectly claim that no firmware files were
requested.

## Test-first chain

| Boundary | Failing test commit | Passing implementation commit |
|---|---|---|
| signed/device-scoped trace oracle | `4b1a4fb` | `aad8d89` |
| deterministic runtime and semantic mutations | `d2cbc8a` | `462d7e9` |

The runtime mutation suite rejects:

1. inherited v9 authorization;
2. enabling the predecessor diagnostic;
3. missing generic runtime-resume tracing;
4. missing generic runtime-suspend tracing;
5. missing built-in RPM resume names;
6. bypassing the trace oracle;
7. substituting GX index 1 for linked CX index 0;
8. allowing GX runtime PM;
9. removing linked-CX suspended-state evidence;
10. removing GEM snapshot equality;
11. accepting a successful open;
12. substituting the predecessor MSM module;
13. changing accepted predecessor state; and
14. making the diagnostic parameter writable.

The trace-oracle suite independently rejects malformed or zero-extended
returns, wrong pointers, wrong device names, wrong ordering, missing
resume/suspend calls, duplicate calls, GX activity, post-boundary work,
failed state transition, and failed rollback.

## Accepted identities

| Input or control | SHA-256 |
|---|---|
| runtime test | `dc34308124bde7b86b573888556151a92a1005c9b7bf8c2e9eb4ac709f83b2f8` |
| runtime builder | `a0bd091b1304581fe41bfcf1ceaa77a84fbbdd606d3797144a1e6685e1179942` |
| runtime verifier | `7141c437962b49a90574dc8e14987fad9d291b5d8ea8b9c3371ebf0c8af187b3` |
| baseline patch | `5732f9b170aa133d00a2eafd7b2fab2c262c1e98765ba05c8a848e3e5b85f674` |
| probe patch | `e8ab58ac1efab6441500532574f34b8fe55734b6c0816b3cc28fc977eb9547e4` |
| generated baseline | `a68960aa1ac84dbc6f3b469d8369d1c66dcd343f9adfc0a9f4e9909e9ee4245d` |
| generated probe | `f28b1c28ec43da21747ce7e17247d33074bfa01f7c9c6171e80806a98eb70b36` |
| trace oracle | `33ccadc6ae1e5f6f12ed83de0ddc192d30d204e229ec1b97aa813e1d0ac9c7e6` |
| trace-oracle test | `ca942002debee58a0437218ba4b49410c2a50d7a5d93a9d6872890a8c565f915` |
| v10 kernel patch | `5eef04eb711443acaaf4295e926577f90073b8ab62414cff3d18de2272d3a152` |
| accepted v10 `msm.ko` | `c36fd352c48d624eff9f17fb8200c8f151209eae066d1f276ab3bff67c5d465d` |
| accepted v9 live report | `57af6b4d0ddf6faaa708e7b409197dcf7aa8fcdb52a5a9612b59094aebc9dd2c` |
| accepted v10 build report | `9ae66678340437c4a38b2d6ee390cc375e661548be97cb108bb8f891a418dee4` |

## Decision and next gate

Runtime controls are accepted offline, but v10 remains **HOLD**.

Before any live review, create and independently verify a fresh
consumed-v9-derived protected root containing the exact v10 module, oracle,
baseline, and probe. Then add a verifier-before-state target gate, nested
transition watchdog, strict one-shot/no-retry host runner, mock tests,
inactive-server proof, and a separate pre-live HOLD review.

No current authorization permits a v10 boot, module load, NFS export, retry,
or flash.

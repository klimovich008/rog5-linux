# Exact production display payload — 2026-09-20

Offline host assembly only. No phone/USB/SSH/VM, module/helper execution,
boot candidate, signing, claim or protected-storage operation. Previous turn's
community check restated unchanged leads; this turn advances actual payload binding.

Start `e39bca95e994c434777937aadac46bb3bbbc9e75`, tree `5e83dcd17a3ca5b21f9cc28843ac2ec5d00bef4a`.
Frozen implementation `9f077c950bd7682da5d4e2f4e153cd5602ca4835`, tree `fc8fa8ab8d37d424fdf4888fd4012c1ecc8eeb3a`.
Linux remains `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`; current board pointer SHA256
`5d168da495a9af5af842f24ad67631c58967f0b5c9bc8a148fab17c507ebd279` is unchanged. Signed/installed identities
were not changed or requalified. No kernel, module, Denial or Flutter rebuild.

## Implemented and verified

The existing module intake correctly verifies an inert archive but does not
supply helper/firmware or bind its generic accepted cohort to the current loader.
The regression executes that intake on five inert ARM64 modules and demonstrates
that it lacks helper/firmware; the new assembler rejects this archive against
the actual14-module loader contract. This is a missing integration boundary,
not a claim that the old intake's documented module-only behavior was incorrect.

The new assembler reads literal contracts from actual loader/firmware source,
records those source hashes and rechecks them before publication. Archive and
activation orders intentionally differ; their exact named path/size/hash inventory
must agree. The output layout matches display-modules/modules/lib/modules/..., 
module-once and firmware/qcom/.... Helper0755 and data0644 are normalized; all
subdirectories are0755 regardless of umask, with a private0700 host container.
Exact upstream firmware LICENSE.qcom, NOTICE.qcom and WHENCE travel with the files.
WHENCE's SM8350 ZAP alias is materialized as exact regular-file bytes.

Inputs are held open and checked for type, size, single link, digest and stable
metadata. Copies are streamed and checked again. Existing outputs are never
replaced. Interruption removes private scratch. Failure after final rename
retains the published directory, reports failure and requires inspection rather
than overwriting or falsely claiming absence. Host publication is not target
root-ownership, firmware search-path/init_task-root, authentication or admission
proof. The artifact has authority=none and all physical/activation fields NOT RUN.

Both real payload copies passed in 0.265s and
0.265s. Each includes14 production modules,
one exact helper, three firmware binaries, three documentation files and the
nested module manifest (22 inventoried members plus the outer manifest).
Both outer manifests SHA256: `3323612cca004abdb08da842ab5823e35009994036b7155d3877a1722c8804d6`.
All member sizes, bytes and modes independently matched the manifests afterward.
Payloads remain private under `rog5-display-payload-20260920-r1/payload-a` and
`payload-b`; no generated binaries were added to Git or active candidate pointers.

## Personally executed checks

| Command | Cases | Wall seconds |
| --- | ---: | ---: |
| `python3 -O scripts/device/test-stage-production-display-payload.py` | 27 | 3.322 |
| `python3 -O scripts/device/test-stage-production-display-modules.py` | 31 | 3.122 |
| `python3 -O scripts/host/test-select-repository-test-tier.py` | 37 | 0.866 |

95 focused cases PASS. Payload27 includes exact source extraction, consumer
mismatch, order difference, duplicate/missing/corrupt inputs, path/link rejection,
copy interruption/mutation, consumer mutation, umask, twin reproducibility,
publication race and failure after inner/final rename. Inert small ELF fixtures
exercise actual intake and publication; real payload twins separately exercise
the production14-module inputs. Neither executes ARM64 code.

One frozen active tier: 127 PASS,0 FAIL,0 BLOCKED,0 SKIPPED,
255 NOT_SELECTED, 247.591s.
Limits1GiB/no swap,2 CPU quota,256 tasks,600s,2 workers and disk scratch.
Service peak664.6MiB,zero swap. These are local results, not GitHub CI.
Optional historical subchecks remain recorded separately.
[Qualification](2026-09-20-production-display-payload-qualification.json)
SHA256 `fbdff1a8da74773f5e13f5d649229e4f8fd6c329c524f240890ca14883e5c98c` includes commands, durations, source and complete member hashes.

## Next integration boundary and Pro consultation

The actual patched session.cohort still accesses T.QUERY, removed by the patched
transport. A direct inert reproduction produced AttributeError before execution.
The existing session fixture stubs cohort; initial reproduction retained that stub
and was corrected to execute the real function. Both logs are retained. This is
host source evidence, not a VM/phone result. Old admission's health dispatcher
also still calls the two-argument API; historical pins and seals remain untouched.

Per the new standing instruction, Oracle CLI browser consultation
`rog5-production-cohort-admission` is pending for this complex source-closure
repair. MCP is not exposed. Requested gpt-6-pro, explicit thinking pro;
Oracle recorded verified Latest selection and 'Thinking time: Pro (already
selected)'. The packet contains exact source/patches, current diff, reproduction,
full error logs and constraints; no credentials or raw phone evidence. No API or
weaker mode used. The local source commit is not pushed, explicitly stated in the
briefing. A proposal must be reviewed and tested before implementation is accepted.

Next: complete production source/admission binding with Pro advice, then qualify
firmware root-transition visibility offline. Physical provider/panel preparation
and a successful zero command remain the smallest later hardware question, only
after full preparation and separate authorization. Scanout/touch/GPU/Denial remain
unqualified; S06/R01 and prior VM failures retain FAIL. Goal remains active.

Changed implementation files:

- `configs/repository-tests.json`
- `scripts/device/stage-production-display-payload.py`
- `scripts/device/test-stage-production-display-payload.py`
- `scripts/host/test-repository-linux.sh`

Metadata and standing-instruction files:

- `AGENTS.md`
- `configs/project-status.json`
- `docs/current-state.md` (generated header only)
- `docs/development-lessons.md`
- `test-results/2026-09-20-production-display-payload.md`
- `test-results/2026-09-20-production-display-payload-qualification.json`

Post-publication validation: mobile-status8 cases PASS; artifact inventory595
sets PASS (large/private byte and physical verification explicitly NOT RUN);
nine baseline/source/historical-body hashes unchanged; git diff --check PASS.
Metadata-only publication does not trigger a second unchanged integrated run.

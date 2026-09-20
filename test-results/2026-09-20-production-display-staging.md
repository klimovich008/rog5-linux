# Production display context and source staging — 2026-09-20

**Offline host qualification only. No phone, SSH, USB, VM, signing, claim,
new candidate, target staging or protected-storage operation.** Previous turn:
progress on full-health/session integration. This turn connects the production
backend to exact source staging and retained identity for worker/cleanup paths.

Start `c4f595e0d18f53f643726f258859dab1e38b26e1`, tree `98997e05bf5791011587db2a6602b41751e83b3e`.
Frozen implementation `b818a13d4f1291822076a52f9e0c063e1ee8a47e`, tree `3e3f855451b9a34b61c979b29dc48949b2c699f5`.
Linux remains `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`. Board pointer SHA256 remains
`5d168da495a9af5af842f24ad67631c58967f0b5c9bc8a148fab17c507ebd279`. No kernel, DT, module, Denial or Flutter rebuild.
Signed candidate and installed phone identities have not changed through this work.

## Implemented boundary

The old backend requires nine historical Python files and the separate GPU query.
A production manifest with the six-field artifact identity fails its initial
context predicate; the retained negative control reproduces this incompatibility.
The successor accepts exactly backend, component and four pinned dependencies.
The composed backend SHA256 is `e8354b4591d5110224ed5bd4579a82995071d7c98c846567dd387396e2a1a098`.
No DRM query, separate provider run or hardware operation is added by staging.

Initial context preserves root, RAM/tmpfs, namespace, ownership and all existing
consumed-entry barriers. The reusable binding check verifies canonical manifest
bytes, six source hashes and artifact identity. Worker/result/cleanup paths carry
that retained binding and revalidate it without rerunning initial entry-absence
checks. Cleanup can still instantiate verified code after entry consumption;
a new attempt cannot. Checked component bytes execute directly; dependencies
retain their existing checked-byte readers. Actual endpoint identity is observed
when requested, not fabricated from the manifest.

The source-only stager checks the fixed source/manifest data, RAM parent and
endpoint identity before creating its exclusive namespace. It fsyncs files and
validates context and identity again afterward. The host adapter reserves40
seconds for the35-second command plus forced closure. Existing worker/SSH
credential and source-authority checks remain. Host receipt comparison preserves
JSON types, so integer0 cannot substitute for boolean false. The enclosing session
supplies its production contract and retains ownership of its evidence directory.

The request contains no modules/helper/firmware. These remain separately required
payload inputs, checked before one-use insertion by the loader. Base64 of the
3,010,560-byte module archive exceeds the3MiB worker bound; the limit was not
expanded. The generated source script is118663
bytes; its synthetic-authority fixture request is118910
bytes. A complete private source/admission closure has not been issued.

## Failing-before and passing-after evidence

Two regressions exposed draft staging cleanup defects: KeyboardInterrupt after
opening a file but before obtaining its metadata leaked the FD, and failure to
open the newly created directory left that owned empty directory behind. Both
failed before correction and now pass. Close protection starts immediately after
open; failed metadata acquisition can recover identity from the still-held FD
and matching name. Cleanup removes only recorded matching inodes and preserves
the original exception. A replaced file is retained, not deleted. SIGKILL/crash
recovery and adversarial privileged mutation are not qualified by these fixtures.

The first host-adapter fixture omitted the evidence directory already created
by the real session. Inspection disproved a proposed production bug; the fixture
was corrected and the caller-owned API retained. A nested ownership fixture also
needed to expose original stat attributes. These were fixture defects, not phone
or kernel failures. The source-context and cleanup negative-control logs are
retained separately; no historical evidence was rewritten.

## Personally executed checks

| Command | Cases | Wall seconds |
| --- | ---: | ---: |
| `python3 -O scripts/device/test-production-display-context.py` | 22 | 0.701 |
| `python3 -O scripts/device/test-production-display-supervisor.py` | 31 | 3.391 |
| `python3 -O scripts/device/test-production-display-transport.py` | 23 | 6.315 |
| `python3 -O scripts/device/test-production-display-session.py` | 28 | 4.367 |
| `python3 -O scripts/device/test-production-kernel-log.py` | 25 | 3.244 |
| `python3 -O scripts/host/test-select-repository-test-tier.py` | 37 | 0.795 |

**166 focused cases PASS.** The22 context/staging cases execute real filesystem
operations, source hashing/import, generated program and host receipt validation,
with explicit root/proc/tmpfs/transport substitutions. They cover source/manifest
mutation, hardlinks, symlinks, unsafe modes, extra/stale files, wrong identity,
consumed entries, non-RAM refusal before writing, repeated publication refusal,
interruption and preservation of replaced files. No actual /run path or device
is touched. Existing real pipe/child supervisor, transport, session and logger
fixtures now use the new backend; hardware callbacks remain inert. They do not
prove target execution, physical cleanup or firmware authentication.

Frozen `scripts/host/test-repository-linux.sh active` ran once:
**126 PASS,0 FAIL,0 BLOCKED,0 SKIPPED suites**;
255 NOT_SELECTED, 222.286 seconds.
Optional historical subchecks remain explicit. Limits:1GiB,zero swap,two CPU
quota,256 tasks,600 seconds,two workers and disk scratch. These are local results,
not imported GitHub CI. [Qualification](2026-09-20-production-display-staging-qualification.json)
SHA256 `256b6a671f6070c69c7f4fee63b008dfc482ece543c3b67e821976ec44472407` includes commands, per-test times and source/log identities.
Private evidence: `rog5-display-context-20260920-r1` under host state.

## Remaining work

The historical private SOURCE/admission and health seals remain unchanged.
No live cohort or execution authority is granted. Next: complete exact private
health/admission closure and the existing module/helper/firmware payload bindings,
including firmware root-transition lifetime. This source-stage success does not
establish that the modules/firmware are present on an installed phone.

After those prerequisites and separate physical authorization, the smallest
hardware question remains whether the exact provider/panel path prepares and
accepts a zero command. Scanout, calibrated touch, GPU rendering and native
Denial session qualification remain separate. Physical **NOT RUN**, S06/R01 and
prior Denial VM failures **FAIL**. No Ready requested. Goal remains active.

Changed implementation files:

- `configs/repository-tests.json`
- `patches/display-controller/0004-production-session.patch`
- `patches/display-controller/0007-production-context.patch`
- `patches/display-controller/0008-production-staging.patch`
- `patches/display-controller/README.md`
- `scripts/device/test-production-display-context.py`
- `scripts/device/test-production-display-supervisor.py`
- `scripts/device/test-production-display-transport.py`
- `scripts/device/test-production-display-session.py`
- `scripts/host/test-repository-linux.sh`

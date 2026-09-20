# Production display source-cohort repair,2026-09-20

Status: **PASS offline source binding**; private runnable session **UNBOUND**.
Physical tests **NOT RUN**. HistoricalS06/R01 and Denial VM failures remainFAIL.
Qualification: [machine-readable evidence](2026-09-20-production-display-cohort-qualification.json).

## Source identity and change

Starting HEADd22cdc9d1738acde491589e4ed5372aa0181194e. The implementation tested
below is `e9534b65d1fd35473f276cd02c8f7862dc09a163`, tree`f4139e69ab35a51c69ced159edaaeeb67cf46196`.
The intervening e8fc50f5 checkpoint records adviser delivery failures; it does not
claim a source repair. No history was rewritten and no changes were pushed.

The actual preceding session.cohort requires T.QUERY/T.B.QUERY_SHA after the
successor removes them. It also imports private dependencies before checking
its source inventory. The regression executes that exact preceding function
with the real successor transport/backend and observes AttributeError:QUERY.

Patch0009 validates ten exact source files against an externally authenticated
source projection before loading dependencies, retains the checked bytes and
executes those bytes without reopening through importlib/pyc. Subsequent calls,
including cached modules, recheck file identity, metadata, hashes and lock.
The nine non-self pins are compiled into session; its own hash remains external.
Transport, health and logger imports are inert and bind dependencies explicitly.
Old provider/query dependencies are removed. The six target-staged sources,
embedded stager, supervisor and reviewed cleanup/recovery ASTs remain unchanged.

An old unscoped lock cannot acquire new authority. Current private inputs()
enforces an exact format/files schema and must receive a separately reviewed
successor producer; raw duplicate-key decoding remains outside the fixture.
Unknown private worker initialization refuses before session output or entry.
This is a source-only successor, not a deployable session or admitted candidate.

Changed implementation files:

- patches/display-controller/0009-production-session-source-binding.patch
- scripts/device/test-production-display-cohort.py
- configs/repository-tests.json
- scripts/host/test-repository-linux.sh

## Adviser and executor evidence

Oracle MCP was unavailable; installed CLI used browser/gpt-6-pro/thinking pro.
The original recorded Pro selection and the follow-up's visible6Pro/loggedPro
were verified. No paid API or weaker mode. The41m30s review returned patch/ZIP
links that failed404. Same-conversation follow-up returned the exact diff inline
in12m08s;55620bytes/841lines SHA256
`6c438eab7dee2755585842f8143b8f1f3805760e093e5a2afb668f27b946563b`.
It applied normally; no historical patches needed recount.

The executor reviewed the source and ran the proposed32 cases successfully
(2.672s wall), then removed packet-recount support,
strengthened the pyc case with valid timestamp/size bytecode that the old path
loader actually executes, and added cached-module revalidation coverage after
an independent read-only review. The production patch remains byte-identical to
Pro's supplied patch; test improvements are local and independently executed.

Final focused commands/results:

- `python3 -O scripts/device/test-production-display-cohort.py`:32 cases PASS,
  2.570s wall before the extra cached-module case.
- `python3 -O scripts/device/test-production-display-cohort.py Cohort.test_cached_module_still_revalidates_the_whole_cohort`:
  1 case PASS,0.365s. Final frozen suite contains33 cases.
- `python3 -O scripts/host/test-select-repository-test-tier.py`:37 cases PASS,
  0.816s.
- `scripts/host/test-repository-linux.sh active`: 128 suites PASS,
  226.376s;0FAIL/0BLOCKED/0mandatorySKIPPED,
  255NOT_SELECTED. Final33-case cohort runs here.

The integrated tier ran once on the clean frozen implementation with1GiB RAM,
no swap,2CPU quota,256tasks,600s deadline,2workers and disk-backed scratch.
Three declared optional historical artifact replays were SKIPPED and remain
explicit in JSON/JUnit; no installed/hardware inference. Exact archive charging,
retained ARM trial-state replay and ARM rail-reader replay were not requested.
All source-dependent sections of the new cohort suite ran with strict application.
No kernel, Rust, Flutter, module or firmware rebuild was needed.

## Remaining boundaries and next work

Actual private bootstrap, worker, capture-common, health producers and their
transitive source/command-policy closure still need review. The old private
health dispatcher uses the obsolete two-argument API; its future correction must
use the same contract/owner and exact script bytes as execution. Historical
SOURCE, private seals, signed fallback and consumed records remain untouched.

The firmware-root packet contains40 exact excerpts and75 verified Alpine input
identities. Partial whole-tree reconstruction failed an unrelated awk.tests
hunk after36 clean patches; switch_root and relevant helper closure are available.
Both Oracle upload attempts failed before submission; no firmware fix or kernel
request qualification is claimed. Keep caller/PID1 agreement separate from
init_task.fs lifetime and source analysis separate from VM/phone evidence.

Next authorized work is offline review/testing of that private closure and
firmware-root visibility. The later hardware question remains a bounded provider
and panel preparation with a verified zero-brightness command and clean shutdown;
prepare every prerequisite and obtain applicable authorization before any phone
action. No Ready is pending. No phone, USB, SSH, VM, protected-storage mutation,
signing, candidate publication or claim issuance/consumption occurred.

Post-publication validation: generated status PASS0.043s; optimized mobile-status
8 cases PASS0.086s; inventory595sets/68small hashes PASS (large/private bytes,
admission and physical verification NOT RUN); git diff --check PASS. Integrated
peak memory831.1MiB,0swap. Headless/mobile contracts, current artifact pointer
and historical current-state body hashes match the preceding checkpoint.

Metadata files changed across this repair: configs/project-status.json,
docs/current-state.md (generated header only), docs/development-lessons.md,
test-results/2026-09-20-production-display-payload.md (earlier delivery checkpoint),
and this report with its sibling qualification JSON. Private checkpoint-end/end
records retain final commit/tree without introducing a tracked self-hash cycle.


## Next-boundary source counterexamples (2026-09-20 continuation)

Starting checkout409e5f4d was clean. Exact private source excerpts were selected
without importing their modules, and original source/excerpt hashes revalidated.
The offline reproduction evaluates the actual retained health/launcher call
expressions against actual successor function definitions. Argument binding
fails before either function body can execute: health lacks contract/owner;
session lacks contract. The launcher's pure result expression also maps a
PASS_PRODUCTION_DISPLAY_SESSION to FAIL. The actual old inputs() schema refuses
the new production_display_sources field using an explicitly synthetic receipt.
These four mismatches are confirmed; no fix or new admission is claimed.

The actual action-callbacks JSON helpers reject top-level and nested duplicate
keys and explicit NaN, and accept ordinary valid JSON. Those four checks pass;
a duplicate-key decoder rewrite is unnecessary. Default float overflow behavior
is not qualified by these checks.

[Counterexample receipt](2026-09-20-private-admission-counterexamples.json) records
source/reproduction/log hashes and exact exception messages. Private source,
code excerpts and full tracebacks remain under rog5-display-private-admission-20260920-r1.
No private profile values, credentials or device evidence were published.

Firmware review delivery recovered using Oracle's documented inline-files mode,
with all40 verified source excerpts and existing verifier tests supplied directly.
The reduced packet omits repeated unrelated download metadata, preserving full
source hashes and reconstruction limitations. Session rog5-firmware-root-inline
records promptSubmitted=true, selectedgpt-6-pro/Latest and loggedPro thinking;
the bound tab independently shows6Pro and a live response. The consultation is
running, not completed or qualified. Retain and poll its existing handle56228.
Do not repeat the two failed pre-submission upload attempts or restart this live
consultation because an observation times out. No implementation depends on an
unreceived answer. No new builds/integrated tests, VM, phone or protected-storage
operation occurred in this continuation.

Continuation metadata validation: generated status PASS0.041s, optimized status
8 cases PASS0.110s, git diff --check PASS. Headless/mobile contracts, current
artifact pointer and historical status body hashes are unchanged. The prior
128-suite result is retained for its frozen implementation, not rerun or relabeled.


### Firmware-root adviser result and executor verification

Oracle session `rog5-firmware-root-inline` completed in verified browser6Pro/Pro;
CLI exit0. No production firmware/kernel/initramfs change was justified. In the
supplied code normal exec does not automatically split `fs_struct`; successful
BusyBox chroot updates the init-task root if sharing persists until that point.
A prior split changes this outcome; a later split initially copies the same root.
Moving `/run` last does not establish uninterrupted lookup during the handoff.

The executor verified the two delivered test-file hashes, reviewed their inert
adapters, then ran the actual source extracts against the pinned Linux, verified
BusyBox source and current repository:12 C cases and23 shell ordering/rollback
cases PASS under Python -O in0.206s. Two local mutations, caller-root lookup and
missing root assignment, were rejected in0.675s and0.625s. These are actual-function
control-flow/root-argument tests, not a VFS model or physical firmware evidence.
Exact commands, hashes, outputs for negative controls and scope are in
[the qualification receipt](2026-09-20-firmware-root-source-qualification.json).
The source fixture and full Pro answer remain in private disk-backed evidence.

Full startup/wrapper/successor and future mount/payload lifetime remain unqualified.
No real mount/chroot, firmware request, VM or phone run occurred. Existing128-test
source qualification is unchanged and was not repeated. Historical health seal
02e007b5 remains untouched and correctly fails the successor configuration's target
identity guard; a source-only optimized-Python reproduction passed in0.0044s.
Runtime briefing now includes11 sanitized attachments and242 original/extracted
mappings, with path-sensitive transitive omissions stated explicitly. No new
seal, input lock, admission or claim was issued.

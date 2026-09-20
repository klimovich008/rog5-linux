# Stage-triggered close capture preparation — 2026-09-20

Offline host fixtures and a small generic ARM64 API guest only. No phone access,
sudo, signing, candidate, admission, claims or protected-storage mutation.
Physical rows remain NOT RUN; accepted rescue/server and S06/R01 FAIL remain.

Starting source `2a3ff7f617f581ecc1afb8e9c81fdd29499502b1`, tree
`dc54d9290816d10999492a2068bb49f859c192a8`. Frozen implementation
`0e39b4d6f1639cd208e09134923c98785e109adb`, tree
`e983687c7eac485d836d6c074a7daedf9bbcd62c`. Publication metadata follows it.

## Executable change

The prior no-unref control still failed Mousepad close, and its PC snapshot
preceded SHUTDOWN_BEFORE by0.815s. Repeating that early capture would not locate
the later unfinished phase. The explicit `--app-close-after-sync` option now
builds a separate `close_stage` mode, requiring `--app-close-ptrace` and the
existing close-only/diagnostic prerequisites. Default sampling remains available.

The launcher passes its already owned lifecycle-log path as a fifth argument;
legacy four-identity invocations remain accepted by default builds. The helper
is still launched asynchronously before TERM. Its stage mode waits for ordered,
same-PID loaded/APP_RUN_BEGIN/SHUTDOWN_BEFORE/BEGIN/END records. Later lifecycle
completion, unknown/out-of-order/duplicate records, changed identity, missing
log or expired deadline refuse capture. Partial final records never authorize it.

The new `app-close-stage.rs` pins a regular0600, single-link, same-UID descriptor
and path inode/device. Reads are limited to1536bytes, use pread, reject observed
truncation/rewrite, and recheck metadata. Concurrent append yields Waiting.
This is a cooperative diagnostic observation, not authentication against a
malicious writer or proof of an atomic process snapshot.

The waiter shares the original1200ms total helper budget; it does not reset
that timer at END. The outer2s timeout and application2s kill grace remain.
Marker/deadline/process checks repeat before ptrace attachment, while stopped,
after detach and before result publication. The existing single-stop, signal,
stack, output and cleanup protections remain. Stage mode omits the periodic
proc rounds and reserves its bounded snapshot output. Failure remains explicit
NOT_RUN/unavailable, not a successful observation.

Files changed: `app-close-probe.rs`, new `app-close-stage.rs`, `logind-apps.sh`,
`test-qemu-logind.py`, their three host test files, and `repository-tests.json`.
The manifest now lists `cc` and both stack/stage source prerequisites. Its host
probe-suite deadline is30s to accommodate the added compiler configurations;
this is separate from every guest capture/application deadline.

## Regressions and preparation failures

The runner-option and launcher-log-argument regressions fail against the prior
implementation; the stage-reader stub fails seven tests. Corrected reader tests
exercise real files, append/partial writes, symlinks/FIFO, permissions, hardlinks,
replacement, truncation, rewrite, record limits and both DSO completion variants.
The integrated production path also uses a real owned child to test successful
capture, completed-log refusal, wrong start identity, and cancellation after
attachment with verified detach. Wait-order/deadline tests use a bounded clock
seam rather than delaying the test process for every missing marker.

Initial stage-only compilation exposed unused/default-only code under warnings
as errors; the conditional declarations were corrected. A source review caught
an ARM64 open-flag error: the exact pinned kernel overrides O_NOFOLLOW to0100000,
where x86-64 uses0400000. The original metadata checks could mask this wrong
constant. The new direct-open test deliberately restores the old ARM64 value
and fails because opening the symlink succeeds; the corrected ARM64 binary
rejects it with ELOOP. These are actual user-emulated syscall checks, not a
constant-marker-only validator. Initial sources/logs remain retained.

A private test wrapper also applied its8MiB log-oriented RLIMIT_FSIZE to compiler
outputs; rust-lld stopped with SIGXFSZ while linking a host test executable.
The replacement private runner bounds log size and process-group lifetime
without imposing that log cap on generated binaries. Compiler containers remain
512MiB/no-swap,one CPU,network disabled. No storage cleanup or global limit change.

Focused final host checks pass: three Python probe wrappers (18 ordinary,
24 stack-enabled,36 stage-enabled and six standalone stack case executions),
17 runner-preflight cases, and47 launcher/cleanup cases. Configurations overlap;
these are not84 distinct Rust functions. The command durations are11.935s,
0.803s and33.906s respectively. Four ARM64 builds pass (reader tests, deliberate
old-flag test, integrated stage tests and release helper). ARM64 user emulation
passes11 reader cases, the wait-order case, and the expected release-host refusal.
The deliberate old-flag mutation fails with exit101 as expected. Exact commands,
outputs and durations are retained in the qualification record.

Read-only review found no implementation blocker. The previous END arrived
roughly1205ms after its first sampler clock, so this bounded mode may legitimately
refuse a late marker. Neither that refusal nor host/API success is evidence that
the failed UI interval has been captured. Do not raise grace to force a result.


## Frozen integrated and API guest results

The active tier passed112 suites in201.934197s:0FAIL,0BLOCKED,0SKIPPED,
255NOT_SELECTED. Three explicitly optional historical subchecks were SKIPPED.
The small exact-kernel ARM64 guest passed13 cases (11 marker-reader, one
wait-order/deadline and one actual owned-child ptrace/cancellation/detach case)
in3.031755s including harness preparation. Normal guest poweroff passed, input
identities remained unchanged, and no owned container remained. The guest ran
as UID1000 with network disabled and no host GPU exposure. It did not run Denial.
The stage release helper SHA-256 is
`dc18bd3c4cc08988a331087dc35e9ede92e0222f188593ba5c08a8e55fadad60`.
The API test executable SHA-256 is
`36ce7d6101d96f777dfb5a9ea41085cdbf4c8dd62f65476edf51758e040937c5`.

Exact commands, individual durations, input/output hashes and logs are bound by
[qualification JSON](2026-09-20-close-stage-preparation-qualification.json).
Historical580 artifact rows and both acceptance contracts remain unchanged;
the new set is a fixture with no admission authority. The next smallest VM
experiment is one stage-triggered no-unref close observation; missing/late
markers must remain NOT RUN. A full UI run and all physical rows are NOT RUN
for this change. Prior Mousepad137 and unmount failures remain unresolved.

The requested upstream/community recheck confirmed live Denial main
`cd84b8b72f21024edc3da33d5f3c8dbe9ce44985` and dev
`5ab4004a36df28799b5f0636ee0cf31d1eba8c31`, unchanged from the
[existing source audit](2026-09-19-upstream-denial-community-audit.md).
The exact main selector still substitutes Linear without renderer membership.
SM8350 board references, Hotdog sensor readiness, wvkbd interoperability and
Pocketblue mobile Firefox remain useful leads; no external code was imported.
No phone operation, new candidate, signing or protected-storage mutation occurred.

# Authenticated VM font preparation and OSK evidence

Scope: generic ARM64 VirGL VM and isolated ARM64 Fontconfig processes. Phone
operations, protected storage, signing, admission and claims: NONE. Physical
mobile rows remain NOT RUN; historical headless S06/R01 FAIL remain unchanged.
No new phone candidate, kernel, Denial, Flutter or runtime-package build.

Start: source87bafd26fe93656780f4995f6ed06072a4ea7225,
tree8841a4743c0497a0e5122307f6f1fd2e48369a00, clean review checkout.
First VM sourcebe1c763a5811944468113d49207bc1293d9ad9d4,
treed2b57ae532f9e1e4b80b3cc5545b7ba91c674ece.
Second VM source723c1b5bca2c86763af882b4562a0e63caed46d8,
tree2452d9341165f48d6590b867a118dabb889708c4.

The extracted package closure omitted two different Fontconfig post-transaction
steps: default configuration links and caches. Cache-only preparation left
`/etc/fonts/conf.d` with just README. The actual retained package hook creates25
links from `conf.default`; applying it only to an isolated private copy changed
the actual ARM64 `fc-match sans` from Adwaita Mono to Noto Sans. Source fonts,
directory timestamps, package bytes and the fixed VM clock remain unchanged.

The guarded VM RAM preparer now runs the exact packaged configuration hook,
preserves valid existing files/links, refuses dangling conflicts and verifies
new link targets. It runs `fc-cache -s -v`, then mobile-UID1000 `fc-conflist` and
`fc-match`. Processing records must identify every default; actual cache-load
records must match each retained cache and source-directory checksum. Cache
hash/inode/time inventories must remain identical and neither per-user fallback
cache directory may appear. Commands and diagnostics have independent bounds.
No host-generated cache is transplanted into the VM.

User-mode ARM64 measurement: cold `fc-cache -v`0.816s, warm0.215s;
`fc-match sans` with empty read-only cache0.816s and6 fallback files, prepared
read-only cache0.164s and0 fallback files. These are isolated process measurements,
not GTK guest startup or phone timings. Fontconfig initialization can create a
cache before its verbose scan prints valid; verbose output alone is insufficient.
The upstream2.18.3 tag source review is qualified separately from the exact
2:2.18.3-2 packaged binaries; the package patch correspondence was not rebuilt.
Future-directory warnings alone do not prove cache invalidation.

First VM: whole-session FAIL in240.024s (239.962s runner). Cache preparation8s,
mobile-user consumption1s, service start19s against20s. Exact12 OSK press/release
events PASS. Original captures were inspected: Mousepad visibly showed
`test → tes → test`. Foot and Mousepad exited0; the launcher exited143 following
owned TERM; PAM/session removal, all-filesystem unmount and normal poweroff
were observed. Overall qualification remains FAIL because terminal rendering
counters were absent from the bounded retained log. Visual success does not
replace that missing evidence.

The previous drainer retained only the first1MiB while consuming later output.
Executable regressions show that terminal counters, duplicate summaries and
all rendering-error strings consumed by the real host parser can be lost after
that cap. The corrected Denial reader retains its ordinary prefix plus a separate
64KiB terminal/error reserve across the entire stream. Reserve overflow returns42
while still draining the producer. Complete retained lines prevent splicing a
truncated trace into a terminal record. Other client/protocol limits are preserved.
The frozen regression set fails before the correction (3failed tests plus8error
subcases) and passes afterward (5tests1.097s); log and cleanup cases together
PASS10tests1.190s. Fontconfig focused cases PASS22tests1.374s.

Second VM: whole-session FAIL in211.321s (211.259s runner). Packaged defaults
restored4s; cache preparation10s; mobile-user config processing1s and cache
consumption2s, matched Noto Sans. Nevertheless service-start returned124 at20s;
no apps or OSK actions ran. Cleanup retained the session-child failure, removed
the PAM/logind session and powered off normally. An earlier /var-unmount failure
message remains recorded even though final shutdown unmounted all filesystems.
Missing font preparation is not a sufficient explanation of recurring startup
timeouts. No unchanged successor was launched.

Independent host review found an ANSI-normalization mismatch in the new log
projection: a styled error could be omitted although the actual host parser
would reject it. One failing test with9subcases demonstrated it. Final source
c986307a6c88cbb09bf236ca7083b5b1dc9461fa,
tree04e5dfc71ebe61f5d989bc9664c66ec638fe1211, normalizes the predicate like that
parser. All11 log/lifecycle cases PASS2.095s. This post-VM correction was not
rerun in a VM; the second VM remains bound to723c1b5b. The existing parser also
accepts an unterminated summary whose final positive count was truncated; that
host-fixture limitation remains open and was not observed in either VM result.

The kernel remains generic Linux7.1.4+ at pinned Linux
7a5cef0db4795d9d453a12e0f61b5b7634fc4d40, built-in FUSE and virtual DRM/input:
Image SHA2562b1c8d95f54dda28e772df82be54af7508b2ce84183f1b0024a7f14e3d5ce0fc;
config23af1f7083bb5607f65904ab6d46a101c5d67fd73a6ae10dd868877db16870af.
Denial SHA25640b1fc631643d602b57db2b988eb2caf8839e1e044890f7c9aa4ad0555bb8af0;
unsigned session archive1ff417307c96bac90977b64a143e1a81b535d94a03109ca967c40e9b1f269d0c.
These are retained VM inputs, separate from installed phone bytes. The full
commands, per-step times, source/tree and input/output identities are in the
[qualification JSON](2026-09-13-font-cache-qualification.json). Raw logs and
captures remain private. Existing source review of the modifier defect is already
incorporated in the retained Denial patch/tests; this run does not reopen that
resolved selector/pool/allocation boundary or turn it into phone GPU evidence.

Final frozen active tier:99 PASS,0 FAIL/BLOCKED/SKIPPED and255 NOT_SELECTED,
148.848s,399.7MiB peak memory and0swap. Three declared optional subchecks are
SKIPPED. This was one active-tier execution on c986307a after source fixes; no
GitHub CI or phone board rebuild is claimed. JSON/JUnit and every suite log are
retained privately and hashed in the qualification. Per-suite results remain
separate from the two overall failed VM qualifications.

This is progress toward a native mobile session; the phone goal remains active.
Next: inspect per-unit service activation and dependency timing under the retained
CPU quota before preparing another bounded VM. Retained journal starts at-spi
at2:44 and GTK/document/desktop at2:46; ready records are2:49,2:52,3:02 and3:03,
with cleanup3:04. All four units use Type=dbus: Started records BusName
acquisition. GTK used6.571CPU/18.485wall seconds. These second-resolution records
suggest little margin but cannot order exact readiness against timeout; capture
monotonic per-unit transitions and CLI completion next. The current20-second aggregate
limit has little measured margin and cache correction did not eliminate failure;
neither a specific service bug nor a justified new limit is established yet.
The next unresolved hardware question remains actual scanout/touch/GPU under the
existing prepared exact-artifact process, outside this task’s authorization.

Publication checks: metadata regressions5 PASS0.929s; mobile status regressions
8 PASS0.021s; inventory PASS523sets/827registered/177tracked files,68small hashes
checked; generated status and whitespace PASS. Large/private verification,
admission and physical qualification are outside that inventory check. Separate
comparisons preserve all prior522sets, every unrelated current pointer, both
acceptance contracts and the historical current-state body. Both VMs' owned
containers were reaped. Free host disk remained3,346,391,040bytes, above3GiB.
Qualification SHA256:
`87083738d2038f9723f3b974af3ef4bb6cb2a67c4a4e08b0275770aa224a4510`.

Changed files relative to the starting source:

- `configs/project-status.json`
- `configs/repository-tests.json`
- `docs/current-state.md`
- `docs/development-lessons.md`
- `docs/development.md`
- `manifests/artifact-sets.json`
- `manifests/current-artifact.json`
- `scripts/host/test-logind-font-cache.py`
- `scripts/host/test-qemu-logind-runner.py`
- `scripts/host/test-qemu-logind.py`
- `scripts/host/test-repository-linux.sh`
- `test-results/2026-09-13-font-cache-qualification.json`
- `test-results/2026-09-13-font-cache.md`
- `tools/qemu-virtio-drm/logind-denial-prepare.sh`
- `tools/qemu-virtio-drm/logind-denial.sh`
- `tools/qemu-virtio-drm/logind-font-cache.sh`

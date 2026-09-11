# ROG5 current state

Updated 2026-09-10: **Denial Wayland is now the active long-term destination**.
The user has reprioritized **kernel and non-cellular hardware bring-up first**.
Defer Denial/Flutter builds while qualifying the kernel: stable boot and recovery,
OLED scanout, front touch, Adreno with minimal DRM/EGL tests, and power management.
Track Wi-Fi, audio, Bluetooth, sensors and cameras explicitly; do not call the
kernel fully working while required hardware remains unqualified. Denial remains
the eventual application layer. Prepare hardware trials completely before Ready.
After each run and goal turn, review priorities, repeated failures and measured
bottlenecks using the [feedback loop](development.md#feedback-after-each-run).
The exact successor kernel is now running on the phone: release
`7.1.4-g05941d04803f`, bundle `kernel-hw-05941-a607a2bb249c918b`, boot
`de90d177-3532-49e0-9bfd-8f8c65889a8d`. Fresh Ready immediately launched the
prepared trial and local touch authentication succeeded. Exactly one 128-MiB
RAM boot completed; the one-use claim is consumed. No partition was flashed.

The full 23-minute physical capture PASSed, including ordered route/firewall/
profile/address cleanup and worker reap. Independent authenticated target health
PASSed at 108.19 s and again after terminal cleanup at 1,383.39 s on the same
boot. Healthy commit was 64.957 s; boot-bound readiness and physical/storage/power
guards passed. No later USB transition was recorded after target enumeration.
These are real headless-kernel observations; OLED/touch/GPU remain unqualified.

The automated controller result is **FAIL** and must stay FAIL. Its initial
health query encountered the still-enumerated fastboot device immediately after
RAM transfer. It failed before waiting for the new USB gadget. Later fallback
location hit a separate host adapter error: unpacking three values from the
network helper's two-value return. That error preceded network ownership or any
fallback SSH command. Old selection eligibility was **not restored during that trial**. The separate
r45 recovery below restores it without changing the original FAIL result. The signed installed fallback was not
modified, but this run did not physically qualify fallback boot/restoration.

The host fixes are now integrated in `successor-live-driver-r1`, with the exact
executed sources archived at `post-trial-driver-fixes-r1/executed-sources` before
editing. The two-value adapter defect also existed in `ssh-worker.py`; its tests
now call the real network adapter with only the subprocess result simulated.
A negative replay reproduced that sibling failure. Final affected regression
checks pass **63 cases in 53.078 s**, including four complete simulated flows.
The earlier integrated transition/route checks passed 32/25 cases. These are
host checks, not a second phone boot or qualification of automatic recovery.

Regression fixtures now tolerate retained terminal execution and consumed claims
without changing production guards. The actual 30-file input lock passes in
0.104 s; the old launcher refuses `trial was already attempted`. Its old live
qualification remains byte-identical, historical and stale for the new sources.
Do not rerun the consumed trial or treat these changes as a new admission.

The separate exact-current-boot recovery now **PASSes on the phone**. In
**7.656 s**, authenticated preflight, RAM staging, one atomic state exchange,
read-only restoration observation and final full health all passed. The original
V9 healthy selection SHA `ed3a62d1…` is restored; the running kernel/boot identity
above is unchanged. Final observed uptime was **3,548.72 s**. This is restored
next-boot eligibility, not a physical fallback boot or a repaired R01/S06 result.

The private `current-target-restore-r1` coordinator is terminal and one-use.
Preserve its `execution-r1`, original custody, RAM entry/completion, and durable
`.kernel-05941-transition` records. That transaction now retains the new healthy
record in `exchange` and the old backup in `old-backup`. Do not rerun restoration,
remove entries or reuse the consumed kernel trial. The old V9/V11 wrapper remains
unchanged. Subsequent read-only checks must use the separate `restored-health.py`
predicate: the original target predicate correctly requires the now-replaced
new selection and will refuse the restored one.

Preparation passed 17 real-ARM64-helper/guard cases (194.746 s summed case times),
11 restored-health cases and nine host ordering/output cases. Hardware telemetry,
systemd and tmpfs are explicit offline fixtures; the final SSH results supply
physical evidence. A fixture-only attempt to edit a read-only custody file
stopped the first batch; its result was retained and only remaining cases resumed.

The OLED successor payload is now composed as byte-identical twins under
`oled-successor-payload-r1`: **4.877/4.625 s** in sequential 512-MiB/no-swap
scopes. Bundle `oled-05941-a2be906cd7b36636`, trial
`b52ead05459f96ae5acde920c903d4ca3138a96083a7b4dbabfc941274fcb242`, archive
SHA `d108d868…`, 57,774,563 bytes. It changes only the descriptor and catalog;
**722 of 724 members**, all 32 loose module copies and the nested radio archive
are preserved. Ten focused real-newc preservation tests pass in 0.026 s.
Pair with the retained display-only DT `2ee1ed4b…`; do not rebuild the kernel or
matching REFGEN/panel modules. The signed wrapper completion below supersedes unsigned packaging status;
the new OLED profile remains unregistered, with no boot admission.

Fresh read-only phone health passes at **4,347.54 s uptime** on the same boot
with old selection still restored. The 2.045-second probe verifies both exact
display modules under `/run/rog5-native-wifi/display-trial`, unloaded, with no
current-release files in the standard `/usr/lib/modules` search tree, no DRM
nodes or backlight, and no fb0. This describes the current headless runtime;
new-DT early probing and future effective-root autoload still require checks.

OLED signed bundle and boot-wrapper twins now **PASS** in
`oled-boot-package-r2`, using the exact new identity above. Both wrappers are
134,217,728 bytes, SHA `08922813…`; raw size 129,966,080 bytes requires the
128-MiB envelope. Bundle signature, both AVB integrity checks and the sealed
verifier pass. Manifest SHA `95d0748d…`, recovery SHA `b9099828…`. All 18 stages
completed without cleanup errors. These are offline artifact checks, not a boot
admission or physical display result. Do not rebuild these successful twins.

The first attempt, `oled-boot-package-r1`, is terminal **FAIL: cgroup OOM**.
Both signature receipts survived; the second wrapper is partial. Preserve all
entered output. Kernel evidence shows 503,865,344 dirty file-cache bytes at the
512-MiB cap; this was a local packaging limit, not system-wide exhaustion.
The unchanged runner and exact inputs succeeded in a fresh output with
`MemoryHigh=256M`, unchanged `MemoryMax=512M`, and `MemorySwapMax=0`: about
75 seconds wall time and 361.5 MiB peak per systemd. Keep this early throttling
policy for future packaging. Twenty-two focused checks had passed in 0.389 s.

The refreshed `oled-root-autoload-r1` static check passes in 0.794 s for release
05941 and the exact new payload. It inherits the retained root inventory only
after checking its pinned receipt and both unchanged image identities, streams
the new 724-member archive/catalog, pairs loader/init source, and repeats four
host kmod dry-run refusals with the new inert display modules. No configured
automatic display loader was found. This does not execute Arch coldplug or prove
absence of early built-in MDSS probing with the display DT. Final root content,
wrapper/controller integration and physical checks remain necessary.

The OLED state-transition components are now separately prepared and tested.
`oled-state-exchange-r1` retains the Rust exchange algorithm, with the new signed
manifest and a fresh `.oled-05941-transition` namespace. Old V9 record remains
`ed3a62d1…`; OLED pending/healthy records are `e77c2e20…` / `aea03ea5…`.
The two static ARM64 PIE builds match SHA `472dfd36…`, 1,253,144 bytes, in
1.262/1.004 s. Fourteen Rust tests pass, including retention of all consumed kernel
transaction records and refusal of prior-kernel states. ABI header checks and
six real ARM64/v1/v2-helper QEMU scenarios pass (0.563 s); no phone write occurred.

`oled-state-guards-r1` recognizes the actual source bundle/kernel 05941 and
unchanged V11 fallback, and checks all six retained kernel transaction files.
Its original physical guard is inherited unchanged; 31 actual ARM64 guard/helper
cases pass in 87.309 s, including missing/tampered/extra prior records, unsafe
power/storage/identity, uncertain outcomes and no retry. Physical telemetry and
mount/device numbers are explicit offline fixtures.
`oled-source-actions-r1` prepares the new RAM/exitrd namespace and source-abort
observer. All 16 file-operation tests (0.644 s) and 22 read-only reconciliation
tests (0.391 s) pass in the intended uid0 user namespace, with telemetry and
reboot calls mocked. All eight action/observation scripts generate successfully.
The separate r49 assembly below now integrates these components; live OLED
admission is still absent.

The fresh authenticated source check passes in 2.094 s at **5,849.97 s uptime**:
same 05941 boot, old selection restored, exact retained prior transaction,
no OLED transaction or exitrd intent, original shutdown and reboot helper.
The initial read-only probe used `/usr/libexec` outside the exitrd and failed;
its receipt is retained. The corrected probe checks the actual helper under
`/run/initramfs/usr/libexec`. No RAM staging, state exchange, reboot or flash
was executed. Current-source identities remain time-bound observations.

The separate `oled-live-driver-r1` / `oled-controller-r1` cohort now passes
**all four offline assembled flows** across 22 unchanged controller phases:
target capture plus post-health, early fallback, late failure with separate
fallback capture, and pre-reboot exitrd/state restoration. Failure scenarios
correctly retain controller FAIL while proving restoration. The target scenario
passed in `full-flow-tests-r2`; only the three remaining scenarios were run in
`full-flow-tests-r3` (17.928 s). USB/SSH/privilege, admission, RAM transfer and
recording time are explicit fixtures; real host capture processes are reaped.
No physical OLED boot or privileged handoff is established by these tests.

The cohort uses a separate integration checkout, `oled-controller-worktree-r1`,
commit `30b72c12`. Exact OLED composition classification is added alongside the
unchanged default headless profile. The OLED profile SHA is `0fc132e8…`; mixed
DT/payload tuples refuse. The new `verified-oled-hardware-boot.py` explicitly
refuses before claim/snapshot/USB access while its composition admission is
unprepared. Nine profile/refusal checks pass in 0.077 s. Existing recovery tools
in the progress checkout and frozen compiled source are untouched.

Installed V9/V11 inventory is inherited independently of new source custody,
and is rechecked by the controller's live route query. Three actual installed
ARM64 selector scenarios pass in 0.332 s. Eleven new ARM64 fallback-observation
cases pass in 52.193 s with real tmpfs/readers/helper and explicit storage/power/
installed-image fixtures. Twenty health cases pass in 0.035 s; the new source
predicate also validates the retained actual r48 snapshot with restored OLD
selection. Seventeen transfer-boundary/process cases pass in 3.675 s.

New host-only custody owner `ba670e08f11d4c3f8e2f95573689619f` binds the exact
r48 source snapshot and old record. Its receipt SHA is `db852a12…`, custody SHA
`c6ebef80…`; it is not RAM-staged. Preserve the earlier custody separately.
Dependency-ordered pin refresh keeps all 59 cohort source references aligned.
Do not rerun `prepare-cohort.py` over the integrated sources. No live execution
directory, input lock, live qualification, registration or claim was created.

The r50 OLED composition run now **PASSes all seven A01 checks** in
**81.851 s**, including wrapper, signed target, archive, paired-root runtime,
module load, firmware and timing/transport. Evidence is `oled-a01-r2/a01/result.json`,
SHA `abcf577d…`, verified by clean source `30b72c12`. Both full logical root-image
hashes match before and after the VM; their metadata is unchanged. The exact
kernel VM exited normally, its container was removed, and its attach process
and group were reaped/closed. Physical OLED probing, scanout, touch and GPU
remain unqualified; virtual hardware cannot establish them.

Integration source is now `462cef05` in `oled-controller-worktree-r1`. Its only
changes after A01 are the explicit OLED boot-adapter evidence binding and tests;
the adapter correctly retains A01 verifier revision `30b72c12`. Twelve profile
and claim-refusal checks pass in 0.136 s. The new 31-file input lock SHA
`d905fc12…` validates in 0.098 s and contains the OLED A01, wrapper, payload and
DT evidence. The current dependency map is `oled-live-driver-r1/pin-refresh-r5.json`.
Do not rerun the initial cohort transformer or substitute headless A01 evidence.

Admission, privilege-fixture and launcher tests pass 24/10/21 cases in
0.447/0.528/0.772 s. Real host processes are used with explicit sudo/root/claim
fixtures; these do not prove privileged handoff. The actual noninteractive
read-only privilege probe stopped in 0.043 s: `sudo: a password is required`.
Its child was reaped, no root probe ran, and no password window opened. Preserve
`oled-live-driver-r1/privilege-probe-r1`; any next attempt needs a fresh output.
No phone query, write, reboot, claim registration/consumption, live qualification
or execution directory was created in r50. The binding receipt is
`oled-live-driver-r1/composition-binding-result-r1.json`.

The first A01 attempt is retained as FAIL: 23.970 s elapsed before missing
ignored Android boot tools stopped wrapper inspection. Five exact tools/template
files were verified against the frozen checkout and staged into Q; bytecode
caches were omitted. The new runner validates these prerequisites before image
hashing. The copied touch askpass executable mode was also restored to 0700
with unchanged bytes and a passing metadata/code preflight. These are host
preparation fixes, not kernel or phone failures.

Next: finish the prepared actual privileged handoff, remaining live qualification
and fresh one-use lifecycle, then fully prepare display capture, late REFGEN/panel
loading, endpoint discovery/blanking and the physical prompt before fresh Ready.
Reuse the passing kernel, modules, payload, wrapper and A01 result. Current-source
health remains r48 uptime 5849.97 s and requires a brief live recheck before
mutation. The r55 authentication outcome and prepared retry are recorded below.

The prepared host authentication check ran immediately after fresh Ready in
r55. Attempt `oled-live-driver-r1/privilege-probe-r2` is terminal **FAIL:
authentication timeout**, 300.014 s. The password window was observed in the
Deck window tree at 04:56:10 UTC, but authentication did not complete. Stderr
was empty; no user report establishes whether the window was accessible or its
keys worked. Do not infer a wrong password or a keyboard defect from this result.

The bounded runner killed its owned authentication group and reaped sudo.
Terminal inspection found no remaining dialog/probe process or password window.
Neither capture nor SSH privileged profile ran. No phone/network/claim action,
boot admission or phone change occurred. Preserve the attempt; never reuse r2.

The later fresh Ready in r56 immediately started the prepared r3 command.
**Actual host authentication and both privileged handoff profiles PASS in
13.378 s**. `oled-live-driver-r1/privilege-probe-r3` is terminal. Capture and
SSH profiles each ran the real root guardian with all four UIDs zero and a
runuser child with deck UID/EUID/GID/EGID 1000. Both child outputs match their
retained raw results, stderr is empty and all launcher/root/deck processes were
reaped or subsequently confirmed gone. Authentication exited zero without a
timeout or retained password. The password window closed.

Receipt `oled-live-driver-r1/handoff-preparation-r2/completed.json`, SHA
`b38eff45…`, binds the raw/proc/result evidence to clean Q `462cef05`, exact
worktree digest and host boot. This is actual host privilege evidence, with
zero phone/network/claim actions; it does not grant boot admission or qualify
OLED hardware. Preserve r2 FAIL and r3 PASS; do not rerun either. No password
request, retry or operator countdown remains pending. The user is released.

Continue live OLED lifecycle/registration and the admitted display
load/discovery/blank/frame/brightness integration. Human display availability
requires a separate fresh request only after the physical test is fully
prepared. Normal future privileged actions still need current credential checks;
this receipt does not promise an indefinitely reusable sudo session.

The r52 `oled-display-component-r1/endpoint.py` now provides an import-only
endpoint reader, guarded zero-brightness write/readback and subsequent framebuffer
sysfs discovery. Twenty tests pass in 0.131 s using actual files, symlinks and
file descriptors in a user namespace, with explicit sysfs write emulation.
No component code ran on the phone and actual sysfs layout is still unverified.
The exact compiled panel source matches the audited source SHA `45e8bcb9…`:
its default/max brightness is 1023 and it exposes no hardware brightness reader.
Zero command/readback success is not an optical-darkness or full-health result.

Backlight identity checks pin the OLED descriptor, expected boot/kernel, one raw
1023-level endpoint, DSI panel driver and DT ancestry. Only zero can be written;
missing/changed authorization, replaced/symlinked attributes, failed/short writes
and nonzero readback refuse. The exact backlight can be blanked before requiring
fb0, so framebuffer failure does not unnecessarily delay that cleanup action.
Framebuffer discovery then requires zero, the same display subtree, msmdrmfb,
1080x2448 at nominal 60 Hz and 32 bpp. It does not open /dev/fb0 or prove pixel
layout, refresh timing, visible output or GPU acceleration. Enclosing admitted
module-load/health/monitor/deadline and fixed-frame integration remain pending.
The r51 prepared authentication source was unchanged in r52; r55 records the later attempt.

The r53 Rust fixed-frame helper is now prepared in `oled-frame-r1`. Independent
ARM64 static-PIE builds match SHA `ed3e8081…`, 1,252,408 bytes; final validation/
build took 2.770 s and the independent build 1.056 s. Rustfmt, Clippy with denied
warnings, 13 release tests (0.02 s) and cross-compiled framebuffer ABI assertions
pass. Actual ARM64 C structure bytes feed the Rust decoder under QEMU; native
and ARM64 render outputs match SHA `859231da…`, 10,653,696 bytes with 4352-byte
fixture stride. Rendering took 0.031/0.125 s. The helper buffers at most one
16-KiB row, accepts bounded layout records on stdin, and emits metadata or one
fixed frame on stdout. It has no device-open, ioctl, module or backlight path.

The inspected preview has an up-arrow, TOP label, RGB bar, asymmetric corner
markers and border. It is generated host evidence, not an OLED photograph.
Malformed/truncated/extra records, interlace/rotation and output failure refuse.
Actual kernel depth24 XRGB (no alpha, offset zero) is recognized alongside
ARGB32. An independent ARM64 header check caught incorrect vmode/rotate offsets
in the first decoder and stopped before a usable ARM64 binary; corrected offsets
132/136 are now checked against C-produced records. Enclosing device/boot-bound
ioctl collection, fixed-frame write and low-brightness/blank controller remain.

The previously missing Rustfmt/Clippy 1.98.0 tools are now staged separately in
`rust-tools-r1`, verified against the retained release manifest hashes. They
work with the existing immutable compiler image, avoiding another repeat of the
known missing-tool failure. No systemwide install, compiler/kernel/package rebuild,
phone action or authentication attempt occurred in r53. The r51 authentication session
remains prepared and unstarted; a goal continuation does not count as Ready.

The r54 import-only `oled-display-component-r1/framebuffer.py` collects the
actual-layout protocol for that Rust helper. It requires the enclosing admission,
exact blanked endpoint/boot, sysfs 29:0 and root-owned character fb0. It first
opens O_PATH for inode validation, then reopens that owned descriptor read-only
through procfs. Only GET_FSCREENINFO/GET_VSCREENINFO are issued, with two equal
samples and renewed device/blank/admission checks around them. All descriptors
close on success or failure. No memory write, mode-set, mmap or backlight change
is exposed. Opening fb0 itself invokes kernel driver operations, so this remains
an admitted display action rather than a generic health query.

Thirteen tests pass in 0.150 s, with real descriptor/path/replacement behavior,
explicit character-device/ioctl fixtures, a real ENOTTY failure and actual ARM64
Rust decoding of the collector's record. All cases check for leaked descriptors.
Physical framebuffer open/GET ioctls are NOT RUN. The collector returns raw
capture, not a false Rust-layout or physical-scanout pass. Same-boot frame
creation/write, brightness session and enclosing load/health/capture/deadline
integration remain pending. Endpoint/frame binaries and prepared authentication
inputs remained unchanged in r54. The later r55 Ready/timeout is recorded above.

The r56 `oled-display-component-r1/frame.py` now connects the exact collector
record to the existing pinned ARM64 Rust renderer. It copies that 1,252,408-byte
ELF into a sealed descriptor, executes the owned descriptor for layout and frame
output, and streams at most 40,108,032 frame bytes with 4-KiB stderr and five-second
child deadlines. Timeout/error paths kill and reap the owned helper and close
all descriptors. No device or brightness access occurs.

The resulting frame is sealed against write, shrink and growth, with a receipt
binding the complete capture, boot identity, raw layout and renderer hashes.
Before device write, the enclosing action must compare a fresh admitted capture
with this binding. A matching receipt is not admission or physical evidence.
The actual ARM64 helper under QEMU reproduced the 10,653,696-byte fixture frame,
SHA `859231da…`, with describe/render times 0.021/0.122 s. Fifteen focused tests
pass in 1.221 s, including changed identity/node/record, replacement of the
renderer path, malformed layout, immutable frame, output/timeout/exit failures,
closed-pipe timeout, pidfd failure and sealing failure. Every case checks for
leaked descriptors. Device/sysfs/ioctl values remain explicit offline fixtures.
Receipt `oled-display-component-r1/frame-result-r1.json` is `787baaa3…`.
Actual framebuffer writes, bounded brightness and enclosing controller/load/
health/capture integration remain next; physical scanout is still NOT RUN.

The r57 import-only `oled-display-component-r1/write-frame.py` now provides
one admitted, entered write and complete memory readback from the sealed frame.
It verifies the full frame hash, consumes the frame's in-process attempt flag,
requires the enclosing durable entry callback, and compares a fresh GET capture
before opening the exact owned fb0 inode read/write. Every 1-MiB write/read chunk
rechecks admission, boot/endpoint/zero brightness, node and raw layout. Partial
writes stop immediately without retry; exceptions retain uncertain-write state
separately from acknowledged bytes. Cleanup errors retain prior write evidence.
All opened descriptors are closed; no illumination or mode change is exposed.

Nineteen tests pass in 3.855 s with the real sealed ARM64-rendered frame and
actual file I/O, descriptor ownership and cleanup. Character-node/sysfs/ioctl,
admission and durable-entry behavior are explicit fixtures. The successful
10,653,696-byte write/readback takes 0.097 s with 11 writes and matching frame
hash `859231da…`. Changes to boot, node, layout, brightness or admission stop
further writes. Short/corrupt readback, partial/uncertain write, entry uncertainty,
deadline and close failures refuse success. The original sources remain pinned;
no kernel, Rust or package rebuild was needed.

The exact clean 05941 kernel sources provide DMA fbdev read/write operations,
including deferred-damage wrappers and positioned I/O. Memory readback does not
prove damage completion, vblank or visible scanout. The ten-second deadline is
checked between syscalls; the enclosing bounded worker remains required for a
stuck kernel operation. Receipt `oled-display-component-r1/write-result-r1.json`
is SHA `da73f546…`. Bounded brightness/blanking and integration with the existing
admitted load/full-health/monitor/durable-entry controller are next. No physical
framebuffer write, phone query, authentication or human request occurred in r57.

The r58 `oled-display-component-r1/display-session.py` now joins the writer to
one fixed brightness request: **32/1023 for 20 seconds**, followed by the pinned
zero-only blank operation. It requires separate current cleanup ownership before
entry. The owner's durable frame/display intent carries the fixed brightness,
duration and cleanup value. A prompt event is queued only after successful frame
readback and nonzero brightness readback. Callbacks must already be installed,
bounded and nonblocking; no callback waits for the human response.

After entry, frame failure, normal health refusal, prompt failure, short/uncertain
brightness write and normal timeout all reach independent blank cleanup. A failed
zero request stays FAIL with no false blank result. Changed boot identity refuses
writes against the new boot. Deadline checks run after authorization callbacks
as well as before them, preventing an overdue callback from queuing a late prompt.
The enclosing worker, transport monitor and postcleanup full health are still
required; this component does not establish a hard hardware timing bound.

Sixteen tests pass in 23.933 s, including virtual-clock failures and a real-clock
production-duration check. That fixture reached confirmed zero in **20.003 s**
after the nonzero attempt (20.095 s total session), with 80 brightness samples.
The real ARM64 frame and file operations are used; sysfs/ioctl/device, admission,
monitor and durable entry are explicit fixtures. No OLED command ran on the phone.
Receipt `oled-display-component-r1/session-result-r1.json` is `d30d2168…`.
The first short-write test had an invalid no-newline sysfs fixture; correcting it
to canonical readback made the existing cleanup path pass without a runtime bypass.

Next, adapt the existing `buttons-module-monitor-r1` and
`buttons-module-physical-r1` components under the retained 20260908 CPU state to
the OLED identity, health, capture closure and prepared display phases. The
monitor proves bounded same-boot USB observation, not target recovery or health.
Reuse its owner/deadline protocol and the module-once loader; no new receiver
family, kernel/package rebuild or authentication retry is needed. Actual module
loading, OLED scanout, touch and Adreno remain unqualified. No human request is
pending; prepare the entire physical session before a fresh Ready.

The r59 `oled-component-monitor-r1/transport.py` adapts the existing pinned
module-monitor server/client/protocol in memory, preserving their original files.
Each OLED phase gets a separate boot/output context; the current source label
is Q `462cef05`. Source/current-headless/zero boots and outside namespaces refuse.
The original 660-second lifetime, 0.5-second sampling, one-second sample freshness,
permanent failure latch, Unix peer/socket checks and exact PID/start/argv guards
remain intact. The reviewed production `monitor.py` must be pinned with the
adapter and all three inherited sources. Reused output refuses before allocating
server resources. A finish still requires the owner's cleanup/health validator.

Twelve tests pass in 2.468 s with real child processes and Unix sockets, including
disconnect/reconnect latching, changed boot/admission/launcher/journal, dead PID,
wrong peer/socket inode, nonempty output and cleanup-gated finish. All test children
were reaped and sockets/FDs closed. USB, admission and physical cleanup/health are
explicit fixtures. `fixture-child.py` is test-only, not a production launcher.
Receipt `oled-component-monitor-r1/result-r1.json` is `1db833c4…`.
Production admission, exact closed OLED boot capture, fresh authenticated target
health, real USB sampler and post-component blank/health closure must still be
wired into this adapter and the r58 display session. No actual USB observation,
phone action, monitor job or human request is active. This reuses the existing
transport mechanism and does not create boot, recovery or target-health authority.

The r60 boot-controller qualification passed the production
`live-admission.py:qualification()` reader. All four full-flow replays pass in
14.843 s at Q `462cef05`; target is COMPONENT_PASS, while early/late fallback and
source-abort remain expected FAIL with restoration proved in their explicit
fixtures. The 31-file input lock passes in 0.162 s. Actual r56 capture/SSH root
handoff receipts match this exact source and host boot and are revalidated.
The historical r60 qualification is SHA `a60705b5…`, with 450 pinned
evidence files. It qualifies current software flows and actual host handoff only.
No phone boot, target health, display or recovery hardware result is added.

Two 1,682,152-byte replay requests are retained in ordered chunks below the
reader's 1-MiB per-file limit. Three mode0644 artifacts have exact private mode0600
copies; eight empty streams are represented explicitly in the archive manifest.
Original evidence is preserved. Initial assembly/validation failures are retained
under `qualification-preparation-r1`; the final production verifier passes. Future
assemblers must check size, nonempty content and metadata before writing the
canonical qualification, and finish all source/pin changes before final replay.

The r61 exact OLED claim is now **registered, pending and host-qualified** at
Q `538fab85a0cc809f0c9ff20a7ae64dd133d27b63` (clean source digest `ef59307b…`).
The sole registry addition is generated from the verified OLED expected fields;
all 227 previous record values are byte-identical. The 21 claim lifecycle tests
pass in 0.233 s, including pending preparation and permanent retry refusal.
The canonical OLED `.record` is SHA `51f8b2bf…`; its attempt remains unconsumed.
All 627 pre-existing claim files and global guards retain their bytes/inodes/
metadata. No OLED `.entered`, launch or controller execution directory exists.

Four derivative files change only digest constants; consumer functions and
actual privilege/authentication entrypoints are unchanged. The r60 source cohort,
input lock and qualification remain archived under `claim-registration-r1`.
The r56 actual root/runuser handoff is inherited with its original source identity
explicitly retained in `handoff-inheritance.json`; no new credential validity is
claimed. Pin map r7 and the 31-file input lock now match the final source.
The current 17 boot, 21 launcher, 24 admission and four complete flow tests pass
(66 cases, 21.898 s including runners). Full flows take 15.471 s internally;
external phone/USB/SSH/privilege/network/claim/time boundaries remain fixtures.

The new `live-qualification.json` is SHA `18b1717f…`, with 460 pinned evidence
files, accepted by the production reader. Every evidence input was normalized
and validated before publishing, without the previous archive failures.
The real read-only `trial-launcher.py:prepare()` passes in **0.256 s**, including
source/input/qualification/registry/pending checks. Result is
`oled-live-driver-r1/claim-registration-r1/result.json`. This is host preparation,
not phone admission, a boot or physical display qualification.

The r62 target module-loading component now passes **17 focused checks in
1.268 s** (1.384 s runner): `oled-display-component-r1/load-modules.py`, SHA
`ae33fc62…`. It reuses the exact 219,912-byte `module-once` ARM64 helper and retained
REFGEN/panel modules. No build was needed. After one durable paired entry, it
loads REFGEN, verifies its platform binding/regulator, then loads the panel once.
It watches for the backlight every 50 ms while the helper is still running and
issues the existing verified zero command immediately on discovery. Insertion
has a five-second deadline and bounded output/reaping; framebuffer discovery is
also bounded. Errors stop without unload or module retry. Separate cleanup
ownership can reassert zero after normal authorization is lost or brightness
changes after the first blank; a different boot refuses stale cleanup.

Tests use real files, held descriptors and child processes with explicit module/
probe/sysfs/health fixtures. The positive sequence takes 0.174 s, blanks during
panel-child execution and reaps both children. The exact ARM64 helper also ran
under QEMU and refused once with errno38 (unimplemented syscall in that path);
this is a refusal-path check, not a kernel insertion. Timeout, output overflow,
changed files/boot, uncertain entry, preloaded modules, missing framebuffer and
late brightness changes fail as expected. The original 15-case pass and initial
fixture setup failure are retained. Result `module-result-r1.json` is SHA
`a5da3d3e…`. No real module was loaded and the phone was not queried or changed.
The r61 boot qualification and unused pending claim remain unchanged.

The r63 completed-boot and fresh-health reader is now prepared at
`oled-component-monitor-r1/provenance.py`, SHA `f4c43495…`. It binds the fixed
actual OLED execution/launcher paths, exact consumed claim/current source,
1380-second capture and ordered cleanup, closed original processes, exact RAM
transfer, and the authenticated postcapture health script/raw result. Historical
boot admission proves that completed run only and grants no component authority.
The actual OLED claim check currently refuses `source BOOT_CLAIMED record still
exists`, as expected: its exact pending record remains unused.

Fresh component health reuses the existing read-only SSH worker and full target
validator. Results must follow capture closure, finish within 40 seconds and be
at most 120 seconds old. `modules`/`frame` phase directories are private; each
`health-before-rN` or `health-after-rN` is exclusive. Stale read-only health can be
refreshed into a new numbered receipt without consuming/repeating a hardware
attempt or replacing old evidence. The later owner must bind the exact path/hash
and enforce before/after role. Final 22 provenance/health checks pass in 0.505 s.
Root UID/time/source/claim/SSH facts in those tests are explicit fixtures.

The transport adapter now binds current Q `538fab85` and is SHA `7e754d20…`;
its 12 real-process/socket checks pass in 2.450 s. The unchanged original USB
sampler also passes an **actual host-only sample in 0.036 s**: target gadget on
`enp4s0f3u1u2`, `cdc_ncm`, product `ROG5 persistent root`, USB anchor `1-1.2`,
serial descriptor absent. No SSH or phone command ran. This is USB/route evidence,
not authenticated target boot/health. The executed sampler source is preserved
and its function matches final source. Evidence is under `source-refresh-r1`,
result SHA `4b1d7978…`; old r59 transport source/results remain archived there.
No actual monitor is running. The r61 boot qualification remains byte-identical.

The r64 rootless component owner and copied monitor entrypoint now pass their
software qualification: `oled-component-monitor-r1/session.py` SHA `3c32272f…`
and `monitor-launcher.py` SHA `f7e29311…`. `Owner` verifies the completed-boot and
fresh-health prerequisites, takes a global lock across module/frame phases,
copies the exact qualified entrypoint into a numbered monitor namespace, binds
the actual controller PID/start/argv, and owns start/probe/stop/reap. An unentered
monitor can be replaced with a new numbered monitor after closure; a durable
hardware phase entry refuses a later attempt. Monitoring grants no module/frame
action by itself.

The live sampler checks parent identity, admission hash and owner lifetime as well
as the inherited USB sample; failures stay latched. Finish requires the same owner/
boot/monitor, a terminal component result with no cleanup errors, a reaped remote
worker, exact zero-command evidence and newly collected full health after cleanup.
Normal owner loss does not prevent verifying independent completed cleanup.
The r65 module backend below now produces target records; the host coordinator
still must validate and convert them into monitor closure records.

Final **19 checks pass in 2.155 s** (2.624 s runner). A real host child and Unix
socket run through `Owner.start()` → live probe → gated finish → reaped exit.
A changed admission latches failure even after its bytes are restored; cleanup
can then finish the failed monitor without changing FAIL. Phone boot/health/USB
and the child bootstrap are explicit test fixtures. Global phase exclusion,
qualified source changes, old entry, stale health, wrong cleanup/health order,
boolean brightness and real process termination are checked. No production
monitor or phone action ran. The initial fixture used a terminal time before its
admission and was corrected; its failure remains retained. The initially qualified
phase-local lock was strengthened to one global lock before physical use, with
previous qualification/source archived.

`component-qualification-r1.json` is now SHA `438a0d20…`, accepted by the real
qualification reader against 13 source files and 15 evidence references. Result:
`session-qualification-r2/result.json`, SHA `76df5ebe…`. Existing endpoint/module/
frame checks are inherited only for unchanged source. Q `538fab85`, the r61 boot
qualification, and the unused OLED pending claim remain unchanged.

The r65 target module supervisor is implemented and passes **28 offline checks**:
22 real process/socket/pipe cases in 4.009 s, plus six root-owned RAM/source
validation cases in a private user/mount namespace in 0.008 s. Summed runner time
is **4.243 s**. `oled-module-backend-r1/backend.py` is SHA `303e9075…`;
its result is SHA `f14c31c0…`. Phone identity, sysfs and module effects are explicit
fixtures. No target SSH session, module insertion or physical display test ran.

The fixed backend accepts only sequenced start/lease/entry-ack/stop records bound
to boot, owner and monitor receipt. It uses the unchanged exact module and endpoint
sources, a global target flock, an exclusive RAM entry and host acknowledgement
before insertion. The lease is three seconds; total normal lifetime is 60 seconds.
Worker and helper process-group closure is checked. After entry, a separate
same-boot zero worker runs even on EOF, expired lease, component failure or blocked
normal worker. Cleanup has four seconds plus a two-second reap allowance. A stuck
kernel task can prevent closure; incomplete reap or zero readback remains FAIL.
These are command/readback checks, with no optical-darkness or scanout claim.

Actual fixture cases prove refusal of duplicate starts/entries/sequences, wrong
owner/monitor/ack, expired/missing lease, overlapping owners and retained entries.
They exercise real worker kill/reap, closed input/output, independent failed or
hung cleanup and changed-boot refusal. The root-file checks use the actual pinned
component sources. Their initial namespace setup could not read protected host
PID1 and failed before mounting anything; the corrected fixture captures its own
host namespace before unshare. That failure remains retained. Only those six
checks were rerun; the passing 22-case suite and earlier components were reused.

**Next:** connect host RAM staging and authenticated duplex SSH to this fixed
module backend using the r64 owner/monitor and r63 health reader. Validate remote
terminal/zero/process records and create the exclusive host phase entry before
acknowledging target entry, then collect full health before monitor finish. The
frame target supervisor/coordinator also remains. The boot launcher is prepared
offline; the whole display test is not yet prepared. Preserve the unused pending
OLED claim until actual launch. Current Ready was released immediately on this
missing prerequisite; it must not be reused for a future physical test.
No phone query/write, password window, recording or operator request is active.

`display-integration-plan-r1/PLAN.md` describes the inert-module/late-load
sequence, but its f17 artifact identities are historical; the old display
packaging recipe also pins f236e710. OLED adds L12/L13 under the already-probed
RPMh parent, whose probe-time child scan does not establish live-overlay support.
Prepare a new DT boot, not regulator unbind. OLED/touch/GPU remain unqualified;
the combined DT proposal is offline only. Kernel work precedes Denial/Flutter.
No physical prompt or job is active. Request fresh availability only after the
physical display test is prepared. Use r65 for the bounded target module supervisor, r64 for owner/monitor lifecycle qualification, r63 for boot/health provenance and current transport/sampler, r62 for the target module/early-blank component, r61 for current registry/pending claim/source qualification, r60 for its historical predecessor, r59 for the component transport adapter, r58 for the timed display session, r57 for the guarded write/readback component, r54 for framebuffer capture, r53 for the Rust frame helper, r52 for the offline display endpoint component, r56 for actual host handoff and sealed frame preparation, r50 for A01/input binding, r49 for controller integration, r48 for transition components/latest
source health, r47 for signed packaging/static autoload, r46 for payload, r45
for restoration, and r43 for the original trial.

Earlier coordinator milestones below retain their original scope and timings;
statements about pending jobs or absent trials there are historical.

Current coordinator handoff: the successor kernel, module and boot-package
builds are complete; do not restart them. All twenty-two controller phases now have
component implementations, including capture lifecycle and the one RAM transfer.
The capture supervisor passes **20 tests in 11.244 s**, using actual child
processes, process groups, pipes and loopback TCP. Two tests run the real
controller through target success and a separate fallback recording after late
failure. Recording time, privilege, USB/network, admission and phone behavior
are explicit fixtures; this does not qualify a physical capture or boot.
The supervisor verifies process ownership and the local readiness challenge,
preserves the original deadline, and checks cleanup records before accepting
closure. It distinguishes proven prelaunch absence from an uncertain launch.
The earlier passive worker's 19 isolated tests and bounded host source reader
remain qualified for their recorded inputs. The RAM-boot callback passes 17
focused tests in 3.696 s, including real sealed-FD child success/failure/timeout
checks with a four-byte fixture. It checks live capture after image preparation
and device queries, retains failed transfer output, and forbids a second attempt.
No production image snapshot or phone boot ran. The concrete installed-route
verifier now passes twelve host tests and six isolated file tests. Its actual
read-only phone probe passes in **2.912 s** on the unchanged V9 boot: all eleven
installed files, boot-partition hash, source state and storage protections match.
It binds a fresh inventory to the controller's preflight and replays the retained
selector decision evidence. This does not prove a physical fallback boot.
The twenty-two components are now assembled into an import-only driver. Twelve
assembly/source-abort integration tests pass in **8.942 s**, using real callback
and controller receipt flow with explicit simulated phone replies. Preflight uses
one combined source/route query; both boot paths use the same concrete route
verifier and distinct owned target/fallback capture checks. The driver checks
nested evidence paths and bridge interfaces before any source mutation.
The fixed sudo capture bridge and process monitor now pass sixteen real process/
pipe/pidfd tests in **7.354 s** and three bridge/supervisor integration cases in
**2.625 s**. The monitor watches both controller and launcher loss; bounded output
writes permit cleanup after reader failure. These tests explicitly substitute
sudo/root/network and recording duration. The actual privileged handoff remains
unverified. The shared admission verifier is now implemented as described below.
The fallback-route worker now passes nineteen component/process tests. It
borrows an exact existing route or cleans up its own temporary route, while
running SSH as deck. The shared child runner now uses `prlimit`, avoiding a
Python pre-execution hook inside the threaded monitor. Thirteen worker tests and
fifty affected integration cases pass; an actual threaded source query passes
in **0.115 s**. Fourteen dependent source-pin updates preserve prior source bytes.
The guarded fallback transport entrypoint and parent adapter are now connected
to action, direct health and nested fallback-locator callbacks. Sixteen transport
tests pass in **1.068 s**, three injection tests in **3.907 s**, and 112 affected
regression cases in **50.460 s** including launch overhead. Actual child sessions,
pidfds and durable output files are exercised; sudo/root/network are fixtures.
Raw root output is bounded separately on disk, preserving diagnostics larger
than the older four-MiB receipt limit. Failed or uncertain mutations cannot retry.
The shared admission verifier and concrete driver factory now pass **24 boundary
tests in 0.451 s** and **three source-abort/assembly tests in 4.835 s**. They bind
the exact input lock, current controller/host boot, qualification evidence,
one-use claim, phase history and generated command bytes. Both root entrypoints
use the same policy. The factory connects the capture and transport authorizers
before returning a driver. Full target/fallback integration and actual privileged
handoff are still unqualified; their required receipt is absent.
An actual 29-file input check passes in **0.105 s**, with an unchanged check in
**0.005 s**. Hashing streams the 128-MiB boot image; changed metadata invalidates
the cache. An actual entrypoint check refuses both the unregistered claim and
missing qualification in **0.339 s**. No admission record or physical execution
directory has been created.
Four complete assembled flows now pass in **22.853 s**: target capture plus
post-capture health, early V11 fallback without target switch-root, late failure
with a separate full fallback recording, and pre-reboot restoration of both
exitrd and selection state. These use real callbacks, admission phase/command
policy, parent fallback transport and recording subprocesses, with explicit
USB/SSH, privilege, RAM transfer and elapsed-time fixtures. They prove host
integration behavior, not phone operation.
The read-only privilege probe passes **nine preparation tests in 0.691 s**.
The first actual attempt stopped before root execution because sudo required a
password. The second attempt's GUI failure and third attempt's input failure are
retained; r2, r3 and r4 are terminal and must not be reused.
It performs no phone, network, claim or live-capture action. After actual handoff
qualification, finish exact claim registration and final qualification. No physical Ready
request or phone recording session is pending.
The import-only one-use launcher is now prepared: **15 focused tests PASS in
0.806 s**, plus **48 affected regression cases PASS in 36.646 s** including
launch overhead. Authentication and the first noninteractive credential refresh
precede claim consumption; the admitted record precedes controller execution.
A bounded refresher keeps the same controller's sudo credentials available
during long recordings. Failures block new phases; cleanup stops the refresher
and owned recordings. A recording requiring emergency cancellation cannot turn
the launcher result into success. Actual sudo refresh remains unverified.
The remaining RAM-transfer `preexec_fn` was replaced with fixed `prlimit` before
introducing the thread. A real four-byte sealed-FD child verifies both limits
and inherited data while another thread is alive. Admission now binds launcher
identity, and the input lock includes the credential helper. The root-boundary probe is unchanged; authentication and the launcher source
pin now include the GUI-limit correction and are prepared for a fresh reply. No trial directory, claim or phone action
was created by this work.
New routes/full capture need host sudo authentication, while normal USB SSH
works as deck. No receiver or Ready request is pending.

Latest actual phone health passes in **2.083 seconds** on unchanged V9 boot
`7c945aa5-80d0-4af2-aa76-113d68e23ac5`, observed at 50,061.14 seconds uptime.
The same boot committed healthy at 64.143 seconds; pinned runtime, current-boot
markers, services and storage/power guards pass. Battery temperature was 30.3 C.
The prepared RAM helper/custody and original boot selection remain preserved.
The new health predicate works after full capture without relaxing the
300-second healthy-commit deadline. This is V9 evidence, not a successor boot.
Use the latest `kernel-hardware-checkpoint-r*.json` in the private state directory
for exact current sources and receipts; later sections retain earlier milestones.

The last hardware inventory has no DRM card/render nodes, framebuffer or
backlight, and only the three qualified key inputs. MDSS, DSI, GPU and GMU are
disabled in its device tree. The existing 60 Hz display evidence belongs to a
different kernel/DT pairing.

The exact historical panel source and unchanged REFGEN regulator source now
build as external modules against the current server kernel. Both module twins
are byte-identical; the two builds and verification took 12.967 seconds. Their
load/unload and driver-registration checks passed under the exact V9 Image in
QEMU in 2.199 seconds. No phone module was loaded and no display was activated.
This establishes a smaller display preparation path without rebuilding the
kernel; it does not establish scanout or GPU rendering on V9.

The current-V9 display DT now composes identically twice and passes strict
preservation checks: ten added nodes and fourteen changed properties. Nine
focused tests pass in normal and optimized Python. The package remains unsigned
and unactivated. Full local source CI passed at
`752742fc2f7aeb1ce19d8389a81658399f1a28fc` in 563.196 seconds; physical
admission and full paired-root qualification remain pending.

Denial source, engine source dependencies and Rust toolchain are pinned in the
[source lock](../configs/denial/source-lock-v1.json). The isolated Rust 1.98
builder is provisioned. The ARM64 control client built offline in 22.010 seconds
and passed emulated help/version checks. Full ARM64 compositor compilation also
passed in 464.094 seconds under the same 3 GiB limit. Both resulting binaries
pass isolated ELF/help/version checks; no engine or phone session was run.
Static closure against the retained Arch layers passes for `denialctl`.
`deniald` still needs GBM, libseat, libinput and xkbcommon libraries there.
The isolated Flutter engine builder is now provisioned, and its exact Flutter
and bootstrap depot_tools checkouts passed verification in 22.003 seconds.
Dependency sync was deliberately stopped at the user's priority change after
796.080 seconds. The container and runner have exited; its partial source/cache
is retained. The raw sync receipt is FAIL/137 from the requested stop, not a
successful dependency closure or evidence of an OOM. Do not restart it during
the kernel-first phase. No hooks, engine compilation or shell assembly ran.
The public mobile shell is available, while the reference
build helpers use x86-64 paths and checksums. See the
[bring-up record](../test-results/2026-09-10-denial-bringup.md) for next actions.

The new unsigned display composer preserves the corrected buttons payload and
adds two inert module files with a fresh descriptor/catalog. Focused composition,
module closure and runtime installer checks pass. Actual unsigned initramfs twins
match SHA-256 `3fcbf6d3dfa9dd45719c0ab167940961c76ee10a5500c8913bfd3e76eff294dc`;
both are 56081476 bytes and composed in 14.745 seconds total. Complete boot-image composition,
paired-root autoload absence and physical display behavior remain unqualified.
The new DT permits built-in display probing before userspace.

Reviewed cleanup removed 67.218 GiB of generated compiler intermediates from
completed historical builds. All 15,559 protected outputs remained unchanged;
sources, final images, recovery data and current module kits were retained.
Approximately 82 GiB was free before temporary full-CI fixtures.

The hash-verified stock DTBO now corroborates the ASUS MP2 front-touch
controller, GPIO22/23/131, L3C/L8C consumers and final 1080x2448 extents.
This is offline board-data evidence; no touch probe or driver activation ran.
The private first FTS3658U driver now builds against the unchanged current kernel.
Twins match in 9.062 seconds; 24,324 parser/ID/transfer checks pass in optimized
and UBSan runs, and six disabled-DT checks pass. Module SHA-256 is
`fc94acd0bc6cd6ce4900e5ccb62c3edb6ca6c17ae332cefdb0ed31d6624bbb60`.
Driver review passes. GENI I2C/GPI provider twins now pass in 16.832 seconds;
the three-module stack registers under the exact V9 Image in QEMU in 2.687
seconds. Touch and I2C unload cleanly there; GPI has no unload implementation
and remains until guest reboot. This does not prove real bus, IRQ or rail behavior.
The disabled touch overlay now composes against both V9 and display DTs with
unrelated properties and boot metadata preserved; twelve hostile-delta tests
pass. The enabled proposal makes five status changes, leaves SPI4 disabled and
retains L8C always-on. Touch unbind cannot undo that rail's always-on vote.
The physical probe remains pending. The
component intentionally leaves suspend/resume unqualified and cannot yet serve
as a complete touch implementation. No module was loaded on the phone.

The reviewed source, disabled overlay and portable test are now integrated at
`e8cebfcd`; C/header bytes match the private build inputs. The test passes eight
cases and 24,324 decoder checks per C build mode in both ordinary and optimized
Python (0.573/0.520 seconds). It is wired into the repository runner. Full CI
for this new integration is pending; the earlier 752742fc result remains scoped
to its own source. See [front-touch prototype](front-touch-prototype.md).

The current-kernel GPU audit found that GMU power-level setup errors were
ignored. Existing patch 0012 fixes that exact path; eight actual-source
fault-injection cases pass and the unpatched baseline fails. Clock and RPMh
fixes 0026/0035 are already present. The clean successor kernel source is
`05941d04803f54208da1e9920a81874edc540ca1`, containing only 0012 over f17.
Its unchanged-config/compiler/release preflight passed in 21.955 seconds.
Cache-assisted kernel twins now **PASS**: 2729.501 and 2698.331 seconds,
with identical Image, Image.gz, vmlinux, Module.symvers, configuration and all
25 scoped modules. Both containers exited without OOM and were removed.
Do not restart the completed runner. The exact Image also passed the earlier
2.633-second generic QEMU boot; physical successor boot remains pending.
The compiled integration source stays frozen at `f74e719c` in private
`worktree`; current progress documentation is maintained in `progress-docs-r1`
so downstream verification can still authenticate the original clean source.

All three pinned A660 firmware files have been recovered from official
linux-firmware 20260622 into private `gpu-firmware-r1`, with matching sizes/hashes
and retained licenses. Fresh ZAP parsing needs 4 KiB within the existing 8 KiB
reservation. SCM authentication, GPU initialization and submission remain
unproven. The first DRM open initializes hardware; it is not a read-only health
check. Use a small explicit DRM test before Mesa or Denial.

Unsigned GPU DT proposals now reproduce on both V9 and display-V9 bases:
exactly four status properties plus the ZAP firmware name change, with all
other property bytes, boot CPU and reservations preserved. Eight focused
test groups pass in ordinary and optimized Python; no phone activation ran.
The private Rust open/query helper passes fourteen native tests per build mode
and exact ARM64 UAPI compile assertions. It permits one operational open and
three scalar queries, preserves primary and close errors separately, and has
no submit or retry path. ARM64 binary twins now match after 1.683/1.271-second
builds. Static library, version and strong-symbol closure passes against the
retained Arch providers. Separate debug-stripped deployment twins are 542,016
bytes, 88.3% smaller, with loaded code/data preserved and originals retained.
No target executable or phone GPU operation ran. A cooperative timer cannot
bound an uninterruptible kernel ioctl. Evidence: private `gpu-query-arm64-r1`.

The matching 3,378-file kernel kit was derived in 9.701 seconds and additively
completed in a 2.582-second service run. Original files remain unchanged;
packaged PDR alone retains the accepted BTF-removal exception. External module
twins now **PASS** in 216.131 and 38.580 seconds, with all 31 raw outputs
identical and clean container cleanup. Selecting the two diagnostic provider
replacements yields 54 unique production modules across both build groups.
The cached comparison took 82.1% less elapsed time than the first module build;
this measures this module run, not a full-kernel or future-build guarantee.

All 54 selected raw modules pass exact export/dependency, namespace and GPL
checks against the successor kernel in a 6.253-second service run. Ordinary
defined symbols do not count as exports. The typed S12 provider/consumer edge
also passes. This static check does not prove full module ABI/BTF compatibility.
The actual ten-module guest passed in 3.797 seconds: indicator, GPUCC, REFGEN,
panel, GPI/GENI and touch loaded and registered; nine unloaded and permanent
GPI remained until poweroff. Physical probes did not run. The remaining 44-module
guest now passes in 8.096 seconds: 41 ordinary loads with runtime BTF checks and
three exact one-call ENODEV board refusals. Its test-only S12 shim was rebuilt
twice against 05941, with identical outputs and clean cleanup in 11.957 seconds
total. The shim observed the activation consumer's BTF COMING, zero LIVE and
zero validator calls, then unloaded. Packaged PDR alone omits BTF as explicitly
qualified; no raw-PDR BTF or successful physical S12 hold is claimed.
Private receipts are in `successor-module-build-r1`,
`successor-module-closure-r1/verification-r1` and
`successor-components-vm-r1/run-r1` and `successor-baseline-vm-r1/run-r1`.

Unsigned successor payload twins now pass in `successor-payload-refresh-r2`:
57,774,555 bytes each, SHA-256
`c7d757727bc6e9295087b02d207e90d44e43d9ac2f1ccb345a4923c04365e058`.
All65 previous module copies were refreshed and four hardware modules added
outside the automatic module search tree. Nested membership stays37 modules;
the new host depmod's exact comment-only `modules.weakdep` is explicitly
qualified as metadata file14. The original inventory refusal is preserved.
Corrected runtime, indicator, shutdown, firmware and other unrelated bytes
remain unchanged. The reserved unsigned bundle is
`kernel-hw-05941-a607a2bb249c918b`, using the retained headless V9 DT.
Signed headless boot-package twins now pass in `successor-boot-package-r2`
(89.009 seconds, 512 MiB/no swap). The 129,966,080-byte raw image requires the
128 MiB AVB envelope; both final wrappers match
`d21405d94a9eabc4b6b8e1b7990bf7c9f2aef1da0795a39e94761a5a09ab3fa6`.
Both AVB checks, nested authenticated runtime plan and signed bundle comparisons
pass. The first packaging failure is preserved: AVB resolves partition `boot`
as sibling `boot.img`, requiring an exact canonical verification copy. Local
signing has occurred; release qualification, admission and phone execution have
not. Paired-root content/runtime checks and exact059 A01 now pass as recorded
below. A complete 128 MiB controller and guarded pending trial-state preparation
remain required.

Full CI on frozen f74 stopped after 84.809 seconds on an unchanged five-second
host-test timeout under a two-CPU quota. The reviewed scheduler now defaults to
two workers, capped by affinity and inherited quota. CI on corrected cc53c3ec
passed that 12-test suite, then stopped after 255.505 seconds at UFS inventory
sorting: the desktop service inherits en_US.UTF-8, unlike the shell's C.UTF-8.
The production verifier now pins C locale; exact inventory/profile refusals
remain unchanged. Full CI now passes on frozen source `492d8cf2` in 593.246
seconds, source unchanged, under 3 GiB/no swap and a two-CPU quota. Receipt:
`source-ci-r6/result.json`. The previous failures remain preserved.


The exact059 A01 integration is now implemented with one versioned artifact
profile. It recognizes all 54 module identities, 32 loose copies, 37 nested
copies and 14 exact metadata files. The retained payload inventory passes in
1.332 seconds (335.5 MiB/no swap). Historical f17 recognition is unchanged.
The profile permits offline wrapper lookup only; it creates no boot claim.
The original test-only shim twins bind through an explicit reference envelope
and actual vmlinux-to-Image comparison in 0.865 seconds, without rebuilding.
The integrated VM now pins the qualified QEMU image and records owned-container
creation, terminal state, removal and process-group cleanup. Console parsing is
bounded. Focused profile, fixture, lifecycle and wiring tests pass, including
missing/duplicate runtime markers, stale identities and incomplete cleanup.
Actual full A01 passes on `f316fe58` in 80.308 seconds: all seven composition
checks, 51 ordinary module loads, two expected board refusals and the separate
activation boundary. Root and upper hashes stayed unchanged. The owned VM
closed cleanly without OOM and was removed. Full source CI on that same clean
commit passes in 596.538 seconds (`source-ci-r7/result.json`). These results
establish offline qualification, not physical hardware behavior.

The exact059 import-only 128 MiB boot primitive is now implemented. It binds
the immutable composition profile, trial, wrapper, fallback and A01 evidence;
requires the successor's own entered claim; and reuses the existing sealed
snapshot/capacity primitives without changing either historical boot path.
The successor remains absent from the claim registry and therefore cannot boot.
Nine new tests plus the existing seven R01 and four ordinary helper tests pass
in both Python modes. The actual wrapper snapshot seals and closes in 0.184
seconds; focused service runtime is 2.450 seconds, peak 281.8 MiB/no swap.
Evidence: `successor-boot-helper-r2/result.json`. Full integration CI for this
helper now passes on clean `63a0c1a1` in 602.727 seconds
(`source-ci-r8/result.json`). The service is terminal; do not restart it.

The private Rust trial-state exchange primitive now passes offline qualification
in `successor-state-exchange-r1/result.json`. It writes and syncs a backup and
new pending record, then atomically exchanges the two names while holding file
locks. This supersedes the proposed absent-record creation interval. Restoration
exchanges the original V9 inode back and retains both records and one-use intent
files. Eleven native test groups cover interruption, locks, tampering, pathname
replacement and retry refusal. Corrected static-PIE ARM64 twins match after
1.071/1.119 seconds. Six isolated ARM64 cases (17 process calls) pass in 0.582
seconds, including real v1/v2 target-helper health acknowledgment and exact
old-record restoration, in an empty root without shared libraries. This does
not establish phone-filesystem power-loss durability or physical authorization.

The ARM64 replay caught a repeated host/target open-flag mistake; target-header
compiler assertions now bind the Rust constants and reject the old values.
An earlier DYN-labelled image crashed before its first syscall because rustc
passed contradictory static/no-PIE options. The corrected linker and actual
ARM64 startup/operation checks qualify the working artifact; failed images and
receipts remain retained. Rust fmt/clippy are absent from the pinned builder;
the attempted lint run is preserved, not labelled PASS.

Source/V11 shell guards now wrap the retained static helper, with exact boot,
sealed tools, power, storage, custody and exclusive operation-entry checks.
All 28 namespace cases passed across two runs with the actual ARM64 tools and
explicit synthetic telemetry. The first run remains FAIL: fixture setup stopped
after 19 passing cases. The corrected harness records each result durably and
completed only the remaining nine in 15.572 seconds. Retained outputs and final
fixture states were replayed without repeating ARM64 operations. Seven host
custody tests pass in normal and optimized Python. A fresh real-phone health
check passed in 1.206 seconds; the new guard's read-only subset then passed on
the same V9 boot in 0.972 seconds. The exact old selection record is now retained
in durable host custody. Evidence: `successor-state-guards-r1/result.json`.
That guard run did not upload a helper or change selection.

The source transition primitives now pass sixteen focused tests in normal and
optimized Python (0.750/0.749 seconds). They separate RAM staging, exitrd
installation, one-use reboot request and pre-reboot exitrd restoration. A lost
reboot reply permanently refuses retry and automatic source restoration; an
interrupted exitrd installation can restore the exact old script before the
reboot intent exists. The original Python V11 staging proposal is unusable on
V11, which has no Python; it was never executed there. Use the qualified
BusyBox replacement below. Full controller admission remains pending.

Fresh physical inspection confirmed V9 already has corrected shutdown bytes
`fc1ce027`; the old R01 source shutdown differs. Reuse the previously qualified
`0ee47fb5` fastboot dispatch variant, preserving all corrected cleanup code.
Source RAM staging now **PASS** in 1.368 seconds, followed by independent
readback in 0.258 seconds. Four files are retained under
`/run/rog5-kernel-hw-5ff5ab2bf15642c7a07e788a73caefa2` on the unchanged V9 boot:
the exact Rust helper, custody, inactive fastboot shutdown copy and completed
staging token. The active shutdown and healthy selection record are unchanged;
the state transaction directory is absent. No helper execution, reboot or
persistent write occurred. Do not repeat the completed staging action. Evidence:
`successor-source-actions-r1/result.json`.

The private successor controller ordering now passes 25 failure-injection cases
in normal/optimized Python (13.156/6.148 seconds), with real durable host receipts
and explicitly synthetic driver/capture observations. It preserves full capture
after failed or ambiguous execution, requires fresh post-capture target health,
and keeps successful V11 restoration separate from trial failure. An early target
failure can authenticate V11 without a preceding switch-root event. A fastboot
return requires a separate full fallback capture before one ordinary reboot of
the installed selector. This is ordering qualification; the concrete SSH,
fastboot, capture and admission driver is not implemented or admitted yet.

The exact installed selector function and ARM64 helper now pass three namespace
cases in 0.342 seconds: successor pending/healthy records both select signed V11
without changing those records; restored V9 healthy selects V9 and rearms pending.
Physical installed `boot_b` readback passes in 0.545 seconds, matching the retained
96 MiB wrapper `dcc487f1`, with protected storage read-only and V9 state unchanged.
Storage preparation/cleanup in the selector test is synthetic, so these results
do not establish a physical fallback boot. Evidence: `successor-controller-r1`.

The V11 RAM stager now uses its exact sealed BusyBox/loader and static ARM64
Rust helper. Five actual ARM64 namespace cases pass in 33.006 seconds in an
empty root without Python: pending/healthy restoration, wrong boot, partial
transfer and duplicate staging. Kernel/storage telemetry is synthetic. A bad
fixture device-number encoding was corrected from the fixture's actual sysfs
major/minor; the original failed run remains retained. No V11 phone action ran.

The bounded SSH worker now runs over an existing USB route as deck. Thirteen
focused tests pass in ordinary/optimized Python (0.530/0.569 seconds), including
an actual isolated-process repository import. The first privileged launch failed
before execution because sudo requires a password; a later local probe exposed
a missing sibling import, now fixed and covered. Actual read-only normal USB
SSH then passed in 0.611 seconds, authenticating the same V9 boot and kernel
without host network changes. This is transport continuity, not a new full
hardware health qualification. Evidence: `successor-live-driver-r1`.
New network setup and full capture still require host privileges. These worker
and staging pieces do not yet constitute the complete concrete driver.

Seven concrete mutation callbacks now bind the existing controller to the
qualified source actions, Rust state guard and BusyBox V11 staging generator.
They recheck durable context/intent/custody, write an exclusive command intent,
retain the complete transport response before parsing, and reject stale,
ambiguous, nonzero or timed-out responses without retry. All 27 tests pass in
normal/optimized Python (7.304/7.890 seconds): 22 boundary cases and five actual
controller sequences. Transport, capture, health and admission remain synthetic;
real generated scripts, existing custody and disposable fsynced receipts are used.
The complete driver and admission gate are still pending. The adapter currently
uses deck's existing-route transport; a scoped privileged bridge for fresh
fallback routes must be bound before live execution. Evidence:
`successor-live-driver-r1/callback-tests-r1/result.json`. No phone action ran.

Three read-only source callbacks now implement preflight, interrupted-source
inspection and restoration verification. Their observer accepts only recognized
selection/exitrd transactions, checks both ends of the snapshot, and refuses
reboot intents, partial publications, changed records and unknown owners.
Twenty-two real file/lock namespace tests pass in normal/optimized Python
(0.568/0.510 seconds), with physical telemetry synthetic. Twelve callback tests
pass (2.869/3.045 seconds), replaying actual V9 proof with explicit alterations.

The new observer's actual V9 preflight **PASS** in 1.694 seconds on the unchanged
boot: physical storage/power guards, staged helper/custody, original shutdown and
old healthy selection all match; state/exitrd transactions and reboot intent are
absent. No source mutation or reboot occurred. Evidence:
`successor-live-driver-r1/live-source-observation-r1/result.json`. This qualifies
the current read-only source check, not successor hardware or full boot admission.

The successor health component now derives seven runtime/unit members from the
exact built payload and two healthd files from frozen source. Twenty synthetic
proof tests pass in normal/optimized Python (0.452/0.490 seconds), including late
observation versus late healthy commit. The same complete reader passed on V9
in 2.083 seconds. Replaying that real observation demonstrates why the existing
startup-only smoke predicate cannot serve as a post-capture health check; it is
unchanged. Evidence: `successor-live-driver-r1/health-tests-r1`,
`live-baseline-health-r1` and `health-late-replay-r1`. The successor and V11 still
need their own physical evidence; neither boot nor full capture ran.

Next: implement and qualify V11 health and verification, target health callbacks, capture/fastboot
and privileged fallback routing, then complete admission for the concrete driver using
the staged source artifacts and exact one-use boot admission. The embedded RAM wrapper
bypasses the installed selector, so its
recovery phase stays read-only and requires a separate authenticated V11 return
path. Keep the ordinary full capture and failed-target result separate from
successful assisted recovery. No phone action or Ready request is pending.

The expanded display autoload audit passes for configured root paths: udev
loading uses the absent current-release index, while the new payload is outside
that tree. Historical REFGEN and dormant display scripts remain preserved.
Final wrapper/generated-runtime checks and actual coldplug are still pending.
The next display boot also needs fresh embedded-bundle admission, a matching
guarded userdata trial record, and measured boot-image size/controller binding;
unchanged paired root bytes alone do not satisfy those requirements.
Checkpoint read-only phone health passed again in 1.357 seconds on the same V9
boot after all offline work. That earlier health checkpoint involved no phone module insertion or reboot;
subsequent local successor signing is recorded above.

## Preserved buttons/LED milestone

Updated 2026-09-10: **buttons and visible green indicator have passed component
verification on the current V9 Arch boot**. Power (116), volume-down (114) and
volume-up (115) each supplied one complete press/release and an IRQ delta of two.
The user saw the green light. Three natural pulses at brightness 31/511 returned
to zero after approximately 180 ms; the user confirmed several power presses.
The strict one-pulse session remains FAIL for that extra activity. Its valid
power event and visible-light evidence are retained separately from the later
volume-only COMPONENT_PASS. Final LED readback is zero, full server health
passes, and all component monitors and controllers have closed.

The combined private receipt is `buttons-hardware-result-r1/result.json`, SHA-256
`0c7b0deeda132598b0c50eeffbe7971a97e6f1764d3c10c06fc44684fd4db557`, under the retained
`rog5-cpu-startup-20260908.kjE4IqCf` evidence root. The
[dated report](../test-results/2026-09-10-mobile-input-preparation.md) records the
separate component and strict-case outcomes. The full original V9 boot
observation lasted 1380.892 seconds and its host cleanup passed. S06 and R01
remain failed; this work does not qualify shutdown or autonomous recovery.

The live fixes are RAM additions on kernel `7.1.4-gf17befd4ef17`: the missing
`qcom_pon` parent, the corrected LED firmware-node lookup and the local reader's
ARM64 read-only FD mask. The accepted signed V9 image still contains its original
inert payload. Persistent activation and a promoted successor image remain
unqualified; component success must not be described as an installed release.
Repository integration carries the corrected artifacts and complete module
closure forward without changing the accepted boot image or consumed claims.

Integration commit `bc424ae6` passed full local CI in 531.274 seconds. The unsigned
five-file payload reproduced identically in two compositions (6.949 seconds
each); final archive metadata, four-module ABI/dependency closure, integrity
catalog and radio preservation checks passed in 0.623 seconds. These offline
outputs remain inert and grant no signing, activation or boot authority.

Human-assisted sessions must be fully prepared before asking for Ready. A fresh
reply starts only the brief current checks and recording setup, followed by the
actual key prompt. No operator timer runs while awaiting availability.

## Previous preparation checkpoint

Updated 2026-09-10: the user clarified the destination as a native touch-first
Arch Linux phone inspired by Denial, with cellular excluded. Display, touch
and GPU are central next milestones in the [roadmap](../ROADMAP.md). Buttons
and a default-off status LED are the current bounded step, not final product
completion. The [signed input package and module composition](../test-results/2026-09-10-mobile-input-preparation.md)
passed offline verification at source `458cb42a` in 6.13 seconds. Full
root/runtime composition and physical input/LED evidence remain pending;
V9 is now registered against those exact signed bytes, with all prior records
unchanged. It has not been admitted or booted. Sparse checkout of two completed
review worktrees recovered 5.93 GB while retaining their Git objects and evidence;
the host reserve is restored. A01 now prepares exact-kernel VM load checks for
the three indicator modules while keeping physical behavior NOT RUN. Its
46-test suite passes; paired-root VM composition and full CI remain pending.

After the unplugged startup investigation, installed V8 returned as boot
`159aa8ca-a7d5-425c-87c8-481e9484ff22`; the final authenticated readback passed
installed bytes, power/thermal and local storage checks. The full capture and
cleanup completed and all phone controllers are closed. S06 and R01 remain
failed; the shutdown/startup issue is unresolved. Current readback supersedes
the historical boot and S06 status in the retained checkpoint below.

## Previous qualification checkpoint

Updated 2026-09-09: the corrected RAM-only shutdown passed its physical source
component. Its clean receipt reported mounts and loops clear, with all **117**
physical block nodes read-only. Fastboot followed in **11.801 s**.
One guarded ordinary reboot returned installed V8 as `a60a8d6d-5dda-4e15-9ab3-d46fb015ecf2`;
health committed at **65.542382 s**. The complete **1380.848 s**
capture and route/firewall/profile/address cleanup passed. Final authenticated
readback passed installed bytes, healthy selection, storage guards and absence
of staging at **1336.860 s** uptime. Independent terminal replay passed.
All phone controllers are closed. R01 remains FAIL with its claim consumed;
S06 remains NOT RUN. One coherent release is not yet qualified.

This observation used frozen source `6e7402e2`: full local CI **582.141 s**,
all four GitHub jobs PASS in run **34307973735**, 64 admission cases and nine
assembly cases in both Python modes. Private action/receipt/controller/launcher
checks passed 22/36/28/11 cases per mode. The clean source receipt is component
evidence; it does not establish the original R01 cause or autonomous fallback.

The preceding diagnostic refused residual userdata ext4 (`259:58`, `/dev/sda23`)
after the old shutdown reported clean. A real namespace reproduction showed
that systemd's relocation of a busy mount could bypass fixed-path cleanup.
The correction accepts only one recorded root ext4 userdata mount at its
canonical or exact systemd relocation path, verifies node and reachable-device
identity, strictly unmounts, verifies disappearance, then relocks storage.
Sealed regression passed **71 default / 72 diagnostic cases**. The corrected
shutdown is in source and was tested from RAM; installed shutdown, kernel,
root images, signed fallback and consumed experimental claims remain unchanged.

S06 preparation also exposed two host-side defects. S05/S06 replay now derives
executed shutdown identity from the canonical installed release while keeping
observer-source provenance separate. A scoped `--powered-off-start` receiver
mode reserves the contract's extra 60-second operator transition: 1440-second
capture lifetime, unchanged 1320-second recovery requirement and 1380-second
S06 remaining/deadline gates. The mode is bound on start and check and excludes
experimental source-teardown captures. S05/S06/receiver tests passed 11/19/42
cases in both modes; ordinary smoke passed 23. Retained real S05 replay passed
in 0.711 s with its original input index unchanged. Integration full CI is pending.
No powered-off cycle is admitted; direct operator input and a reviewed live
controller are still required.

## Goal and authority

Deliver the mobile Arch phone described in the [roadmap](../ROADMAP.md), with
the buttons/status LED milestone first. Preserve the headless server and its
existing [acceptance contract](release-acceptance.md) and
[mandatory matrix](../configs/release-acceptance.json) as the baseline.
Missing prerequisites/evidence are BLOCKED or NOT RUN, never PASS.
Use the clarified roadmap for scope; unrelated work stays in the backlog.

Exact phone: `M5AIKN00F0353YH`, product `lahaina`, side USB anchor `1-1.2`.
Preserve official WW33 slot A (`33.0210.0210.200`) as charging/rescue.
Stock charging restoration is complete; do not repeat super/stock restoration.
Keep identity/slot/topology, signatures, battery/thermal, storage scope/backups,
independent fallback and permanent experimental one-use protections.
No new flash, GPT or protected-data operation. Destructive scope is separate.
Private credentials, packages and raw evidence remain outside Git.

## Running release and recovery

Running bundle `headless-server-selector-v8`, kernel `7.1.4-gf17befd4ef17`,
ordinary boot `a60a8d6d-5dda-4e15-9ab3-d46fb015ecf2`. Pinned SSH, current-boot health,
healthy selection, protected storage and all twelve installed hashes passed
again after full capture closure. Health committed at **65.542382 s**;
final readback was at **1336.860 s** uptime. The original installed shutdown
is present, exitrd is tmpfs, the restart provider is bound and staging is absent.

Source boot `545c66d9-35d7-47d9-9432-b54aaffbfcac` produced one clean
source teardown receipt using the corrected RAM shutdown and reached fastboot
in **11.801 s**. The subsequent installed return and full capture
passed independently. This does not qualify R01 or retry a consumed RAM claim.

V11 boot `96c3e790-a422-4723-b9ca-a5039da2a14a` provided the separately guarded
selection restoration. The later ordinary smoke remains FAIL because capture
hit a source NetworkManager teardown race and its first SSH probe timed out.
The readback confirms current service, not that failed smoke or autonomous R01
recovery. The prior S05 result keeps boot `af66d09d-f512-4954-a036-0904616e17af`.
Signed primary manifest:
`27f18d68cf2f7aaa791efb14de3ccc728506dca6b772b5ef006c890b3a787334`.
Other primary identities derive from the canonical expected record.

Installed boot-B loader unchanged:
`dcc487f17d6b4926ea633cbb242c62b598019e332640a81c1100c2d91087f723`.
Retained previous boot B:
`340f639276d9df3dfc073b8614a72f82507ea18c622c9df5d1e60f2c1622ccad`.
Signed V11 fallback manifest unchanged:
`a684bad14f84251ba342a87bde07da1f7b9aea412275ad124f7000716e94bbe2`.

Pinned USB SSH is `10.77.0.2`, alias `169.254.77.2`, fingerprint
`SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
V8 reached authenticated readiness in **98.215 s**. Local-root component PASS:
P24 RO/no replay, expected persistent overlay, 117 physical nodes, only
sda/sda23 writable, exact deployed userspace and current-boot readiness.
Wi-Fi, Tailscale and persistent-state services started. The full-hour load result is recorded below.

V8's experimental claim is permanently consumed, as are V6 and V7.
Do not retry their RAM execution or issue replacement claims. R01 armed the
accepted V8 record as pending; its exact healthy state was restored only after
fresh authenticated V11 and installed-file guards passed. The normal installed path is separate from a RAM
claim and does not constitute full release acceptance. V7's pending failure record and old
selector were archived during staged V8 installation. V5 accepted payloads,
prior claims, V11 fallback and the failed-soak scratch remain preserved.

## Proven startup correction

V7's CPU guard refused 62.4°C before applying any cap. Its CPU unit had waited
for tmpfiles because `PrivateTmp=yes` added an implicit dependency.
V8 uses `PrivateTmp=disconnected` plus inaccessible `/var/tmp`; all existing
power/storage guards and the 60°C thermal threshold remain unchanged.

Physical journal: CPU unit started at **20.654 s**, before tmpfiles at
**21.485 s**; policy application completed successfully. Verified maxima:
policy0 **1,209,600 kHz**, policy4/policy7 **1,555,200 kHz**.
Later read-only observation: all zones below 60°C, maximum **35.8°C**;
battery Full 100%, Good 29.8°C, 8.593 V, USB online, current 0.
This answers the startup question, not H03 regulation or a 60-minute load soak.

The cycle reused the existing kernel/DT/modules and boot wrapper. No flash.
Staging **2.126 s**, independent postcheck **0.747 s**, orderly V11-to-fastboot
transition **9.327 s**, exact fastboot battery 8.606 V / SOC gate yes.
Full capture completed **1,380.863 s**; route/firewall/profile/address cleanup
all PASS. No further phone execution was requested during that observation.

## Current checkpoint and next mandatory outcome

One coordinator owns this phone. S01–S05, S07 and F02 retain their completed
independent evidence. The failed R01 capture closed its full lifetime and all
host cleanup passed. The separate installed recovery capture after
normal-address SSH timed out has also closed; the later authenticated V8 readback
is recorded above. No phone controller is running.
Do not retry the consumed negative candidate or run a second phone controller.

On `f0a3420b`, full local CI passed **520.115 s** and all four jobs passed in
GitHub run **34214045938**: exact head, merge compatibility, publication and QEMU.
The original failed CI and USB-teardown capture remain preserved. The receiver
fix permits only precisely tagged ENOENT/ENODEV followed by positive absence
before target observation, within the existing 150 ms check. Identity mismatch,
permission errors, unresolved discovery and post-target loss still fail.

Fresh S01 reached authenticated local-root SSH in **93.193 s** and completed
its full **1,380.504 s** capture. Fresh S02 passed four 256 MiB USB/Wi-Fi transfer
directions in **303.671 s**; fresh S03 recovered all four services in **35.081 s**.
Both independent replay checks passed on that same boot. Earlier S03 r1/r2
remain FAIL; r3 and its actual producer revision are retained.

Fresh S04 passed **102.744 s**: one 64 MiB file was written/fsynced, survived
one ordinary reboot, read back with the expected hash and was cleaned by exact
file identity. SSH returned in **93.850 s**. The complete **1,380.582 s** capture
had no failed diagnostics, and its independent S01/S04 checks passed. The
original failed S04 capture is not relabeled. Its old scratch, the existing
acceptance namespace and unrelated files remain preserved.

S05 passed three distinct ordinary boots in **330.639 s**. Per-boot closed
observations took **103.910 / 102.807 / 103.412 s**; healthy-state observations
took **102.849 / 101.872 / 102.368 s**. Each started a full failure receiver
before one reboot request. Successful capture closure used the qualified full
S04 baseline plus the new exact healthy record; no failed boot was retried.
The independent three-boot checker passed. Kernel, DTB, signed archives,
installed boot B, selector and V11 fallback are unchanged.

On `af960758`, full local CI passed **526.883 s** and all four GitHub jobs
passed in **34221548267**. S07 then measured **3600.030 s** of combined load;
its full run completed **113 storage windows and 188 transfers**, each 64 MiB.
All workers stopped and exact scratch cleanup passed in **3666.628 s** overall.
The independent S07 checker passed in **68.277 s**. Old failed-soak scratch and
receipts remain preserved; this successful run has fresh identities throughout.

Across 367 heartbeat samples, maximum thermal-zone temperature was **51.4°C**,
battery temperature at most **30.8°C**, minimum pack voltage **8.413 V**.
Final power was Good, 30.8°C, 8.436 V. No new kernel messages appeared during
the measured load; ext4 error counters for loop1, sda23 and sda24 stayed zero.
Backing-device I/O and log continuity passed the original strict criteria.
This is endurance evidence; H03 retains its separate radio-free charging method.

Exact V8 F01 passed **85.412 s** using disposable networkless QEMU disks;
interrupted-update recovery succeeded and genuine corruption was rejected.
The original kernel/archive/root and protected fixture stayed unchanged.
F02 passed WPA/DHCP recovery in **29.141 s**, with three authenticated Wi-Fi
endpoint checks and unchanged radio/core service identities. Independent replay
passed; the sole coordinator closed in **30.104 s**.

The existing `headless-acceptance-rescue-v8` uses the same kernel and base Arch
root as the server. Its sealed runtime still matches all eight historical
runtime files. Fresh paired-root A01/C02 passed **66.261 / 76.473 s**. Its
September-6 original boot, capture, watchdog and 61 charging samples are retained;
the 600.265 s firmware-Full interval reproduces its original result offline.
That rescue claim remains consumed; signed V11 remains the independent fallback.

The dispatcher now supports an explicit `rescue_companion` receipt sharing
the primary's exact kernel and base-root files. Completed H01/H02/H03 replay
checks original producer versions, full capture/cleanup, paired composition,
raw samples and original boot/source identities. It grants no boot authority.
Portable and actual retained-data regressions passed; the integrated focused
suite passed **138 tests per mode in 20.793 s**.

On `be0a8d2e`, full local CI passed **533.795 s**, and all four GitHub jobs
passed in **34229955565**. One explicit paired receipt then passed H01/H02/H03,
S01–S05, S07 and F02 in **153.915 s**. Final source/artifact revalidation passed;
the original producer revisions and distinct rescue/server boots remain intact.
The rescue rows took **1.568 / 1.518 / 1.518 s**; S07 replay took **68.672 s**.
These are offline replay times, not fresh physical observations. Full release
qualification remains false; powered-off startup and controlled failed-boot
recovery remain outstanding.

R01 preparation confirmed that an ordinary watchdog reboot after a RAM-only
failure would still select healthy V8. That alone does not prove return to V11.
The existing trial helper offers a narrower preparation route: healthy-to-pending
rearming followed by a different trial's rejected health acknowledgment leaves
V11 selected at the next loader entry. The new regression passed on the host
and exact ARM64 helper, normally and optimized; all four 17-test suites passed
in **8.978 s** (one ARM-only test skipped in each host run). Retained V8 helper,
health and rollback bytes match current source; its outer timer is 900 seconds.
On `a1f9a10c`, full local CI passed **545.761 s**, and all four GitHub jobs
passed in **34232752925**. Unsigned `headless-recovery-negative-v1` target twins
then matched after **8.225 s**; only the trial descriptor and its checksum
manifest differ from accepted V8. Kernel, root, services and rollback are reused.
No signing, candidate registration, new claim or phone action has occurred.

The private V8 arming primitive passed six isolated ARM64 integration cases
normally and optimized, including namespace containment and lost-reply handling;
six synthetic guard tests per mode cover boot, power and storage refusals.
V11 has no Python, so restoration uses a separate sealed-shell generator.
Its six cases passed in **12.268 s** with the actual V11 BusyBox and canonical
ARM64 helper; kernel, sysfs and mount observations were explicit fixtures.
These are component tests only. A separate passive two-boot receiver now
preserves the original receiver's exact bytes and prior evidence bindings.
It requires an explicit canonical R01 fallback, a completed initial root
handover and positive USB absence before accepting one distinct rescue boot.
Premature/third-boot loss, wrong identity, unclassified teardown, networking
errors and earlier failures remain fatal; the capture lattice is unchanged.
Its 15 portable tests passed normally and optimized, and the original receiver's
33 tests passed. The receiver-only active checkpoint passed **47.789 s**.

The read-only negative-health observer requires the exact helper-refusal journal
sequence within the failed unit's execution, the unchanged installed pending
record, current-boot SSH/core readiness, sealed health/rollback bytes, an armed
900-second timer, and safe power/storage. Its nine focused tests include actual
bounded file reads and pathname replacement; malformed or unrelated failure
cannot qualify. Raw SSH output is retained before post-read topology checks,
including partial output on timeout. The one-shot controller, autonomous timer
stream and complete R01 evidence replay still need integration, followed by
signed packaging, admission and fresh physical preflight. No new phone action,
claim or full release qualification is implied by these observer components.
The combined active tier passed **45.383 s**; both focused suites also passed
optimized, with all recorded runtime/producer inputs unchanged. Full integration
CI and publication remain pending with the controller/evidence work.

Private rollback journal replay now checks the retained Arch catalog's fixed
service-job identifiers, the exact boot, PID 1, job ID, execution ordering and
callback deadline. Eight replay tests per mode and five shell cases passed;
the shell used the unsigned negative target's actual BusyBox timeout under
QEMU with explicit host/synthetic fixtures. The V8 source-to-fastboot RAM
shutdown delta also passed exact sealed-shell syntax and reversible byte checks.
It preserves teardown/poweroff and is separate from the unchanged negative
target shutdown. The first namespace fixture failure remains recorded; no live
transition, state arming, candidate execution or new claim has occurred.

The private controller ordering engine passed nine fault-injection cases per
Python mode. It fsyncs exclusive phase intents before callbacks, refuses phase
re-entry, preserves full capture after ambiguous execution, and requires a fresh
independent V11 guard before restoration plus a distinct healthy ordinary V8
boot afterward. User interruption permits cleanup without later mutations.
The generated source-side arming and RAM-transition scripts then passed eight
namespace execution cases in **0.640 s**, using the real ARM64 trial helper and
sealed BusyBox. Physical guard observations were explicit fixtures; a harmless
recorder replaced reboot. Genuine file metadata, exclusive publication, RAM
replacement, chroot syntax and mount-namespace containment were exercised.
Wrong state/source, symlinks, existing backup state and failed reboot replies
were handled without retry or changes to the original synthetic trial state.
The import-only private driver now implements every controller phase. Eleven
boundary tests cover raw reply retention, timeout/no-retry behavior, claim-account
selection, exact fastboot fields and the twelve-file installed inventory. The
inventory derives payload hashes from canonical primary/fallback manifests and
pins their signature companions. Local admission additionally requires the
exact six artifact roles, canonical restoration helper, unchanged producer
closure and exactly four successful CI jobs. Twenty-two admission cases passed
in **0.651 s**, using explicitly synthetic canonical/CI records and real file
pins, source hashes, primitive compilation and inventory derivation.

Actual driver restoration passed five namespace cases in **43.915 s**, using
the V11 BusyBox and ARM64 helper under QEMU. Lost staging/restoration replies
were not retried; exact fixture state and helper leftovers were retained. Five
execution-child cases passed in **1.217 s** with real disposable claim handling
and sealed-memory snapshots, while a harmless sink replaced fastboot. Failures
after consumption kept those fixture claims consumed. The real V8 claim was
checked read-only under its existing lifecycle account and stayed unchanged.

The offline R01 consumer and matrix dispatcher now accept a pinned completed
input envelope. They independently replay the full ordinary S01 prerequisite,
all raw controller commands, negative state/journal, two-boot capture and later
ordinary health. A regression caught consistent but wrong primary trial IDs;
those now refuse. The integrated checkpoint passed **60.500 s**, including
active **48.502 s**, with all inputs unchanged. Six subsequent tests exercised
the actual Driver/Core phase sequence and public replay with synthetic
transport/clock/admission in **6.581 s**; restoration never converted a failed
experiment into PASS. That checkpoint predates the reset-log binding.

Bounded reset diagnostics read only already-mounted pstore locations before
arming and after full capture on V11. Absence, unsupported mounts, read errors,
truncation and overflow are explicit; empty pstore never proves reset cause.
Twenty cases passed with both actual sealed BusyBox binaries in **6.347 s**.
They caught and corrected disabled glob expansion that had skipped present
records. The original failure and raw logs remain private; fixture bytes were
unchanged. Five public protocol tests cover malformed/stale/ambiguous evidence.

The latest combined checkpoint includes the reset-log binding and passed
**66.838 s**, including active **55.014 s**, with sources unchanged. All six
actual phase simulations passed again against the current producers; no real
transport, receiver process or claim was used.

The fixed root entrypoint now binds all nine private sources and hands closed
evidence to the desktop account only after every owned producer exits. Exact
primary/fallback manifests and signatures were verified from retained artifacts;
27 admission cases passed in **0.659 s**. The complete binding assessment
`r01-controller-bindings-r2` passed **0.103 s**, retaining compatible earlier
restoration coverage and the current full entrypoint simulations.

The full negative target cannot fit beside the unchanged ASUS kernel in the
existing 96 MiB RAM image. A separate R01-only helper requires an exact
**128 MiB** image, its canonical hash and consumed claim, plus a fresh single
unambiguous bootloader download-capacity response before consumption. Existing
96 MiB boot helpers and partition sizes remain unchanged. Seven helper tests,
twelve driver boundary tests, raw replay contradictions and the active suite
passed in **60.939 s** (active **55.566 s**). The actual 128 MiB execution child
passed five cases in **1.704 s**; six current lifecycle simulations passed
**6.976 s**. These use disposable claims and simulated transport, not a phone.

Signed twin packaging passed **24.182 s** with byte-identical outputs and sealed
signature verification. The recovery archive is 77,011,442 bytes; the padded
RAM boot image is exactly 134,217,728 bytes. Its canonical record now binds the
actual image, distinct negative trial and unchanged V11 fallback. Registration
consumer tests passed in both Python modes in **3.275 s**. Exact negative A01/C02/C01 subsequently passed
**77.695 / 96.128 / 134.995 s** on `b00a1b81`, retaining unchanged root/upper
bytes. Subsequent full integration CI and the physical result are recorded below.

The first exact negative A01 ran every functional check successfully but failed
its unchanged 120 s deadline at **146.582 s**. Root/upper hashes remained exact.
A read-only sparse-hash probe reproduced the entire accepted 34.36 GB logical
root digest in **20.903 s**, reading 4.19 GB and hashing 30.17 GB of holes as
zeros. A01 now reuses the already-tested C02 hasher for both root/upper checks
and records timings. The original failure is retained; the corrected exact
A01/C02/C01 run passed. Focused and active
validation passed **55.595 s** (active **55.430 s**), with source inputs unchanged.



Full integration on `c0025810` passed **532.692 s** locally and all four GitHub
jobs in **34266500765**; PR1 remains draft. The first controller stopped during
read-only preflight because its private userdata guard assumed `8:23`. Actual
userdata is `259:58`, with matching partition identity, geometry, mount and
inode. It made no state change or claim. Corrected private guards passed sealed
V11 shell/helper tests, full lifecycle simulations and connected read-only
preflight. All original failed evidence was preserved.

A fixed continuation then consumed the negative RAM claim once. The bootloader
accepted the exact 128 MiB image, but boot
`8f739c2f-c755-4ec7-8fc0-2f346d0fae1f` reported `final-storage FAIL` with
`ufs-q0-s0-j1-e0` before switch-root. It returned to fastboot. Full capture
closed at **1,380.488 s**, all four cleanup steps passed, and 60 files transferred
unchanged to the desktop reader. Independent replay refused qualification.
The journal count identifies one recovery match outside the allowed overlay
exception; it does not identify the filesystem or prove corruption/causality.
R01 is **FAIL**, with no autonomous V11 return and no experimental retry.

A separate normal installed boot reached V11 switch-root, but SSH to `10.77.0.2`
timed out. Its full capture closed with all cleanup checks passing. A pinned
read-only probe of `169.254.77.2` authenticated the same V11 boot and observed
the exact pending record, protected partitions read-only and safe power.
Fresh readiness, all twelve installed hashes and sealed storage/power guards
then passed. The existing helper restored V8 selection to its exact healthy
record and was removed. Assisted restoration cannot convert R01 to PASS.

The later ordinary reboot check could not connect to diagnostic SSH: the passive
receiver classified V11 as the source and skipped preparing its diagnostic
route. No reboot command reached the phone; the failed controller retains its
full observation window. A separately gated ordinary service check must first
verify closed evidence, unchanged source-boot continuity and healthy selection.

The repository observer duplicated the same `8:23`/`2071` assumption. Its
correction binds the runtime allocation to the exact userdata partition and
geometry, then matches mount and pending-record device IDs. A second observer
fix records terminal transport failures once per transition instead of flooding
the log on every poll. Both preserve strict failure classification and the full
capture lifetime. Full local CI for those two fixes passed **498.013 s** on
`91ff9e24`, with terminal completion and unchanged source. Two earlier checkout
setup failures are preserved; the pinned boot tools and canonical 12 KiB template
were restored from verified retained inputs.

Ordinary capture now prepares the diagnostic route before declaring the source
ready. It still rejects source stage frames and requires an observed disconnect
before accepting a new target. All **35** focused receiver/network tests pass,
including pending route convergence and permanent route failure. Full CI for
that correction passed **492.129 s** on `9d4cd138`, and all four GitHub jobs
passed in **34276164597**. A fresh ordinary reboot was then acknowledged and
V8 reached switch-root. During source teardown, repeated source route setup
raced `nmcli -g`; capture retained a permanent failure. The first normal-address
SSH probe then timed out. The smoke controller closed FAIL in **1,384.354 s**
after its full capture, with all four owned network cleanup steps passing.

The receiver now retains successful source-route preparation until an observed
disconnect instead of repeating NetworkManager setup during source shutdown.
Initial route failures remain fatal, source stages remain inadmissible, and new
target routing still runs after disconnect. A retained-event fixture reproduced
21 setup calls and the failure before the fix; all **36** receiver/network tests
pass after it. Full local CI passed **499.610 s** on `95cbc09d`, with its
completion marker and unchanged source; all four GitHub jobs passed in
**34278168035**. After full capture closure, fresh pinned SSH verified the same
V8 boot, readiness, local root, healthy selection and all twelve installed hashes.
An optional reset collector initially refused an extra serial field locally;
its corrected three-field call and final same-boot storage/state guard passed
in **0.640 s**, preserving and independently replaying the required reads.
Pstore remained present but empty, so reset cause is still unproven. No further
reboot or selection change occurred. Kernel, root/upper images, signed payloads
and claims remain unchanged.

## Mandatory results

Do not combine incompatible releases or simulation and physical evidence.

| Outcome | Current result / next action |
|---|---|
| A01 / C01 / C02 | V8 offline PASS; A01/C02 include complete retained upper |
| H01 / H02 | Explicit paired rescue replay PASS on `be0a8d2e`; original rescue boot retained |
| H03 regulation | Paired dispatcher PASS on `be0a8d2e`; all 61 original raw samples revalidated |
| S01 local startup | Fresh V8 full ordinary capture PASS on `f0a3420b`; latest 93.850 s to SSH |
| S02 transfers | Fresh V8 PASS on `f0a3420b`, four 256 MiB directions in 303.671 s |
| S03 service recovery | Fresh V8 PASS on `f0a3420b`, 35.081 s; earlier failures retained |
| S04 durability | Fresh V8 file and full capture PASS; original failed capture retained |
| S05 repeated boots | V8 three-boot sequence and independent replay PASS, 330.639 s |
| S06 powered-off start | NOT RUN |
| S07 combined load | V8 full 3600.030 s observation and independent replay PASS on `af960758` |
| F01 / F02 | Exact V8 F01 PASS 85.412 s; fresh F02 plus independent replay PASS, 29.141 s |
| R01 recovery | FAIL: early final-storage gate; negative claim consumed, full capture retained |

## Evidence, fast loop and retention

Use [development](development.md) for impact-based selection and cache reuse.
Full V8 A01/C01/C02 took **88.128/131.751/104.415 s**; unchanged artifacts reused.
Complete-upper correction `cdfe00572b81fca619231bdba26702bf8982667d` is pushed:
focused **18.252 s**, full local **533.553 s**, all four GitHub jobs PASS in
34172685138 (including exact-head/merge). Retain those original results; do not relabel them as testing later changed code.

Preserve the complete inactive upper snapshot used for composition:
`dff8988f3c2f4c5204d2e827114f63e54068acc530a75010dd2d522de3795388`.
Normal persistent state may change after boot; do not relabel the snapshot.
Private current work: `rog5-cpu-startup-20260908.kjE4IqCf`.
Detailed V6/V7 failures, V8 staging/runtime proof, fixture fixes, original
timings and exact retention procedures are in the
[existing dated report](../test-results/2026-09-05-headless-acceptance.md).

Home has about 6.6 GB free with the two isolated observer checkouts; preserve the 3 GiB reserve. V5's lossless reverse
delta and durable V7 base must stay together. Unique archives still occupy RAM:
no host reboot until retained safely. Never remove failed-soak scratch, accepted
payloads, private evidence or claims. Leave unrelated SteamOS CEF port 8081 alone.
Schedule heavy A01/C02 separately from full local CI; remote checks and bounded
independent preparation may overlap. No test deadline or release gate is reduced.

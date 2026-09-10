# Wi-Fi S12 shared-rail checkpoint

Wi-Fi is not yet functional. Preserve the working V11 and stock slot A. All
seven previous native RAM trials are permanently consumed; v6 did not run the
radio probe. No flashing, storage transaction, or persistent selector change.

## V7 evidence

Source22e659189593c1b792e309a08ccb63f5454acc01 passed all GitHub jobs in
run33346483047. The source shutdown implementation had passed full local CI
in456.869s; its subsequent test/data-only delta passed focused checks in9.073s.

The source ACM recorded clean teardown and native executor entry at
1788138928.035538. Target SSH arrived at1788138965.547197, approximately37.512s
later. All117 UFS nodes were locked RO before radio activation. The PMIC PON
snapshots before handoff and before the radio probe were byte-identical.

At target uptime46.151284, S12 enable entered. The trace then captured a
synchronous RPMh voltage request at0x40100, value0x548 (1352mV), response-bearing
message0x10108 and RSC submission return0. No completion, voltage-call return,
or enable-register request was recorded. Missing tail does not prove those
events never happened. UFS PHY power-on returned0 about63ms earlier; this is
temporal evidence, not proof of an electrical fault.

Afterward, V11 recovered and PON showed PS_HOLD warm-reset count6→7. No panic
dump exists, and this reset category does not identify the software cause.
The real trace is now a regression fixture: `s12-voltage-submit-reset.json`.
Failure class: new shared-rail/hardware boundary with an R8 observability gap,
not an established host parser or radio-firmware failure.

## Authenticated stock contract

All60 retained official WW33 DTB/DTBO compositions agree; the completed audit
took727.697s and is retained privately, not recomputed. S12 is `smpb12`,
PMIC5 HFSMPS, always-on, active+sleep set3, initial1256mV, range1224–1360mV.
Consumers include UFS VCCQ, WLAN RFA2, Bluetooth and PM8008 inputs.

The20 DTBOs set UFS parent load210000µA through the exact `ufshc_mem` fixup.
Vendor `ufs-qcom.c` sets that load before enabling the parent. Its regulator
mode threshold is200000µA, so active UFS selects AUTO, not RET. Suspend can
remove the load. Always-on does not itself mean permanently AUTO.

Actual V11/v7 DTBs instead parent L9 through S11; v7's S12 Wi-Fi node also
lacks always-on. Do not immediately reparent it or add always-on: that would
flush the pending1352mV request during early UFS initialization, before capture.
The exact mainline HFSMPS510 ops lack load-based mode selection, so merely
copying a210mA load is insufficient. Stock batching voltage+enable is also not
guaranteed for every call; valid/changed fields determine the request.

## Smallest discriminating implementation

`tools/s12_ufs_vote` uses the regulator API, not raw RPMh/MMIO writes:

- `query`: exact consumer lookup and cached observations, no mode/enable call.
- `mode`: one NORMAL/AUTO request and checked return/cache; no voltage/enable.
- `held-enable`: separate later action requiring AUTO, one enable and a retained
  module/consumer reference until reboot. It can flush1352mV and is not passive.

Identity checks bind the board, fixed PMU node, exact phandle, PM8350 PMICb,
cmd-db address0x40100, voltage window, initial RET and fixed always-on VPH
parent with no GPIO. A trylock refuses a concurrently bound PMU driver. No
dummy/alias regulator fallback, disable call, or voltage setter is available.
Query/mode release their independent references without restoring RET; a
successful held vote self-pins and cannot be ordinarily unloaded. It protects
balanced consumer unwind, not force-unload/provider removal or other mode writers.

The new DTB changes only S12's allowed runtime modes from the v7 artifact;
initial RET, voltage, UFS wiring, Image, initramfs and firmware remain unchanged.
Independent review caught vendor AUTO=3 wrongly copied into the prototype:
mainline3 is HPM, which would coerce NORMAL to FAST/PWM. Correct permissions
are `<0 2>`; module code uses binding constants. Before the fix, the regression
accepted the unsafe pair and rejected the correct pair. No faulty prototype
was loaded on the phone. Query remains the first live test because regulator
acquisition itself resolves dependencies.

## Offline proof

- Focused tests:3 module tests (25 mode pairs and8 action/error cases),8 DT
  tests and9 trace tests pass in0.294s command wall time.
- Exact cached V11 module twins match; no Image/wrapper rebuild. Compilation
  intervals from copied-source to KO mtime:3.227s and2.883s, excluding container
  and unchanged-kit hashing. Retained probe/build fixtures consume under7MiB.
- Module SHA-256:
  `78c5bfdd05ddf49a03e012fbd2993982e1a4124ce89b6457274d63843f7c3413`.
- DTB twins SHA-256:
  `d9b53f4a43a309642a2a8cfe8ad85ea1a2a2bdbce25b7faa06b0eb64d434305b`.
- Full-system QEMU with the exact V11 Image reaches the new module's identity
  guard, rejects the generic board and reports no unresolved symbols/BTF error.
  This proves load compatibility, not physical rail behavior. MODVERSIONS is
  disabled; no symbol-CRC enforcement is claimed.
- Active tier passed in84.841s. Host-side signed bundle twins packaged in0.728s;
  the generated exact-record registry binds their tools/module without creating
  or consuming a one-use claim. Full publication checks precede live admission.

Next: finish publication checks, then one signed RAM-only query/AUTO probe with
RPMh ACK capture, read-only UFS checks, bounded rollback and PON comparison.
Do not automatically proceed to held-enable or radio activation on missing
evidence. No successor has yet been admitted or booted at this checkpoint.

## V8 consumed: an earlier charging-readiness gate

The frozen source above was committed as
`a2673435d1777308b044c8ec8b336df6a565c5f4`. Full local CI passed in454.099s;
all four jobs passed in GitHub33353250552. Signed twins and the exact phone
verifier preflight passed. The one-use claim was consumed at1788146704.667329.

Source ACM proved executor entry at1788146710.737040. At1788146718.985 the
target reported `ufs-ready FAIL power-usb-usb-offline` through working NCM.
Target boot: `615ca385-7b23-4f96-ab0a-6f99df118f74`. No SSH, S12 query,
AUTO vote, held-enable or Wi-Fi probe followed. This is not an S12 test result.
The controlled rollback went to fastboot, not automatically to V11.

Exact serial/product/topology and active B were verified there:8641mV and
battery-soc-ok=yes. One normal `fastboot reboot`, without any payload/flash,
restored unchanged V11. Pinned SSH proved boot
`e7f26eff-09a8-47ab-896c-74f353272973` at1788146855.935804. State/Tailscale
are active, onlysda/sda23 writable, battery Good8.627V/29.9°C, USBonline1,
5.018V input and500mA limit. Temporary management address/firewall access and
source ACM are gone. Slot A, B loader, selector, GPT and filesystem layout are unchanged.
The postmortem includes the explicit fastboot reboot/hard-reset transition;
do not interpret its reset-counter reset as the radio failure's cause.

New fixture: `s12-mode-v8-usb-offline.json`, parsed by the actual stage parser.
The historical sealed charging helper exactly matches the repository version:
it waits for sysfs nodes, then takes just one online sample. Node presence
does not establish completed charging negotiation. The live record proves
online0 at that instant, **not** whether it would have settled in the same boot.

The minimal helper correction waits for online1 within the same shared node/
value sampling budget:200 polls and a20s monotonic deadline, never two windows.
It rechecks battery voltage/temperature each pass, immediately rejects invalid
or unsafe telemetry, and still requires valid input voltage/current, sink/device
roles, NCM route and no storage before proceeding. No charging-control write.
Checks before/after the property reads reject readiness arriving past deadline;
in-flight kernel/RPC reads are not preempted by this shell deadline. The driver
has a1s request-ACK timeout; kernel stalls remain the separate rollback layer's
responsibility. No watchdog/rollback setting was changed.

Six fail-first assertions exposed the one-sample/late-readiness behavior.
Six focused tests now pass (0.269s host,2.098s exact sealed BusyBox/QEMU),
including later unsafe temperature, absent/invalid online, never-online,
late-online and already-spent node budget. The extraction initially needed
parent directories and the sealed musl loader; those host-only preparation
errors were corrected without another phone operation. BusyBox SHA-256:
`97d52efa149563c8d886e3670e2496d4140d3c54138017afd3a105e0397fae2e`.

Classification: R3 readiness semantics/R4 sampling budget; actual reason for
the transient or persistent online0 remains unknown. Repack only the target
initramfs after publication checks. Keep the proven module/DTB twins, Image,
firmware and wrapper; V8 remains permanently consumed. No successor is issued.
The helper emits advisory first-offline and ready/deadline kernel records with
battery readings and poll count, so a successful boot can prove whether the
wait was actually needed rather than merely assuming a race was fixed.

The final observed-helper initramfs twins reproduce in16.347s:
`edf60a81162b7b64fc334e8450283c0c061fd4fbb6d8cc95a6a6cd1ba1aea343`.
Only `sbin/rog5-load-persistent-power-usb` differs from the retained V11 newc
archive; all other payloads, permissions, owners, timestamps and metadata match.
An independent GNU cpio extraction matches the updated source. The earlier
unobserved-helper repack is retained but not selected. The active tier passed
in84.097s; subsequent advisory-log assertions pass in the exact BusyBox tests.

Fresh signed S12-ready-v9 twins reuse the same Image/DTB/modules/tools and package
in0.565s. Only the initramfs, bundle identity and signature differ from v8.
Its exact-record row is generated from that build receipt; no claim exists yet.
Complete frozen-source publication and connected gates before any execution.

## V9 passed: AUTO acknowledgment and stable read-only operation

Source `220ba05b351e226ae883ac3f22ad4cd5683b2f52` passed full local CI in
450.562s and every job in GitHub33354938967. The signed native verifier and
connected non-consuming preflight passed. Its sole claim was consumed at
1788148580.964392. Target `996b7652-d804-4ce2-a83f-7c7ed5a33ae0` reached
SSH at1788148619.470807; PON snapshots before/after kexec were identical.

The helper reported ready at uptime3.856686, attempt8, battery8.626V/30°C and
USBonline1. No first-offline record occurred: these polls were for node appearance.
This successful boot does **not** prove V8 would have settled in the same boot.

With117 nodes RO, query returned0 and emitted no S12 request. Its cached enable
state was -22/error, correctly non-fatal, not evidence the physical rail was off.
AUTO then sent0x40108/data6 at uptime34.075965. The native acknowledgment
arrived at34.076016; the API returned0 and cached mode changed8→2. Neither
0x40100 voltage nor0x40104 enable was sent. The cached1352mV is not a physical
voltage measurement. No held-enable, PCIe-power or Wi-Fi activation occurred.

Ten repeated1MiB buffered reads from read-only p24 and NCM checks passed;
subsequent reads may be cached, so this is not ten independent physical UFS
transfers. Prefer direct I/O for the next hardware-read check. Battery stayed
Good/30°C and all117 nodes were RO at completion.

A deliberate normal reboot restored V11 boot
`76daa970-fd40-4f93-9dad-ab5b821bc6e0`, first pinned SSH1788148699.309353.
State/Tailscale are active; onlysda/sda23 writable, Good8.625V/30°C, USBonline1
and NCM configured. Host management address/8079 access were removed; source
ACM disappeared on reboot. No flash, slot change, layout or selector mutation.
PON after the deliberate reboot includes that transition and is not a separate
crash diagnosis. V9 is permanently consumed.

Next: one fresh exact-record protected-enable/radio experiment, with the held
module retained until reboot, verified AUTO first, direct read checks, trace and
rollback budgets covering every stage. No successor is currently prepared.

## Protected-enable/radio successor prepared, not executed

The private canonical cycle plan defines S12-held-v10, the source V11 boot,
artifact inputs and timing. Signed bundle twins package in0.567s; Image, DTB,
initramfs, modules and firmware are identical to the verified V9 composition.
No kernel/module/wrapper build. The exact claim row is generated from that
receipt; generating it does not create or consume execution authority.

Query and AUTO gates remain first. Held-enable must return0, retain module
reference count1 and deliver both voltage0x40100/data0x548 and enable0x40104/data1
ACKs. The module must not be unloaded afterward. Three distinct1MiB O_DIRECT
reads and safety checks precede optional radio startup. O_DIRECT compatibility
was verified with one read-only aligned read on the exact V11/p24 baseline.

A600s operational timer is armed immediately after identifying target SSH,
before target setup/assertions, and is never canceled to extend radio time.
Radio entry checks the target monotonic clock after SSH/guard delays and refuses
entry at30s. A whole-probe timeout includes preflight, guards and collection;
its TERM+KILL budget ends30s before the original timer. The old554s arithmetic
was only nominal: it omitted unbounded guard/collection overhead and is not
used as a hard execution guarantee. The later radio timer cannot replace the
earlier one. The initramfs900s watchdog is disarmed at switch-root, not counted here.
These userspace timers cover transport/controller loss, not a total kernel
lockup; panic=10 and the proven rescue routes remain separate existing layers.

Independent review caught exception paths that skipped fallback and a stale
host-side deadline check. The corrected controller wraps setup/probing in
boot-checked reboot/fallback handling, including timer-arm and retained-reference
failures. Eight power branches, three early exception paths and target-side
delay/deadline cases pass offline. No local full CI is
repeated for identity-only registry/docs changes: source equivalence to full-tested
220ba05b is checked structurally, plus focused exact-claim and artifact checks.

## V10 consumed: AUTO does not prevent the first-enable failure

Published9523b547470c914513d34b1159693e80fe8607db passed every job in
GitHub33356792433. Final focused source/artifact/controller checks took1.133s;
full source CI was carried from220ba05b rather than repeated locally. Only a
non-executable result-document correction remained outside HEAD at execution;
the verifier refused all unpublished executable/admission data and untracked inputs.
The reviewed controller also permits one boot-checked normal-reboot retry after
a failed recovery request and fresh proof that the same target is still running.
It never retries a power phase/kexec or unloads the held module.

The claim was consumed at1788151121.577742. Target
`b8cecb86-a043-404c-bc9f-408364af7571` reached SSH at1788151161.566439; all117
nodes were RO. PON snapshots before and after handoff were identical.
Query returned0; AUTO wrote0x40108/data6, got ACK at uptime40.234122 and
returned0. The subsequent held-enable logged cached mode2 and entry at41.281484.
No later regulator/RPMh trace or API return was delivered. Lost tail remains
possible; unlike v7, a voltage submission is **not directly proved** for v10.
No GPIO, PCIe PHY or Wi-Fi driver activation occurred.

The call's SSH transport returned255 at1788151197.989967; the recovery request
also returned255. V11 recovered as `3d760020-1bda-45b5-aedd-b30a3747f673` at
1788151237.486697. PON gained20 bytes, PS_HOLD warm reset count0→1. No panic
dump or exact faulting instruction is known. State/Tailscale, pinned SSH and NCM
are restored; onlysda/sda23 writable, Good8.624V/30°C. Host management address/
8079 and temporary ACM are removed. No flash, selector, slot or layout change.
Fixture: `s12-auto-enable-reset.json`; AUTO alone is no longer a plausible fix.

### Read-only follow-up

A targeted authenticated stock audit (one composition, three bases,20 overlay
deltas;13.23s) confirms enabled CNSS RFA2 config `<1350000 1350000 0 0 1>`.
No zero-voltage override or converged-list substitution applies. `need_unvote=1`
withdraws a later vote, not the initial request. Thus1352mV exceeds the stock
consumer's1350mV software ceiling; the provider ceiling is1360mV. This proves
a request-contract difference, not electrical overvoltage or the WW33 binary's
actual runtime behavior. The retained AOP image is stripped; no per-rail bound
has been established from it. Older aop_b backups differ and are not current evidence.

Opus was retried in safe, tool-free mode and failed authentication in1.218s:
expired OAuth could not refresh. No Opus review is claimed. The systematic-
debugging workflow keeps new voltage guesses paused while tracing state/data.

The exact kernel's existing regmap debugfs supports fixed-offset reads. Its
PM8350 map has16-bit addresses,8-bit values and a contiguous0–ffff range; each
printed register occupies9 bytes. A small static reader uses pread, never a
skip-by-reading fallback or full dump. It checks board/kernel/PMIC/map metadata,
then reads only identity, peripheral type/subtype, and documented HFSMPS510
configuration offsets. Read errors remain XX, not evidence of off/absent rails.
Programmed setpoints are not ADC measurements. No register write API, module
load, reboot, or persistent install is involved. Host syscall fixtures and exact
ARM64/QEMU fixtures pass; live read-only validation follows the active tier.

The active tier passed in83.826s. Static AArch64 twins are2680 bytes and share
SHA-256 `fc34f41ad0288641b12a57874fe8f55084ac3c8fa6dd9378ad59f4609f168b17`.
The live read completed in0.632s on unchanged V11, with no reboot/module load.
It read PMIC identity51/subtype30 and88 bounded peripheral-metadata rows.
No recognized BUCK/HFSMPS510 control was found in the sampled1400–3f00 window;
many registers returned XX. Therefore **no S12 voltage or enable measurement
was obtained**. This does not prove the rail absent/off or identify why each
read failed. Do not expand to arbitrary register/control writes.
State/Tailscale and the two-node write scope stayed unchanged, battery8.622V/
30.1°C; the copied RAM helper was removed after its hash was rechecked.

The retained WW33 AOP image is245760 bytes, SHA-256
`3ad5f97be3e2c4d5a2ea57d91ef9d3919d947fa4be1acac747589e94396f1f54`,
with no ELF symbols/sections. Metadata inspection did not establish a per-rail
limit or quantization rule. Do not infer one from literal-number searches.

Qualcomm's [RPMh readback series](https://patchew.org/linux/20260801-b4-read-rpmh-v5-v6-0-9fcb54928523@oss.qualcomm.com/)
was accepted into the regulator for-7.3 tree. It offers an APPS-vote observation
route, not physical aggregate-voltage measurement. A future read-only backport
must audit timeout/late-completion lifetime and avoid importing automatic
regulator-initialization changes blindly. No backport or new candidate is built.

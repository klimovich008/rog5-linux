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

A600s operational timer is armed before power changes and never canceled to
extend the radio window. Radio may begin only within30s of that timer's setup;
its unchanged17*(20+2)+30+60+90=554s bound then fits within600s, with16s margin.
Its own later600s timer does not replace the earlier one. The initramfs900s
watchdog is disarmed after successful switch-root and is not counted here.
These userspace timers cover transport/controller loss, not a total kernel
lockup; panic=10 and the proven rescue routes remain separate existing layers.

Eight offline controller branches cover missing prerequisites/ACKs, held-reference
failure, late radio admission and at-most-once activation. No local full CI is
repeated for identity-only registry/docs changes: source equivalence to full-tested
220ba05b is checked structurally, plus focused exact-claim and artifact checks.

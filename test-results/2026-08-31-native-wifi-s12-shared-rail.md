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

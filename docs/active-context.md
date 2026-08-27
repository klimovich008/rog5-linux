# Active ROG Phone 5 Linux context

Updated: 2026-08-27

This file contains only the current handoff. Historical cycles remain in Git
history, `test-results/`, and `docs/archive-index.md`.

## Device baseline

- Device: ASUS ROG Phone 5 ZS673KS (`lahaina`)
- Serial: `M5AIKN00F0353YH`
- Active slot: A
- Bootloader: unlocked
- Rescue OS: official ASUS WW33 / Android 13
- Build: `33.0210.0210.200`
- Known-good rescue functions: Android boot, stock recovery, powered-off
  charging, RNDIS/ADB

Slot A is the permanent charging and recovery route. Future Linux work uses
RAM-only `fastboot boot` until a persistent design explicitly preserves it.

## Active storage cycle

Generation 194 is consumed and permanently non-retryable. It reached mainline
UFS/NCM/key-only SSH, then froze during the redundant full 16 GiB source hash.
No clone-write marker was observed, but transport loss makes p24 disposition
unknown. Exact fastboot returned after 19m31s; the 900-second shell timer was
delayed by the same kernel/UFS stall and is not independent rollback.

Generation 195 passed and is consumed: p24 is non-ext4 and its first 4 MiB is
exactly zero-filled. The target and stock-slot-A fastboot proofs passed, and
the durable intent is `TARGET_ACCEPTED`.

Generation 196 is consumed before storage writes: the watchdog module loaded,
but an optional sysfs timeout assertion was incompatible with
`CONFIG_WATCHDOG_SYSFS=n`. Exact fastboot and fallback resolution passed.

Generation 197 is consumed at the same generic prewrite watchdog boundary; p24
remains untouched. No further writable successor is allowed without a finite
classification.

Generation 198 is consumed. The watchdog armed and target emitted the exact
`storage-locked` stage, proving the prior generic watchdog failures were not a
kernel stall. A host R7 parser typo allowed only `storage-relock`, closed the
listener, and discarded later evidence. The 900-second target fallback then
returned exact slot-A fastboot at the host wait deadline; a canonical fallback
record was captured and intent resolved `FALLBACK_RETURNED`. No p24 write path
was packaged. The parser and fallback deadline race are fixed offline; no
Generation-198 artifact may be retried.

Generation 199 is consumed before p24 access. UFS, NCM, runtime and key-only
SSH passed in 7.86 seconds, then clone admission found the watchdog helper PID
gone. No `source VERIFY` or write-window marker appeared. Exact slot-A fastboot
and `FALLBACK_RETURNED` intent resolution passed. The current blocker is now
watchdog userspace lifetime, not UFS, NCM, recovery, or the clone algorithm.
The next candidate must be read-only and capture the exact helper log/status
after its first 5-second ping; do not issue another writable clone yet.

Generation 200 passed read-only and is consumed. It proved BusyBox failed
`ENOENT` because `qcom_wdt` never loaded; dmesg identified an exact
`.gnu.linkonce.this_module` size mismatch. The rejected reconstructed module
was `0x4c0`; clean twins built against the actual g359 output and original
Clang-18/BTF environment are `3fcea56e...` with size `0x500`. Every watchdog
predicate now returns explicitly despite the outer `if !`, and admission waits
six seconds to cover the first ping. The next cycle remains read-only until
this corrected module is physically proven loaded, alive and reset-capable.

Generation 201 is consumed. The exact-ABI upstream module correlated with NCM
timeout and target loss about 13 seconds after enumeration, followed by stock
slot-A recovery. No reporter or storage-write path ran; intent resolved
`FALLBACK_RETURNED`. Do not issue another `qcom,kpss-wdt` candidate. The next
watchdog track is an offline port/review of ASUS/QTI `qcom,msm-watchdog`; the
phone must first be returned physically from unauthorized recovery to fastboot.

A read-only watchdog register observer is built offline at module hash
`b06271c6...`. It uses a private diagnostic compatible and only reads EN, STS,
BARK, BITE and clock rate from the stock MMIO range. No WDT registration,
interrupt or register write exists. Physical admission waits for fastboot.

Generation 202 is consumed. Even with no watchdog write or registration, NCM
disconnected at 12 seconds and stock recovery returned, proving the watchdog
is inherited armed. No storage write occurred. The next observer moves ahead
of power/UFS and publishes its register snapshot through the existing repeated
stage record before the inherited deadline.

Generation 203 is consumed: external-module relocation/probe still missed the
inherited deadline and no stage survived. Generation 204 is the active
module-free read-only successor. It uses exact sealed BusyBox `dd`/`od` on
`/dev/mem` immediately after NCM carrier, before power/UFS, and publishes the
register tuple directly. Target/manifest/wrapper hashes are `bb090ddd...`,
`596df1af...` and `8ecd4f34...`; no write path existed. Generation 204 is now
consumed after `watchdog-mmio-detail`: `dd | od | tr` masked the first command's
failure. The corrected target uses explicit four-byte files and publishes every
accepted register separately before the final tuple. Generation 205 is
consumed after exact `watchdog-mmio-en`; arm64 `/dev/mem` `read()` accepts only
mapped memblock RAM and rejects this MMIO page before access. Exact fastboot
and `FALLBACK_RETURNED` passed. A static read-only mmap helper now passes
offline twin and fixture tests. Generation 206 is consumed after exact
`watchdog-mmio-bus`: mmap succeeded, but the first APSS register read raised
SIGBUS. Exact fastboot and `FALLBACK_RETURNED` passed. Stop direct MMIO work;
evaluate standard kernel `softdog` offline for the Stage-2 clone rollback.
Exact-ABI `softdog.ko` twins now pass offline at `ab0175a4...`; no candidate
or phone execution has been created from them. Generation 207 passed and is
consumed: `softdog-armed-20` was followed by automatic exact slot-A fastboot
23.6 seconds later, with `TARGET_ACCEPTED` and no UFS/storage access.
Generation 208 is consumed before writes: runtime passed in 6.95 seconds, but
full source-tree verification exceeded 850 seconds with only `source VERIFY`.
Exact fastboot/cleanup passed; softdog and the p24 write window were not armed.
Generation 209 is consumed: source admission and softdog passed, then the p24
`e2image` clone hit its 420-second bound. Exact fastboot/cleanup and
`FALLBACK_RETURNED` passed. p24 is partial/unknown and requires read-only
postmortem before another write.
Generation 210 is consumed read-only: p24 has ext4 magic but `dumpe2fs` failed,
proving a partial/corrupt clone. Exact fastboot and `FALLBACK_RETURNED` passed.
The next writer must overwrite all known allocated source extents directly.

Normal slot-A Android boot now enters stock recovery because userdata was
deliberately converted to the Linux ext4 filesystem. Keep the phone in
fastboot between development cycles. Generation 160 returned directly to
fastboot after exposing the persistent-root NCM gadget for 23 seconds. The host
had selected the obsolete staging product, so it never activated networking.
The corrected successor changes only that host selector and early initramfs
observability; it does not flash or replace the kernel. Generation 161 consumed
that cycle and reached mounted local Arch before an unreachable staged-seal
policy branch caused exact `root-verify` rollback. The next target changes only
that control flow. Generation 162 then passed local Arch/systemd/key-only SSH
in 325.697 seconds. Its final reboot entered stock recovery because exitrd
omitted the restart2 helper referenced by shutdown; the repeat adds only that
helper and requires exact fastboot success.
V54/Generation 163 repeated local Arch/systemd/key-only SSH in
338.141 seconds and returned to exact fastboot; the RAM-only local-root MVP is
now reproducible.

Generation 164 consumed and permanently revoked the current RAM-only read-only
storage preflight. It passed exact UFS/GPT/ext4 geometry with 1,219,496 minimum
ext4 blocks, all block devices read-only, zero mounts, and no write; automatic
rollback reached exact slot-A recovery on the anchored side port. The next gate
is the separately reviewed Stage-1 shrink/GPT transaction. Authority-free
Generation 165 now binds the current twin initramfs and exact private execution
record. The user gave exact final confirmation. Generation 165 was consumed
before collector/ACK/write because its host template retained a short USB path;
exact slot-A fallback passed. Byte-identical-raw Generation 166 corrected only
that private host path, reached durable backup ACK, and shrank
ext4, failed at the target multi-option S60 `sgdisk` edit, restored the original
GPT, and returned through slot A. The successor seals the offline-verified
desired GPT backup and uses the live-proven single `--load-backup` operation.
Generation 167 then failed before S30/ACK/write on the stale pre-shrink
filesystem-block guard and returned through slot A. The unissued successor
changes only that guard to the current 51,124,000 blocks. Full CI passed.
Generation 168 then lost its pre-S30 record before the anchor-first
collector started; no ACK/write occurred and slot-A fallback passed. After the
required systematic/Opus review, Generation 169 reissues byte-identical raw
target bytes with a receive-only collector started before boot. It stops at S30
without readiness or ACK. Stage 2 is authorized only after Stage 1 passes.
Generation 169 captured a receive-only verdict but discarded it before
publication when expected departure failed final USB revalidation. No write
occurred and slot-A fallback passed. The host-only successor writes validated
evidence before classifying `DEPARTED` versus `CHANGED`. Generation 170 is a
byte-identical-raw receive-only successor. Generation 170 captured exact
`S00_CONFIG/invalid_private_config` with zero host bytes and no write. The next
receive-only diagnostic exposes the exact finite config predicate and still
stops at S30. Generation 171 passed exact S00-S30 with zero host bytes and no
write, then returned through slot A. Storage-layout rollback now invokes the
sealed restart2 bootloader helper before generic reboot, removing the recurring
stock-recovery/manual-button bottleneck in future cycles.
Full CI passed for production Generation 172. It bound the exact S00-S30 proof,
current filesystem, sealed GPT load, normal fresh-backup/ACK collector, and
restart2 fastboot fallback.
Generation 172 then passed fresh backup ACK and the sealed GPT/new geometry,
failed at generic S70 filesystem verification, restored the old GPT, and
returned directly to exact fastboot. The successor changes only filesystem
failure classification; the storage sequence is unchanged.
Generation 173 reproduced the boundary and classified it exactly as
`S70_POSTVERIFY/filesystem_dumpe2fs_failed`. The old GPT was restored and the
restart2 path returned exact fastboot. This is R3: the executor assumed that
one immediate `BLKRRPART`/BusyBox `mdev -s` pass made the pre-transaction p23
pathname usable. Stage 1 remains incomplete; no candidate is currently allowed.
Generation 174 removed the explicit reread but still returned exact
`S70_POSTVERIFY/old_userdata_mapping_changed`; rollback and fastboot passed.
Retained upstream source proves `sgdisk` calls `DiskSync()`, sleeps, and issues
`BLKRRPART` after writing. A future transaction must therefore avoid a live
partitioning tool and write independently verified fixed GPT regions directly.
Generation 175 did so and passed exact Stage 1: fresh backup ACK, secondary then
primary fixed-region writes, exact readback, new p23/p24 GPT geometry, protected
partitions, clean 51,124,000-block ext4, relock, S99, and automatic fastboot all
passed. The next gate is a separate RAM-only read-only boot proving that the
kernel enumerates the persisted p23/p24 layout before any Stage-2 clone write.
Generation 176 consumed the first read-only gate but completed or failed before
ACM stabilized, so no target verdict survived; no write path was reachable. Its
Stage-2 wrapper also omitted the restart2 helper and therefore entered stock
recovery. The successor changes only terminal delivery hold and helper packaging.
Generation 177 proved the remaining pre-USB cause: recovery-init globally
expected 116 physical block nodes, while the correct post-Stage-1 topology is
117 after p24 creation. No Stage-2 write path was reachable, and packaged
restart2 returned exact fastboot. Stage 1 remains intact. The successor makes
the count mode-specific: Stage 1 remains 116 and Stage 2 requires exactly 117.
Generation 178 contained that exact packed fix but still returned before ACM,
proving another pre-USB recovery guard remains. No Stage-2 write path was
reachable and exact fastboot returned. The next read-only discriminator moves
only aggregate wrapper-count admission behind USB; exact p23/p24 geometry,
read-only state, and zero mounts remain mandatory in the executor.
Generation 179 deferred only the aggregate count but still returned before ACM,
proving an earlier UFS discovery, isolation, power-containment, or inventory
guard rejects before USB. No write path was reachable and exact fastboot
returned. The next sealed read-only mode binds USB first, then reports each UFS
guard; clone mode retains the current pre-USB fail-closed ordering.
Generation 180 consumed that read-only cycle. It reported discovery, isolation,
and inventory `pass`, power containment `fail`, and exactly 117 physical block
nodes. The executor then rejected partition 24 as
`arch_root_identity_changed` with `target_state=untouched`; packaged restart2
returned exact slot-A fastboot. The next gate is a read-only exact-field report,
not a clone: identify the missing UFS marker/count and the mismatching canonical
partition-24 field first.
Generation 181 is consumed after a distinct pre-ACM regression: fastboot
returned in 7.33 seconds with no recovery USB and no storage path. Its rebuilt
wrapper Image `d98f53c1...` replaced the live-proven `8dc38de4...` Image even
though Generation 180 already proved that stable Image plus an external boot
ramdisk. The next read-only control must reuse the live-proven Image and change
only a fresh external one-use ramdisk; do not rebuild the ASUS kernel again.
Generation 182 did exactly that and restored ACM. It proved the rebuilt Image,
not the diagnostic script, caused Generation 181's pre-USB return. It also
reported the complete p24 identity: only attributes differ, at exact
`0004000000000000`; UFS custom-marker counts are all zero because the stable
ASUS Image contains none of those mainline-only strings. The next preflight
accepts that exact persisted attribute and reports marker telemetry as
`unsupported`, without changing clone or write authority.
Generation 183 is consumed. Its corrected stable-wrapper recovery ACM existed
for 12.81 seconds, but the collector lost the stream on disconnect before a
terminal record was retained. No storage write path ran. Restart2 did not
retain the bootloader reason on this return, so the phone is in slot-A
unauthorized stock recovery. Preserve partial records and add a bounded
host-open rendezvous before a successor; a physical fastboot entry is required
now.
Generation 184 is consumed. Its fsynced partial transcript is exactly empty and
its recovery USB lifetime matched Generation 183, proving no Stage-2 record was
emitted. The exact source defect is an unbound-variable exit: classifying UFS
markers as `unsupported` skipped the function that initialized five counters,
then `set -u` exited before the guard report and executor. The counters are now
initialized in the deferred-guard block. No storage path ran; the phone again
returned to unauthorized slot-A recovery.
Generations 185-188 all reached exact p24 identity and returned safely with the
target untouched. Their `arch_root_signature_size` result was a false-positive
control-flow defect, not evidence of a residual signature or oversized output:
the exact sealed BusyBox 1.37 `blkid` returns success with zero output. The
executor now captures once, bounds at 4097 bytes, and considers only non-empty
output a signature. A zero-output-success runtime fixture fails on the old
code and passes on the correction. Generation 188 is consumed and revoked;
no Stage-2 write, mount, or watchdog disarm occurred.
Generation 189 passed the corrected signature gate, proving p24 has no
recognizable bounded signature output, then failed separately at
`temperature_unsafe`. It returned exact fastboot with the target untouched.
The clone gate remains closed pending exact temperature-predicate evidence.
Generation 190 proved the stable wrapper has no `type=Battery` supply and again
returned untouched to exact fastboot. No more wrapper successors are planned.
The next read-only gate reuses the Generation-158 mainline V49 charging/UFS
runtime, which already passed qcom-battmgr safety checks and completed bounded
high-speed 16-GiB staging in about 92 seconds.
Generation 191 was consumed before recovery ACM: its reused V54 recovery
ramdisk still expected the pre-Stage-1 topology. The target bundle never ran,
phone storage remained untouched, and slot-A stock recovery returned. The
next successor changes only the full recovery ramdisk to current 117-node
source; wrapper kernel and mainline target remain frozen.
Generation 192 reached healthy mainline runtime and key-only SSH at 254
seconds. Runtime evidence was correct for the current layout
(`physical_blocks=117`, two read-only backing mounts, zero UFS errors), but the
host parser still required 116. Exact fallback passed. The next successor is
host-parser/identity-only; target and recovery payload bytes stay unchanged.
Generation 193 then passed end-to-end in 339.080 seconds: exact p23/p24,
read-only local Arch, systemd, strict SSH, 30.1 C battery, +312 mA USB input,
39.5 C maximum thermal, zero UFS errors, and exact fastboot fallback. The
read-only gate is complete; active work moves to the separately authorized
p24-only Stage-2 clone and native-root verification.

## Completed charging repair

The August charging loop is resolved. Reconstructed dynamic-partition metadata
incorrectly marked the one physical, unsuffixed `super` device as
slot-suffixed. Android first-stage init therefore waited for nonexistent
`super_b`, `/vendor` never mounted, charger services did not start, and the
phone returned to fastboot.

The corrected explicit-A/B `super` image was flashed once and verified. It
contains explicit `*_a` and factory-empty `*_b` logical partitions backed by
physical `super`. The official WW33 AVB chain passes, stock charger mode raised
the battery from about 3% to 47%, and Android booted with
`sys.boot_completed=1`.

Authoritative private evidence:

- `/home/deck/.local/state/rog5-super-explicit-ab-20260819-r1/SUCCESS-EVIDENCE.md`
- `/home/deck/.local/state/rog5-super-explicit-ab-20260819-r1/BUILD-RECORD.md`
- `/home/deck/.local/state/rog5-super-explicit-ab-20260819-r1/corrected-super-live.log`

Do not rebuild or reflash `super`, attempt a WW18 rollback, or write GPT,
`persist`, `factory`, `batinfo`, modem/EFS, calibration, RPMB/devinfo, or
per-unit key material.

## Current objective

Build a reliable standalone Arch Linux server while preserving slot A.
Immediate work is Linux power over the side data port:

1. keep side controller `a600000` in peripheral mode for NCM/ACM data;
2. reproduce side-port sink charging while NCM/SSH remains active;
3. bring up ADSP, PMIC GLINK, `qcom_battmgr`, and UCSI;
4. expose aggregate and dual-cell battery telemetry;
5. prove net-positive charging and safe temperature under sustained load;
6. keep NCM, key-only SSH, and rollback stable throughout;
7. return to persistent local-root Arch only after this foundation passes.

Generation 154 is consumed. Direct 32 MiB I/O passed in 50.25 seconds while
buffered fsync blocked beyond 180 seconds. Its independent sync-free timer
returned directly to exact slot-A fastboot, so the recovery-loop concern is
resolved without flashing. The next target must stage the image with aligned
direct writes and sparse-hole skipping; buffered writeback is forbidden.
Generation 155/V46 is the one admitted RAM-only successor: 37 ordered aligned
direct ranges totaling 1,850,654,720 bytes recreate the reviewed 16 GiB Arch
image at one fixed path. Full local CI and exact-head/merge/QEMU checks passed.

## Current physical evidence

Stock WW33 establishes the physical UCSI mapping:

- `port1`: with only the PC cable attached, connected as UFP/sink/device while
  RNDIS/ADB uses `a600000.dwc3`; this is the side data/charging port.
- `port0`: disconnected in that side-only state and connected only when the
  bottom cable is attached; this is the bottom port.

With only the side PC connection, Android reports UFP/sink/device, charging,
5 V / 500 mA input, `side usb status: 1`, and `asus charger: 0`. The immediate
Linux gate is the same side-only combination; bottom-port arbitration is
deferred.

Android names the controller `a600000.dwc3`; the proven Linux 7.1 UDC is
`a600000.usb`. Do not rename the Linux contract based only on Android's name.

## Current implementation

Authoritative clean repository:

- path: `/home/deck/.local/state/rog5-haven-clean-ci-20260810`
- branch: `agent/linux-recovery-host`
- starting published head: `9a86c94bf2357f8128ef42301f19283e226d82a3`

The separate workspace at
`/home/deck/Projects/rog-phone-linux-migration/repo` preserves unfinished
VCNL36866 work and must not be cleaned, stashed, or overwritten implicitly.

The active power/USB identity is defined only by
`configs/recovery-candidates/power-usb-active.json`; generated identities are
recorded in `manifests/power-usb-active.lock.json`. V7 is consumed after
passing NFS, systemd, the corrected 29-zone acceptance, key-only SSH, watchdog
fallback, and exact stock slot-A return. It exposed an R1 target selector that
recognized only three historical charging candidates, so no charging probe
ran. V8 generated the target identity but was revoked unbooted when review
showed its early PID1 probe had no SSH observation channel. V9 deferred the
probe; retained pstore later proved its rebuilt initramfs omitted the private
ADSP firmware source and failed `prepare_shutdown_root`. V10 was aborted before
COMMIT after exposing that evidence. V11 embeds the exact hash-pinned WW33
firmware and passed SSH, but the probe refused inherited runtime-mask/disarmed-
watchdog preconditions before hardware. V12 composed those preconditions but
exposed obsolete reserved-memory paths before ADSP. V13 bound the accepted
geometry but had two noncanonical channel-size strings. V14 corrected them,
then found systemd had already coldplugged `qcom_q6v5_pas`. V15 masked whole
services before switch-root and prevented systemd readiness. V16 used a narrow
volatile pre-switch modprobe blacklist and reached the hardware probe, where
PAS returned `-EINVAL`; the deployed full-UCSI DTB had regressed by omitting
the three stock-owned RAM exclusions previously required for successful ADSP
startup. V17 restored those nodes and reached runtime acceptance, but its
reused initramfs still selected V16 exactly, skipped deferred charging mode,
and omitted the retained probe. V18 replaced that identity copy, reached ADSP
`running`, and then found `pdr_interface.ko` had incompatible build-specific
BTF. V19 passed PDR/PMIC GLINK/UCSI and found `port_type` is source-validly
optional. V20 classified that absence, then was revoked unbooted before phone
contact. V21 is consumed after its diagnostic-profile token was rejected
before target USB. V22 reached target NCM/ACM, then its first transport check
used unsupported BusyBox `find -printf` and rolled back. Exact stock fallback
passed. V23 reached target NCM/ACM, then its textual mountinfo guard
misclassified required `/dev/pts` as phone storage. V24 is the target-only
observer that first produced a complete typed stream; it exposed unsupported
BusyBox `modprobe --first-time`. V25 then loaded the complete charging stack
and proved side-port input, but the full battery made positive pack current
unobservable. V26 repeated the exact target bytes at 98% and proved positive
pack current. The power/USB observer track is complete. See
`test-results/2026-08-20-power-usb-v7-r1-target-selector.md`.

## Current loop optimization

- The observer runs before NFS/systemd/SSH and reports optional telemetry
  non-fatally over typed ACM netstrings.
- Its real module closure is 15 files rather than the 844 MB module tree.
- Twin offline initramfs builds match at
  `3ebd3260581af3300187de55768b61cd8ef57f4574febb4b0540e21e7566dbcf`.
- `test-repository-linux.sh probe` takes about 5.6 seconds.
- The ASUS wrapper path checks a recovery-only content-addressed cache before
  compiling; target bundles and documentation do not invalidate it.
- Persistent stock-Android ADB is no longer a project objective. Linux cycles
  use fastboot, ACM/NCM, and later key-only SSH.

## Next execution sequence

Generation 101 is consumed and must never be retried. The exact signed bundle
transfer, PREPARE, and COMMIT passed, then recovery USB departed at 06:31:56
and no target NCM/ACM appeared. The exact phone exposed stock slot-A USB about
30 seconds later and subsequently returned responsive fastboot. No staging SSH
command ran, so the 16 GiB image was not written. The replacement minimal init
is the only new target layer; its exact failing line remains unproven. Avoid a
second speculative staging initramfs: place the already-verified image through
one exact userdata-only sparse transfer and reuse the mature local-root path.

The actual staging route used one exact Android-sparse `userdata` image because
stock Android cannot boot the new plaintext ext4. Four chunks completed in
38.194 seconds; no GPT or other partition changed. Generation 102 then exposed
`ROG5 persistent root` NCM/ACM for 15 seconds and rolled back. The new image's
UUID, label, and seal are correct, but it lacks V9's required
`/var/lib/rog5/local-image-write-probe-v1`. V10 therefore changes only the
sealed target mode to the already-tested bounded `local-write/current` path;
it may create that one probe, relock, and continue to read-only Arch.

Generation 103 is consumed. Its NCM stayed reachable for 60 seconds, matching
the exact `ufs-power` failure delay after pairing local-write initramfs policy
with V8's intentionally forced-read-only UFS kernel. No probe or storage write
occurred. The bounded writer successor reuses the exact Generation-64
write-capable Image/DTB/module lineage that already persisted this probe format;
it does not modify the charging/read-only production baseline.

Generation 104 is consumed after a 14-second target-NCM window. This matches
the known Generation-64 probe-write then UFS-health rollback, but the stage
listener missed the window, so success is not assumed. The next read-only
target accepts exactly one canonical, non-current producer UUID from the probe;
the freshly staged image was independently proven marker-free before the sole
writer, so a valid probe now uniquely answers the write question.

Generation 105 is consumed after another manual-host race: target NCM existed
for 19 seconds, but the next tool call started after departure. No target write
occurred. Generation 106 keeps the exact V12 target bytes and changes only the
signed identity plus host execution route: the tested continuous
`run-persistent-root-storage-live-cycle.py` now owns claim, recovery, COMMIT,
network activation, stage capture, pinned SSH, reboot, and fallback without a
chat/tool boundary.

Generation 106 is consumed. The continuous runner removed the host race:
network and stage listener were active from target uptime approximately two
seconds, yet no stage was emitted before a 20-second rollback. The exact source
bug is the pre-reporter policy case that still accepted only UUID-valued
read-only probe IDs and rejected `any-prior`. Generation 107 adds only
`read-only:any-prior) ;;` to that early gate and retains the continuous runner.

Generation 107 is revoked unbooted. Its target would still use SysRq hard reset
on failure or shutdown, allowing the current slot-A rescue path to enter ASUS
recovery repeatedly. Generation 108 keeps the same Image, DTB, charging/UFS/NCM
stack, and early `any-prior` fix, but seals the already-proven fixed AArch64
`RESTART2("bootloader")` helper into the target. Failure, watchdog, and shutdown
request exact fastboot first and retain SysRq only if that syscall returns.

Generation 108 is consumed. It advanced through read-only UFS and userdata
mount, then emitted `userdata-rog5-directory`; retained host image inspection
proves `/rog5/images/arch-local-a.ext4` exists in the source sparse filesystem,
so deployed userdata content changed after staging. Restart2 did reboot but did
not retain the bootloader command: `CONFIG_NVMEM_REBOOT_MODE=m` and
`CONFIG_NVMEM_SPMI_SDAM=m`, while the target initramfs contains neither. The
phone is presently slot-A unauthorized recovery ADB and needs a physical
fastboot entry. Do not reuse Generation 108.

Generation 109/V16 is an offline-only successor. Clean twins reproduce Image
`1a1958fe...` and config `15e1ea49...`; the only linkage change is built-in
PMK8350 SDAM plus NVMEM reboot mode. Its target proves the bound standard DT
reboot-mode device before UFS. Exact fastboot returned, and the previously
verified sparse userdata image was restaged in four successful userdata-only
chunks in 38.964 seconds. Generation 109 nevertheless repeated the exact
directory failure and is consumed; its built-in reboot-mode path returned
exact fastboot. Generation 110 is the one-use read-only discriminator: it
publishes hashes for blocks 1, 32, 1086, 8224, 8225, 9278, 14680096,
14688288, and 14688289, then returns to fastboot. The host now stops on the
terminal stage and accepts exact slot-A fastboot as a valid fallback.

Generation 110 is consumed. Its hashes prove the ABL sparse operation is a
no-op, not a 4-GiB wrap. The next artifact is the separately scoped controlled
writer: clean twins from `359318de...` match Image `a7e0cd84...` and config
`6329b42f...`, with `SCSI_UFS_DISCOVERY_DATA_WRITE=y`, charging, and built-in
reboot mode. The exact installer initramfs is now packaged below.

Generation 111 is consumed. Its signed transfer and COMMIT passed, recovery USB
departed at 05:27:56.653, no target USB enumerated, and slot-A unauthorized
recovery appeared at 05:28:27.362. No SSH transfer or storage write occurred.
The host also lacked the new target product in its reviewed allowlist; that is
fixed offline but cannot explain the complete absence of a target USB event.
The lifecycle's premature fallback-resolution condition is also fixed; the
existing Generation 111 resolution record remains evidence, not fallback proof.

Root cause investigation now proves one fatal pre-USB command shared by
Generations 101 and 111: `set -e` terminated PID 1 when the optional
`/proc/sys/kernel/hotplug` redirect failed under exact kernels with
`CONFIG_UEVENT_HELPER` disabled. The smallest source fix is only `|| :`; a
sealed-AArch64-BusyBox test fails unguarded and passes guarded. Collect retained
ramoops from a fresh RAM-only observer before treating this as the sole cause.

Generation 112 is consumed: target initramfs `0cb40afd...`, manifest
`d3e3dc86...`, and wrapper `dafa1030...`. The hotplug guard advanced the target
to an immediate controlled pre-gadget failure; exact fastboot returned 6.903
seconds after recovery USB departure. The 20-second UDC wait and a 10-second
panic are too long, so the next no-storage discriminator separates release,
command-line, and both-checks-pass outcomes by fixed timing.

Generation 113 is consumed: initramfs `b859c7bf...`, manifest `0ab3364d...`,
wrapper `615ab418...`. Its 31.910-second return selected the 25-second
both-checks-pass path. The next full staging successor adds only the mature
USB path's exact `a600000.ssusb/mode=peripheral` transition before ConfigFS.

Generation 114 is consumed: initramfs `5cf22d30...`, manifest `78091cdf...`,
wrapper `b4334d27...`. The mode path is absent in this mainline tree and runtime
timing remained 6.903 seconds. The boundary is now immediate ConfigFS setup;
the next target is a no-storage grouped ConfigFS beacon.

Generation 115 is consumed: initramfs `2a1312e0...`, manifest `e68acce8...`,
wrapper `6b376583...`. Its 51.961-second return selected UDC identity: expected
`a600000.usb` exists alongside an extra candidate. No UFS or storage path ran.

Generation 116 is admitted once: initramfs `48944376...`, manifest
`16e4bdec...`, wrapper `4c0ac096...`. It binds no UDC and classifies the sole
extra basename into known controller patterns, unknown, or multiple buckets.
Its live early sample returned `no extra yet` in 16.887 seconds; combined with
Generation 115, the extra UDC registers late. A five-second stabilized inventory
is next.

Generation 117 is admitted once: initramfs `3cf4d974...`, manifest
`f26c2a4c...`, wrapper `0fb3e250...`. It waits five seconds after expected UDC
registration before classifying the late extra basename and binds nothing.
Its 21.750-second result selected no-extra after the stabilization window.
Combined with Generation 115, the duplicate exists only during NCM+ACM setup.
The next full staging target removes unnecessary ACM and requires five seconds
of continuously unique `a600000.usb` before binding.
Generation 118 is that one admitted full-staging successor. It changes only the
target initramfs, reuses the exact clean-twin writer Image/DTB and stable
recovery transport, and retains one-file write containment plus fastboot return.
Its sole cycle is consumed: target NCM never appeared, exact slot-A fastboot
returned, no target write ran, and the intent resolved `FALLBACK_RETURNED`.
Read retained ramoops through an observation-only recovery before changing the
UDC gate or any downstream module path.
The observer is consumed. It retained only the prior recovery kexec-shutdown
tail and no target lineage, so it cannot distinguish UDC selection from bind,
usb0, carrier, or module failure. The next cycle is timing-only instrumentation
with target behavior otherwise unchanged.
Generation 119 is the admitted timing-only successor. It has no UFS or storage
execution path and asks only which pre-NCM/power-USB boundary returns fastboot.
Its sole cycle selected `ncm-address`: all earlier ConfigFS/UDC/usb0/link-up
steps returned success, then the exact IPv4 add returned nonzero. The next
cycle classifies only the address state and remains storage-free.
Generation 120 is the admitted address-only discriminator with five fixed
70–90 second outcomes and no later subsystem or storage execution.
Its sole cycle selected `address-show-failed`. The next full staging target
moves only `mdev -s` before UDC selection/bind, matching the proven mature path.
Generation 121 is the admitted full-staging successor with that single ordering
correction and unchanged kernel, DTB, modules, installer, and rollback.
Its sole cycle is consumed with no target USB. The next target removes the
redundant second `mdev -s`; devtmpfs plus explicit UDC/usb0 polling remain.
Generation 122 is the admitted full-staging successor with that simplification.
Its sole cycle is consumed at the UDC identity timeout. The next cycle only
classifies post-ConfigFS UDC inventory and binds nothing.
Generation 123 is the admitted no-bind inventory classifier.
Its sole cycle proved zero/exact UDC churn. The next selector tolerates absence
but requires two consecutive exact samples and post-bind revalidation.
Generation 124 is the admitted full-staging successor with that selector.
Its sole cycle timed out without two consecutive samples. The next target uses
immediate exact bind with post-bind verification.
Generation 125 is the admitted full-staging successor with immediate exact bind.
Its sole cycle timed out because the pre-bind inventory scan remained too slow.
The next target uses direct expected-path bind and post-bind full validation.
Generation 126 is the admitted full-staging successor with that direct bind.
Its sole cycle proved a synchronous exact bind-write refusal. The next cycle
classifies the kernel-reported ConfigFS/DWC3 errno and touches no storage.
Generation 127 is the admitted bind-errno classifier.
Its sole cycle selected bind-success: target NCM remained enumerated for
89.864 seconds. A host-only R7 allowlist omission filtered the exact local-stage
model, so the host never accepted the target and no storage path ran.
Generation 128 is the admitted full-staging successor with the host parser and
post-COMMIT cleanup fixes plus bounded retry of only an exact unbound UDC.
Its sole cycle is consumed at the 6.903960-second immediate-return baseline.
The exact ConfigFS store source plus the prior empty/exact UDC-class trace
identify the one-shot post-bind class-level assertion as the failure; no target
USB, SSH, installer, or storage path ran.
Generation 129 is the admitted one-question successor and removes only that
assertion while retaining exact ConfigFS readback and all later gates.
Its sole cycle is consumed. Target NCM enumerated for 0.519517 seconds, proving
the UDC fix, then target rollback outran host activation. The stager currently
collapses the detailed power-loader result and has no stage reporter.
Generation 130 is admitted once with the existing stage reporter started before
the loader and a ten-second terminal evidence dwell.
Its sole cycle is consumed by an R7 host call-site defect: the reporter dwell
worked, but the runner selected the SSH-only helper instead of the stage-aware
helper. Exact fallback passed and no storage path ran.
Generation 131 is admitted once with that one-line host call-site fix and a
fresh target identity.
Its sole cycle is consumed and captured exact
`power-usb/module-qcom-q6v5-load`. Offline inspection proves the packaged
module vermagic was ae717 while the target is g359; no storage path ran.
Generation 132 target twins now package the retained matching g359 UFS and
power/USB modules and are byte-identical, but remain unsigned and unadmitted.
Generation 132 is signed and admitted once; its only material target delta is
the exact g359 replacement module closure.
Its sole cycle is consumed and advanced through power/USB plus UFS module load,
then failed `ufs-ready/ufs-count` after 20 seconds. No storage path ran.
Generation 133 is admitted once to retain the observed physical-device count.
Its sole cycle is consumed and proved exact `ufs-count-0`. No block device or
storage write existed; the UFS boundary now requires architecture/source audit.
Generation 134 is admitted once to distinguish platform absence, unbound
platform, bound-without-host, or host-without-block state.
Its sole cycle is consumed and reported exact `ufs-platform-0`; no SCSI or
storage surface existed. Next compare runtime DT node/status to sealed DTB.
Generation 135 is admitted once for that exact runtime DT comparison.
Its sole cycle is consumed: runtime UFS DT is okay, address-name platform scan
is zero, and no storage surface existed. Next scan exact `of_node` identity.
Generation 136 exact-OF-node twins and signatures are ready but unadmitted;
policy, claim, publication, and phone boot remain pending.
Generation 136 is now admitted once; no claim or phone boot has occurred yet.
Its sole cycle is consumed and exact OF matching still reported platform zero.
Next re-establish the live-proven g359 UFS Image/DT baseline before power merge.
The proven Image/DT and four original g359 UFS modules are hash-reverified;
the next build is a minimal UFS-only successor with no power or storage write.
Generation 137 is admitted once for that baseline; no claim or boot exists yet.
Its sole cycle is consumed: NCM passed, but exact terminal detail was
`ufs-count-0`. Slot-A stock recovery USB returned at the anchored path, while
the fallback verifier rejected its now-observed `18d1:d001` descriptor because
it still pins the older Android descriptor. Generation 109 is the stronger
control: its ae717 target passed UFS under the current wrapper and returned
exact fastboot through built-in PMK8350 reboot mode. Generation 138 is the
minimal UFS/NCM successor on that exact target lineage.
The fallback verifier now accepts the exact current `18d1:d001` recovery tuple
as well as the historical complete tuple, rejects mixed identities, and passed
the live Generation-137 recovery with its retained slot-A preboot record.
Generation 138 is consumed: exact ae717 UFS still reported count zero, while
built-in reboot mode returned exact fastboot. The sealed Generation-109 init
loads its 15-module PMIC GLINK/remoteproc/UCSI stack before UFS; the minimal
successor had packaged but never executed that loader. Generation 139 restores
that exact dependency order and still exposes no storage-write path.
Generation 139 is consumed: the complete power/USB loader passed and fastboot
returned, but `set -f` made every fixed sysfs glob literal and forced a false
zero UFS result. Generation 140 removes glob suppression and uses the proven
Generation-109 disk-plus-partition topology algorithm; no storage write exists.
Generation 140 is consumed and exact terminal `count-116` proves UFS. Exact
fastboot fallback passed. Generation 141 uses the same power/UFS/reboot lineage
with the full writer init corrected for globbing and topology count, key-only
SSH transfer, one bounded image-file write, and complete relock.
Generation 141 is consumed: UFS passed and host-key pinning passed, but sealed
`/etc/nologin` rejected every SSH connection before authentication. No image
bytes or storage command ran. Generation 142 removes only that exact empty
regular file before key-only sshd; all write and fallback bounds are unchanged.
Generation 142 is consumed before target acceptance by a transient empty
NetworkManager ownership result on the new NCM interface. No write occurred and
fastboot fallback passed. Generation 143 changes only host observation:
no-address/unknown is transitional, any escaped `/30` or final unknown remains
fatal.
Generation 143 is consumed before host-key readiness because redundant
post-COMMIT cleanup delayed target activation. No write occurred. Generation
144 removes only that duplicate wait after the bundle server's canonical
cleanup; final fallback cleanup remains unchanged and mandatory.
Generation 144 is consumed: immediate target activation and UFS passed, then an
uninstrumented post-UFS pre-SSH failure returned exact fastboot with no write.
Generation 145 adds only existing stage records around userdata identity,
storage lock, nologin removal, host-key creation, and sshd.
Generation 145 is consumed at exact `runtime/nologin-identity`: no nologin file
exists. The actual SSH blocker was locked `root:!`. Generation 146 passed
first-attempt key-only SSH and the exact gzip transfer, then its duplicate
installer `set -f` disabled both `"$mountpoint"/*` and relock globs. It failed
the literal-asterisk content check before creating the image path and returned
exact fastboot. The target-only successor removes that line and reports any
future installer failure before reboot; no kernel or wrapper rebuild is
justified by this R3 shell defect.
Generation 147 is consumed. It passed the installer glob, exact UFS, runtime,
first-attempt key-only SSH, and transfer, then returned exact
`reason=write-window` before mount or image creation. The successor changes
only parent-before-child read-write ordering and exact readback reasons; it
retains the proven kernel, DTB, 19 modules, recovery raw bytes, storage scope,
and slot-A fallback.
Generation 148 is consumed at exact `disk-rw-state`. The deployed ae717 config
is compile-time read-only and cannot satisfy the installer regardless of
BLKROSET ordering. The successor reuses the retained clean-twin g359
write-capable Image, matching four UFS and 15 charging modules, current DTB and
installer, and unchanged RAM-only recovery/fallback.
Generation 149 is consumed. It proved the bounded-write kernel composition,
then dense decompression created an 825,884,672-byte partial image before the
UFS path stalled in D state. The watchdog's `sync` also blocked. Exact fastboot
returned only after the sealed helper had set the bootloader reason and
emergency SysRq bypassed device shutdown. No full-image candidate is admitted;
next work is a sealed sparse writer plus sync-independent emergency rollback.
Generations 150 and 151 are consumed at `partial-identity` before benchmark
data. Generation 152 accepts only absent or one root-owned mode-0600/0644
partial bounded by the fixed 17,179,869,184-byte logical image, reports it,
then compares 32 MiB direct and buffered writes with sync-independent fallback.
Generation 152 repeated the same boundary. Generation 153 is read-only and
reports exact partial/final/directory metadata under `ro,noload`; no block write
window, benchmark directory, or image write is reachable.
Generation 153 proved the partial is regular `0:0`, mode 0644, one link, but
empty with zero allocated blocks. This is the exact cause of the repeated
partial-identity refusal. No successor is admitted yet.

Generation 78 is consumed. Removing BTF from `pdr_interface.ko` advanced the
combined target from no stage evidence to exact sequence 3 at `ufs-ready`, but
the power/USB loader returned its legacy generic failure before UFS. Exact
stock slot-A fallback and cleanup passed. Missing pstore lineage does not prove
or disprove a crash; the observed initramfs path explicitly waited two seconds
and forced rollback after the loader failure.

Generation 84 is consumed. Raw `userdata` remained type/magic-opaque and ext4
mount returned status 255/`EINVAL`; WW33 fstab proves the plaintext F2FS exists
behind `dm-default-key`, not on raw partition 23. Exact fallback passed.

Generation 79 is consumed. It proved exact failure
`power-usb-typec-data-role`: V26's retained raw evidence shows mainline's
writable role attributes as `host [device]` and `source [sink]`, with brackets
marking the selected roles. The loader's bare-string comparison was wrong.
Its bundle was
`persistent-root-power-usb-v3`, manifest SHA-256
`d0a1e7b2d9a2fce6d934fc560af466c476f66c1b5ee700dd6efdc6134b6e68eb`,
and RAM-only AVB SHA-256
`2e49097855eaee747d5935e2d1a6dfe28a42a99396bcafc670db47e3bf388623`.
The recovery raw image was unchanged; no ASUS kernel compilation ran. Exact
stock slot-A fallback and cleanup passed, and Generation 79 must not be
retried.

Generation 80 is consumed. It passed the bracketed roles, complete power/USB
loader, deferred UFS, storage lock, and exact userdata resolution, then failed
at `userdata-mount` with the old generic detail. Its bundle was
`persistent-root-power-usb-v4`, manifest SHA-256
`2240afeecc90e45e4cf51e94365473a8fbe269731cebc7d1dcba86b7bfd84bf2`,
and RAM-only AVB SHA-256
`f948a480806805b7726e3de5fd2f1def3b457a82219d0e8fa8a3ad7ca94d0ae9`.

Generation 81 is consumed. It proved exact detail `userdata-mount-call`, so
the ext4 mount syscall failed before every post-mount check. Its bundle was
`persistent-root-power-usb-v5`, manifest SHA-256
`5320f9cca8582ca7475f06f0a4c3e25e0b961fd1596077c832e9e622667b19bf`,
and RAM-only AVB SHA-256
`6856794c55777c8f473a23a5a2cee55c57c9d652122b57da048e516da2f63ce5`.

Generation 82 is consumed. It retained mount status 255/`EINVAL`, but `blkid`
exposed no recognized type and its type gate skipped `dumpe2fs`. Its bundle was
`persistent-root-power-usb-v6`, manifest SHA-256
`b83d5bacb8b22a7125a33c087b10403cc5e1e9cf35dc5e8ee8d1e48e185e935a`,
and RAM-only AVB SHA-256
`e040c38cbbd311310899f2b4e55cb4bbfbc8c62c12f3c040d06f58469802fb60`.

Generation 83 is consumed. Sealed BusyBox `od` compressed duplicate hex lines
to `*`, preventing magic classification. Its bundle was
`persistent-root-power-usb-v7`, manifest SHA-256
`ed43083b35d7f1e4d3c7aa6aa8dacb4ec4e22a2d1e57cd818c4efa20f78080cd`,
and RAM-only AVB SHA-256
`b1e69cbdb2a379d763a65c2841182b2e3f163ad7648da5fc470b75bba4092517`.

Generation 84 is consumed. Its bundle was
`persistent-root-power-usb-v8`, manifest SHA-256
`c70ed13367192b26225aa3408bf8cdf4dd3a91da1d3a0c0f5fba59c81be36289`,
and RAM-only AVB SHA-256
`88075dba4a8564fa21d73c69d696b64813dc024389a5d097be345f7cd9f302bb`.

There is no admitted successor. The next storage transition replaces the
opaque encrypted contents of the unchanged `userdata` GPT partition with an
unencrypted ext4 filesystem, then recreates the bounded Arch image. The owner
confirmed the exact destructive proposal in
`configs/storage/rog5-userdata-ext4-reset-v1.json` on 2026-08-22. Offline
formatter implementation and verification precede a separate one-use
admission; GPT and every non-`userdata` partition remain immutable.

Generation 85 is unbooted and revoked because its normal post-success reboot
could let stock Android reformat Linux ext4. Generation 86 is consumed: exact
recovery ACM existed for 11 seconds, but the host did not stabilize it; no
backup directory or ACK existed, so the write boundary was never crossed.
Generation 87 is consumed with no ACK/write. Generation 88 is also consumed:
the canonical root collector opened ACM and proved the target was repeating
an exact pre-backup four-field FAIL, but the old parser discarded its
stage/reason. No backup directory or ACK existed; restart2 returned fastboot.
Generation 89 is consumed and proved exact target failure
`S10_TOPOLOGY/userdata_content_changed/gpt_restored=not_needed`; no backup,
ACK, or write existed. The defect was the target's assumption that confirmed
Android userdata must remain raw-opaque. Generation 90 is consumed with R7
classification: the root collector attached after the target had begun raw
GPT streaming and rejected binary payload bytes as an overlong framed line.
No output directory or durable ACK existed, so the target could not format or
write. The successor must require one exact operation-bound host-ready record
before `BACKUP_BEGIN` or any binary payload; Generation 90 must never be
retried. Its 900-second recovery watchdog returned exact stock WW33 slot A;
ADB then proved `sys.boot_completed=1` and `/data` remained mounted as F2FS.
Generation 91 is consumed with R7 classification: the target reported exact
`S30_FRESH_BACKUP/host_ready_mismatch` because the host sent readiness at ACM
open rather than after parsing target stage S30. No output directory or
durable ACK existed, so no format or write occurred. The collector now waits
for exact target `S30_FRESH_BACKUP`, sends one operation-bound `HOST_READY`,
and refuses `BACKUP_BEGIN` before that sequence. Generation 91 must never be
retried; its identical raw wrapper may only be reissued under a fresh AVB
generation after this host-only correction passes publication CI.
The 900-second recovery watchdog returned stock slot-A Android USB at
15:28:58. ADB remained unauthorized, so a second live `/data` mount query was
unavailable; absence of the mandatory durable backup ACK remains the direct
proof that the formatter could not enter its write path.
Generation 92 is consumed and must never be retried. Even after the collector
parsed exact target `S30_FRESH_BACKUP` before sending readiness, the target
again reported `host_ready_mismatch`; no output directory or durable ACK
existed, so no format or write occurred. The 900-second watchdog returned
stock slot A, and ADB proved `/data` remained F2FS. An exact sealed AArch64
BusyBox PTY experiment received the unchanged 85-byte token both before and
after S30, ruling out ash `read` syntax and ordinary TTY directionality. Two
bounded Opus reviews timed out without a verdict. The remaining uncertainty
is physical gadget-ACM input contamination or transformation; the successor
must use a four-record/120-second exact-token loop and finite non-secret
failure categories without normalizing the accepted token.
Generation 93 is consumed and must never be retried. It classified the first
physical gadget-ACM record as `host_ready_leading_data`; no output directory
or durable ACK existed, so no format or write occurred. This proves the exact
token survives as a suffix behind stale leading bytes. The successor keeps
the accepted token unchanged and prepends one empty separator record, so the
bounded target loop consumes the contaminated separator record before reading
the exact operation-bound token. Its raw wrapper can be reused under a fresh
AVB generation; no kernel rebuild is required.
Its 900-second watchdog returned stock slot-A Android USB by 17:38:56. ADB
remained unauthorized, so a second `/data` query was unavailable; absence of
the mandatory backup ACK remains the direct proof that no write began.
Generation 94 is consumed and must never be retried. Its empty separator
worked: the target accepted exact host readiness, streamed a fresh GPT backup,
and received the host's durable mutation ACK. It then stopped before any
userdata write at exact `S32_WATCHDOG_DISARM/rollback_watchdog_disarm_failed`;
`gpt_restored=not_needed`. The fresh backup set is
`1a6295725cb63ab27f90022e5061be6552eec7d6a4297cc4f5ff088543948679`.
Offline reproduction classified the failure as R3/R8: the exact killed
watchdog can remain an inert zombie while PID 1 waits for the executor, but
the helper required `/proc/PID` to disappear. The collector then closed after
the first terminal record, so repeated ACM writes blocked fallback until a
read-only drain was attached; exact fastboot returned. The successor accepts
only the exact same PID/start-time/parent in zombie state, rejects every live
or changed identity, emits one terminal failure record, and returns directly
to restart2. No GPT or userdata write occurred in Generation 94.
Generation 95 is consumed and must never be retried. Two clean ASUS 5.4 wrapper builds
produced identical Image `4e31a01c3675f003d71851cc208af6568a5ada7eac10b880f91299b2d4b1d5e1`
with initramfs `423785f6f343a5bb0b5b4164d7db5a68c2158e482d9dfa445529c368e3752982`.
Its authority-free generation-1 AVB image is
`d93aa10dc21221a7733f4d9a66d3e25ef43541c213ce3682bd728336afd7e596`,
bound by `manifests/userdata-ext4-reset-generation95.manifest`. No recovery
USB enumerated; the exact stock slot-A fallback returned in about 27 seconds,
and authorized ADB proved `/data` remained F2FS on `dm-40`. The exact deployed
boot image carried `rog5.recovery_timeout=300` even though its manifest and
sealed stage-1 mode require 900, so recovery-init rejected it before USB. This
is R2, not a kernel or S32 failure. The successor must repack the already
twin-proven Image and initramfs with exact timeout 900 and pass an artifact-level
cmdline regression; no kernel rebuild is needed.
Generation 96 is consumed and must never be retried. It reused exact twin-proven
kernel `4e31a01c3675f003d71851cc208af6568a5ada7eac10b880f91299b2d4b1d5e1`
and initramfs `423785f6f343a5bb0b5b4164d7db5a68c2158e482d9dfa445529c368e3752982`,
changing only the raw boot cmdline to exact `rog5.recovery_timeout=900`.
Its authority-free generation-1 AVB image is
`d7fc5fa4d4b7a29c7a64359ef9a5c45b62c3ab17748e5406da6f8da97992ddb7`,
bound by `manifests/userdata-ext4-reset-generation96.manifest`. Artifact-level
testing parsed the final boot image and rejected timeout 300 before admission.
Generation 96 reached fresh backup and durable ACK, then reproduced exact
`S32_WATCHDOG_DISARM/rollback_watchdog_disarm_failed`; no userdata or GPT write
occurred and restart2 returned exact fastboot immediately. The zombie fix was
not reached: recovery-init created `/run/rog5-recovery-armed` before setting
`umask 077`, while the helper requires exact mode 0600. Linux init's normal
umask therefore made the marker 0644. A fail-first ordering regression now
requires umask 077 before marker creation. This is R3 and requires a changed
initramfs/wrapper, not another host-only AVB reissue.
Generation 97 is consumed and must never be retried. Two clean ASUS 5.4 wrapper builds
produced identical Image `2aaecea0805ab35a22a71ef4a62e6c475b424121ef9a88104e40d623af0cec32`
with initramfs `7d6f888338752e0a55a45efb9d6a1d06949416395c9cfd3450786a60b4263d60`.
The exact final boot cmdline contains timeout 900, and source/testing require
umask 077 before the mode-0600 armed marker. Its authority-free generation-1
AVB image is `b9f9df8d01eaa7e90b792520c178cbec15ec29f03b62fa05a069c1668ae14cb2`,
bound by `manifests/userdata-ext4-reset-generation97.manifest`.
It reached fresh backup and durable ACK but still returned the generic exact
S32 watchdog-disarm failure before any userdata/GPT write; restart2 returned
fastboot immediately. The mode hypothesis was disproven. The executor had
collapsed every sealed helper predicate into one generic reason, so the next
cycle changes only observability: it converts the helper's final fixed `FAIL`
message into one bounded lowercase machine reason and emits that through the
existing terminal field. All helper reasons are static, unique, non-secret,
and source-tested; no write ordering changes.
Generation 98 is consumed and must never be retried. Two clean ASUS 5.4
wrapper builds produced identical Image
`175d141e8c11b69263b17ce437ebb7ea4e535d8c3db279563f411d6b8a7815ba`
with initramfs `75f0ed3f528788f2bf9f186657a674c4c2885ae6d6229b0f8333b082132eedc9`.
Its authority-free generation-1 AVB image is
`1ccb04a304d017061e8edb0cf8e44f87dbf2da41cbbf8b5898405b8b603008b2`,
bound by `manifests/userdata-ext4-reset-generation98.manifest`. One live cycle
must either complete the intended format or return the exact inner watchdog
predicate; it must not be used to test any second hypothesis.
It returned exact
`S32_WATCHDOG_DISARM/watchdog_cannot_inspect_watchdog_timer_child` before any
userdata/GPT write, then restart2 returned exact fastboot. The built wrapper
config proves `CONFIG_PROC_CHILDREN` is not set. The helper already binds the
rollback shell by root-owned lease, exact PID/starttime, direct parent PID 1,
stopped state, and post-kill identity; an orphaned sleep cannot execute the
shell's rollback continuation. The successor therefore removes only the
unavailable procfs child inspection and child kill, retaining every shell
identity, marker, freeze, kill, zombie, and no-write check.
Generation 99 is consumed and must never be retried. Two clean ASUS 5.4 wrapper builds
produced identical Image `c0f8e4ccccca4d64a1c5d887b304149f9d247b7bbf5a4d0c323e0e2c302ecf5a`
with initramfs `e03ab7339f6504dea919b9636b621f831181c74cb28782ce821912a34f75a6ea`.
Its authority-free generation-1 AVB image is
`51a51d8b985f321da26d7796f22a0c3af0e2ca0c7338489e5615a81cf1a145e2`,
bound by `manifests/userdata-ext4-reset-generation99.manifest`.
It passed the complete owner-authorized transaction. Fresh GPT backup set
`1a6295725cb63ab27f90022e5061be6552eec7d6a4297cc4f5ff088543948679`
was durably ACKed; watchdog disarm succeeded; only unchanged userdata
partition 23 was formatted ext4; GPT remained unchanged. Terminal proof:
59,513,299 blocks, UUID `0892bacf-3e02-41b0-84a4-5f05c2df7ce5`, label
`rog5-linux`, last LBA 61865978, all UFS block nodes read-only, zero block
mounts. Exact fastboot returned. The next action is a separate bounded 16 GiB
Arch image staging cycle; stock Android must not be booted because it may
reformat the new Linux filesystem.
V27 is revoked unbooted. Offline composition review proved its reused V20 DTB
keeps UFS disabled and its network-root initramfs rejects every physical block
device, so it cannot stage userdata. The corrected successor must retain the
proven `ae717` UFS-capable kernel/DT bytes and change only the target initramfs
and one-use identity. No V27 claim or phone boot occurred.
The corrected `local-image-stage-v1` target now has signed manifest
`cef076e59fd114ad2559178f115d2873c3a62912a1a00f5028f6a02e392d7271`
and recovery generation 101 SHA-256
`e4451a7bd042ff4de9593f0649c405d712f7ce2a75ac598d36cd0a5f60a8b267`.
It is unbooted and admitted for one RAM-only cycle. The exact compressed image
is prepared on the host; no claim has entered and no phone contact occurred.
4. After the power/USB boundary passes, continue the existing read-only UFS/local-image
   path to key-only SSH and measure power under one bounded server-style load.
5. Resume native persistent layout work only after the combined path repeats.

## Boundaries

- Never reuse a consumed or ambiguous candidate.
- Never flash an experimental kernel or recovery image.
- Keep slot A and the official WW33 charging route intact.
- Stop on identity/topology mismatch, unsafe temperature/power, unexpected
  phone-storage writes, or loss of the rescue route.
- Keep private keys, firmware, phone dumps, and live evidence outside Git.

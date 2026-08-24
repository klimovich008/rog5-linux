# Active ROG Phone 5 Linux context

Updated: 2026-08-23

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

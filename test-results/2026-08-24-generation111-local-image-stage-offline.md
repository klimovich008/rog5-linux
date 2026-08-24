# Generation 111 controlled local-image staging

Date: 2026-08-24

Primary question: can the clean-twin bounded UFS writer stage the exact 16 GiB
Arch image at `/rog5/images/arch-local-a.ext4`, relock storage, and return to
fastboot without entering stock recovery?

The preceding Generation 110 failure is R2: ASUS ABL returned successful sparse
transfer status, but read-only target hashes proved the installed userdata bytes
did not match the source. The successor therefore uses the already-reviewed
mainline writer instead of redesigning the kernel or retrying sparse fastboot.

Offline checkpoint:

- kernel source: `359318de534f196c1281de7195fbf5868c6f7333`;
- clean-twin Image: `a7e0cd84238d9e0c399a6c93d3c7a5996571dc3536b10c7323cbe1455dbad01e`;
- clean-twin config: `6329b42fac5876d3f42557802bd530ba2c077aa73c4543f0bbc37ea65902eeb4`;
- target initramfs: `077d7140439f7e861efe9f3a9dc9fcb78a02544d2bc241481ee7184282c79baf`;
- signed manifest: `f296276d49af5db4b498d2f14afc935065adf1ec4ca4e043e2b14c7a3b707bda`;
- Generation 111 wrapper: `f58153ef41186b5f2a5c8b2449d432dc02b6f92a9fb4c9397298d2d026d4e7cb`;
- focused tests: 5 seconds;
- full local CI: 364 seconds (the first 279-second run exposed and then fixed
  three stale historical-runner assertions; the frozen successor run passed);
- exact sealed BusyBox `stat`, `sha256sum`, `cut`, `cat`, and shell pipeline: passed.

The wrapper remains RAM-only and the target installer is the only storage-write
surface. It accepts one exact compressed source, one exact userdata partition,
one empty ext4 filesystem, and one final pathname before relocking every block
device and requesting bootloader restart.

Live result: **CONSUMED; PRE-USB FAILURE.** Recovery USB disconnected at
05:27:56.653 after signed COMMIT. No target USB product enumerated. Exact slot-A
unauthorized recovery appeared at 05:28:27.362, a 30.708-second gap. No target
host-key, SSH-transfer, or installer log exists, so no storage write occurred.
The host product allowlist also omitted `ROG5 local image stage`; a regression
test now covers it, but the kernel journal proves that omission was not the
cause of the target USB absence.

The failure path also set `fallback_attempted` before exact fallback proof and
therefore resolved the intent even though stock-recovery descriptor verification
failed. The durable record is retained as evidence but is not treated as proof;
the runner now resolves only after `fallback_proven` is true.

Systematic comparison with Generation 101 and the working Generation 102
isolated a fatal R3 initramfs capability defect. Both failing initramfs archives
use `set -e` and redirect to `/proc/sys/kernel/hotplug` before ConfigFS USB.
Both exact Images have `CONFIG_UEVENT_HELPER` disabled, and Linux registers that
sysctl only when the symbol is enabled. The exact sealed BusyBox exits status 1
on the real procfs EACCES path and never reaches the following command. Because
`rdinit=/init panic=10`, PID-1 exit explains the pre-USB panic/reboot sequence.

A bounded Opus review independently classified this as a proven fatal defect,
while correctly retaining initramfs-delivery and later strict-command failures
as alternatives until ramoops or a successful USB beacon proves `/init`
execution. The fail-first regression now executes the unguarded and guarded
forms under the archived AArch64 BusyBox. The only source fix is `|| :` on the
optional hotplug-helper write; `set -e`, kernel, DTB, modules, and all storage
logic remain unchanged.

Reusable classifications: R3 for the fatal exact-capability mismatch, R1 for
the separate omitted host target-product identity, and R8 for premature intent
resolution before exact fallback proof.

# Current project state

Updated: 2026-08-23

The project resumes from a verified stock WW33 charging/Android rescue
baseline. Historical detail is intentionally kept out of this active document;
use Git history and dated `test-results/` records for older generations.

## Baseline

| Area | State | Evidence / next gate |
|---|---|---|
| Stock charging and Android | Passed | Corrected explicit-A/B `super`; battery charged to 47%; WW33 boot completed |
| Rescue route | Passed | Active slot A, stock recovery and Android retained |
| Mainline kernel | Passed baseline | Linux 7.1 Image repeatedly reached RAM-only target execution |
| Side USB NCM/ACM | Passed baseline | Linux UDC `a600000.usb`; exact `/30` NCM route and SSH previously passed |
| NFS + OverlayFS + systemd + SSH | Passed baseline | Generation 20 reached strict SSH in about 380 seconds |
| ADSP | Passed twice | Stock WW33 firmware, PAS/SCM, remoteproc and QRTR accepted |
| PMIC GLINK battery telemetry | Passed | V26 exposed aggregate battery/USB/wireless read-only supplies |
| Full UCSI and side charging | Passed | V26 proved sink/device mode, 500 mA USB input, rising voltage and +10 to +154 mA pack current |
| Dual-cell telemetry | Clean-twin build passed | OEM read-only cell-voltage patch remains unbooted |
| UFS read-only enumeration | Passed | Exact physical inventory obtained in prior cycles |
| Local Arch image | Passed | Read-only local-image boot, systemd, key-only SSH and rollback passed |
| Persistent Arch layout | Active next phase | Integrate proven side power with local-image Arch + key-only SSH before native repartitioning |
| VCNL36866 | Preserved, paused | Separate dirty worktree; no current subsystem expansion |

## Charging repair facts

The charging failure was not a battery or ABL defect. Incorrect liblp metadata
made first-stage init request physical `super_b` on a device with only physical
`super`. Correct explicit-A/B metadata restored `/vendor`, ASUS charger
services, sustained charging, and verified Android boot.

Candidate SHA-256:
`281d5f6bc48972a1d428db5a268a2a6078d05fbceb0008d4996ceae1f4e0f549`.

Runtime WW33 vbmeta digest:
`48cc851a31e80492d60b3d1895e6be8605f4ef5d9d7c940c8582215fd80ac005`.

The orange verified-boot state is expected because the bootloader is unlocked.

## Power and USB design

The first Linux observer keeps the Android-proven side-port topology:

- primary `a600000` DWC3: high-speed peripheral, ConfigFS NCM/ACM;
- secondary `a800000` DWC3: disabled;
- ADSP firmware: exact retained WW33 set, staged in volatile memory;
- PMIC GLINK: full battery, UCSI, and alt-mode client publication;
- charging controls: no writes;
- phone storage: disabled in kernel and DT for this cycle;
- rollback: independent timer remains armed until acceptance.

Android proves UCSI `port1` is the side `a600000.dwc3` data/charging port:
with only the PC cable connected it is UFP/sink/device while `port0` is
disconnected. The first Linux cycle therefore uses only the side cable and
defers bottom-port arbitration.

## Active successor

V7 is consumed after passing NFS, systemd, 29-zone runtime acceptance, and
key-only SSH, then exposing a target selector that omitted the canonical
candidate and never entered the charging probe. V8 generated that target
identity but was revoked unbooted because its early probe lacked a usable SSH
evidence path. Retained V9 pstore proved the rebuilt initramfs omitted the
private ADSP firmware and failed before switch-root; V10 was therefore aborted
before COMMIT. V11 embedded the firmware and passed SSH, but the probe refused
unmet runtime-mask/watchdog preconditions before hardware. V12 composed them
but exposed obsolete reserved-memory paths. V13 then exposed two 31-digit
channel-size strings. V14 masked module coldplug too late; V15 masked whole
services too early and blocked systemd readiness. V16 passed NFS, systemd,
key-only SSH, and probe isolation, then exposed an R2 deployed-DTB regression:
the full-UCSI artifact had lost three live-proven stock-owned PAS memory
exclusions, so secure firmware rejected ADSP metadata with `-EINVAL`. V17 added
those exclusions and passed NFS, systemd, strict SSH, runtime acceptance, and
fallback, but its reused initramfs still selected V16 exactly and omitted the
retained probe. V18 selected the stable power/USB capability family, reached
ADSP `running`, then exposed stale build-specific BTF in `pdr_interface.ko`.
ABI. V19 passed PDR, PMIC GLINK, and UCSI, then exposed a source-valid absent
`port_type` and a probe variable collision. V20 classified that optional
attribute but was revoked unbooted before phone contact. V21 is consumed after
its diagnostic-profile token was rejected before target USB. V22 reached the
mainline NCM/ACM gadget, then its first transport check used GNU `find -printf`,
which the sealed BusyBox 1.37 initramfs does not support; exact stock fallback
passed. V23 reached NCM/ACM, then its textual mountinfo check mistook required
`/dev/pts` for phone storage. V24 then delivered a complete typed stream and
stable NCM, but BusyBox `modprobe` rejected `--first-time`, leaving charging
telemetry absent. V25 then passed the full charging stack and side-port input,
but its 100% Full battery reported zero pack current. V26 reuses the exact
target bytes and passed the sub-full positive-current test. The power/USB
candidate track is now consumed; its canonical historical source remains
`configs/recovery-candidates/power-usb-active.json`; candidate, policy, Python,
shell, and `manifests/power-usb-active.lock.json` are generated. The lock records
`boot_policy_status=none`; the historical V20 policy row is revoked.

The initramfs builder installs the reviewed charging probe explicitly and the
archive verifier compares the embedded bytes with repository source. The
probe records:

- each UCSI port's data role, power role, port type, operation mode, sysfs
  control mode, and partner presence;
- aggregate USB online, voltage, current, negotiated maxima, input limit, and
  USB type;
- battery capacity, voltage, current, temperature, and status;
- exact side UDC, gadget binding, carrier, address, and direct source route
  after UCSI initialization.

## Storage and context

On 2026-08-19 the host had only 9 GB free. Seventy reproducible historical
`vmlinux.o` intermediates totaling 92.25 GiB were removed. Source, tracked
artifacts, signed candidates, private evidence, phone backups, and the VCNL
working tree were retained. Free space rose to about 96 GB.

The active handoff documents had grown to 3,723 lines. Historical facts remain
recoverable from Git; new work updates these concise summaries instead of
appending lifecycle transcripts.

## Immediate next gate

V26 completed the early power/USB gate with stable NCM, valid battery/UCSI
telemetry, a safe 30.2 C pack, 500 mA side-port input, rising voltage, and
positive pack current. The exact 15-module closure is retained at SHA-256
`3ebd3260581af3300187de55768b61cd8ef57f4574febb4b0540e21e7566dbcf`.

Generation 99 has now reformatted only unchanged userdata partition 23 as
unencrypted ext4, with GPT unchanged, exact fastboot return, and all UFS block
nodes relocked read-only. V27 was revoked before claim or phone contact: its
reused V20 network-root DTB disables UFS and its initramfs rejects physical
storage, so it could not stage userdata. The successor must use the proven
UFS-capable `ae717` kernel/DT composition and a target-only RAM staging
initramfs. That corrected target was signed and consumed once as
`local-image-stage-v1` with recovery generation 101. Transfer, PREPARE, and
COMMIT passed, but its replacement minimal target init exposed no NCM/ACM
before stock slot-A return about 30 seconds later. No staging SSH command ran
and no image write occurred. The exact failure line is unproven; the Image and
DTB remain independently live-proven. Because stock Android cannot boot the
new plaintext ext4, staging uses one host-built Android-sparse userdata image;
the mature mainline local-root path then reads that bounded file. A later cycle will
boot the image read-only, retain
side-port charging/NCM, and benchmark SSH against Generation 20's approximately
380 seconds.

The verified sparse userdata image was written once in four exact chunks, with
GPT and every other partition unchanged. Generation 102 then exposed mature
target NCM/ACM for 15 seconds before rollback. Offline inspection proves the
new image lacks V9's required prior-write probe, so that read-only composition
cannot complete. The target-only V10 successor uses the existing bounded
`local-write/current` mode to create only that probe inside the image, relock
all storage, and continue into the normal read-only runtime.

Generation 103 proved the target-only change was insufficient: NCM stayed
reachable for 60 seconds, but its V8 kernel deliberately forces UFS read-only
before registration and cannot satisfy local-write power containment. No probe
or target write occurred. The next writer uses the exact live-proven Generation
64 bounded-write Image, DTB, and UFS modules only for the short probe cycle;
the charging/read-only baseline returns for the subsequent Arch boot.

Generation 104 used that exact writer lineage and exposed target NCM for 14
seconds before rollback, matching the historical post-probe UFS-health path.
The stage listener attached after departure, so the write outcome remains
ambiguous and the candidate is permanently consumed. The read-only successor
accepts one canonical prior-boot UUID from the probe itself; this is bounded to
the freshly staged image proven marker-free before the sole writer ran.

Generation 105 repeated the read-only target but manual multi-call host
orchestration again attached after its 19-second NCM window. The target is
consumed without a probe verdict. The next cycle reuses byte-identical target
bytes and runs exclusively through the repository's continuous persistent-root
lifecycle, which historically captured 14-second writer stages and carries
network activation, stage reception, host-key pinning, SSH, and fallback in one
process.

Generation 106 ran through that continuous lifecycle. Host networking and the
stage listener were ready two seconds after target NCM, but zero stages arrived
before an exact 20-second rollback. Source audit proved the cause: the new
`any-prior` policy was implemented in marker verification but omitted from the
earlier pre-reporter policy gate, which therefore emitted the
`kernel-release-file` 20-second failure. The corrected successor adds that one
missing accepted case and changes no kernel or DT.

Generation 107 was built but never booted. Before admission, rollback review
found that persistent-root failures and shutdown still used SysRq hard reset,
which can route active slot A into ASUS recovery now that userdata contains a
Linux filesystem. Generation 107 is revoked unbooted. Generation 108 retains
the same kernel, DTB, charging/UFS/NCM stack, and `any-prior` correction, and
adds the reviewed fixed `RESTART2("bootloader")` helper before the emergency
SysRq fallback in failure, watchdog, and shutdown paths. Slot A is unchanged.

Generation 108 is consumed. It passed kernel identity, power/USB, UFS,
storage lock, userdata resolution, and the read-only userdata mount. It then
reported exact `userdata-mount FAIL detail=userdata-rog5-directory`: the live
filesystem no longer contains `/rog5/images`, although the retained sparse
source does. No target write occurred. The restart2 helper rebooted, but the
exact target config leaves `NVMEM_REBOOT_MODE` and `NVMEM_SPMI_SDAM` modular
and the sealed initramfs contains neither module, so the Qualcomm bootloader
reason was not written; slot A entered unauthorized ASUS recovery ADB. The
next cycle requires restored userdata content and proven reboot-mode support.

The offline Generation 109/V16 successor now provides that kernel support.
Two fresh container builds are byte-identical: config SHA-256 `15e1ea49...`,
Image SHA-256 `1a1958fe...`, 15 charging modules, and four deferred UFS
modules. Only `CONFIG_NVMEM_SPMI_SDAM` and `CONFIG_NVMEM_REBOOT_MODE` move
from modules to built-ins. The unchanged DTB already contains the standard
PMK8350 SDAM reboot cell and `mode-bootloader = <2>`. The target additionally
requires the bound `nvmem-reboot-mode` device before UFS. The exact approved
userdata sparse image was then restaged to `userdata` in four successful
chunks (38.964 seconds), with GPT and every other partition untouched.
Generation 109 is consumed. It reproduced `userdata-rog5-directory` after the
exact restage, but proved the reboot-mode correction by returning directly to
exact fastboot. The target wrote no storage. Systematic review showed the
source and sparse round-trip encode all critical directory blocks as RAW,
including the inode table and directory data around byte 60.1 GB. Generation
110 keeps the V16 kernel/DT and adds only nine read-only block hashes covering
the source blocks and their corrected 4-GiB aliases (32, 8224, and 8225).

Generation 110 is consumed and decisive: low source metadata differs, all
three high metadata blocks are zero, and the alias blocks remain unchanged.
ASUS ABL accepted the sparse transfers but left userdata unchanged. Development
has returned to the controlled mainline writer. Clean twins at source commit
`359318de...` reproduce Image `a7e0cd84...`, config `6329b42f...`, all 15
charging modules, and four UFS modules with bounded data-write plus reboot mode.

Generation 111 is consumed. Recovery departed after COMMIT, but no target USB
appeared before slot-A unauthorized recovery returned 30.708 seconds later.
No SSH transfer or storage write occurred. Retained host evidence therefore
places the failure before target USB. Exact artifact comparison proves a fatal
pre-gadget command: strict PID 1 wrote the absent `kernel.hotplug` sysctl while
`CONFIG_UEVENT_HELPER` was disabled. A sealed-BusyBox regression covers the
one-token `|| :` fix; observation recovery remains the next independent check.

Generation 112 is consumed. Guarding the optional sysctl advanced execution,
but no target USB appeared and exact fastboot returned only 6.903 seconds after
recovery departure. This excludes the 20-second UDC wait and `panic=10`, leaving
the immediate controlled kernel-release or command-line checks as the boundary.
No SSH, transfer, installer, or storage write occurred.

Generation 113 is consumed. Exact fastboot returned 31.910 seconds after
recovery departure, matching the 25-second both-checks-pass path plus measured
bootloader overhead. Release and command-line validation are exonerated. The
next concrete parity defect is the staging init's omission of the mature path's
`a600000.ssusb/mode=peripheral` transition before ConfigFS binding.

Generation 114 is consumed. The guarded mode path is absent in this mainline
tree, so it was a no-op; exact fastboot repeated after 6.903 seconds. The next
no-storage beacon distinguishes ConfigFS mount, gadget directories, descriptors,
functions, links, UDC discovery, and binding in one cycle.

Generation 115 is consumed. Its 51.961-second return selected the 45-second
UDC-identity branch: `a600000.usb` exists, but at least one additional UDC is
present. The strict selector correctly refused to bind; no storage was touched.

Generation 116 is admitted as a no-bind UDC basename classifier. It requires the
expected UDC, identifies one extra candidate by fixed controller-family timing,
and has no gadget, UFS, block-device, SSH, or installer execution surface.
Generation 116 is now consumed: its early sample found no extra yet and returned
in 16.887 seconds. Combined with Generation 115, the second UDC is a late
registration race. The next classifier waits five seconds before naming it.

Generation 117 is admitted once with that stabilization window. It reuses the
exact Image and DTB, binds no UDC, and has no gadget or storage surface.
Generation 117 is now consumed: no extra remained after five seconds. Combined
with Generation 115, the duplicate is transient during NCM+ACM ConfigFS setup.
The production staging path is simplified to NCM-only and now requires the
expected UDC to remain uniquely stable for five seconds before binding.
Generation 118 is admitted once with that target-only correction. It reuses
the clean-twin writer Image/DTB and stable recovery raw payload; one RAM-only
cycle must either expose NCM plus key-only SSH and stage the exact Arch image,
or return the earliest retained failure without any broader kernel change.
Generation 118 is now consumed. Recovery transfer and COMMIT passed, but target
NCM never appeared before exact slot-A fastboot returned. No SSH transfer,
installer, or storage write ran; intent resolved `FALLBACK_RETURNED`. The next
step is observation-only ramoops recovery, not another staging successor.
That observer found one retained 161,854-byte record, but its tail is the prior
ASUS recovery kernel's kexec shutdown and carries no target lineage. The target
boundary remains unclassified. Use one timing-only pre-NCM discriminator next;
do not change the UDC gate, kernel, DTB, or modules in that cycle.
Generation 119 is admitted once as that timing-only discriminator. It reuses
the exact Image/DTB and power/USB path, maps pre-storage failures to fixed
5–85 second delays, and stops before UFS, userdata, SSH, or installer code.
Generation 119 is consumed. Its exact 77.046-second USB timeline selects the
70-second `ncm-address` branch. BusyBox syntax passes independently; the next
target must distinguish absent `usb0`, exact preexisting address, conflicting
address, and first-add rejection without changing any earlier USB behavior.
Generation 120 is admitted once for exactly that address-state classification.
It stops before carrier, charging, UFS, userdata, SSH, and storage.
Generation 120 is consumed and selected `address-show-failed`: `usb0` became
unqueryable immediately after link-up. The root-fix successor moves the exact
`mdev -s` scan from post-bind to pre-bind, matching the mature working path,
without changing the kernel, DTB, UDC policy, address command, or later stack.
Generation 121 is admitted once as that full-staging root-fix successor.
Generation 121 is consumed: no target USB appeared and fastboot returned after
31.992 seconds. Moving the second mdev scan did not fix enumeration. The next
full-staging target removes that redundant scan entirely; the initial devtmpfs
scan and explicit UDC/usb0 polls remain.
Generation 122 is admitted once as the full-staging successor with no second
USB-time mdev scan.
Generation 122 is consumed and selected the 25-second UDC identity timeout.
The next no-bind classifier names the ConfigFS-induced extra UDC or zero/expected
churn before any gadget bind or storage path.
Generation 123 is admitted once for that no-bind post-ConfigFS inventory.
Generation 123 is consumed and proved zero/exact `a600000.usb` churn with no
unexpected name. The successor uses a bounded two-sample exact selector and
still rejects wrong/multiple candidates plus post-bind identity loss.
Generation 124 is admitted once as that full-staging successor.
Generation 124 is consumed at the two-sample timeout. The next selector binds
immediately on one exact observation, retries only absence, and verifies exact
identity after bind.
Generation 125 is admitted once as that full-staging successor.
Generation 125 is consumed at the 25-second bind timeout. The next selector
attempts the exact bind directly from the expected path and performs full
inventory validation after successful binding.
Generation 126 is admitted once with direct exact-path binding.
Generation 126 is consumed: the exact bind write was synchronously refused
while the expected UDC path remained present. Next classify the kernel errno.
Generation 127 is admitted once for that storage-free errno classification.
Generation 127 is consumed. Its target NCM product enumerated for 89.864
seconds, proving ConfigFS bind success. The host then rejected the otherwise
exact interface because the shared NCM model set omitted
`ROG5_local_image_stage` (R7); no target network or storage write ran.
Generation 128 is the one admitted full-staging successor. It reuses the exact
kernel, DTB, modules, installer, and stable recovery bytes; only the target
initramfs identity/exact-unbound UDC retry and the proven host R7 fixes differ.
Generation 128 is consumed. It returned to exact slot-A fastboot 6.903960
seconds after recovery departure, before target USB or storage. Linux 7.1
ConfigFS store semantics exclude bind-loop exhaustion; the immediate
post-bind `/sys/class/udc` level check rejected the already-observed transient
empty phase. The next target must retain exact ConfigFS readback and remove
only that false post-bind class invariant.
Generation 129 is admitted once with exactly that target-initramfs-only fix;
kernel, DTB, modules, recovery raw bytes, installer, storage scope, and slot-A
fallback remain unchanged.
Generation 129 is consumed and proved exact target NCM enumeration for
0.519517 seconds. The host missed the short-lived product while NetworkManager
was still activating. The next target must publish the existing exact stage
protocol before running the detailed power/USB loader and keep a terminal
failure visible long enough for host capture; no UDC or kernel redesign.
Generation 130 is admitted once with that existing stage protocol and no
kernel/DT/module/storage-scope change. It either reports the exact power/USB
loader boundary or continues into the unchanged UFS/SSH/image staging path.
Generation 130 is consumed. The target NCM/reporter dwell lasted 10.506
seconds, but the host invoked `wait_for_stage_host_key()` instead of the
already-implemented `wait_for_target_host_key()` listener, so the exact detail
was sent to no listener. No storage write occurred; fallback passed.
Generation 131 is admitted once with the existing stage-aware wait selected.
The target reporter and all kernel/DT/module/storage paths are unchanged under
a fresh one-use identity.
Generation 131 is consumed and returned exact `power-usb` detail
`module-qcom-q6v5-load`. The packaged module was for
`7.1.4-gae717d919f87`, not target `7.1.4-g359318de534f`; the mismatch is the
proven rejection cause. Matching g359 UFS and power/USB twin module roots are
retained and must be supplied to the next initramfs build.
Corrected Generation 132 target twins are built but unsigned and unadmitted at
`54ab6e369a7b558c7f0952ced166ea289c16a384a46861ab5f1ea5ccd7da8406`;
all 19 packaged modules have exact g359 vermagic. No phone candidate exists.
Generation 132 is now signed and admitted once with manifest
`ce0f2c191afaf5c4ed49fc513062422b54c1cab3639e462cd63e00a372b02a1b`
and recovery `7e555e989ceed7db4f71a6f2195b802cbc532460892e4511a41a51db4ca5c114`.
Generation 132 is consumed. Exact stage evidence proves the g359 power/USB
module chain passed and UFS modules loaded; the target then timed out at the
generic expected-116 physical-device count before any storage write. The next
cycle must report the observed count, not repeat this generic failure.
Generation 133 is admitted once with only count-bearing `ufs-count-N` terminal
evidence; all kernel, DT, module, reporter, and storage-scope inputs are
unchanged from Generation 132.
Generation 133 is consumed and proved exact `ufs-count-0`: no physical UFS
device appeared after the g359 module chain and 20-second wait. Successor
issuance is paused for DT/config/source comparison and bounded Opus review.
Generation 134 is admitted once after the required review. It retains all
Generation 133 bytes except the read-only platform/binding/SCSI-host classifier.
Generation 134 is consumed and proved exact `ufs-platform-0`: the runtime has
no platform device matching address `0x1d84000`. The next classifier must read
the runtime `/proc/device-tree` UFS node and status before changing drivers.
Generation 135 is admitted once with runtime DT node/status classification and
no kernel, DTB, module, or storage-scope change.
Generation 135 is consumed and proved runtime UFS DT exists with status okay,
but the address-name platform scan found zero. Next use exact `of_node` symlink
identity rather than inferring platform-device names.
Generation 136 exact-OF-node target twins are built and signed but unadmitted.
No claim or phone boot exists; target SHA-256 is
`ee1afba10527d7324c4dc596918f7bc1cb14be7858b540acbbbb3de2fe04f2ed`.
Generation 136 is admitted once with exact OF-node platform matching; kernel,
DTB, modules, reporter, and storage scope remain unchanged.
Generation 136 is consumed and exact OF identity still proves no UFS platform
device. The current pair (`a7e0cd84…`/`4f6518b3…`) is therefore retired for
UFS work; the next cycle returns to the live-proven g359 pair
(`7c89d9a0…`/`40fb477a…`) with a minimal UFS-only target.
The live-proven baseline inputs are reverified and retained: exact Image
`7c89d9a0a7ace2b0057b6cf2b535e134da596d3f3c3c3774c5b64014e32bf234`,
DTB `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`,
and four matching g359 UFS modules. No baseline successor is admitted yet.
Generation 137 is admitted once as a minimal UFS-only baseline using those
exact live-proven inputs. It has NCM/stage reporting and fallback only; no
power, SSH, userdata, installer, mount, or storage-write execution path.
Its sole cycle is consumed. Stable NCM and all four exact modules passed, but
the topology remained `ufs-count-0` for 20 seconds. Exact slot-A stock recovery
USB returned; its post-reset `18d1:d001` descriptor exposed stale fallback
policy rather than loss of rescue. The targeted host correction now accepts
that exact complete descriptor tuple, rejects mixed identities, and has passed
against the retained preboot record and live recovery USB. The stronger
retained control is Generation
109: its ae717 Image/DT/modules passed UFS under the current wrapper and its
built-in PMK8350 reboot-mode path returned exact fastboot. Generation 138 uses
that live-proven lineage with the minimal NCM/UFS counter only. Do not retry
Generation 137 or flash its non-working kernel.
Generation 138 is consumed. Built-in PMK8350 reboot mode worked and returned
exact fastboot, but UFS remained `ufs-count-0`. Exact comparison with the
sealed Generation-109 init proved the minimal init omitted its packaged
15-module PMIC GLINK/remoteproc/UCSI loader before UFS. Generation 139 restores
that single proven ordering dependency while keeping storage unreachable.
Generation 139 is consumed. The full power/USB loader passed, but UFS still
reported zero because the minimal init's `set -f` disabled pathname expansion;
all `/sys/class/block/*` and earlier platform-device classifiers had iterated a
literal asterisk. Generation 140 removes that line and restores Generation
109's exact 116-node disk-plus-partition topology count. Storage remains
unreachable until that count passes.
Generation 140 is consumed and passed the exact complete 116-node UFS topology,
power/USB telemetry, NCM, and automatic fastboot return. Generation 141 moves
to the real staging objective: the same proven lineage plus corrected full
writer init, key-only SSH, the hash-verified 649,960,943-byte Arch gzip, one
bounded userdata image-file install, and complete storage relock.
Generation 141 is consumed. UFS passed and the target host key was pinned, but
OpenSSH reset pre-auth with `Not allowed at this time` because the sealed base
retained a zero-byte `/etc/nologin`; no image transfer or write occurred.
Generation 142 validates and removes only that volatile boot-inhibition file
before starting key-only sshd, with all writer and storage bounds unchanged.
Generation 142 is consumed by an R6 host-only race: post-COMMIT cleanup saw the
new target NCM interface before NetworkManager exposed either ownership field.
No target stage, SSH, transfer, installer, or write evidence exists; exact
fastboot fallback passed. Generation 143 observes that no-address interface as
ownership-unknown during non-final cleanup, while escaped `/30` and final
unmanaged state still fail.
Generation 143 is consumed: the NetworkManager classification fix held, but a
redundant post-COMMIT `wait_host_clean()` delayed target profile activation
until the target returned fastboot. No stage, transfer, or write occurred.
Generation 144 relies on the bundle server's completed canonical cleanup and
activates target networking immediately; final cleanup remains mandatory.

Generation 77 rolled back before any target stage because its packaged
`pdr_interface.ko` retained rejected BTF. Generation 78 removed only that
section and advanced to an exact target `ufs-ready` failure record, proving
that the earlier loader boundary was cleared. Its power/USB loader then failed
before UFS, but the old generic `detail=power-usb` cannot identify which
module, telemetry, Type-C, NCM, or safety check failed. Generation 78 is
consumed and revoked; exact stock slot-A fallback and host cleanup passed.
The next candidate must report the new bounded per-check failure code and ask
only which power/USB loader boundary fails. It must not reuse Generation 78.

Generation 79 consumed its sole cycle and identified the failure as the
Type-C role parser: mainline exported `host [device]` and `source [sink]`,
where brackets mark the active role, but the loader required bare `device`
and `sink`. Exact stock slot-A fallback and cleanup passed. The correction
accepts only the exact bare fixed-role form or the exact bracketed active-role
form; inactive and malformed forms remain rejected.

Generation 80 reused the exact
Generation 79 kernel, DTB, recovery raw image, UFS modules, charging modules,
firmware, local image, and rollback. Its twin target initramfses reproduce at
SHA-256 `7a69e97606d2d4422ba0ead12f5225802cd27d3b036914c0041b7c9da1973c25`.
Only exact Type-C active-role parsing changed; no kernel compilation ran.

Generation 80 then passed power/USB, deferred UFS, storage lock, and exact
userdata resolution before failing at the generic `userdata-mount` boundary.
Exact stock slot-A fallback and cleanup passed. Generation 81 is the unbooted,
unadmitted target-only discriminator; it preserves the exact mount operation
and reports the first failing mount/containment substage. Twin initramfs
SHA-256 is `6590cc95c9e73fedf24b3b1643d6395514943057b9e2ebb3ba6a05347905033d`.

Generation 81 proved the ext4 mount syscall itself returned nonzero. Exact
stock slot-A fallback and cleanup passed. A bounded read-only Opus review and
independent Linux 7.1 source inspection both recommend measuring the current
filesystem type/features before changing config. Generation 82 is the
unbooted, unadmitted classifier; it adds bounded `blkid`, `dumpe2fs -h`, mount
status, and ext4/VFS error categories without changing the mount operation.

Generation 82 is consumed. It retained mount status 255/`EINVAL`, but BusyBox `blkid` exposed
no recognized filesystem type, so its type-gated path did not run
`dumpe2fs`. Generation 83 is consumed. It reads only
64 bytes at the standard superblock offset to distinguish ext4/F2FS magic and
runs `dumpe2fs -h` whenever ext4 magic is present, independent of `blkid`.

Generation 83 reproduced mount status 255/`EINVAL`, but sealed BusyBox `od`
compressed duplicate hex lines to `*`. Exact execution of that BusyBox proved
`od -v` is required. Generation 84 is consumed; no kernel, config, recovery,
or mount behavior changed.

Generation 84 proved the restored WW33 userdata was encrypted F2FS rather than
plaintext ext4. The owner-authorized Generation 99 successor completed the
replacement with unencrypted ext4 without changing GPT. The fresh filesystem
has UUID `0892bacf-3e02-41b0-84a4-5f05c2df7ce5`, label `rog5-linux`, and
59,513,299 blocks. V27 is revoked unbooted for its UFS-excluding composition;
stock Android remains excluded until a corrected Linux image is safely
published.

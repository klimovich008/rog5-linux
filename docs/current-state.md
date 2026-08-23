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

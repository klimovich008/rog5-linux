# Current project state

Updated: 2026-08-21

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
| PMIC GLINK battery telemetry | Passed once | Aggregate battery/USB/wireless read-only supplies observed |
| Full UCSI | Host prevention work active | Canonical candidate has no boot authority until the mandatory checklist passes |
| Dual-cell telemetry | Clean-twin build passed | OEM read-only cell-voltage patch remains unbooted |
| UFS read-only enumeration | Passed | Exact physical inventory obtained in prior cycles |
| Local Arch image | Passed | Read-only local-image boot, systemd, key-only SSH and rollback passed |
| Persistent Arch layout | Deferred | Resume after power/USB and slot-A preservation gates |
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
`/dev/pts` for phone storage; fallback again passed. V24 is the next
target-only observer. The only hand-maintained successor source is
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

The next observer runs after NCM carrier and before NFS, systemd, or SSH. It
streams bounded typed battery, power-supply, Type-C, remoteproc, PMIC GLINK,
UCSI, and dmesg records over ACM. Optional telemetry records
`present`/`absent`/`error`; only identity, unsafe power or temperature, storage
visibility, transport integrity, and rollback failures are fatal.

The exact 16-file module closure produced twin-identical 22.4 MB initramfses
with SHA-256 `64c0e4be67f39817c7d86c31ee4d07fd0c9e7a076a971fd3fb8b1b9934c1b2d3`.
The focused `probe` tier takes about 5.6 seconds. The ASUS wrapper path now
checks a recovery-only content-addressed cache before compiling; documentation
and target-bundle bytes are outside that key.

Publish the canonical V24 source and exact-head CI, then build, sign, and admit
one byte-distinct RAM-only candidate through the existing reviewed workflow.
Its sole live question is whether side-port NCM remains stable while
battery/UCSI telemetry reports sustained positive input current at a safe
temperature.

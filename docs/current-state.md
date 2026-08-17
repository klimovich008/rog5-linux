# Current-state evidence ledger — 2026-08-01

This long-form file preserves verified chronology and exact identities. For
day-to-day orientation, start with [active-context.md](active-context.md).
The ordered plan is in [ROADMAP.md](../ROADMAP.md), and the detailed recovery
design is in [recovery-control-plane.md](recovery-control-plane.md).

## Hardware and boot

- Device: ASUS ROG Phone 5, codename `anakin`, Snapdragon 888 / SM8350,
  Adreno 660, roughly 11 GiB usable RAM.
- Bootloader: unlocked; verified boot reports orange.
- Development/fallback slot: B. Active-slot metadata is restored to B after
  the slot-A recovery path entered Qualcomm crashdump; see
  [the charging recovery runbook](asus-charging-recovery.md).
- Retained AVB metadata proves slot A is internally mismatched: `boot_a` is
  ASUS `18.0840.2103.26-0`, while `vendor_boot_a` is
  `18.1220.2202.206-0`; neither component is to be flashed at low battery.
- Experimental boot method: attended `fastboot boot` only.
- No experimental kernel, recovery, DTB, or Linux root has been flashed.
- Installed fallback: userdata-backed Alpine 3.24 on
  `5.4.134-qgki-perf-00001-g6c308144c23e`.
- Proven temporary baseline: vendor-derived
  `5.4.210-qgki-perf #20`.
- Mainline development kernel: reproducible Linux 7.1.4 ARM64.

The installed fallback is intentionally left available after every temporary
cycle.

The phone's USB-free immediate restart is now tracked separately from charger
insertion. The running 5.4.134 fallback rejects its vendor `msm-poweroff`
module on symbol-version mismatch and has no bound `msm-restart` platform
device; the retained PMIC log identifies the current Power-key event as a hard
reset. This strongly supports a broken shutdown path, while the earlier
`USB_CHARGER` PMIC trigger independently proves charger-triggered wake can also
occur.

It is not an accepted low-battery charging environment. Its ASUS/Qualcomm
charging stack is incomplete, so external power can boot Alpine while pack
voltage falls. Slot-A recovery is also rejected after it entered crashdump.
Stage 1 remains paused, its claim is unconsumed, and neither installed slot is
claimed to charge the pack. Fastboot must prove `battery-soc-ok: yes` and
substantial voltage recovery before Stage 1 resumes.

The retained build-21 kernel and `ramdisk-new` reproduce the historical
`rog5-alpine-5.4.210-rtcharger.img` exactly at
`b5805cc29cea05ed13f0e4695ba8ffa50a2893223ff2fc06b6b9c60decf88d86`.
This is provenance evidence only. The original manifest calls build #21 a
charger-calibration experiment and contains no successful-boot evidence; the
separate image/kernel #20 remains the documented known-good charging baseline.
A new headless RAM-only derivative combines the coherent 5.4.210 poweroff
closure with the exact six charger/ADSP modules, no userdata path, NCM/ACM,
SSH, battery samples, and a 30-second diagnostic rollback. Its clean twins
reproduce at initramfs
`7366600f925587613629a2336036dd75321c67a5e51ffa470b43de40fdec74fb`.
USB diagnostics and SSH start before charger activation, so charger-stack
failure does not suppress the primary live evidence channel.
The installed-fallback kexec route is consumed after failing before execution:
that fallback has `CONFIG_KEXEC=n` and `CONFIG_KEXEC_FILE=n`. A separate direct
bootloader route is consumed after an accepted RAM-only boot produced no target
USB during a 66-second blackout and returned to exact fallback. Voltage moved
only 6.900 V to 6.901 V. Charging remains unproven. The successor now arms
rollback before the first `mdev`, uses dependency-aware base-module loading,
and retains base failures for post-USB inspection. The shorter rollback is an
intentional discriminator: fallback before the earlier 66-second boundary
proves that PID 1 reached the arm point.

That successor is also consumed. Its exact fastboot device departed, no target
USB appeared, and exact fallback returned on the same 67-second boundary even
though rollback was now 30 seconds and armed before `mdev` or modules. This
excludes module ordering and the userspace timeout as causes of the return and
strongly indicates PID 1 never reached the arm point. Build #21 has no built-in
initramfs, while the proven 5.4.210 recovery wrappers do; direct build-21
fastboot packaging is retired. The coherent WW33 charging payload has now been
recomposed as a distinct direct header-v3 RAM-only image, removing the
ASUS-5.4-to-ASUS-5.4 kexec boundary without returning to build #21. The first
offline composition was rejected before claim or boot because it selected
slot A for the matching `vendor_boot` but retained the kexec initramfs's
slot-B assertion. V2 fixed that mismatch but was also rejected before issuance:
its inherited SysRq rollback would reboot the known-bad active slot A. V3
proves the sealed initramfs and active-slot requirement both select A and
replaces only that rollback with a static AArch64
`RESTART2("bootloader")` helper. A returned syscall stays fail-closed instead
of falling through to a normal reboot. Clean twins match at
`17380c1b…e8ae`. Its sole live cycle was consumed: ABL accepted it, no target
USB or 30-second userspace rollback appeared, and Qualcomm `05c6:900e`
full-RAM-dump mode enumerated about 115 seconds later. Slot B was restored
after physical fastboot recovery. The image must never be retried. See the
[direct-entry offline checkpoint](../test-results/2026-08-17-official-ww33-direct-charging-rescue-offline.md).
The earlier stock charging candidate is separately consumed: its bundle
transferred and its claim entered, but the post-claim recovery response timed
out and target execution remained unknown, so it cannot be reused.

The exact WW `18.0840.2202.231` slot-B stock boot has since been recovered and
authenticated against installed ASUS-signed `vbmeta_b`. Its signed payload,
header-v3 metadata, empty image command line, 5.4.134 kernel, fingerprint, and
February 2022 patch all match the already coherent slot-B `vendor_boot`, DTBO,
and vbmeta lineage. Its sole RAM-only boot was consumed once from slot B at
6.886 V. Exact fastboot returned about 19 seconds later at 6.885 V with
`battery-soc-ok: no`; no charger USB, ADB, or crashdump appeared. A bounded
fallback postmortem found empty pstore and two `PS_HOLD`/`HARD_RESET` cycles
whose ordering is ambiguous. This closes the simple temporary stock path and
freezes further wrapper work. See the
[exact stock live result](../test-results/2026-08-17-stock-slotb-charger-live.md).

The normal powered-off architecture now requires persistently restoring that
exact image to `boot_b`, after separately preserving a verified recovery route.
The current hard boundary forbids that write while `battery-soc-ok: no`, so
Stage 1 and all additional phone-storage work remain paused.

Two bounded RAM-only vendor-kernel charging probes returned directly to exact
fastboot without storage access. The consumed 30-second probe changed the
reported pack voltage from 6.801 V to 6.933 V, but the consumed five-minute
probe changed it from 6.934 V to 6.931 V. A subsequent fastboot soak fell from
6.931 V to 6.925 V over 30 minutes. None proves net-positive charging.

The consumed 90-second output-only telemetry cycle then produced 35 complete
ACM frames, but every frame reported zero power-supply devices. The retained
5.4 config has the Qualcomm battery and PMIC-GLINK drivers built in; live Type-C
logs reached `Attached.SNK` while the battery service remained absent. Source
review binds that missing registration to the unavailable
`PMIC_RTR_ADSP_APPS` / `msm/adsp/charger_pd` path.

A later RAM-only hybrid used the exact slot-B 5.4.134 kernel with its matching
installed vendor-boot companion and the preserved ASUS charger/recovery
ramdisk. Its first version was canceled before claim entry. The bounded second
version was consumed once, disconnected USB, and returned to exact fastboot
about eight seconds later without ADB, charger telemetry, or crashdump mode.
It is not a charging route and must not be retried. The remaining hardware
discriminator is a physical side-port-VBUS disconnect while the bottom ASUS
wall charger remains attached; the host hub's logical port-power control did
not electrically isolate the side cable. See the
[live charging-rescue result](../test-results/2026-08-16-low-battery-charging-rescue-live.md).

## 2026-08-12 headless MVP milestone

Generation 20 completed the real temporary Linux 7.1.4 path through stable USB
NCM, read-only NFSv4.2, sealed-root verification, OverlayFS, systemd, OpenSSH,
and strict key-only runtime acceptance. The target remained fault-free until
the intentional rollback watchdog boundary, then returned to exact Alpine
fallback with strict SSH and host cleanup. Generation 20 is consumed, removed
from temporary-boot policy, and must never be retried.
Pstore was unavailable after fallback and remains inconclusive. See the
[live result](../test-results/2026-08-12-generation-20-arch-ssh-mvp-live.md).

## What works on the vendor-derived baseline

The 5.4.210 temporary baseline has passed:

- UFS root and initramfs startup;
- USB NCM and key-only SSH;
- DSI DRM/panel and FocalTech touch;
- real Qualcomm charger path and UPower battery reporting;
- Plasma Mobile with software rendering;
- power-button screen toggle, DPMS, and OLED-off server operation;
- Wi-Fi client and AP/hotspot after delayed radio startup;
- supervised modem support processes.

The persistent 5.4.134 fallback remains useful for SSH, screen-off operation,
and remote GUI, but it does not have matching ADSP/battery modules.
Incompatible 5.4.210 modules must not be force-loaded into it.

The fallback screen service was restored after the latest rejected P2
entry cycle. The panel can remain off while the server is reachable.

## Recovery

Recovery v18 remains historical staging evidence and is recorded as revoked in
`manifests/temporary-boot-images.tsv`. Diagnostic generations 0–12 are consumed
and absent from boot policy. Generation 11 reached exact recovery ACM/NCM, then
failed closed before the bundle-server ready marker when the privileged host
path rejected its newly started TCP 8081 collector as not uniquely confined.
No PREPARE, transfer, COMMIT, NFS, or target occurred; exact Alpine fallback
and host cleanup passed. A production-faithful host-only reproduction captured
the real scoped `SO_BINDTODEVICE` endpoint, and the controller now requires one
exact scoped record with the sole launched PID/fd owner and no IPv6 conflict;
complete CI, host installation, and implementation-commit exact-head CI pass.
Generation-12 AVB `615d7498…d72cf6` is the distinct authority-free successor
over the byte-identical raw recovery. Its deterministic twins and immutable
offline profile pass. Commit `52ce322` and exact-head GitHub Actions run
`30935842119` publish that reviewed checkpoint. Commit `328b33c` adds the
exact live profile and lifecycle selector, the sole
central-policy `allow` row, and a fail-closed irreversible Generation-12 claim
consumer; exact-head run `30942517411` passed. An anchored strict-SSH
Alpine-to-fastboot transition and connected preflight then passed, with the
conflicting Steam TCP-8081 socket restored. Commit `1ee5508` and exact-head run
`30944062957` published that evidence. The sole Generation-12 lifecycle then
entered its private claim, transferred all 46,163,787 bundle bytes, accepted
correlated PREPARE/COMMIT, and produced 40 lossless target frames through
stage 70 `nfs-mount-begin`. USB disconnected before stage 80 `nfs-mount-ok` or
a terminal fault frame. The watchdog returned exact Alpine fallback; strict
SSH, profile restoration, host cleanup, Steam socket restoration, and
`FALLBACK_RETURNED` resolution passed. Generation 12 is removed from policy,
recorded consumed, permanently claimed, and never reusable. The [live
result](../test-results/2026-08-04-generation-12-nfs-mount-disconnect-live.md)
does not claim a panic without current-cycle console or postmortem lineage.
Recovery-side postmortem transport has since been hardened offline: the native
responder validates the full fixed pstore snapshot against canonical status
metadata before opening its session, parses exact console-ramoops and
dmesg-ramoops printk forms, and returns bounded lineage-marker hashes. The
read-only `postmortem-status` host action compares those hashes with one exact
expected candidate/boot ID and redacts the reversible tail. This is a future
correlation mechanism, not proof that ramoops survives target → bootloader →
recovery; the result and candidate recommendation remain HOLD. See the
[offline checkpoint](../test-results/2026-08-09-recovery-postmortem-lineage-offline.md).
The complete recovery composition has since been
[refrozen offline](../test-results/2026-08-09-recovery-postmortem-refreeze-offline.md):
two shell-free initramfses reproduce at `c778588a…a380`, and two clean sealed
ASUS 5.4 builds reproduce kernel `4b30cfff…9495`, raw boot-v3
`5141f0d0…deab`, and unsigned AVB `b004e500…c218`. This closes the offline
integration gap only. The disposable trust input, `Algorithm: NONE`, absent
policy/candidate record, and untested physical retention keep admission at
**HOLD**.
The subsequent [exact-UDC recovery hardening](../test-results/2026-08-09-stable-recovery-exact-udc-offline.md)
removes stable recovery's arbitrary-controller fallback. It accepts only one
stable exact `a600000.dwc3`, revalidates before and after binding, and produces
byte-identical 7,602,307-byte initramfs twins `afc55f96…d790`. Wrong, renamed,
multiple, disappearing, or changing candidates now leave rollback armed and
fail closed. This is ignored offline evidence with no wrapper, candidate,
policy row, credential, or boot authority; admission remains **HOLD**.
The subsequent
[observation-only recovery composition](../test-results/2026-08-09-observation-only-recovery-offline.md)
adds a packaged `observation-only-v1` identity. Its responder permits only
`HELLO`/`STATUS`, refuses execution verbs before mutation, and starts only
from pristine state. Twin 5,371,780-byte initramfses `613d6e3e…70db` also
remove the fetcher, verifier, trust key, kexec binary, and bundle root. The
[outer-wrapper checkpoint](../test-results/2026-08-09-observation-recovery-wrapper-offline.md)
then binds that archive into two clean, byte-identical ASUS 5.4 Images
`efcc4db8…a6ab`, raw boot-v3 images `fdcf9b85…a163`, and unsigned AVB images
`63fc0a1a…43b1`. Exact pstore config and the 4 MiB ramoops command line pass,
but physical retention is still untested. No candidate, signing, or boot
authority exists, so admission remains **HOLD**.
The following
[fallback-transition preflight](../test-results/2026-08-09-fallback-ramoops-transition-preflight-offline.md)
adds a separate read-only action to the identity-pinned fallback helper. It
requires the same exact command-line and `0x9b800000 + 0x400000` DT reservation,
no overlapping fixed sibling, no visible ramoops consumer, and empty pstore
before a later observer transition. The action cannot reboot and passed ten
hostile fixture groups plus the existing fallback-helper suite. It has not
been run on the phone and therefore changes neither the retention result nor
the **HOLD** recommendation.
The subsequent [two-identity retention review](../test-results/2026-08-09-retention-cycle-two-identity-review-offline.md)
jointly binds the exact execution wrapper, observation-only wrapper, boot-v3
and unsigned-AVB composition, transition order, absent new claims, and empty
temporary-boot policy. Hostile offline tests pass, but no physical retention
result, candidate issuance, credential, or boot authority exists. Admission
therefore remains **HOLD**.
The [Haven-aware retention refreeze](../test-results/2026-08-10-haven-retention-observer-refreeze-offline.md)
supersedes the retained execution/observer bytes without changing authority.
Its repository-owned build record binds the exact recovery responder source,
builder, pinned ARM64 image/toolchain, and reproducible output before both
recovery archives are accepted. The distinct clean twins pass the joint
authority-free review, but no physical retention result, new claim, policy
row, production signature, or boot authority exists. Admission remains
**HOLD**.
The subsequent
[production execution refreeze](../test-results/2026-08-10-production-retention-execution-refreeze-offline.md)
replaces only that execution role with guarded project-key clean twins. The
exact recovery initramfs is `ab0a3ee2…`, wrapper Image `8a600acf…`, raw image
`ea9e90fd…`, and unsigned AVB image `cba4e6e8…`; the observation-only role is
unchanged. The joint verifier still reports undefined claims, zero policy
`allow` rows, `authority=none`, `retention=unproven`,
`missing_pstore=inconclusive`, and recommendation **HOLD**. Commit `adef485`
and exact-head GitHub run `31363962284` pass.
The observer side now has a separate
[offline-only current HOLD gate](../test-results/2026-08-10-current-observation-recovery-live-gate-offline.md).
It pins observation initramfs `b2440d8c…`, Image `eedb7deb…`, raw image
`5daf0919…`, unsigned AVB `3c9b2820…`, and all retained verification inputs;
connected actions fail before host inspection. Hard-linked retained trees are
not admissible inputs. No claim, policy row, sequence runner, credential, or
phone action was added, so the result remains **HOLD**.
The next [offline sequence reference](../test-results/2026-08-10-retention-sequence-reference-offline.md)
binds two distinct, still-unregistered draft claim bodies and models every
irreversible boundary from execution preflight through one observer read. It
rejects wrong order, duplicate operations, missing rollback, wrong port or
serial, weak lineage, and retries; absent or ambiguous pstore remains
inconclusive. The current gates still reject connected actions and no runner,
claim, policy row, credential, or phone action exists, so **HOLD** is
unchanged.
The follow-on [offline transaction journal](../test-results/2026-08-10-retention-cycle-transaction-offline.md)
provides the missing crash-synced handoff record. Its append-only canonical
events bind one host boot, physical USB location, distinct target/fallback boot
IDs, exact claim dispositions, same-port fastboot serial, both rollback-armed
boot intents, and a preclaimed one-read postmortem budget. Ambiguous intent on
process reopen is terminal and inconclusive, not retryable. The journal has no
CLI, process, credential, or device surface and no existing live helper calls
it; claims and policy remain empty and **HOLD** is unchanged.
The [offline callback adapter](../test-results/2026-08-10-retention-cycle-adapter-offline.md)
then binds six exact repository helper descriptors to those durable intents.
Injected fixture callbacks can run only after the journal event is visible and
fsynced; failure or malformed output leaves that intent terminal-only on
reopen. Its fallback descriptor now uses the accepted nonce-framed ACM reboot
helper, not the legacy SSH-key path. A separate
[pure executor contract](../test-results/2026-08-10-retention-cycle-executor-contract-offline.md)
pins the exact helper bytes, arguments, interpreters, closed environments,
stream bounds, deadlines, and cleanup semantics without adding a launcher.
The adapter and contract have no built-in executor or CLI and cannot open the
canonical host-pin path they carry. The real gate profiles still reject boot,
so ordering is proved without connected authority. Claims and policy remain
empty and **HOLD** is unchanged.
The [pure executor boundary](../test-results/2026-08-10-retention-cycle-executor-boundary-offline.md)
adds exact program/interpreter descriptor revalidation, public fallback
host-pin snapshot validation, and fail-closed decoding without opening a path
or launching a process. The follow-on
[boot-output checkpoint](../test-results/2026-08-10-retention-cycle-boot-output-contract-offline.md)
defines one exact terminal `rog5-retention-boot-result-v1` record and decodes
all six action results only with matching descriptor attestation and journal
lineage. Fallback reboot now reports its actually verified physical location,
fastboot product/serial, and digest of the inspected public host pin. The
selected production and observation recovery gates still cannot emit a
successful record because both are HOLD; this is decoder/schema readiness,
not execution readiness.
The [offline runtime-closure fixture](../test-results/2026-08-10-retention-cycle-runtime-closure-offline.md)
now holds those real descriptors and one fresh fsynced intent while proving
new empty pipes, bounded fixed-writer process control, cross-cycle proof
refusal, and exact six-action result-event release. Its decoded wrapper is
explicitly adapter-ineligible. It does not execute the held production
program/interpreter, so production descriptor execution, a live entry point,
host-pin admission, claims, policy, and connected authority remain unproven or
absent; **HOLD** remains mandatory.
The [held-descriptor execution successor](../test-results/2026-08-10-retention-cycle-descriptor-execution-offline.md)
now proves the missing exec mechanism with a pinned harmless probe. It executes
the held interpreter by FD and the held program through `/proc/self/fd/198`,
while independently reporting exact descriptor identities, closed process
context, `0077` umask, devnull/bounded-pipe state, FD closure, and
session/process-group isolation. Nine hostile groups and the expanded
27-test admission suite pass. It is still adapter-ineligible and does not run
the six production helpers; `production_descriptor_execution=unproven` and
**HOLD** remain exact.
The complete 18-field lifecycle parser correction is published through
`606303a` with green exact-head run `30952333022`. Successor v2 was consumed
before any phone boot while exposing a mismatch between the generic claim
consumer's account-home guard and the lifecycle verifier's XDG-state guard
lookup; it must never be retried. Successor v3 was then consumed once after
exact-head run `31395428663`: fastboot accepted the sealed recovery image, but
no recovery ACM ever enumerated and the exact Alpine fallback returned on the
same USB port about 21.4 seconds after fastboot disconnected. Bounded fallback
evidence reports `PS_HOLD` / `HARD_RESET`, no PMIC-watchdog signal, and empty
temporarily mounted pstore; the empty result remains inconclusive because no
retained marker had first been proven. The physical ASUS 5.4 wrapper exposes
the exact UDC inventory `a600000.dwc3`, `a800000.dwc3`, and `dummy_udc.0`, while
recovery-init rejected every total count other than one. The implementation
successor now requires exactly that three-name inventory, selects only
`a600000.dwc3`, and rejects unknown, missing, renamed, extra, or changing
entries. The v4 production candidate (`ee662ab9…6752`) booted once and proved
exact recovery ACM/NCM, but the host rejected the recovery ancestry because
the invocation supplied short USB name `1-1.2` instead of its full canonical
physical path. No control session, payload, NFS, or target ran; the 180-second
rollback returned exact Alpine. V4 is consumed. V5 (`e4ae6373…c722`) changes
only the deterministic AVB generation over the unchanged clean-twin raw
wrapper. Its sole RAM-only boot reached exact recovery ACM/NCM, transferred
and verified the 46,166,378-byte bundle, accepted PREPARE and COMMIT, and
started the restricted NFS server, but target ACM never appeared. Recovery
remained present until the 180-second userspace rollback; exact Alpine,
strict SSH, profile restoration, host cleanup, and Steam socket restoration
passed. PMIC reports `PS_HOLD` / `HARD_RESET` with no watchdog signal, while
pstore was unavailable. V5 is consumed and must never be retried. The leading
unproven cause is a post-COMMIT recovery execution failure because `CLAIMED`
was returned before the Haven handoff and `kexec -e`. V6
(`43613a11…8eb0a`) added one bounded host STATUS request after `CLAIMED`.
Its sole RAM-only boot reached exact recovery ACM/NCM, transferred and
verified the bundle, accepted PREPARE and COMMIT, then returned
`state=EXEC_FAILED`, `execution_started=NO`, and
`last_error=HAVEN_WDOG_FAILED`. The target kernel never started; recovery
refused the Haven-watchdog handoff and restricted NFS was cancelled only
after that refusal. Exact Alpine fallback and cleanup passed. V6 is consumed
and must never be retried. V7 (`0dc48152…28be2`) preserved fail-closed kexec
ordering while distinguishing secure-watchdog, hypervisor-VDOG, and generic
deactivation failures. Its sole RAM-only boot reached exact recovery ACM/NCM,
transferred and verified the 46,166,378-byte bundle, accepted PREPARE and
COMMIT, then returned `state=EXEC_FAILED`, `execution_started=NO`, and
`last_error=HAVEN_WDOG_FAILED`. No target kernel ran; exact Alpine fallback
and cleanup passed. V7 is consumed and must never be retried. V8 r2
(`faf7ebd1…f034f`) added exact fail-closed driver, device, binding,
compatible, initial-state, kmsg-open, control, write, close, readback,
kmsg-scan, secure-watchdog, and hypervisor-VDOG boundaries. Its sole RAM-only
cycle reached recovery, transferred and verified the exact bundle, accepted
PREPARE and COMMIT, then returned `state=EXEC_FAILED`,
`execution_started=NO`, and `last_error=HAVEN_KMSG_OPEN_FAILED`. The target
kernel never ran. Exact Alpine fallback and cleanup passed. The retained
wrapper configuration has no devtmpfs, recovery mounted a tmpfs at `/dev`,
and no `/dev/kmsg` existed; V8 correctly failed closed before touching the
watchdog. V8 is consumed and must never be retried. V8 r1 was superseded
before claim or phone contact after review found unsafe-control and
compatible-race classification defects. V9 (`4f3bb23c…68133`) materialized
and validated only a root-owned mode-`0600` character device 1:11 at
`/dev/kmsg` before the controller started. Its sole RAM-only cycle transferred
and verified the exact bundle, persisted PREPARED, accepted COMMIT, disabled
the Haven watchdog, loaded kexec, and began handoff. Target ACM/NCM never
appeared before exact Alpine fallback returned about 23.3 seconds later; PMIC
reported `PS_HOLD` / `HARD_RESET` with no PMIC watchdog signal, and no NFS
attempt was observed. V9 is consumed and must never be retried. V10
(`fb5fce1…3452`) is consumed and must never be retried. Its sole RAM-only
cycle kept V9's byte-identical raw wrapper `06732992…4aff`, disabled Haven,
entered the mainline target, and returned to exact Alpine fallback. The
separately admitted corrected observer (`a655d4b3…05b`) is also consumed and
must never be retried. It exposed retained ramoops proving that target
userspace armed rollback, rejected USB transport before NFS, and requested a
reboot. The fixed target had required the downstream recovery UDC name
`a600000.dwc3`; the mainline DT platform device and UDC are named
`a600000.usb`. The current offline successor corrects that exact target-only
selector while preserving the recovery wrapper's `.dwc3` contract.
The target bundle adds stage 75 `nfs-mount-returned`, a target boot-ID lineage line,
and private same-port NCM, NFS-RPC, and exact target-specific TCP
state/queue/current-unrecovered-RTO snapshots. Its historical reporter and
diagnostic initramfs v1 reproduce at `dc53932d…a10` and `83240834…31d`.
Fallback-side
pstore correlation is implemented as a bounded,
read-only, signed strict-SSH summary before unchanged fallback health. It
binds the expected target boot ID and candidate, keeps raw records on the
phone, classifies lineage separately from recognized fatal tokens, and
cross-checks the fallback boot ID across both signed probes. Sixty-four
fallback, 27 collector, and 80 lifecycle tests, complete local CI, and
independent review
pass in the [host-only
checkpoint](../test-results/2026-08-05-stage75-postmortem-host-integration-offline.md).
Implementation commit `eeb157b` is published with green exact-head GitHub
Actions run `30988099391` (`qemu-system` 37s; `recovery-core` 4m03s). This
closes the host-only publication gate; policy still contains no successor
`allow` row.

The current offline successor extends that postmortem contract to v2 with a
read-only, deadline-driven, true 4 MiB bounded PMIC PON dmesg reader. It keeps
only a hash and normalized summary, accepts only the last complete known
29-entry FIFO cycle, and leaves missing, unknown, or ambiguous evidence
inconclusive. The exact retained ASUS 5.4.210 source/config proves the
behavioral oracle and that `qcom-reboot-reason` is only a next-boot writer; it
does not prove that the installed 5.4.134 fallback has the PMIC reader. No
Generation-12 reset reason was retained. This is host-only offline evidence,
so the [PMIC PON checkpoint](../test-results/2026-08-10-fallback-pmic-pon-postmortem-offline.md)
does not change **HOLD**.

A distinct current write-side candidate
`headless-netroot-early-diag-v2` now binds the host-port-classifying reporter
`26249252…bafa` to the bounded 6,013,458-byte v3 initramfs
`94edd625…cffc`, accepted Image, corrected DTB, and sealed Arch root. The
wire-visible bundle identity remains v2 so target lineage and the fixed
collector/control vocabulary do not change; the canonical candidate record
is `41c23330…b9cf` and its unsigned runtime-manifest body is
`54f53420…6efc`. The prior disposable-key signed tuple and v2 component row
remain immutable superseded evidence. This current state proves
authority-free source, initramfs, and runtime-bundle composition only. A later
guarded offline build used the existing project key and destroyed its private
snapshot; central policy remains empty, no claim or phone action exists, and
hardware admission remains **HOLD**. The exact authority-free clean-twin
composition is recorded in the
[offline rebind result](../test-results/2026-08-09-host-rendezvous-v3-candidate-rebind-offline.md).
The current
[production live-gate checkpoint](../test-results/2026-08-10-current-production-recovery-live-gate-offline.md)
now gives those exact project-key artifacts an offline-only gate profile. It
can verify policy identities and artifact bytes, including the repository-owned
exact-UDC init, but rejects connected preflight and boot before host or policy
inspection. This is not issuance or admission.
Generation 12 is consumed and must never be retried; it is not pending live
admission. Any future one-shot generation must be a new exact record consumed
through the generic repository-owned claim consumer after exact-head CI. The
generic consumer now requires a lifecycle-account anchor whose parent is
neither owned nor writable by the lifecycle user, then enters a
repository-derived, no-replace
guard there before publishing the claim-root marker. A
claim-root rename can therefore fail the current invocation but cannot expose
the replacement root to a second successful consumption. Exact guard bytes,
owner, mode, link count, fsync, source pathname revalidation, root/anchor
and anchor-parent revalidation, lifecycle-owned read-only parent refusal, and
concurrent refusal are hardware-free tested. See the
[current-head follow-up](../test-results/2026-08-08-current-head-targeted-recovery-follow-up.md).
Generation 10 accepted
PREPARE and completed the host-side signed-bundle transfer, but ACM closed
before later device progress or `PREPARED` could be observed. No COMMIT intent
existed, no target ran, and exact Alpine fallback plus host cleanup passed.
Recovery v18 has:

- exact fastboot product `lahaina`, observed by both accepted v18 preflights;
- two completed credential-free RAM-only staging/rollback cycles;
- exact recovery USB identity, ACM, and NCM;
- zero block-backed mounts;
- all observed physical disks/partitions forced read-only;
- an armed automatic rollback watchdog;
- a separate accepted Linux 7.1.4 load/target/rollback cycle.

Evidence:

- [v18 offline](../test-results/2026-07-24-recovery-v18-offline.md)
- [v18 staging live](../test-results/2026-07-24-recovery-v18-live.md)
- [v18 mainline live](../test-results/2026-07-24-recovery-v18-mainline-live.md)

The legacy v18 artifact remains unchanged and interactive, but its successor
source removes the shell from recovery, network-root, and persistent-root.
A deterministic builder removes SSH/getty/login/DHCP entry points and
credentials, locks root, and integrates the static responder, fetcher,
verifier, pinned kexec runtime, and a caller-supplied raw public key. Eight
init-policy tests and malicious-archive/init fixtures enforce that boundary.
Builds under different locales and time zones are byte-identical.

That shell-free path has now completed one attended signed live transaction.
The exact guarded runner used only `fastboot boot`; recovery fetched and
verified one signed bundle, returned correlated `PREPARED` and `CLAIMED`
responses, started the target NCM gadget, and automatically returned to the
exact persistent fallback. The durable host intent was resolved as
`FALLBACK_RETURNED`; no commit was retried.

The target did not reach SSH. Its signed candidate selected historical
network-root v1 DTB hash `255c5ac1...`, which leaves RMTFS, GPUCC, GMU, and
the Adreno SMMU enabled and reproduces the documented roughly 16-second
coldplug reset. The tracked candidate now pins the accepted v3-isolated DTB
hash `86e5cb81...` and a regression test requires that complete identity.
The correction now passes a complete twin build of the target bundle,
shell-free recovery initramfs, vendor-compatible wrapper kernel, raw boot
image, and unsigned AVB test wrapper. One disposable test private key was
destroyed before success; retained products say `authority=none`. The
DTB builder now also enforces an exact property-level delta against its base.
The retained rejected v1 and accepted v3 objects differ in only the four
expected RMTFS/GPUCC/GMU/Adreno-SMMU isolation states; malicious node,
property, phandle, truncation, and signal-interruption fixtures fail in core
CI. See the
[semantic oracle](../test-results/2026-07-29-corrected-dtb-semantic-oracle-offline.md).
The current Linux host also revalidated the optional positive source/DTB leg,
matching configuration and retained module archive, buttons/indicator source
contract, and corrected-successor artifact gate in one
[accepted-baseline checkpoint](../test-results/2026-07-31-accepted-core-baseline-revalidation.md).
The correction has not been signed by a live trust root or booted. There is no
repeat live authority. See the
[live result](../test-results/2026-07-29-headless-stable-recovery-live.md)
and
[corrected offline twin build](../test-results/2026-07-29-corrected-headless-candidate-offline.md),
plus [re-freeze integration](recovery-refreeze-integration.md).

The ASUS 5.4 and accepted Linux 7.1 behavioral ancestry is now also encoded in
a strict [core compatibility oracle](core-compatibility-oracle.md). It binds
the historical evidence hashes and markers, artifact-manifest hash, accepted
Image/config identities, corrected candidate Image/DTB/initramfs ancestry,
six active headless capability contracts, eight future capability states,
exact CI entries, and the kernel-build verifier invocation. A committed
golden config, the retained accepted 7.1 config, and 39 mutation/CLI tests
pass. The complete hardware-free repository CI tier passes.

This is an ancestry and regression result, not a new hardware result.
`phase=active` means current roadmap scope; only `candidate_status` describes
acceptance. Buttons and battery remain baseline diagnostics, display-off is
evidence-only, and suspend, sensors, and audio remain pending. The corrected
root is still `live-pending` with `authority=none`. See the
[offline result](../test-results/2026-07-29-core-compatibility-oracle-offline.md).

The first sensor now has a separate test-first port boundary. The
[VCNL36866 source/port contract](vcnl36866-als-proximity.md) pins the exact
ASUS 5.4 EVB-to-MP5 inheritance, QUPv3 SE0 `0x980000` controller, I2C address
`0x60`, GPIO89 active-low IRQ, PM8350C L7 3.3 V rail, two-byte little-endian
register transport, ID `0xf6`/`0x62`, and ALS/proximity data registers
`0xf1`/`0xf4`. It also proves accepted Linux 7.1.4 has no VCNL36866 driver or
binding and defines the future read-only IIO candidate/runtime requirements.
Seventeen hostile and retained-source cases pass. This is `port-required`
evidence only: no driver, overlay, kernel candidate, phone boot, or hardware
result exists.

The future `battery-charging` capability now has a hardware-free sustained
observation gate. A read-only target collector emits one canonical
candidate/boot/source-bound phase record with 21 samples at 30-second
intervals. It requires the exact three SM8350 power supplies, mode-`0444`
telemetry and input-current-limit files, no charge-control thresholds, and no
Type-C control device. The host verifier rejects malformed or replaced
evidence and compares same-boot unplugged and USB records only when status and
median current distinguish the phases; it derives either driver sign
convention rather than assuming one. Eleven hostile test groups pass and
Claude's complete-source review returned `NO_BLOCKERS`. This is an offline
test contract, not a new phone result or charging-safety acceptance. See the
[contract](battery-telemetry-series.md) and
[offline result](../test-results/2026-07-31-headless-battery-series-offline.md).

The battery path also has a bounded
[read-only dual-cell candidate](dual-cell-readonly-telemetry.md). It adds one
DT-opt-in OEM PMIC GLINK read to upstream qcom_battmgr, validates the exact
vendor-evidenced 16-byte response, and exposes only mode-`0444`
`cell_voltages`. Hostile source, one-property DT, and sysfs-fixture gates pass,
and the patched driver compiles as AArch64 in the pinned builder. Two complete,
uncached builds from deterministic patched source now produce byte-identical
kernel images, `Module.symvers`, module archives, metadata, and linked
`qcom_battmgr.ko`; two exact candidate DTBs also compare byte-for-byte. The
locally assembled candidate is unbooted and explicitly carries
`authority=none`, `boot_authority=none`, and
`hardware_acceptance=unproven`. No phone execution, cell observation,
battery-health classification, or charging acceptance is claimed. See the
[source/ABI result](../test-results/2026-08-09-dual-cell-readonly-candidate-offline.md)
and [clean-twin result](../test-results/2026-08-09-dual-cell-readonly-clean-twin-offline.md).

The corrected target's next live observation is now specified independently
of the boot controller. One read-only target probe emits exactly 88 canonical
fields for the six active capabilities. A host verifier binds the record to
the current probe hash, a separately observed boot ID, the full compatibility
oracle, the corrected candidate's root identities, exact CPUs `0-7`, the
three EPSS CPUfreq policy groups and schedutil governor, accepted RAM/thermal
envelopes, exact OverlayFS/NFSv4.2/tmpfs mount IDs and backing paths, zero
block/SCSI/RPMB/UFS exposure, the exact ConfigFS NCM gadget and primary
high-speed UDC, an isolated no-default-route `/30`, one current USB-peer SSH
session, matching Ed25519 authorized/host-key identities, strict key-only SSH,
and the live 600-second rollback lease. Target, host, and mocked strict-SSH
runner tests pass offline.
The runner executes the probe once and cannot boot, sign, retry kexec, disarm,
or reboot. No credential was used and no phone was contacted. See the
[runtime contract](minimal-headless-runtime-acceptance.md) and
[CPU/RAM result](../test-results/2026-07-29-cpu-ram-topology-offline.md), plus
the
[storage-isolation result](../test-results/2026-07-29-storage-isolation-offline.md)
and
[USB/NCM/SSH result](../test-results/2026-07-30-usb-ncm-ssh-offline.md).

The compatibility gate now also checks the kernel source and generated board
DTB rather than stopping at Kconfig and artifact ancestry. The retained exact
Linux 7.1.4 tree passes 43 Kconfig, Makefile, OF-table, binding, and source
entry-point checks; the accepted corrected DTB passes 23 RAM-bank, CPU/EPSS,
UFS-isolation, USB2/NCM, PSCI, and TSENS topology checks. The expanded source
gate and cross-node thermal policy additionally pin both
TSENS critical IRQ routes through PDC/GIC, 12 CPU thermal zones with exact
trips and cooling maps, five PMIC alarms/zones, and the kernel default
critical-shutdown path. Disabled zones, rewired interrupts, duplicate or
out-of-range sensors, changed trips, and altered cooling targets fail.
A future source or
DTB can run in candidate mode, but a pass reports
`compatible-not-accepted` and cannot promote hardware state. See the
[source/DT contract](core-source-dtb-contract.md), the
[static thermal result](../test-results/2026-07-31-thermal-policy-static-oracle-offline.md),
and the
[CPU/RAM result](../test-results/2026-07-29-cpu-ram-topology-offline.md).

The accepted config still builds the PMIC alarm driver as a module and sets
the emergency-poweroff delay to zero. The oracle therefore keeps PMIC
critical enforcement and a bounded 10–30 second forced fallback as separate
future capabilities. No IRQ delivery, cooling response, PMIC registration,
or shutdown behavior is accepted by this offline result.

A separate compile-only network-root output now proves that the exact accepted
7.1.4 config can change only `CONFIG_QCOM_SPMI_TEMP_ALARM=m` to `y`, produce a
complete deterministic module archive, and expose the PMIC probe/IRQ/init
symbols in built-in `vmlinux`. It is not a clean-twin issuance and has no boot
authority. The emergency delay remains zero pending measured orderly-shutdown
and rollback timing. See the
[offline thermal-PMIC candidate result](../test-results/2026-08-09-network-root-thermal-pmic-candidate-offline.md).

The first H4 input/indicator delta is now packaged without widening any other
hardware boundary. It pins the accepted source, config, LPG module archive,
and corrected DTB; adds power, volume-down, PM8350 GPIO6 volume-up, and only
PM8350C green LPG channel 2; and keeps the LED default-off. Exact semantic and
source/config/module hostile suites pass in both repository tiers. This is
offline readiness only: no physical key or LED behavior has been accepted.
See the [buttons/indicator contract](buttons-indicator.md) and
[offline result](../test-results/2026-07-30-buttons-indicator-offline.md).

The matching userspace path is now native and bounded. A reproducible
67,520-byte static AArch64 daemon validates the exact PMIC power input and
green LPG class/driver/DT identity before accepting events. Only a value-1
`KEY_POWER` produces brightness 31 for 180 ms; signals and failures restore
zero. Host and AArch64/QEMU hostile suites pass, and a successor headless-root
staging profile adds only this binary, its confined service, and one module
line. The existing SSH-only root is unchanged, and no successor live
behavior is accepted yet. The successor archive is now sealed at
535,163,814 bytes with SHA-256
`f52bd75f023ab6209a04f842881356e5a224e1e1845f1d5732ab71da7d36e66b`;
both staged and clean-extraction verification pass with the repository's
public test key. The archive stays outside Git, is unsigned and unbooted, and
does not grant live authority. See the
[native runtime contract](headless-key-indicator.md) and
[offline result](../test-results/2026-07-30-headless-key-indicator-offline.md).

The sealed lower deliberately has no reusable SSH host key, so the corrected
temporary target cannot have a static known-hosts entry before boot. The new
host-key bootstrap closes that development-only gap without `accept-new`: it
records the exact recovery USB device location, requires the
`ROG5_network_root` NCM gadget and `cdc_ncm` driver on the same port, verifies
the direct `169.254.77.1/30` route, scans exactly one nonzero Ed25519 public
key without offering a client credential, rechecks USB and route continuity,
and publishes a caller-owned mode-`0600` alias pin. Fifteen hardware-free test
groups reject stale/cross-boot anchors, duplicate or wrong gadgets, another
port, wrong driver, routed peers, malformed/multiple/RSA/zero keys, unsafe
paths, and missing authorization. This does not create a persistent server
identity or grant a live cycle. See the
[bootstrap contract](minimal-headless-host-key-bootstrap.md) and
[offline result](../test-results/2026-07-29-minimal-headless-host-key-bootstrap-offline.md).

Those independent gates now have one hardware-free-tested lifecycle
controller. It performs complete preflight before mutation, waits for the
one-transfer recovery bundle server to exit and clean its firewall state
before starting NFS, commits exactly once, pins the volatile target key,
captures one strict-SSH runtime record through a single connection (rather
than five independent SSH/SCP handshakes), keeps rollback armed, verifies exact
fallback and host cleanup, and only then resolves the durable intent. An
ambiguous COMMIT is looked up in the ledger and is never replayed. The NFS
exporter is also staged for a fixed root-owned installation rather than
privileged execution of a mutable repository script. This checkpoint has not
installed the changed host components, booted the phone, or used a
credential. See the
[one-shot lifecycle runbook](minimal-headless-live-cycle.md).

The protocol reference model and host write-ahead ledger pass 48 offline
fault, replay, parser, crash-consistency, and concurrency tests. A static
native responder now passes 56 pseudo-terminal, postmortem, and
PREPARE-boundary tests as both a host build and a real AArch64 static binary
under QEMU. A separate
static native signed-bundle verifier enforces the canonical manifest, raw
Ed25519 trust root, artifact identity, arm64 Image/FDT policy, bounded
gzip/newc initramfs, and generated command line. The verifier now transfers
immutable write-sealed snapshots of the exact three verified files to the
responder over `SCM_RIGHTS`; the responder parses the canonical plan, performs
bounded watchdog-supervised `kexec -c -l` through `/proc/self/fd`, and
persists `PREPARED` only after load success. Host and AArch64/QEMU tests
replace and overwrite every bundle pathname and cover malformed handoff
without descriptor leaks, bounded child failure/timeout cleanup, watchdog
death, ledger-boundary replay, and crash-after-load retry.
An uncommitted image is now removed with fixed `kexec -c -u` after a rejected
or timed-out load, after a returned executor, and during every non-prepared
startup. The fixed execution child also uses bounded kill/reap under watchdog
death. These unload and executor paths pass through the same fake-kexec seam
on host and AArch64/QEMU; real kernel-side unload remains a staging-only live
gate.

The fixed-host acquisition helper now passes 30 native tests,
30 tests as root through a network-disabled container, and 25 executable
AArch64/QEMU cases, with five expected QEMU-only skips. It binds a fixed NCM
source/interface/peer, isolates
network parsing in a UID/GID-65534 chroot/seccomp worker, independently
revalidates the root-owned, non-writable staged files in the privileged
parent, and publishes with `RENAME_NOREPLACE`. QEMU user mode cannot safely
emulate a guest seccomp filter, so native and root suites own that gate. The
responder invokes the helper first under a 190-second outer deadline and maps
permanent bundle-ID conflict or an exact bounded fetch-stage failure without
invoking verifier or kexec. The helper's 180-second deadline is nested below a
190-second responder fetch wait, one 260-second same-session host PREPARE
deadline that also covers verification and kexec load, and a 320-second
lifecycle wait that includes initial ACM stabilization. At that checkpoint
the three binaries passed offline initramfs integration, but no production
signing key had been created. The accepted v18 recovery still contained the
old interactive control shell. None of those offline checkpoints granted live
authority.

The fixed NFS host server also has an authenticated cancellation boundary.
It publishes a root-owned PID/start-time/caller/token record before lengthy
setup, validates and freezes the exact isolated process leader through a
pidfd, signals only that process group, and accepts a terminal zombie only
after the server removed its own state record. A real-host serve/cancel test
passed and left no listener, export, NFS worker, mount daemon, marker, mount,
temporary PolicyKit rule, or writable SteamOS root state.
See the
[reference result](../test-results/2026-07-28-recovery-control-reference-offline.md)
and
[native result](../test-results/2026-07-28-recovery-control-native-offline.md),
plus the
[runtime bundle contract](recovery-bundle-contract.md) and
[verifier result](../test-results/2026-07-28-recovery-bundle-verifier-offline.md).
The combined descriptor/load checkpoint is recorded in the
[sealed PREPARE result](../test-results/2026-07-28-recovery-sealed-prepare-offline.md).
The fixed transport is specified in
[recovery fetch contract](recovery-fetch-contract.md), with evidence in the
[fixed fetch offline result](../test-results/2026-07-28-recovery-fixed-fetch-offline.md).
The matching one-shot host server and root-owned runtime firewall controller
now pass nine protocol/descriptor tests and nine mocked controller-lifecycle
tests. The server opens only the fixed caller-owned bundle root, serves
already-verified descriptors as an unprivileged capability-free process, and
the controller restores every address, rule, zone assignment, and
NetworkManager override it creates. The reviewed helpers have not been
installed and no live host network state was changed. See the
[host server result](../test-results/2026-07-28-recovery-host-server-offline.md).

The host now also has one atomic runtime-bundle packager. With an explicitly
supplied ephemeral Ed25519 key, it snapshots the kernel, DTB, and initramfs
through already-open descriptors, creates the canonical signed manifest in a
private staging directory, enforces exact `0700/0500/0400` ownership and mode
policy, and publishes with one no-replace rename. Its refusal suite covers
unsafe identity, timeout, symlink, key, and root metadata; injected signing
failure leaves the bundle root unchanged, and a competing final directory is
preserved. All three fixed profiles pass the native verifier and host-server
opener, and two roots produce byte-identical output with the same inputs. The
persistent Arch payload maps to
`persistent-root-ro-v1`; accepted A660 ancestry maps to `network-root-v1`.
That checkpoint created no production key, live bundle, allowlist change,
host-network mutation, or phone action.

The installed fallback still cannot read the ramoops reservation: no driver
is bound, `/dev/mem` and `devmem` are absent, and `CONFIG_DEVMEM` is unset.
The stable recovery wrapper already has built-in `PSTORE_RAM` and the exact
4 MiB ramoops command line. Recovery source now arms rollback first, mounts
pstore read-only, takes an immutable RAM snapshot without deleting records,
and exports state, record count, byte count, SHA-256, and a 512-byte tail
through framed status. Its empty/present/unavailable and malformed-state
tests pass offline. Two clean final builds produced identical initramfs,
wrapper kernel, raw boot-v3, and test-only AVB images. The hashes and commands
are recorded in the
[headless speed-amplifier result](../test-results/2026-07-29-headless-speed-amplifiers-offline.md).
Whether the reserved DRAM survives target → bootloader → recovery remains a
live experiment; no retained log has yet been claimed.

## Active headless Arch root

Status correction, 2026-07-30: the old identities below remain historical
evidence. The replacement `headless-ssh-v2` recipe is now offline,
credential-clean, and key-bound. Two fresh roots from commit `9739abe` are
byte-identical at 536,750,378 bytes with SHA-256
`2abe8c533179da598c37939ff8ebb4667a243bd8140c2d497237e41fbea72e6a`.
The fixed v3 package is 536,747,283 bytes, seals 37,735 entries, and binds the
canonical Ed25519 fingerprint across the build record, authorized key, whole
tree, and package. It uses only the public fixture, is unbooted, and is not
deployment authority. The distinct `headless-ssh-network-root-v3` fixture
candidate now binds that exact tree and seal to the accepted corrected DTB.
Its twin signed bundles, shell-free recovery initramfses, clean ASUS wrapper
kernels, boot-v3 images, and test-only AVB images reproduce and pass the
native verifier; the disposable signing key was destroyed and authority
remains `none`. See the
[hardening report](../test-results/2026-07-30-headless-root-credential-reproducibility-hardening.md)
and
[key-bound package report](../test-results/2026-07-30-headless-ssh-v2-key-bound-package.md),
plus the
[candidate report](../test-results/2026-07-30-headless-ssh-v2-candidate-offline.md).

The lifecycle now has a separate deployment-key admission boundary. After
exact guards and a clean, synchronized repository checkpoint, but before
privilege or phone discovery, it derives the public half from the caller's
canonical private key through fixed `/usr/bin/ssh-keygen`. It requires one
non-fixture `headless-ssh-v2` package, corrected candidate, and runtime
manifest chain; binds their root identities and exact Image/DTB/initramfs
tuple; and emits only hashes, the public fingerprint, and `authority=none`.
Fourteen hostile verifier tests and seventeen lifecycle tests use disposable
keys only. No deployment credential or phone was used. See the
[admission report](../test-results/2026-07-31-headless-ssh-v2-key-admission-offline.md).

The admitted identities now continue through the host-only execution path.
The lifecycle passes the exact package hash to a fixed
`headless-ssh-deployment-v3` NFS profile, recovery COMMIT waits for a
root-owned canonical v2 handoff marker containing that profile, fixed export
root, fresh token, listener, and package hash, and runtime acceptance receives
the exact admitted candidate path and hash. The target probe accepts only the
historical or deployment candidate identifier. The host verifier requires an
external canonical read-only non-fixture candidate for deployment and never
falls back to the tracked historical record. Historical no-argument NFS,
marker, recovery-control, target-probe, and runtime-verifier paths remain
intact. See the
[profile-threading report](../test-results/2026-07-31-headless-ssh-v3-profile-threading-offline.md).

Status update, 2026-07-31: the authorized non-fixture deployment chain is now
built. The sealed root archive is 536,746,495 bytes with SHA-256
`4d120a4b3a10be098cea47ba8536969bbaa931b47b31cc37fc3474fea045b324`;
its manifest, candidate, signed runtime manifest, raw recovery trust root,
recovery initramfs, wrapper kernel, raw boot image, and AVB wrapper are bound
by the new `headless-ssh-deployment-v3` live-gate profile. Two clean complete
builds are byte-identical, AVB verification passes, and the real artifact
preflight succeeds without phone access. See the
[deployment-chain report](../test-results/2026-07-31-headless-ssh-deployment-chain-offline.md).

The consumed v3 manifest is now superseded by signed bundle
`headless-ssh-network-root-v3-r2`. Its guarded twin build from clean pushed
checkpoint `81d2736` is byte-identical, retains only the public trust key, and
passes the production artifact gate before fastboot discovery. The exact r2
manifest is `9ea27452…d630` and the recovery AVB image is `11feb00b…13c`.
Candidate and bundle identities are now distinct throughout key admission,
recovery control, lifecycle intent, and runtime verification. See the
[signed-r2 report](../test-results/2026-07-31-headless-ssh-successor-r2-signed-build.md).

The host publication boundary was first implemented and accepted offline.
Its unprivileged launcher requires a clean branch synchronized with its exact
`origin` peer, verifies root-owned installed components byte-for-byte, and
reruns deployment-key admission. Only the canonical archive path, package
path, and admitted package SHA-256 enter the fixed PolicyKit command; the
private key, candidate, and runtime manifest do not. The root-owned installer
copies the caller-owned archive into an anonymous root-owned snapshot, binds
those exact bytes to the package, rejects unsafe archive members and tracked
fixture identities, extracts into a private deterministic stage, verifies the
complete root, syncs files and directories bottom-up, and publishes only with
`renameat2(RENAME_NOREPLACE)`. Eleven hostile installer tests and eight
launcher tests pass, including in-place rewrite, pathname replacement, unsafe
links/devices/credentials, stale installed bytes, and publication races. That
original acceptance used no PolicyKit action, host installation, deployment
credential, or phone. The later real-host deployment is recorded below. See
the
[export-installer report](../test-results/2026-07-31-headless-ssh-v3-export-installer-offline.md).

The first minimal mainline userspace profile was built and verified offline.
It used an official signed Arch Linux ARM base plus the exact
`7.1.4-g7a5cef0db479` modules and only three requested additions: `attr`,
`diffutils`, and `openssh`.

The historical stage removed the generic Arch kernel, twelve
`linux-firmware*` packages
(1,281.37 MiB installed), the published `alarm` account, all reusable SSH
host keys, and the reusable machine ID. It enables key-only root SSH and the
existing sleep inhibitor, sets `multi-user.target`, and leaves USB networking
to the initramfs rather than enabling NetworkManager or systemd-networkd.
Desktop, browser, Vulkan, GPU firmware, Wi-Fi, VPN/hotspot, Node, and agent
packages are absent.

The final archive was built from commit
`eb61a45938c851b1b02a2f3151db5265ab9213e7` and passed the complete verifier
inside the staged root and again after clean extraction:

```text
path: artifacts/arch/rog5-arch-headless-ssh-7.1.4.tar.gz
size: 535093875
sha256: 4e472f2fa3f21fd3a5cf6de9eaf96810104083758039e8cdeefc4e03ec4e6427
packages: 150
```

This is 73.3% smaller than the 2,007,033,670-byte successor-v3 Plasma
archive. The number is disk/archive evidence, not a RAM or battery
measurement. Package versions are recorded in the historical root. The
corrected stage does not contact an Arch repository or generate a Pacman
trust database; it requires every requested package to be present in the
exact manifest-pinned base archive and empties Pacman signing state before
verification.

The recovery side also has a strict offline manifest adapter for the consumed
persistent-root P2 artifacts. It verifies their tracked sizes and hashes,
delegates canonical signing/publication to the stable runtime-bundle
packager, and requires either a consumed parity fixture or an offline
network-root candidate plus `authority=none`.

The historical root was packaged as a separately transported, sealed
`network-root-v1` lower. Two complete rootless builds produced the same
535,094,061-byte pax-restricted archive with SHA-256
`ee310c82ef925c9a801c310ab36f56f94b124ceb089d8db745c0959493c52b24`.
Its 37,669-entry tree, persistent seal, and explicit `workload=none` command
manifest are bound into the tracked `headless-network-root-v1` candidate.
The new 5,978,369-byte target initramfs includes the exact static AArch64
whole-tree verifier and also reproduces byte-for-byte.

The five frozen Linux 7.1.4 `network-root-v1` kernel artifacts are now
recoverable from a fresh exact source checkout and the reconstructed
historical builder. The missing input was Git ref state: retaining a local
`refs/tags/v7.1.4` changes `scripts/setlocalversion` from
`7.1.4-g7a5cef0db479` to `7.1.4`, despite an identical commit, tree, and
config. Two independently fetched, network-disabled builds from the
deliberate no-local-tag checkout are byte-identical and match every frozen
size and SHA-256 identity. This is host-only reproducibility evidence, not a
hardware or boot result.

The pruned recovery dependency chain is also closed. Two retained P2
lineages reconstruct the successor-only v18r base; exact historical source
transitions then recover the accepted network-root v3 archive and the
5,978,369-byte headless target initramfs byte-for-byte. Recovery component
builders run through pinned private rootless ARM64 emulation, and immutable
AOSP Git blobs recover the accepted Android boot tools. A reproducible 12 KiB
boot-v3 metadata template replaces the missing 96 MiB historical template
for successor builds. The historical wrapper builder remains frozen, while a
separate successor starts from the accepted v18 output config. See the
[dependency-closure proof](../test-results/2026-07-30-headless-recovery-dependency-closure.md).

The first signed live target exposed exact network-root NCM, then returned to
fallback before SSH because the candidate carried historical DTB v1. The
candidate now pins the accepted v3 GPU/RMTFS-isolated DTB
`86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46`.
The corrected target, signed bundle, shell-free recovery, vendor wrapper, raw
boot image, and unsigned AVB test wrapper now reproduce in two clean offline
builds. The disposable test private key was destroyed. This correction
remains `authority=none` and grants no repeat authority.

The reconstructed successor path independently repeats that complete gate
with the qualified post-migration builders, compact canonical template, and
accepted v18 output config. Its two ASUS wrapper Images, raw boot-v3 images,
and AVB images are byte-identical; the exact source seal is unchanged, AVB
verification passes, and no private key remains. See the
[successor offline report](../test-results/2026-07-30-corrected-headless-successor-offline.md).

The retained historical recovery successor still passes its exact production
stable-recovery artifact boundary without a connected phone, but the new
lifecycle deliberately accepts only `headless-ssh-deployment-v3`. That
deployment profile now pins the complete non-fixture wrapper, trust root,
manifest, and verifier chain. The root-owned NFS controller understands only
that exact profile and package identity at its fixed v3 path. The first real
export publication stopped safely before extraction because SteamOS's 230 MiB
`/var` could not hold the 1.53 GiB lower. The reviewed remediation is now
pushed and installed. The fixed
`/home/rog5-linux/exports/headless-ssh-network-root-v3` store contains the
atomically published 37,735-entry root; every ancestor below `/home` is
root-owned mode `0700`. Export ancestry, complete-tree identity, fixed NFS
host state, exact recovery artifacts, and one connected `lahaina` fastboot
device pass.

A normal reboot into installed Alpine did not consume the experimental boot.
The new deployment key is not among its two older authorized keys. The USB
serial health payload nevertheless proved the exact fallback kernel, BusyBox
init, `qcom,lahaina-mtp`, ext4 root, zero project modules, empty pstore and
fatal-signature result, 70 thermal zones with a 38,800 m°C maximum, and Python
availability. A later Alpine/BusyBox source audit showed that invoking that
payload through the legacy interactive shell may also have updated its
history file; the historical inspection is therefore not retained as a
zero-write proof. The phone remains on the healthy fallback. At that
checkpoint, strict fallback SSH was the sole pre-lifecycle blocker: the untouched tier
would have required one of the existing authorized private keys, while
appending the deployment public key would have required an explicit
safety-tier revision and separate bounded phone-write approval.
See the
[real-host deployment result](../test-results/2026-07-31-steamos-deployment-preflight-live.md).

Current implementation supersedes the client-key blocker without changing
fallback configuration or `authorized_keys`. A fixed USB ACM controller sends
one nonce-bound read-only Python health payload through the exact Alpine
serial interface. The fallback signs the canonical
kernel/init/compatible/root, module, pstore, dmesg, thermal, Python, and boot
identity record with its existing Ed25519 SSH host key; the host verifies it
against the private pin captured during the deployment preflight.
The controller binds the same physical USB port, uses exclusive raw serial
ownership and bounded output, and requires a second guard plus verified ACK
and same-boot recheck before its only mutating action,
`RESTART2("bootloader")`. It then requires one same-port `lahaina` fastboot
device. Alpine 3.24 enables BusyBox per-command history, and reads from its
writable `relatime` ext4 root may update inode access times. Every action
therefore requires a separate action-scoped storage-write guard. It has no
fallback client key, host-network, mount, explicit storage-write, flash,
erase, or retry path. The isolated/no-site Python loader is bounded below
Alpine's 2,048-byte BusyBox line-editor limit. The host now drains and bounds
echoed bytes during writes, labels every write stage and byte count, and sends
one atomic Ctrl-C/newline plus split-literal nonce marker before the larger
launcher. It sends bounded, hash-checked source chunks only after one
nonce-bound ready marker, and the phone rejects missing or partial delivery
under a fixed deadline.
Non-reboot actions return to the supervised interactive shell. The
lifecycle permits at most one fallback contact even if final host cleanup
later fails. Before boot, its host-only preflight validates the exact
allowed-signers pin, fixed tools, ModemManager state, wait and loader bounds,
and the recovery-anchor time budget without opening ACM. The anchor consumer
is directly bound to the real capture producer and rechecks wall-clock
freshness after ACM discovery. Nonce-bound phone errors retain their failure
class through the last serial read. The clean-host gate reads the root-owned
canonical NFS export table directly, avoiding the successful-but-diagnostic
unprivileged `exportfs -v` lock path while still rejecting any real entry.
The emergency ACM protocol remains covered, while the active fallback path
now uses strict SSH over exact USB-NCM. Forty-six transport tests and all
twenty-six lifecycle methods pass hardware-free. The host has a persistent
no-gateway `rog5-fallback-usb-ssh` profile at `169.254.77.1/30`, and the
dedicated client key has passed a live strict-SSH fallback health preflight.
The first complete cycle through this path fetched, prepared, and committed
the target, then safely rejected a stale target route-parser assumption. The
watchdog returned the same port to Alpine, NetworkManager restored the
profile automatically, strict SSH verified the signed fallback at 44.1
degrees C without opening ACM, and the durable intent resolved
`FALLBACK_RETURNED`. See the
[strict-SSH fallback result](../test-results/2026-07-31-minimal-headless-live-cycle-ssh-fallback.md).

The distinct r2 successor subsequently completed framed recovery transfer,
PREPARE, and one durable COMMIT. Linux 7.1 exposed the expected USB-NCM gadget
on the exact port but physically disconnected 23 seconds later, before target
SSH host-key acceptance. The watchdog returned Alpine on that port and one
fresh signed strict-SSH fallback proof resolved the intent
`FALLBACK_RETURNED`. The controller now bounds the observed final
NetworkManager/udev identity race with a continuously clean dwell and one
shared deadline; all other residue still fails immediately. r2 is consumed.
See the
[r2 target USB-loss result](../test-results/2026-08-01-minimal-headless-r2-target-usb-loss.md).

The first authorized live ACM preflight was rejected because the existing
device-side reader had wedged; exact USB reset and host rebind could not
restore it. A physical reboot returned the exact fallback through fastboot and
restored its supervised ACM reader. The next signed exchange isolated a stale
exact-70-zone thermal predicate: the fallback now exposes 96 contiguous zones
with unavailable auxiliary modem/board channels but healthy core telemetry.
The collector now requires 70 through 128 contiguous zones, at least 29
stable positive readings, six named CPU/GPU/system sensor classes, and the
unchanged temperature ceilings. It ignores unreadable values only for the
exact observed auxiliary-type allowlist, plus zero and Qualcomm-inactive
values. Thirty-nine protocol tests pass, and a
fresh signed live preflight now passes with its no-replace mode-`0600` proof
retained outside Git. No experimental boot, flash, mount, fallback
configuration change, or client-key admission occurred. See the
[live acceptance](../test-results/2026-07-31-fallback-acm-preflight-live-accepted.md)
and preceding
[reader rejection](../test-results/2026-07-31-fallback-acm-preflight-live-rejected.md).
The private lifecycle record retains the verified nonce, physical USB
location, thermal maximum, and SHA-256 identities of the signed record,
signature, and inspected host-key pin, without retaining any private key.
The
`corrected-headless-successor-2026-07-30` profile binds its wrapper, raw image,
initramfs, signed bundle, accepted DTB, public trust root, verifiers, responder,
fetcher, wrapper configuration, AVB tool, unpacker, and qualified `cpio`.
`artifact-preflight` exits before fastboot discovery, and the one-shot
lifecycle rejects the consumed historical profile before credential paths.
See the
[live-gate admission report](../test-results/2026-07-30-corrected-successor-live-gate-admission.md).

The accepted stable-recovery wrapper now also has a fail-closed,
content-addressed cache path. A portable seal binds all 79,030 ASUS source
entries by path, type, mode, file content, and symlink target while excluding
host ownership and timestamps. Publication still requires the complete twin
kernel/raw/AVB gate and equal pre/post source seals. Materialization requires
the exact input key and caller-supplied entry ID, rehashes every cached file,
and never compiles or contacts the phone. The first 208 MiB entry reconstructs
the accepted corrected-headless wrapper in 3.10 seconds. It contains only the
historical public trust root; the disposable private key was destroyed, so
the cache is neither signing authority nor live authority. See the
[cache contract](recovery-wrapper-cache.md) and
[offline proof](../test-results/2026-07-30-stable-recovery-wrapper-cache.md).

The cached broad wrapper now has a separate configuration-slimming
experiment. A fail-closed policy, seven hostile mutations, and one positive
test preserve the
boot/CPU/RAM, UFS, gadget-only USB ACM/NCM, kexec, pstore, thermal, charging,
reboot, and PMIC power-key boundary while removing 601 built-ins and 655
active options. Two source-sealed clean builds produced the same
34,787,840-byte Image, 31.11% smaller than the accepted cached Image. Two
boot-header-v3/unsigned-AVB repacks also match and recover the exact kernel
and stable-recovery initramfs. Vendor HID and minimal V4L2 cores remain only
because ASUS Makefiles compile dependent accessory/video objects
unconditionally. The result is unbooted, `status=experiment`, and
`authority=none`; it neither changes the accepted cache nor grants live
authority. See the
[slimming contract](stable-wrapper-config-slimming.md) and
[offline proof](../test-results/2026-07-30-stable-wrapper-config-slimming-offline.md).

The historical native-indicator successor has a separate, non-sparse source
encoding and a v2 host package contract. Its 534,347,412-byte sealed archive
binds `build_profile=headless-core-v2`, 37,675 entries, the exact no-workload
command manifest, and the persistent seal while continuing to use the
accepted `network-root-v1` boot protocol. Normalization preserves the exact
source member set, hard-link topology, and inode flags before any verifier
mountpoints are created. The tracked
`headless-core-network-root-v2` candidate selects the 103,554-byte
buttons/default-off status-LED DTB. A full hardware-free gate reproduced two
signed bundles, stable-recovery initramfses, ASUS wrapper kernels, raw images,
and test-only AVB images under one disposable trust root; the private key was
destroyed and authority remains `none`. See the
[headless-core candidate result](../test-results/2026-07-30-headless-core-candidate-offline.md).

An ephemeral-key signed v2 bundle passes the real native verifier with
manifest SHA-256
`70136ad498fad21bce5279f60cbad36359c7d6df6eb42280591071c5e1389bf6`.
The real consumed P2 fixture also passes one complete offline
prepare/serve/fetch/verify/descriptor-load/execute composition through the
framed responder; a changed signature never reaches load. That earlier
offline checkpoint added no production key or live authority. See the
[root checkpoint](../test-results/2026-07-29-headless-root-candidate-offline.md)
and
[runtime integration result](../test-results/2026-07-29-headless-runtime-integration-offline.md),
plus the
[live rejection](../test-results/2026-07-29-headless-stable-recovery-live.md)
and
[corrected twin build](../test-results/2026-07-29-corrected-headless-candidate-offline.md).

## Persistent Arch root

The successor-v3 Arch root is built, verified, and recursively sealed offline.
It contains:

- systemd and minimal Plasma/server packages;
- exact Linux 7.1.4 modules and pinned firmware;
- key-only SSH;
- screen-off-first behavior and confined power-button handling;
- a locked, resource-limited automation account;
- fail-closed hotspot packaging.

The persistent-root P2 package also passed its offline construction and
storage-isolation contract. Its live target did not reach the required
acceptance marker and returned to the exact fallback. Follow-up wrapper,
timing, identity, release, and procfs diagnostics narrowed the failure but did
not produce a promotable target.

Entry-v1 then moved the oracle earlier. Its sole allowed live cycle executed
kexec once, never produced a stable entry marker, and returned to the exact
fallback with the root still `UNBOOTED` and selectors absent.

Evidence:

- [P2 offline](../test-results/2026-07-28-persistent-root-p2-offline.md)
- [P2 live rejected](../test-results/2026-07-28-persistent-root-p2-live-rejected.md)
- [entry-v1 offline](../test-results/2026-07-28-persistent-root-entry-v1-offline.md)
- [entry-v1 live rejected](../test-results/2026-07-28-persistent-root-entry-v1-live-rejected.md)

P2 and entry-v1 are consumed evidence. They must not be retried. Persistent
root work resumes only after stable recovery can classify one execute
transaction without relying on terminal markers.

## Mainline GPU

The vendor KGSL path can identify A660 with Mesa Turnip on a fresh boot, but a
second raw `/dev/kgsl-3d0` open times out after GMU HFI and translation-fault
errors. That failure occurs on both tested vendor kernels and poisons KGSL
until reboot. It is not caused by KDE or noVNC.

The Linux 7.1.4 path has isolated, rollback-guarded evidence for:

- Adreno SMMU;
- A660 registration;
- firmware request;
- microcode allocation;
- GMU resume entry;
- GMU/linked-CX runtime power management offline.

V9 GMU resume entry is the last live-accepted GPU ancestry. The v10 GMU/CX
runtime-PM package is offline-accepted and remains on HOLD; it has not run on
the phone. The v11 clock-preparation change is source/offline work only and is
not a runnable candidate. Stable DRM render-node operation, repeated
open/close, KWin/Wayland, Chromium, suspend/resume, and thermal acceptance
remain pending.

Before any wider GPU candidate runs, the repository now has one unified A660
acceptance harness and a minimal Vulkan queue-submit helper. Offline fault
tests cover exact mainline-render identity, KGSL rejection, rollback-versus-
soak separation, software-renderer rejection, boot-time and new
fatal-kernel-signature detection, finite Wayland frame completion, lightweight
continuous physical-darkness sampling plus bounded DPMS checks, private
evidence metadata, independent full Plasma PSS inventory, malformed telemetry,
watchdog/KWin PID reuse, signed and
sealed command execution, delegated-cgroup cleanup of `setsid` descendants,
before/after full-root verification, and atomic helper publication. A
test-only Vulkan implementation covers success, missing or
duplicate A660, missing queue, submit failure, and fence timeout.

The bounded staging mode requires target-visible signed 600/900-second timing,
enforces its own 540-second deadline, and rechecks storage isolation. The
network-root init now atomically attests the watchdog, its live timer child,
deadline, and timeout; the harness pins those identities, executable and
write-capable reset/log descriptors. It also records stable mount IDs before
moving the OverlayFS, authenticated lower, and tmpfs state; the harness
rejects a pathname-correct decoy mount. The 30-minute soak requires an
independently promoted persistent root with an exact OverlayFS-to-sealed-ext4
mapping, bounded tmpfs state, exact bundle/kernel/subtree/tree/seal identities,
an exact read-only verification mount, and a successful tree recomputation
before workload.

The incompatible signed bundle v2 format now emits target timeout,
command-manifest identity, and the complete `arch-a` lower-tree identity;
v2 components reject the older unsigned-root v1 schema. A static AArch64
verifier is now required inside the signed network-root initramfs and
authenticates the lower before OverlayFS or distribution userspace starts.
The canonical command manifest, static cgroup executor, static root verifier,
Vulkan submit helper, and unified acceptance harness are now installed in two
offline, versioned, read-only roots. One derives from successor-v3 and one
preserves the accepted v10 GPU ancestry before adding the runtime surface.
Both identities bind the exact base verifier, base seal, pre-integration base
tree, runtime provenance, commands, tools, complete tree, and persistent seal.
Their builders require the external approved runtime-tools manifest hash,
compare every pre-existing entry against a private read-only base snapshot,
permit only the fixed runtime additions, independently verify the final tree
with a static AArch64 binary, and publish the root plus identity together
through one atomic no-replace directory rename.

This is a sealed-root milestone, not a signed-bundle or live-acceptance
milestone. Promoted-root device identity, signed bundle packaging, the host
server profile, and the versioned recovery rebuild remain pending. No
installed recovery, trust root, or phone state changed. Neither acceptance
mode has run on the phone. See the
[offline runtime-root evidence](../test-results/2026-07-28-a660-runtime-root-offline.md).
See [A660 accelerated-desktop acceptance](a660-acceptance.md).

Machine acceptance records remain under `manifests/acceptance/`.

## Wi-Fi and VPN hotspot

Read-only fallback evidence identifies Qualcomm PCIe endpoint `17cb:1103`
with ASUS subsystem `17cb:0108`. The WCN6855 package supplies the reviewed
PCIe/QMP/power graph, matching ath11k modules, firmware layout, regulatory
data, enumeration-only oracle, root overlay, watchdog handoff, and
verifier-first host controls.

Two clean builds/packages are reproducible. The protected successor-v3 root
and one-cycle runner pass offline readiness. The package remains
`UNBOOTED_HOLD`; no mainline radio activation has occurred.

The hotspot v2 policy passes offline:

- kill-switch-first setup and partial-failure rollback;
- IPv4 and IPv6 ordinary-uplink leak rejection;
- unsolicited VPN-side ingress rejection;
- real WireGuard packet, handshake, and encrypted-transfer checks;
- UDP and TCP DNS through the tunnel;
- endpoint/interface loss remains fail-closed;
- exact cleanup and restart recovery.

Still pending on real hardware are ath11k client/AP operation, provider
WireGuard, DHCP/provider DNS, coexistence, throughput, thermal behavior, and
battery drain.

## Desktop, remote access, and memory

The fallback has a loopback-only remote administration stack reached through
a reconnecting host user service:

- ttyd terminal;
- noVNC/Xvnc emergency desktop;
- nested KWin/Plasma;
- Chromium CDP;
- singleton phone-side supervisor.

An induced tunnel failure restarted correctly, and a Chromium termination was
recovered without creating duplicate supervisors. The physical panel remained
off.

The recorded screen-off baseline retained about 10.1 GiB available memory and
zero swap. Approximate proportional memory was 390 MiB for KDE, 345 MiB for
Chromium, and 67 MiB for remote transport; a short low-overhead sample was
below 1% aggregate CPU. Wall-power and battery measurements are still needed.

A minimal Plasma/KWin installation is preferred over a full default Plasma or
GNOME environment. The device has enough RAM; idle power, GPU reliability,
service count, and thermal stability are the stronger constraints.

See [remote GUI](remote-gui.md).

## Automation-agent boundary

The development Arch image has a separate locked agent account with native
systemd limits:

- two CPUs;
- 2 GiB RAM;
- 512 MiB swap;
- 256 tasks;
- reduced CPU and I/O weight;
- private writable state only.

No email account, CV, browser profile, provider token, or API key is embedded.
Future Codex/Claude/OpenRouter-style automation should use narrow connectors,
revocable credentials, audit logs, and explicit confirmation for external
submissions. A general desktop login with access to all personal data is not
the intended security model.

## Refresh rate and screen-off policy

The vendor panel exposes fixed 60, 90, 120, and 144 Hz profiles. Dynamic FPS,
qsync, and dynamic bit clock are not advertised by the observed connector
capabilities.

- 60 Hz is the server/battery default.
- 90 Hz is the balanced interactive profile.
- 120/144 Hz remain explicit performance choices.
- DPMS off plus backlight zero is the default remote-server state.

Mainline refresh-rate acceptance waits for stable DRM/KWin acceleration.

## Current blockers

1. The external `headless-netroot-early-diag-v1` successor is production
   signed, twin-built, and installed, but remains unexecuted. After two
   pre-transfer host rejections, the remediated lifecycle transferred its
   response header and manifest; the recovery fetcher rejected the valid
   diagnostic Arch trust tuple as `FETCH_MANIFEST` before completing bundle
   transfer, `PREPARE`, intent, NFS, or `COMMIT_EXEC`. The 180-second watchdog
   and strict signed same-port fallback proof passed at 43.5 C.
2. The runtime PolicyKit remediation is installed and accepted. The exact
   operator-owned mode-`0600` socket and fixed root broker pass hostile tests,
   complete local/GitHub CI, exact installed-hash checks, SteamOS read-only
   restoration, and the real prompt-free 37,735-entry deployment-root
   preflight. Its first lifecycle rejected before listener/transfer because
   consumed r2 remained beside the diagnostic bundle in the sole-entry root;
   automatic fallback and strict signed proof passed again.
3. Consumed r2 is recoverably archived and the exact descriptor validator
   checks sole-root inventory, every artifact, and the canonical manifest
   during preflight without a listener. The published/reinstalled remediation
   passed real unchanged-atime bundle and 37,735-entry NFS preflights.
4. The fetcher's profile branch now matches every other contract component;
   its new native test reproduces live exit 50 before the fix and accepts the
   Arch-bound diagnostic while rejecting each partial zero/`none` mutation;
   persistent-root positive, trust-carrying, and rollback-floor cases also
   pass. Complete local CI passes. The corrected code also completed the full
   disposable-key deployment composition at checkpoint `2653e61`: both ASUS
   5.4 wrappers are byte-identical at test-AVB SHA-256 `2a44a908…62c53`, the
   embedded fetcher is `f410ca87…b5d13d`, native artifact preflight passes,
   and authority remains `none`. A subsequent production-key twin build from
   checkpoint `84a9cc8` produced exact corrected AVB wrapper
   `f710bbcd…97b0ef`, raw wrapper `2f460aa0…628a01`, ASUS `Image`
   `7fac4dda…728ed`, stable-recovery initramfs `fec72c4d…1c57a`, and the
   unchanged trust root `f10ca076…c57b`. The real artifact preflight passes
   and the wrapper is admitted for one RAM-only boot. The fallback-profile
   cleanup race is now closed offline: the lifecycle suppresses autoconnect,
   leaves recovery unmanaged after transfer, and restores the exact profile
   only after stable same-port Alpine USB identity. The bounded, serialized,
   idempotent restore passes partial-failure, detach, duplicate, wrong-port,
   hung-udev, socket, and lifecycle tests plus complete local CI. Host
   installation and connected preflight remain before any phone boot; never
   reuse the consumed `9c060a27…204ef` wrapper. See the
   [disposable](../test-results/2026-08-01-corrected-diagnostic-recovery-disposable-build.md)
   [production](../test-results/2026-08-01-corrected-diagnostic-recovery-production-build.md),
   and [bounded restoration](../test-results/2026-08-01-bounded-fallback-profile-restoration-offline.md)
   results.
5. The corrected wrapper `f710bbcd…97b0ef` booted once after reviewed host
   installation and connected preflight. Recovery reached NCM/ACM, but the
   privileged controller rejected Steam's loopback-only TCP 8080 listener
   before bundle response, `PREPARE`, intent, NFS, or `COMMIT_EXEC`. Watchdog
   fallback and strict pinned Alpine SSH passed. The wrapper is consumed and
   denied; the target remains unexecuted. The scoped privileged listener check
   now passes 25 tests, independent review, local CI, and GitHub CI. A
   deterministic generation-1 AVB successor `332889a8…b51830` was issued over
   byte-identical raw recovery `2f460aa0…628a01`; only descriptor salt and
   digest differ, and the full artifact preflight passes. The corrected
   controller is installed byte-exact at `9f3be8e9…90894`, its socket is active,
   SteamOS read-only mode is restored, and complete local/GitHub CI plus
   connected preflight passed. Generation 1 then booted once: recovery fetched
   and verified the exact signed bundle, returned `PREPARED`, and claimed one
   commit. The host control client's NFS policy omitted the diagnostic bundle,
   so the commit preceded NFS startup, no target frame arrived, exact Alpine
   fallback passed, and the intent was resolved `FALLBACK_RETURNED`.
   Generation 1 is consumed. The fail-closed host correction requires the
   diagnostic v3 profile/package handoff and rejects unknown guarded bundles
   before phone discovery; 20 control and 39 lifecycle tests, independent
   review, local CI, and GitHub CI pass at `77336ed`. Distinct generation-2 AVB
   `70fd77f7…fc72b1` preserved raw recovery `2f460aa0…628a01`, passed artifact
   and connected preflight, and booted once. Recovery returned `PREPARED`, but
   the host saw no completed HTTP transfer; NFS never started and control
   failed before COMMIT. No intent or target execution occurred, exact
   same-port Alpine fallback passed, and generation 2 is consumed. The offline
   correction now requires fatal `/run` tmpfs validation, fresh-fetch-only
   PREPARE, the corrected lifecycle fixture, and continuously stabilized host
   cleanup plus deferred-profile proof. Forty-one lifecycle tests, complete
   local CI, Claude review, and GitHub Actions run `30750260056` pass at commit
   `1af3275`. The fresh production twins pin generation-3 AVB
   `eb514a57…d77b6`, raw wrapper `f1a7c5ad…6a4ce`, and recovery initramfs
   `144f1cfd…e4ec`; exact artifact preflight passes. The immutable offline
   profile still rejects connected actions. A separate exact
   `headless-diagnostic-generation3-live-v1` profile selected the lifecycle.
   Connected preflight passed, then the sole cycle reached verified
   `PREPARED` after fresh fetch, verification, and kexec load. The 70-second
   host transfer server did not emit its completion receipt, so recovery
   network cleanup did not complete, NFS never started, and control failed
   before COMMIT. No target ran; exact strict-SSH Alpine fallback and clean
   host state passed. Generation 3 is consumed and no image is admitted. The
   historical 190-second recovery fetch limit versus 70/75/95-second host
   bounds is now covered by a hardware-free regression. Source uses a nested
   180/190/195/205/220/260/320-second worker-to-control lattice, and a hostile
   PREPARED/forged-receipt/nonzero-exit case still blocks NFS and COMMIT.
   Commit `4c2da4b` passed local and GitHub CI; its exact controller/server
   sources are installed with matching hashes. Distinct generation-4 AVB
   `220e8556…270d` was issued twice over unchanged raw recovery
   `f1a7c5ad…6a4ce`, admitted once, and consumed by one RAM-only lifecycle.
   Connected preflight passed. Recovery ACM/NCM and rollback armed, and both
   collector and bundle service became ready, but the service never emitted
   its independent completion marker before the 45-second NFS-ready deadline.
   NFS did not start, COMMIT was never sent, and no target ran. The phone
   returned automatically to Alpine. Initial host cleanup proof failed while
   the controller remained under its 205-second watchdog; after watchdog exit,
   fixed anchored profile restoration and strict fallback preflight passed
   with no project server/export residue. Generation 4 is removed from boot
   policy, classified consumed/offline-only, and must never be retried or
   flashed. The hardware-free correction now reproduces the exact
   PREPARED/control-exits-first stall, performs one anchored fallback restore
   and strict-SSH proof without an intent or retry, and still proves host
   cleanup if fallback proof fails. PREPARED is flushed before the NFS gate;
   transfer progress is non-authoritative; and the real host server/native
   fetcher pair passes at the Generation-4 artifact sizes. Complete local CI
   and GitHub Actions run `30793088424` pass at implementation commit
   `38b6019`. No Generation-5 image is built or admitted.
   See the
   [live result](../test-results/2026-08-02-corrected-diagnostic-bundle-listener-rejected.md),
   [successor result](../test-results/2026-08-02-listener-successor-avb-generation-offline.md),
   [NFS-bypass result](../test-results/2026-08-02-diagnostic-nfs-handoff-bypass-live.md),
   [generation-2 live result](../test-results/2026-08-02-generation-2-fresh-fetch-gap-live.md),
   [generation-3 production build](../test-results/2026-08-02-generation-3-fresh-fetch-production-build.md),
   [generation-3 admission](../test-results/2026-08-02-generation-3-live-admission-offline.md),
   [generation-3 live result](../test-results/2026-08-03-generation-3-transfer-timeout-live.md),
   and [generation-4 offline issuance](../test-results/2026-08-03-generation-4-timeout-lattice-offline.md).
   The [generation-4 live-profile transition](../test-results/2026-08-03-generation-4-live-profile-offline.md)
   remained phone-free and passed complete local CI, constrained Claude Opus
   review, and GitHub Actions run `30787774104` at exact implementation commit
   `f058d47`.
   The [generation-4 admission](../test-results/2026-08-03-generation-4-live-admission-offline.md)
   is the historical phone-free authority change. The
   [generation-4 live result](../test-results/2026-08-03-generation-4-nfs-readiness-live.md)
   records its sole cycle and consumed disposition. The
   [offline choreography correction](../test-results/2026-08-03-generation-4-choreography-fix-offline.md)
   records the published host-side fix and its evidence boundary. The
   [host-install result](../test-results/2026-08-03-choreography-host-install-live.md)
   proves the corrected installed hashes, the real 37,735-entry deployment
   root, the retained diagnostic-bundle preflight, and residue-free host idle
   state without contacting the phone.
   Distinct Generation-5 AVB `abe4501f…beb1a` is independently reproduced
   twice over unchanged raw recovery `f1a7c5ad…6a4ce`. Its offline-only profile
   passed exact artifact and mutation gates and rejected connected preflight
   and direct boot outside the lifecycle. See the
   [Generation-5 offline issuance](../test-results/2026-08-03-generation-5-choreography-offline.md).
   The diagnostic lifecycle selected the identical tuple through
   `headless-diagnostic-generation5-live-v1`; direct boot remained restricted
   to that lifecycle. Central policy admitted exactly one
   connected-preflight-gated RAM-only cycle. See the
   [offline profile transition](../test-results/2026-08-03-generation-5-live-profile-offline.md)
   and [one-shot admission](../test-results/2026-08-03-generation-5-live-admission-offline.md).
   The exact Alpine fallback then passed guarded health preflight and
   acknowledged one SSH-issued `RESTART2("bootloader")`. It disconnected with
   no phone USB re-enumeration during 105 seconds of bounded observation, then
   later appeared as exact ASUS fastboot at the same physical port. No cause
   is inferred and no reboot was retried. The
   [anchored transition result](../test-results/2026-08-03-fallback-to-fastboot-anchored-diagnostics-live.md)
   records the live boundary and corrected standalone helper.
   Generation 5 then passed its exact credential-bound connected lifecycle
   preflight at commit `4c55b1c`, including deployment key admission,
   installed host surfaces, rollback prerequisites, and one `lahaina`
   fastboot device. No boot, transfer, SSH connection, privileged server, or
   lifecycle output started. The exact green checkpoint `3e7ff47` then booted
   Generation 5 once in RAM. Recovery reached verified `PREPARED`, and the host
   sent all 46,163,787 signed-bundle bytes, but the independent completion-to-
   NFS handoff did not make the NFSv4.2 listener ready before COMMIT.
   `execution_started` remained `NO`; no target ran. Once the controller's
   fixed watchdog released its lock, anchored profile restoration, exact
   Alpine strict SSH, installed bundle/root preflights, and final host cleanup
   passed. Generation 5 is consumed, absent from boot policy, and must never
   be retried or flashed. See the
   [connected preflight](../test-results/2026-08-03-generation-5-connected-preflight-live.md)
   and [live result](../test-results/2026-08-03-generation-5-nfs-readiness-live.md).
   Timestamp reconstruction then proved the complete bundle was sent about 46
   seconds before control rejected. The privileged broker had spawned the
   controller with TERM blocked, and that mask propagated to its watchdog and
   cleanup descendants. The controller consequently waited for the full
   watchdog sleep and could not publish the completion receipt that gates NFS.
   The [offline signal-mask correction](../test-results/2026-08-03-generation-5-signal-mask-choreography-fix-offline.md)
   restores the exact caller mask before spawn, forwards cancellation to the
   child process group, and passes 13 broker, 25 controller, 47 lifecycle
   tests, and complete local CI. It does not increase a timeout, contact the
   phone, or authorize a successor. GitHub Actions run `30803393832` passes at
   exact follow-up commit `c9e3285`; the broker is installed at exact hash
   `fbafce24…cc42c`, both real host-only preflights pass, and final host residue
   is empty. See the
   [host installation](../test-results/2026-08-03-generation-5-signal-mask-host-install-live.md).
   Distinct Generation-6 AVB `6aa47517…d398` is independently reproduced
   twice over unchanged raw recovery `f1a7c5ad…6a4ce`. Its immutable offline
   profile and exact artifact/policy/mutation gates pass; connected preflight
   or boot through that profile rejects before host inspection even with all
   live flags. See the
   [Generation-6 offline result](../test-results/2026-08-03-generation-6-signal-fix-offline.md).
   The diagnostic lifecycle now selects that identical tuple through
   `headless-diagnostic-generation6-live-v1`; direct boot remains restricted
   to the lifecycle. Its connected preflight passed, then its sole RAM-only
   cycle completed the signed-bundle transfer while recovery control produced
   no output or `PREPARED` record. Independently, the collector expired with
   zero target frames. No COMMIT intent existed and no target ran. Exact Alpine
   restoration and strict SSH passed. Automated final cleanup returned FAIL
   on the production fallback udev model mismatch; independent residue checks
   were clean. The classifier defect is now reproduced and corrected offline:
   the real fallback model and three exact project NCM models are accepted,
   while prefix, suffix, whitespace, case, empty, missing, and embedded
   lookalikes fail closed. This is not a replacement live cleanup proof.
   Generation 6 is consumed and absent from policy. See the
   [offline udev correction](../test-results/2026-08-03-fallback-udev-model-classification-fix-offline.md),
   [offline profile transition](../test-results/2026-08-03-generation-6-live-profile-offline.md)
   and [one-shot admission](../test-results/2026-08-03-generation-6-live-admission-offline.md),
   [connected preflight](../test-results/2026-08-03-generation-6-connected-preflight-live.md),
   and [live result](../test-results/2026-08-03-generation-6-recovery-control-silence-live.md).
6. The private timeline and NetworkManager journal now explain the
   complete-transfer/empty-control-log boundary: the host hit its 10-second
   deferred-profile cleanup rejection and terminated control before waiting
   for `PREPARED`. NetworkManager had already made the interface unmanaged and
   address-free but retained the exact fallback UUID as historical
   association data. The
   [offline choreography correction](../test-results/2026-08-03-generation-6-deferred-profile-association-fix-offline.md)
   accepts only that exact UUID or an empty association after all other
   deferred-state checks pass continuously; wrong, duplicate, mixed, managed,
   addressed, or autoconnect-enabled cases fail. Generation 6 still has no
   live `PREPARED` and remains consumed.
7. Distinct Generation-7 AVB `d3d4cdb9…12901` was independently issued twice
   over unchanged raw recovery `f1a7c5ad…6a4ce`, with exact generation record
   `8127197d…799e`. Its immutable offline issuance profile is
   `headless-diagnostic-generation7-offline-v1`; connected preflight and boot
   reject before host inspection, both production twin trees pass artifact
   preflight, and a mutated generation record fails closed. The separate
   `headless-diagnostic-generation7-live-v1` selects the identical tuple
   through the lifecycle and rejects direct boot without its lifecycle guard.
   It was inventoried with the offline issuance record's `authority=none`,
   while central policy separately admitted exactly one
   connected-preflight-gated RAM-only lifecycle. Connected preflight passed,
   then its sole RAM-only boot transferred the complete signed bundle but
   produced no `PREPARED` or target frame. No intent, NFS handoff, or target
   execution occurred; exact Alpine restoration and strict SSH passed.
   Generation 7 is consumed and absent from boot policy. See the
   [offline issuance](../test-results/2026-08-03-generation-7-deferred-profile-fix-offline.md)
   and [profile transition](../test-results/2026-08-03-generation-7-live-profile-offline.md),
   [one-shot admission](../test-results/2026-08-03-generation-7-live-admission-offline.md),
   [live result](../test-results/2026-08-03-generation-7-acm-stability-live.md),
   [cleanup snapshot correction](../test-results/2026-08-03-generation-7-cleanup-snapshot-fix-offline.md),
   and [NetworkManager empty-field correction](../test-results/2026-08-03-generation-7-nmcli-empty-field-fix-offline.md).
8. Distinct Generation-8 AVB `f102d53c…f2415` is host-locally twin-issued
   over unchanged raw recovery `f1a7c5ad…6a4ce`, with exact generation record
   `9805809c…59d5`. The immutable
   `headless-diagnostic-generation8-offline-v1` profile pins its full tuple,
   both retained trees pass artifact preflight, and a generation-record
   mutation fails closed. The separate live profile selected that exact tuple
   through the lifecycle. Commit `c667718` and GitHub run `30832269180` passed,
   connected preflight passed, and the sole RAM-only boot transferred the full
   signed bundle. Recovery control then rejected because recovery ACM identity
   did not remain stable; no PREPARED record, COMMIT intent, or target execution
   existed. Exact Alpine fallback returned. The final host proof exposed an
   empty root-owned mode-`0600` NFS export-table inspection defect while
   independent checks found no service, listener, export, mount, kernel NFS
   thread, or lifecycle marker. Generation 8 is consumed and absent from boot
   policy. See the
   [offline successor](../test-results/2026-08-03-generation-8-nmcli-empty-field-successor-offline.md)
   and [live-profile transition](../test-results/2026-08-03-generation-8-live-profile-offline.md),
   [one-shot admission](../test-results/2026-08-03-generation-8-live-admission-offline.md),
   and [consumed live result](../test-results/2026-08-03-generation-8-recovery-acm-stability-live.md).
9. The mode-`0600` export-table proof now runs read-only through the fixed
   privileged host broker, preserves the table metadata, passes hostile
   offline identity/content tests, and is installed with two successful
   production proofs of the real mode-`0600` empty table. The next host-only
   correction adds bounded recovery-ACM stability classification before any
   distinct Generation-9 successor: eight fixed states, saturated counts, at
   most 16 transitions, and changed identity-field names only. Twenty-nine
   focused recovery-control tests, the 62-test lifecycle suite, and complete
   local repository CI pass; exact selection, two-second dwell, final
   revalidation, and no-retry behavior stay unchanged. Commit `77543ee` and
   exact-head GitHub run `30838804593` pass. The lifecycle executes this file
   from the synchronized checkout, so no root-installed broker update is
   involved. See the
   [offline result](../test-results/2026-08-03-generation-9-recovery-acm-classifier-offline.md).
   The subsequent test-first issuer checkpoint extends disposable twin
   generation through Generation 9, preserving both raw twins and rejecting
   reuse of every Generation 1–8 AVB identity; see the
   [issuer-readiness result](../test-results/2026-08-03-generation-9-issuer-readiness-offline.md).
   Distinct Generation-9 AVB `b458e64b…d008` is now retained in two
   byte-identical host-local trees over unchanged raw recovery
   `f1a7c5ad…6a4ce`. Its immutable
   `headless-diagnostic-generation9-offline-v1` profile pins the full tuple,
   rejects connected actions before host inspection, and locally passes both
   retained-tree artifact preflights plus mutated-generation-record rejection.
   Clean-checkout CI intentionally skips those ignored-tree checks while the
   tracked issuer and policy regressions still run. The inventory records
   issuance `authority=none`. Exact-head GitHub run
   `30841980164` passed at issuance commit `6193056`. The separate live profile
   now selects the identical tuple through the lifecycle; exact-head GitHub run
   `30843398402` passed at commit `4979581`. Admission commit `eea0989` and
   exact-head GitHub run `30847253087` passed. Key and connected preflight then
   passed. The sole RAM-only lifecycle transferred all 46,163,787 signed-bundle
   bytes over exact recovery ACM/NCM, but recovery returned no `PREPARED`
   response before USB disconnected about 178 seconds after enumeration and
   watchdog fallback began. The complete transfer and USB timeline make replay
   discovery after transport loss, when Alpine was already present, the best
   interpretation of its final 216-sample `product-mismatch` trace; the
   controller did not label that phase directly. Initial exact ACM had
   succeeded and delivered PREPARE. No COMMIT intent existed and no target ran.
   Exact Alpine fallback and final host cleanup passed. Generation 9 is
   consumed, absent from policy, permanently `BOOT_CLAIMED`, and never
   reusable. See the
   [offline successor](../test-results/2026-08-03-generation-9-acm-classifier-successor-offline.md)
   [live-profile transition](../test-results/2026-08-03-generation-9-live-profile-offline.md),
   [one-shot admission](../test-results/2026-08-03-generation-9-live-admission-offline.md),
   and [live result](../test-results/2026-08-03-generation-9-prepared-response-gap-live.md).
   Hardware-free host regressions now preserve the initial PREPARE transport
   loss while separately labeling and retaining bounded `prepare-replay` ACM
   classification. The recovery responder now emits five canonical,
   body-hashed, request-correlated PREPARE boundaries from request acceptance
   through immutable PREPARED publication. Host regressions enforce exact
   identity and contiguous per-attempt order, preserve separate initial/replay
   prefixes across transport loss, and prove that neither progress nor its
   loss can authorize COMMIT. Watchdog exit remains an independent lifecycle
   observation because reset can remove ACM before a final frame drains. The
   distinct responder also passes the full offline integration path: twin
   cross-compiles, extracted initramfs component identity, twin initramfses,
   two clean ASUS 5.4 wrapper Images, and twin raw/unsigned-AVB repacks are
   byte-identical. The disposable key was destroyed and the candidate remained
   `authority=none`; no phone interface was used. See the
   [progress result](../test-results/2026-08-03-prepare-progress-observability-offline.md)
   and [wrapper result](../test-results/2026-08-03-prepare-progress-wrapper-integration-offline.md).
   The subsequent guarded production build bound that responder to the
   existing production trust root and produced byte-identical A/B signed
   bundles, recovery initramfses, ASUS 5.4 wrapper Images, raw wrappers, and
   canonical AVB wrappers. The recovery initramfs is `99046d30…6e31`, wrapper
   Image `bb49b405…5f98`, and raw wrapper `27f4dbcc…73b3`. Two separate
   Generation-10 issuer invocations retain exact matching 11-file trees at AVB
   `b983e89b…8b51`, generation record `cb999cd8…3b6d`, and
   `authority=none`. The private snapshot was destroyed, external inputs
   remained unchanged, and the phone was not contacted. At that checkpoint,
   Generation 10 was unbooted and could not be used by the lifecycle. See the
   [offline successor](../test-results/2026-08-03-generation-10-prepare-progress-successor-offline.md).
   Independent review, publication at `d04b804`, and exact-head GitHub Actions
   run `30865091104` now pass. The immutable
   `headless-diagnostic-generation10-offline-v1` profile subsequently pins the
   complete tuple, rejects connected actions before host inspection, and
   passes both retained-tree artifact preflights plus generation-record
   mutation rejection on this host; clean CI skips those ignored trees.
   Inventory records `unbooted` and `authority=none`;
   temporary-boot policy remains unchanged with zero `allow` rows. See the
   [offline profile](../test-results/2026-08-03-generation-10-offline-profile.md).
   Constrained re-review and complete local CI passed; publication at `edae5d1`
   and exact-head GitHub Actions run `30867110893` are green. The separate
   `headless-diagnostic-generation10-live-v1` profile now selects that exact
   tuple through the lifecycle, but direct connected actions require the
   lifecycle guard and every missing, duplicate, or wrong-basis policy state
   rejects before host inspection. That transition was published at `adc4123`
   and passed exact-head GitHub Actions run `30869110964` while central policy
   remained empty. See the
   [live-profile result](../test-results/2026-08-04-generation-10-live-profile-offline.md).
   A separate central-policy checkpoint then contained exactly one
   Generation-10 `allow` row with the pinned one-shot basis. Inventory still
   recorded issuance `authority=none`, `unbooted`, and no boot claim at that
   checkpoint. Focused and complete local suites pass, and constrained Opus
   re-review returns `NO FINDINGS`;
   publication at `a9c012c` passed exact-head GitHub Actions run `30870594823`.
   See the
   [admission result](../test-results/2026-08-04-generation-10-live-admission-offline.md).
   The first connected-preflight transition verified exact Alpine fallback and
   issued one authenticated `RESTART2("bootloader")`, but USB disconnected
   without any anchored-port mode returning during the fixed 45-second window
   or an additional 30-second read-only check. No recovery image, payload, boot
   command, boot claim, or consumption occurred. Exact fastboot appeared later
   on the same connection after those bounded observations ended; the cause is
   not inferred. A fresh Generation-10 connected preflight from clean pushed
   commit `70d2f36` then passed the complete deployment-key chain, exact
   recovery/bundle artifacts, installed host state, rollback prerequisites,
   isolated USB profile, and one `lahaina` device. It started no phone boot,
   payload transfer, SSH connection, or privileged server. See the
   [transition result](../test-results/2026-08-04-generation-10-connected-preflight-transition-live.md)
   and
   [connected-preflight result](../test-results/2026-08-04-generation-10-connected-preflight-live.md).
   The result was reviewed and published at `f4b9e1c`; exact-head GitHub run
   `30872608193` passed (`recovery-core` 3m47s; QEMU 43s). The sole
   Generation-10 lifecycle then reached exact recovery ACM/NCM, emitted
   correlated `REQUEST_ACCEPTED`, and transferred all 46,163,787 signed-bundle
   bytes. The ACM response channel then closed before any later progress or
   `PREPARED` response reached the host; the exact device-side boundary remains
   unknown. Replay was explicitly `prepare-replay` with 216 stable
   fallback/product-mismatch samples and no identity changes. Restricted NFS
   reached pre-COMMIT readiness, but no COMMIT intent existed and no target
   ran. Exact Alpine fallback, strict SSH, profile restoration, and final host
   cleanup passed. Generation 10 is permanently `BOOT_CLAIMED`, absent from
   boot policy, consumed in inventory, and never reusable. See the
   [live result](../test-results/2026-08-04-generation-10-request-accepted-transport-gap-live.md).
   The next gate is an independent progress channel that survives ACM loss.
   Its receive-only NCM implementation now spans the device responder, exact
   production namespace, fixed privileged broker/firewall/controller,
   irreversible root-to-user collector, and private post-COMMIT lifecycle
   assessment. Every byte-level truncation is explicitly partial; absent,
   malformed, or mismatched evidence remains unavailable or non-authoritative,
   and no trace can create a COMMIT claim. Focused suites and the complete
   local Linux `ci` and provisioned `quick` tiers pass. See
   [the NCM progress contract](recovery-ncm-progress.md)
   and
   [offline host-integration result](../test-results/2026-08-04-generation-11-ncm-progress-host-integration-offline.md).
   A distinct
   [Generation-11 recovery wrapper](../test-results/2026-08-04-generation-11-ncm-progress-wrapper-offline.md)
   now reproduces across two clean builds and two offline issuances as AVB
   `8472b206…bcf562`. Its exact recovery and unchanged signed-target tuple now
   passes an immutable
   [offline profile](../test-results/2026-08-04-generation-11-offline-profile.md)
   against both retained trees. The one-shot controller now selects the same
   tuple through a separate
   [live-capable profile](../test-results/2026-08-04-generation-11-live-profile-offline.md),
   while central boot policy remains deny-by-default for every other image. A
   separate
   [one-shot admission](../test-results/2026-08-04-generation-11-live-admission-offline.md)
   added the sole exact `allow` row for use only after connected preflight.
   Commit `5293e56` passed exact-head
   GitHub Actions run `30899370666`. The reviewed profile and CI-race correction
   were published at `98f8d27`; exact-head run `30904224177` passed. The next
   live-profile transition now passes Claude Opus review, independent Codex
   review, and complete local CI. Commit `2a483ec` passed exact-head GitHub run
   `30908649494`. Admission-focused and complete local CI pass, and independent
   spec and standards reviews report no findings. The admission was published
   at `8e22bc5`; exact-head GitHub Actions run `30916646825` passed. Exact key
   and [connected preflight](../test-results/2026-08-04-generation-11-connected-preflight-live.md)
   then passed after strict fallback proof and an anchored same-port reboot to
   one `lahaina` fastboot device. At that checkpoint the artifact remained
   unbooted and had no boot claim. Independent spec and standards review and
   complete local CI passed;
   commit `7b76733` published this evidence and exact-head GitHub Actions run
   `30921019231` passed. Publication commit `04132f0` then passed exact-head
   run `30921533485`. The
   [sole live cycle](../test-results/2026-08-04-generation-11-progress-listener-confinement-live.md)
   entered the permanent private claim and booted exact recovery ACM/NCM, but
   the privileged host path rejected its started TCP 8081 collector as not
   uniquely confined before the bundle-server ready marker. Progress remained
   `PARTIAL/NO_ADMISSION` with zero records; recovery control never started, so
   no PREPARE, transfer, COMMIT intent, NFS, or target occurred. Exact Alpine
   fallback, strict SSH, host cleanup, and Steam socket restoration passed.
   Generation 11 is absent from boot policy, recorded `consumed`, and cannot be
   retried or readmitted on its former exact basis.
10. Bring up the headless core in order: boot/storage/USB/SSH, power/charging/
   thermal/suspend, input/sensors, then audio and wireless.

GPU, display, desktop, hotspot, and automation work is frozen until the
headless reliability gate. Phone actions use the central standing
authorization and still must pass the lifecycle runbook's exact technical
gates; this status section does not relax them.

## Operational constraints

- Credentials and private identifiers stay outside Git.
- `artifacts/`, `build/`, and `dist/` are ignored and are not covered by the
  Git archive tag.
- The accepted pre-reduction tracked state is recoverable at
  `archive/pre-stable-recovery-2026-07-28`.
- Linux v7.1.4 now has an exact tag-object/commit/tree/source-ref contract and
  a twice-reproduced rootless x86_64 builder with pinned base images, Ubuntu
  snapshot, complete package closure, and offline verification. The frozen
  network-root build specifically requires the shallow `rog5-build`
  `FETCH_HEAD` state with no local `refs/tags/v7.1.4`.
- Android packaging dependencies now have an immutable AOSP Git-blob
  bootstrap with exact accepted byte identities, including the historical
  CRLF normalization. The compact canonical boot-v3 metadata template is
  independently reproducible and replaces the missing 96 MiB historical
  template for successor builds.
- The corrected headless stage is network-disabled, consumes only the exact
  manifest-pinned Arch base and modules, rejects embedded Pacman secret or
  revocation state, normalizes timestamps, and emits a sorted archive.
  The `headless-ssh-v2` source and v3 fixture package/candidate are
  byte-reproducible; the non-fixture deployment package and live-candidate
  identities remain pending.
- Fastboot remains boot-only. The fallback slot and guarded
  `RESTART2("bootloader")` helper remain unchanged.

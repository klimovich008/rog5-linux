# Kernel audit integration: k119 qualification

This integrates the 2026-10-02 display, audio/DSP and USB/power audits. It is
host-tested source, not installed-phone evidence. No phone operation is part of
this work. The installed component status and accepted bundles stay unchanged.

The inherited commits are `d6003bd2`, `daaf7360` and `e911cc06`. They corrected
0070/0152 in place and added 0180–0197. This continuation adds 0198–0207;
0154–0179 are unchanged. Every new entry is appended to `series.production`.

## Patch inventory and provenance

“Local” means no equivalent backport was found in the lore.kernel.org and
git.kernel.org searches; it does not imply the underlying upstream bug is new.
The MSM v3 patches are proposal backports with local corrections, not a claim
that the whole proposal has merged. Hardware case names refer to the steps below.

| Patch | Change | Provenance | Hardware cases |
|---|---|---|---|
| 0070 (inherited edit) | Persistent encoder assignment instead of atomic-state dereference; IRQ-safe lockless assignment reads | Local | D1 |
| 0152 (inherited edit) | Checked GPU runtime resume before MMIO and retryable hardware initialization | Local | D2 |
| 0180 | Serialize framebuffer pin state; initialize before publication | [MSM v3 1/6](https://lore.kernel.org/all/20260912-fd-kms-fix-smmu-v3-1-a7ddc6fe2032@oss.qualcomm.com/) | D1 |
| 0181 | Unwind failed preparation and pins | [MSM v3 2/6](https://lore.kernel.org/all/20260912-fd-kms-fix-smmu-v3-2-a7ddc6fe2032@oss.qualcomm.com/) | D1 |
| 0182 | Staged KMS initialization unwind | [MSM v3 3/6](https://lore.kernel.org/all/20260912-fd-kms-fix-smmu-v3-3-a7ddc6fe2032@oss.qualcomm.com/) | D3 |
| 0183 | Snapshot/workqueue/DPU destruction after partial initialization | Local follow-up | D3 |
| 0184 | Retain framebuffer pin and reference until a safe vblank | [MSM v3 4/6](https://lore.kernel.org/all/20260912-fd-kms-fix-smmu-v3-4-a7ddc6fe2032@oss.qualcomm.com/) | D1 |
| 0185 | Queue/off/drain serialization and safe allocation fallback | Local follow-up; completed by 0199 | D1 |
| 0186 | Clear stale DSC slots | [MSM v3 6/6](https://lore.kernel.org/all/20260912-fd-kms-fix-smmu-v3-6-a7ddc6fe2032@oss.qualcomm.com/) | D4 |
| 0187 | FastRPC attachment error double-free (F1) | [linux-next 2159430fe26068ca3c89557ddd2d5eb17a5a8cf0](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=2159430fe26068ca3c89557ddd2d5eb17a5a8cf0) | A1 |
| 0188 | DMA buffers retain channel, not freed user (F2) | Local | A1 |
| 0189 | Stop PDR producers, drain work/QMI, then free services (F3) | Local | A2 |
| 0190 | Notification enable shares battmgr request mutex | Local; completed by 0204 | P1 |
| 0191 | GENI forced runtime-suspend balance and pinctrl failure unwind | Local | P2 |
| 0192 | Sticky FULL USB bandwidth vote for untracked topology | Local | U1 |
| 0193 | Atomic matching/claim of OEM replies | Local | P1 |
| 0194 | Mark SECUREMAP only after successful assignment | Local FastRPC F1 follow-up | A1 |
| 0195 | Keep amplifier off after failed protection restore; reset after failed mute | Local F4; completed by 0198 | A3 |
| 0196 | Propagate SENARY clock/format/TDM and ASP format errors | Local F6 | A4 |
| 0197 | Unwind VA macro resume on regcache-sync failure | Equivalent to [upstream eb667d0fbdd3](https://git.kernel.org/broonie/sound/c/eb667d0fbdd3), adapted | A4 |
| 0198 | Persistent amplifier fault/reset latch and hardware-bypassed default readback | Local F4 | A3 |
| 0199 | Queued/in-flight flush generations and frozen retirement target | Local correction of 0184/0185 | D1 |
| 0200 | Unique APR vote tokens, valid handles, acknowledged devotes and uncertain state | Local F5 | A4 |
| 0201 | PCM ownership cleanup independent of RUNNING; quarantine uncertain DMA/session | Local F8 | A5 |
| 0202 | Reject training exhaustion/insufficient bandwidth; checked PHY init/exit ownership | Local | D5 |
| 0203 | Gate newly registered gadgets by requested role; release FULL only after stop | Local | U1 |
| 0204 | Ordinary reply opcode/property/generation correlation and timeout poison | Local | P1 |
| 0205 | Desired/confirmed/unknown boost; best-effort OFF; pause limited charging before sleep | Local | P1, P3 |
| 0206 | Coherent buffers hold the DMA device through final free | Local F2 follow-up | A1 |
| 0207 | Permit bypassed readback of the four restored operating-point registers | Local; ASUS WW33 readable-register policy | A3 |

## Host evidence and its limits

`scripts/device/test-kernel-audit-20261002.py` is registered in active, ci,
nightly and board. It reconstructs real driver functions from sparse preimage
fragments plus the production patches, compiles them with strict host warnings,
and executes fault/interleaving cases and rejecting mutations. Set
`ROG5_LINUX_SOURCE` to compare those functions with the fully applied source.
Mocks model ordering and failures; they do not establish IRQ concurrency,
lockdep safety, firmware protocol behavior or physical DMA cessation.

The exact full production build and test results are recorded in the dated
test-results report after completion. Warning-policy-clean means the existing
reviewed diagnostic policy passes; it does not mean every upstream warning is
absent. The build's result.json retains actual input hashes and diagnostics.

Important conservative behavior needing qualification:

- A retired framebuffer whose initial allocation/scheduling fails while a flush
  is uncertain keeps a pin/reference permanently. A failed work rearm retains
  a listed pin until hardware-off drain. Neither path invents scanout completion.
- LPASS firmware must echo the full opaque APR token and acknowledge devotes.
  Timeout makes that block unusable until AFE rebind after service restart.
- PCM close/unmap uncertainty detaches/drains callbacks, reserves the FE session
  and transfers fixed preallocation out of ALSA's freeing path. The allocation,
  client and device are deliberately retained until reboot. Automatic reclamation
  after DSP restart needs a separate proven quiescence API. Compressed gapless
  streams are outside the audited PCM finding and are unchanged.
- FastRPC's device reference prevents device-object UAF; it does not prove an
  IOMMU domain remains usable after arbitrary session-device unbind.
- With a percentage limit below 100, suspend pauses charging even below the
  limit. Charging resumes according to the awake policy after resume. Continuous
  charging during sleep with firmware-owned thresholds or wake evaluation is
  deferred because that protocol/wake behavior has not been qualified.

## Exact hardware qualification sequence (not executed)

Use the project's reviewed RAM-trial workflow in [development](../development.md).
Package the recorded k119 Image/modules with the current admitted DTB and init,
verify payload/build IDs and signature, and create a fresh trial descriptor.
Boot only through the reviewed controller after its identity, power and fallback
guards. Record `uname -r`, `/sys/kernel/notes`, the trial receipt and a fresh
kernel-log marker. Never unload MSM on a running display. Fault cases below need
a separately reviewed instrumented image or mock firmware; k119 does not add
public fault-control interfaces. Do not use unrestricted I2C/register pokes.

1. **D1 — framebuffer and encoder lifetime:** On the panel, alternate two reused
   framebuffers for 10,000 atomic flips while issuing 10,000 asynchronous cursor
   replacements. Repeat with panel plus DP sharing a framebuffer and with 100
   output disable/enable cycles. In the instrumented image, pause the async worker
   after it clears pending_crtc_mask and before wait_flush; advance vblanks and
   verify the retired IOVA stays mapped. Resume flush and verify release only
   after its next vblank. Complete a newer flush before retirement executes and
   verify the target does not move. Inject framebuffer preparation/allocation and
   vblank enable/rearm errors individually, then disable the CRTC. Check for zero
   addresses, premature unmaps, SMMU faults, lockdep reports and growth in pins on
   normal paths; retained fault pins must follow the documented behavior.
2. **D2 — GPU power failures:** Fail the GMU runtime resume before submit and each
   recovery resume in an instrumented image. Submit a bounded GPU job. Verify no
   GMU/GPU MMIO or hw_init occurs after the failed resume, jobs remain deferred or
   error, and a successful later resume retries initialization. Record PM reference
   counts and kernel logs; do not infer a pass from absence of an immediate crash.
3. **D3 — display probe unwind:** On separate fresh boots fail each KMS initialization
   stage: workqueue allocation, snapshot worker, IRQ/postinstall and DPU global
   state. Verify the original probe error, no NULL workqueue use, double IRQ free,
   stranded worker or callback after destruction. Then boot without injection.
4. **D4 — DSC:** On a topology-capable instrumented configuration reserve two DSC
   blocks, then one, then none. Verify unused hw_dsc slots are NULL and merge is
   disabled. Current AMS678 topology alone cannot qualify this transition.
5. **D5 — DP:** Perform 100 native-DP and HDMI-hub replug/DPMS cycles under both
   reduced and maximum link policies. Fail all training attempts, then train at
   bandwidth below mode demand with the configured margin. Both must reject
   enable. Inject each PHY init/exit failure; inspect init_count and PM references,
   require no AUX traffic after failed init and successful later recovery. Include
   the eDP runtime-suspend failure path on an applicable test configuration.
6. **A1 — FastRPC:** With an authorized test process create a small DMA-buf and
   request a larger MEM_MAP; require one detach/put and an error. Allocate an
   exported FastRPC buffer, close the FastRPC FD, then mmap/attach/close the held
   buffer FD; require no user/channel/device UAF. Repeat export/allocation failure
   and failed secure assignment. Instrument reference counts, and separately
   qualify session-device teardown/domain lifetime; arbitrary unbind is not a
   production test established by this change.
7. **A2 — PDR:** In a fresh instrumented trial race ADSP/APR removal with locator,
   notifier and indication callbacks, including a worker awaiting QMI response.
   Verify no enqueue after stopping, workers finish before service free, QMI
   callbacks cease before queues are destroyed, and the uninjected boot recovers.
8. **A3 — amplifier F4 first:** Keep speaker output muted and physically monitor
   reset/enable while injecting each vendor setup, default restore and bypassed
   readback error. After failed rollback request direct DACPCM and a DSP restart;
   require no GLOBAL_EN enable until complete hardware defaults and BBPE clear
   are verified. Fail emergency mute too: reset must remain asserted through DSP
   reload and repeated playback attempts. Restore the bus and rebind on a fresh
   safe trial before low-gain direct/DSP listening tests on both speakers.
9. **A4 — LPASS/SENARY/VA:** Repeat 100 idle-to-playback and capture cycles. Trace
   vote/devote opcode, full token and nonzero returned handle for every used block;
   require a devote acknowledgement. Inject wrong/stale tokens, wrong opcodes,
   zero/truncated handles and timeouts; reuse must fail until AFE service rebind.
   Inject SENARY bitclock/format/TDM and VA regcache-sync errors separately; require
   the startup/resume error, balanced clocks and successful uninjected retry.
10. **A5 — PCM:** On the actual discovered FE, run S16_LE, S24_LE and S32_LE
    playback and supported S16_LE/S32_LE capture, then 100 prepare/drop/reprepare/close cycles including a
    prepared-but-never-started stream. Inject format rejection and map/open/close/
    unmap timeout one at a time. A confirmed cleanup permits reuse; uncertain
    cleanup must retain DMA and reject reopening that FE with EBUSY. Close ALSA
    and remove the card in the instrumented trial: no callback into freed runtime
    or recycled DSP buffer is allowed. Reboot to reclaim quarantined resources.
11. **U1 — USB:** Trace requested/current role, UDC pullup/DCTL state and usb-ddr
    votes. Delay role work before and after its mutex, request HOST then NONE,
    and verify the newly created UDC never connects. From DEVICE request HOST
    and NONE with gadget stop delayed for more than two seconds: FULL must persist
    past watchdog expiry and fall only after confirmed stop. Fail USB tracking
    allocation with an HS storage/network device attached; FULL must persist
    until primary xHCI bus teardown. Repeat hub/NCM reattach and suspend/resume.
12. **P1 — battmgr/boost:** Restart the test service while policy reads and
    notification enable compete. Inject unrelated opcode/property/type responses,
    duplicates and matched malformed payloads; only the intended request may
    complete or update its cache. Delay a reply past timeout: identical retries
    must fail until service recovery. Isolate GPIO4 in the reviewed test setup,
    lose ON and OFF acknowledgements, and verify is_enabled reports unknown,
    best-effort OFF is sent, and no stale ON reply proves OFF. Service recovery
    must freshly acknowledge the desired OFF/ON state.
13. **P2 — GENI:** Record runtime-PM usage/active state, suspend/resume an active
    UART 100 times, then repeat while already runtime-suspended. Inject sleep
    pinctrl failure; require forced resume unwind and restored port state, with
    no clock/reference imbalance or lost uninjected UART operation.
14. **P3 — charge limit during sleep:** Record existing thresholds, set start/end
    to 70/80 while capacity is below 70 on external power, then suspend for
    15 minutes. Verify fresh pause acknowledgement precedes sleep and charging
    remains paused; resume must obtain fresh capacity and restore charging under
    the awake policy. Repeat at/above 80. Inject pause timeout: suspend must abort.
    Restore the original thresholds and record current, capacity, temperature,
    service generations and logs. This qualifies pause-during-sleep behavior,
    not continuous asleep charging to a firmware percentage threshold.

Power-floor tuning, diagnostic defaults, dumb-buffer padding, panel first-frame
policy, UFS clock restructuring, PCI scoping and watchdog qualification are
audit improvement ideas, not correctness fixes requested in this integration.
They are deferred to separate measured experiments. No iris/video patch is
changed, and no phone test or installation is claimed.

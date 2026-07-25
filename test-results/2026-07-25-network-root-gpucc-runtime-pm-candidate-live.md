# Network-root v15 CCF orphan runtime-PM candidate — live result

Date: 2026-07-25

Result: **bounded diagnostic partial success with successful rollback**. V15
supports the CCF/provider runtime-PM ordering hypothesis: the existing
DISPCC RCG read that did not return in v14 completed seven times, and GPUCC
clock registration advanced through completed index 6 and into index 7.
GPUCC registration itself did not return before the independent 75-second
watchdog reset the phone, so normal GPUCC coldplug is not yet accepted.

The reset occurred while high-volume 100 ms trace markers were still arriving
continuously. The first timed marker was at 402.023171 seconds and the last at
475.924613 seconds, a 73.901-second span with a maximum 0.116-second gap
between consecutive markers. The final marker was:

```text
phase=consumer-allocation-complete clock=gpu_cc_cx_qdss_tsctr_clk ret=0
```

This timing strongly supports diagnostic trace-budget exhaustion rather than
a new non-returning operation, but that remains an inference: the module-load
return and GPUCC registration-complete markers did not arrive. V15 is consumed
and must not be retried.

The independent watchdog restored the exact persistent fallback with a
changed private boot identity. Nothing was flashed, Linux 7.1 exposed no
physical storage, the fallback retained no pstore or fatal record, and all
temporary host NFS, firewall, inhibitor, address, profile, service, and mount
state was removed.

## Scope and safety boundary

- One temporary `fastboot boot`, followed by one attended RAM-only kexec.
- Linux `7.1.4-g7a5cef0db479` with OverlayFS over a read-only NFSv4.2 lower.
- SCSI/UFS absent from the kernel, zero physical block devices, and zero
  block-backed mounts.
- Only `/soc@0/clock-controller@3d90000` changed from `disabled` to `okay`.
- GPU, GMU, Adreno SMMU, display consumers, UFS, RTC, input, and every remote
  processor remained explicitly disabled.
- The external GPUCC module existed only in target tmpfs, was root-owned,
  mode `0400`, and matched SHA-256
  `9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a`.
- The three inherited core trace parameters were read-only, default-off, and
  enabled exactly once only for this diagnostic boot.
- The original 900-second rollback watchdog remained armed through target
  baseline and payload verification. The remote probe command then disarmed
  it and immediately armed the independent 75-second process-group watchdog.
- The GPUCC module load and kexec execute action were each invoked once and
  never retried.
- The first staging load marker was lost during ACM re-enumeration. The
  control-safe helper rediscovered the exact endpoint and replayed only the
  identical idempotent load action once. Execute was not replayed.
- No firmware, credential, personal data, full command line, private boot
  identity, NetworkManager identifier, phone identifier, or fallback helper
  path enters this report.

## Reproducible candidate

The
[v15 offline report](2026-07-25-network-root-gpucc-runtime-pm-candidate-offline.md)
records the source model, red/green and mutation tests, clock KUnit result,
two clean mainline builds, two nested wrapper/package paths, and every offline
gate.

The exact behavioral patch is
`patches/linux-7.1.4/0011-clk-guard-orphan-reparent-with-runtime-PM.patch`,
with SHA-256
`a309fe55dc6221f4475c22beb43018dde0f2eb107fa60e84f8e43f28e17a4a25`.
The final source is commit
`d9ac316489f4258d389d6298659d5e9c22183400`, tree
`c796deb1cc54e942f8bb46a2c76a7199e19e5c92`.

The live inputs were:

| Artifact | SHA-256 |
|---|---|
| Linux 7.1.4 Image | `d30df38804750ded48607135a7d23d4f95e0947c49b68395a8f6818c4a27c54b` |
| Linux 7.1.4 Image.gz | `a620dd40df6d495e00a8f7f84e707c9ceb7483f0828afb2372792985e69f008e` |
| matching module archive | `9350e5a010c0af11fe4bde48527d056701c83a0072be4ad29cce2565a75204a1` |
| external `gpucc-sm8350.ko` | `9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a` |
| GPUCC-only DTB | `e6f86c3022f58a765351b5b761c8bc815b093209517adb4678107d542ff5bcb5` |
| target initramfs | `4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac` |
| nested staging initramfs | `68b8729c5aef7f9a3eacba07685fe952f4df6cac29eb8c35d9559fda98722fab` |
| ASUS wrapper Image | `bf4abdad89941b34f769af25f80d8b93ac202a77c31005d572bc559255d61b7e` |
| raw boot image | `392ee5b0aa674f95da1b2dd544d25aab8d201f8d5a310fda2c8ab805fc1a6793` |
| temporary-boot AVB image | `bb4a6e34c98475f991a9575defe57c52ac732da0cea96a10585ee0bb92ae7730` |
| fourteen-file manifest | `a739f975f87ac30918625178007b4cd7302449ae96c26e5c42185e9e1a0425cc` |

The module archive, external GPUCC module, exported symbol table, and RCG2
object remain byte-identical to v14. Only the generic CCF object and mainline
Image changed.

## Live baseline

The host began from the exact persistent fallback with strict pinned SSH,
zero Fastboot/ADB targets, one fallback ACM, zero pstore/fatal records, no
diagnostic module, 73 readable thermal zones, and a 39.1 C maximum. The NFS,
firewall, profile, listener, mount, service, inhibitor, candidate-hash, export,
and synchronized-Git gates passed before temporary boot.

The first target baseline attempt raced early systemd startup and failed
closed with `FAIL systemd`. The target remained alive with its original
watchdog armed and GPUCC unloaded. After systemd reached `running` with zero
failed units, the same read-only baseline was rerun and passed:

- exact Linux release, PID 1 systemd, and runtime-masked automatic coldplug;
- all three exact mode-`0400` trace parameters enabled once;
- OverlayFS `/`, exact read-only NFSv4.2 lower, and stable isolated USB link;
- zero physical block devices and zero block-backed mounts;
- GPUCC `okay`, with GPU, GMU, Adreno SMMU, UFS, RTC, display consumers, and
  every remote processor disabled;
- no loaded GPUCC module and no DRM render node;
- 1,008 module files read completely from the read-only lower;
- zero failed units and zero current fatal signatures; and
- 29 readable thermal zones with a 38.1 C maximum.

Immediately before the probe, all 29 thermal zones remained readable with a
36.2 C maximum. The original watchdog was alive, GPUCC remained unloaded,
and current fatal-signature count remained zero.

The target exposed one standard pstore record. Its private 226,568-byte
content contains the preceding Linux 5.4.210 staging console, no Linux 7.1
target content, and no fatal signature. Its SHA-256 is
`84ab37b9b9a786e62c967dc6e47a34f0c17b4094b7914840d441854d11e09fce`.

## Delivered trace

The private mode-`0600` probe log is 86,130 bytes with SHA-256
`e462f630a895e4cb04c743f18b003e006162feba1e5331193145eefbeeb106d3`.
It contains:

| Marker class | Count |
|---|---:|
| GPUCC driver | 7 |
| Qualcomm common-clock | 84 |
| generic CCF | 552 |
| RCG2 parent-read | 14 |

The original-watchdog disarm PASS, probe BEGIN, and external module-load begin
each appear exactly once. There are zero fatal, warning, call-trace, or fault
signatures.

The first new behavioral sequence was:

```text
phase=runtime-get-all-begin clock=gpu_cc_ahb_clk ret=0
phase=runtime-get-all-complete clock=gpu_cc_ahb_clk ret=0
phase=prepare-lock-begin clock=gpu_cc_ahb_clk ret=0
phase=prepare-lock-complete clock=gpu_cc_ahb_clk ret=0
phase=orphan-runtime-state clock=disp_cc_mdss_pclk0_clk_src ret=11
phase=orphan-get-parent-begin clock=disp_cc_mdss_pclk0_clk_src ret=0
phase=parent-read-begin clock=disp_cc_mdss_pclk0_clk_src ret=0
phase=parent-read-complete clock=disp_cc_mdss_pclk0_clk_src ret=0
phase=orphan-get-parent-complete clock=disp_cc_mdss_pclk0_clk_src ret=1
phase=orphan-reparent-complete clock=gpu_cc_ahb_clk ret=0
phase=runtime-put-all-begin clock=gpu_cc_ahb_clk ret=0
phase=runtime-put-all-complete clock=gpu_cc_ahb_clk ret=0
phase=core-init-exit clock=gpu_cc_ahb_clk ret=0
phase=clock-regmap-register-complete index=0 ret=0
```

The runtime-state encoding is provider present (`1`), runtime PM enabled
(`2`), runtime-suspended (`4`), and runtime-active (`8`). V14 recorded `7`:
present, enabled, and suspended. V15 recorded `11`: present, enabled, active,
and not suspended. The corresponding parent read then completed with return
zero, and the outer callback returned parent index 1.

Across the captured run:

- 7/7 `runtime-get-all-begin` markers have matching successful completions;
- 7/7 `runtime-put-all-begin` markers have matching completions;
- 7/7 `parent-read-begin` markers have matching successful completions;
- common-clock registration completed indexes 0 through 6;
- registration began index 7 and continued through its CCF
  `consumer-allocation-complete` phase; and
- no marker gap exceeded 0.116 seconds.

No GPUCC `registration-complete`, module-load-return, or probe PASS marker
arrived before reset. The independent-watchdog expiry notice also could not
traverse the departing transport. The SSH client ended with the expected
departed-transport status.

## Interpretation

V15 resolves the exact v14 boundary under observation. Acquiring provider
runtime-PM references before `prepare_lock` makes DISPCC active, its existing
RCG read returns repeatedly, CCF completes the first seven GPUCC clock
registrations, and no new warning or fatal signature appears.

It does not prove complete GPUCC registration. The diagnostic emits hundreds
of markers and deliberately delays 100 ms after each. The final marker
arrived 73.901 seconds after the first with uninterrupted 0.112–0.116-second
spacing, immediately at the 75-second watchdog boundary. Therefore
trace-budget exhaustion is the strongest explanation for this reset, not a
localized hang at the final source operation. A trace-free confirmation is
required before accepting the candidate.

The result does not prove that the experimental RFC is safe for arbitrary
clock providers. It still resumes every registered runtime-PM clock-provider
device and holds the provider-list lock across that work. GPU, GMU, IOMMU,
firmware, DRM/MSM, and every real GPU consumer remained disabled.

## Rollback and cleanup

The independent watchdog returned the exact fallback with a changed private
boot identity. Final phone checks passed:

- exact fallback kernel and ext4 root through strict pinned key-only SSH;
- zero Fastboot and ADB targets, with one fallback ACM;
- zero retained pstore records, current fatal signatures, or diagnostic
  modules; and
- 73 readable thermal zones with a 37.8 C maximum.

Final host checks passed:

- inactive NFS service and mount daemon;
- zero exports, NFS listeners, NFS threads, NFS mounts, or temporary bind
  mounts;
- restored `ip_nonlocal_bind`;
- zero temporary firewall interfaces, sources, services, ports, forwarding,
  masquerade, or rich rules;
- active firewalld and ModemManager;
- explicit active non-autoconnecting fallback USB profile, with the temporary
  `/30` address absent;
- no temporary host sleep inhibitor; and
- a clean Git worktree synchronized with the pushed branch before this report
  was written.

## Decision and next gate

V15 must not be rerun. GPUCC remains rejected for normal coldplug because the
module's registration and the post-load stability checks did not return.

The next candidate is a trace-free v16 confirmation, not a new kernel
behavior change:

1. keep the exact v15 source, module, DTB, disabled consumers, UFS-disabled
   kernel, read-only NFS root, rollback, and 75-second independent watchdog;
2. boot with all high-volume Qualcomm/CCF/RCG2 trace parameters absent;
3. retain only the bounded seven-phase outer GPUCC module trace;
4. add source and mutation contracts that reject accidental core-trace
   enablement and prove the confirmation probe cannot accept a traced boot;
5. offline-verify the exact trace-free loader transport and package before
   considering one attended RAM-only attempt; and
6. accept the CCF candidate only if GPUCC binds one device, remains stable,
   introduces no consumer/render node, fatal/warning, storage, or thermal
   regression, and returns through clean rollback.

Only after that confirmation may the project proceed to separately isolated
power-domain, regulator, IOMMU, GMU, firmware, and DRM/MSM tiers.

# Network-root v10 GPUCC common-clock diagnostic — live result

Date: 2026-07-25

Result: **bounded diagnostic failure with successful rollback**. The SM8350
GPU clock controller completed MMIO mapping, both existing Lucid PLL
configuration calls, reset-controller registration, both GDSC registration
steps, and the protected-clock drop. It then stopped during registration of
regmap clock index 0. The final delivered marker was
`clock-regmap-register-begin index=0 ret=0`; its matching completion marker
never arrived.

An independent 75-second SysRq watchdog reset the phone to the exact
persistent fallback. Nothing was flashed, no phone storage was exposed to
Linux 7.1, standard pstore retained no record, and all temporary host
NFS/firewall state was removed.

## Scope and safety boundary

- Temporary `fastboot boot`, followed by a separately authorized RAM kexec.
- Linux `7.1.4-g7a5cef0db479` with OverlayFS over a read-only NFSv4.2 lower.
- SCSI/UFS absent from the kernel, zero physical block devices, and zero
  block-backed mounts.
- Only `/soc@0/clock-controller@3d90000` changed from `disabled` to `okay`.
- GPU, GMU, Adreno SMMU, display, UFS, RTC, input, and every remote processor
  remained explicitly disabled.
- The GPUCC module was supplied only from target tmpfs, root-owned, mode
  `0400`, and hash-pinned.
- Both diagnostic parameters were read-only and default-off. The common-clock
  trace was additionally gated to the exact `qcom,sm8350-gpucc` compatible.
- Trace markers added only logging plus a diagnostic 100 ms delivery delay;
  they did not add, skip, or modify a register, clock, reset, power-domain,
  regulator, storage, or persistent-state operation.
- The normal network-root rollback watchdog remained armed through the full
  baseline gate. It was then safely disarmed and replaced by the probe's
  independent process-group watchdog before `insmod`.
- No firmware, credential, personal data, or private device identifier entered
  the bundle or this report. The complete live log remains private outside the
  repository with mode `0600`.

## Reproducible candidate

The source was recreated from exact Linux commit
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`. Applying the GPUCC driver trace
and common-clock trace in that order produced commits
`86f3c68a666446d9bbcb9bd9f90df50f989ba8ea` and
`d4bb00313e92514f89bc0a9e7a7dffcb4884834f`, with final tree
`3b185820802b882d05830b9c6aee35bff984e07b`.

Two clean, network-isolated Linux builds matched byte-for-byte. Two clean ASUS
wrapper builds also matched byte-for-byte. The GPUCC-only DTB, nested staging
initramfs, target initramfs, matching module archive, header-v3 image, and AVB
package passed the dedicated bundle verifier.

| Artifact | SHA-256 |
|---|---|
| Linux 7.1.4 Image | `c0127c338b6af50a51e51c1e4837961d9806d0be969cd7337c3e597583e2dd62` |
| Linux 7.1.4 Image.gz | `dd16b19988c2ceae2fc08655e027711e540e5ed860ced5cc69d50afb3b4ba813` |
| matching module archive | `7c49c648c076326a6f008082f0d38e389bd8bb7c8a867ee0935d83e6a4195224` |
| external `gpucc-sm8350.ko` | `0ccb0059ec1960becb3676903aaccb623f105dbc8df08984cbd13a7d1ea6e73c` |
| GPUCC-only DTB | `e6f86c3022f58a765351b5b761c8bc815b093209517adb4678107d542ff5bcb5` |
| target initramfs | `4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac` |
| nested staging initramfs | `e8593e64eeee6cff5649c4c239c66cdf7fcd4edaccfab900c56b8e9764dd1ed3` |
| ASUS wrapper Image | `86a7b26819215d1d9b43bfa24ec90bef63cb817a91463b75e704b5113a1142e1` |
| raw boot image | `262e3683a891e85aa7eb670580651c34c2448cdf04ed75cdb1a58848ed66f045` |
| temporary-boot AVB image | `53d64ca611939516572bb79eb43008c5ff18857f4a4233177bdddef2dbe6d9f7` |

The GPUCC driver trace patch has SHA-256
`50ec8d394583951ab00e65c38686775031d0abadc6a3faf1730edda13eb7be94`.
The common-clock patch has SHA-256
`a6084f1b9f7d72fc984827a9f43559ef6a9a5cb3222a273775249924567f2df5`.
The pinned builder image was
`localhost/rog5-kernel-builder@sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c`.

Offline acceptance included:

- strict patch verification plus mutations for writable, broad,
  non-settling, incomplete, and hardware-changing variants;
- deterministic clean-source recreation and exact commit/tree checks;
- two byte-identical mainline builds and two byte-identical wrapper builds;
- all non-privileged shell tests and the pseudo-terminal ACM transport suite;
- the real-DTB deterministic mutation test;
- the privileged VPN/hotspot test in a pinned network-isolated container; and
- exact verification of all fifteen manifest entries.

## Live baseline

Before watchdog disarm, the target passed:

- exact Linux 7.1.4 and systemd diagnostic mode;
- exact opt-in trace command-line flag and read-only `Y` core parameter;
- running systemd, zero failed units, and zero fatal kernel signatures;
- OverlayFS `/`, exact read-only NFSv4.2 lower, and stable USB carrier;
- a complete read of all 1,008 files in the matching module tree;
- zero physical block devices and zero block-backed mounts;
- GPUCC `okay`, with every listed consumer and unrelated hardware disabled;
- no loaded GPUCC module and no DRM render node; and
- the original rollback watchdog present and armed.

The probe, watchdog-disarm helper, and module were copied only to target tmpfs
and matched their host hashes, ownership, and modes before execution.

The first fixed loader command was lost during staging ACM re-enumeration and
did not produce its required PASS marker. One immediate, idempotent retry of
that same fixed load action succeeded. The separate `execute` action was never
automatically retried. This is transport evidence, not a GPUCC result: the
current two-second stable-identity wait does not fully eliminate the staging
race and must be strengthened before another live diagnostic.

## Probe trace

The host received these ordered markers:

```text
ROG5 GPUCC diagnostic: begin
ROG5 GPUCC diagnostic: map-complete
ROG5 GPUCC diagnostic: pll0-begin
ROG5 GPUCC diagnostic: pll0-complete
ROG5 GPUCC diagnostic: pll1-begin
ROG5 GPUCC diagnostic: pll1-complete
ROG5 GPUCC diagnostic: registration-begin
ROG5 QCOM CC diagnostic: phase=entry index=-1 ret=0
ROG5 QCOM CC diagnostic: phase=allocation-complete index=-1 ret=0
ROG5 QCOM CC diagnostic: phase=power-domain-attach-begin index=-1 ret=0
ROG5 QCOM CC diagnostic: phase=power-domain-attach-complete index=-1 ret=0
ROG5 QCOM CC diagnostic: phase=reset-register-begin index=-1 ret=0
ROG5 QCOM CC diagnostic: phase=reset-register-complete index=-1 ret=0
ROG5 QCOM CC diagnostic: phase=gdsc-allocation-begin index=-1 ret=0
ROG5 QCOM CC diagnostic: phase=gdsc-allocation-complete index=-1 ret=0
ROG5 QCOM CC diagnostic: phase=gdsc-register-begin index=-1 ret=0
ROG5 QCOM CC diagnostic: phase=gdsc-register-complete index=-1 ret=0
ROG5 QCOM CC diagnostic: phase=gdsc-action-begin index=-1 ret=0
ROG5 QCOM CC diagnostic: phase=gdsc-action-complete index=-1 ret=0
ROG5 QCOM CC diagnostic: phase=drop-protected-begin index=-1 ret=0
ROG5 QCOM CC diagnostic: phase=drop-protected-complete index=-1 ret=0
ROG5 QCOM CC diagnostic: phase=clock-regmap-register-begin index=0 ret=0
```

No `clock-regmap-register-complete index=0`, provider-registration marker,
common-clock exit, GPUCC registration completion, or `insmod` return marker
reached the host. The independent watchdog then reset the phone.

Strict key-only SSH verified the exact persistent fallback kernel and ext4
root. Standard pstore was mounted read-only and contained zero retained
records, so no crash signature narrows the final sub-phase.

## Source localization

Clock binding ID 0 maps to `GPU_CC_AHB_CLK`, and array index 0 maps to
`gpu_cc_ahb_clk`. It is a `clk_branch2_ops` branch with halt/enable register
`0x1078`, one parent (`gpu_cc_hub_ahb_div_clk_src`, array index 17),
`CLK_SET_RATE_PARENT`, and no `CLK_IS_CRITICAL` flag.

The parent has not registered when index 0 is processed, so ordinary CCF
behavior is to register index 0 as an orphan and reparent it when index 17 is
later available. This index-0 clock has no registration-time `.init`,
`.get_parent`, `.get_phase`, or `.recalc_rate` callback. Because it is not
critical, ordinary registration also does not call its branch `.enable`
operation.

`devm_clk_register_regmap()` first assigns the provider regmap and then calls
`devm_clk_hw_register()`. That path allocates a managed resource and a
`clk_core`, populates the parent map, allocates its consumer handle, takes the
CCF prepare lock, conditionally obtains runtime PM, initializes parent/orphan
topology and the clock hash, derives phase/duty/rate, reparents existing
orphans, and finally registers debugfs state.

Therefore the trace proves a stall somewhere in that registration path but
does **not** prove that register `0x1078`, or any other GPUCC register, was
accessed. Runtime PM is also not yet a proven cause: the SM8350 GPUCC
descriptor omits `use_rpm`, while CCF's runtime-PM branch depends on the live
provider device state.

## Cleanup

The attended NFS process observed target departure and removed its export,
listener, bind mount, NFS threads, temporary sysctl, firewall rules, and
network-root address. The fallback profile is intentionally
non-autoconnecting, so the host reactivated that exact fallback USB profile
after cleanup.

Final checks passed:

- exact fallback kernel and strict SSH;
- zero Fastboot and ADB devices;
- inactive system NFS service and mount daemon;
- zero exports, NFS/mountd listeners, and NFS threads;
- no network-root bind mount, temporary firewall rule, or retained sysctl;
- clean drop zone, active ModemManager, and active firewalld;
- no temporary host sleep inhibitor; and
- zero retained pstore records or fatal signatures.

## Decision and next gate

GPUCC remains **rejected for normal coldplug**. V10 localizes the first
non-returning operation to registration of `gpu_cc_ahb_clk`, but it does not
establish a root cause and does not justify changing clock topology or
hardware state.

Before another live attempt:

1. strengthen and test idempotent recovery from a lost **load** marker without
   ever retrying `execute`;
2. add an exact-compatible, read-only, default-off trace around regmap lookup,
   devres allocation, `__clk_register()` allocation/parent-map setup,
   prepare-lock acquisition, runtime-PM get, parent/orphan/hash insertion,
   phase/duty/rate handling, orphan reparenting, debug registration, and
   return;
3. prove through source contracts and mutations that the trace adds no
   hardware, storage, or persistent-state operation;
4. produce two byte-identical clean kernel/module and wrapper/package builds;
   and
5. repeat the full zero-storage, independent-watchdog, fallback, and host
   cleanup gates.

No further live GPUCC probe is justified until that narrower candidate passes
every offline gate.

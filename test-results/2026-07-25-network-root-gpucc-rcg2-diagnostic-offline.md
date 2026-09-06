# Network-root v14 DISPCC RCG parent-read diagnostic — offline acceptance

Date: 2026-07-25

Result: **offline acceptance passed; no live GPU, GPUCC, DISPCC, or register
access claim**. Network-root v14 is eligible only for one later attended,
RAM-only diagnostic. The phone was not booted, rebooted, or otherwise touched
while this checkpoint was built. Nothing was flashed.

V13 proved that late GPUCC registration revisits the existing
`disp_cc_mdss_pclk0_clk_src` orphan while its DISPCC provider is
runtime-suspended, enters that clock's `get_parent()` callback, and does not
return. Source maps the callback to `clk_rcg2_get_parent()`, whose first
substantive operation is one existing `regmap_read()`. V14 adds two bounded
markers immediately around that read.

## Source identity and diagnostic boundary

The source chain starts at exact Linux commit
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`:

| Step | Commit or tree |
|---|---|
| GPUCC trace commit | `86f3c68a666446d9bbcb9bd9f90df50f989ba8ea` |
| Qualcomm common-clock trace commit | `d4bb00313e92514f89bc0a9e7a7dffcb4884834f` |
| generic CCF trace commit | `6eef0ab56609f5a5ee6d2de9807178daf1065fa7` |
| per-orphan trace commit | `b2059b161861d6d7d1aeb9b7d93ad86b13d85048` |
| inner-parent trace commit | `f7c0a9d067db77f05a40a5bc242c1e14ac297ac5` |
| RCG parent-read trace commit | `6e40861cc51c067f9989c4513003e8fbd046c22f` |
| final source tree | `49ef6cb95768496b8f926b11e428ea224406464e` |

The new patch is
`patches/linux-7.1.4/0010-clk-qcom-trace-attended-SM8350-DISPCC-RCG-parent-read.patch`,
with SHA-256
`ac7975bf5f4cb2791f45a2fe8b5b811c7e60fd4692f8aff4cd71a2f2150fa3c6`.
It changes only `drivers/clk/clk.c` and
`drivers/clk/qcom/clk-rcg2.c`, with 24 insertions and one deletion, and passes
strict `checkpatch.pl` with zero errors, warnings, or checks.

The exact default-off core parameter is `rog5_rcg2_parent_trace`, mode `0400`.
It can emit only for `disp_cc_mdss_pclk0_clk_src`, and only when the inherited
exact GPUCC/CCF trace gates and this new gate are all explicitly enabled for
the attended load. The two new phases are:

- `parent-read-begin`, immediately before the existing
  `regmap_read(rcg->clkr.regmap, RCG_CFG_OFFSET(rcg), &cfg)`; and
- `parent-read-complete`, immediately after that same read, carrying its
  return value.

Source and mutation contracts preserve exactly one existing read, its
arguments, order, error handling, and return behavior. They reject missing or
duplicated markers, broad RCG tracing, a second register access, runtime-PM
control, clock/reset/regulator/power-domain control, MMIO helpers, persistent
I/O, and changed callback behavior. Normal boot leaves the parameter off.

V14 reduces the inherited orphan trace limit from four entries to the two
already localized by v13. Two orphans at twenty 100 ms CCF markers plus the
two 100 ms RCG markers produce a 4.2-second maximum trace delay. The offline
budget combines a 20-second pre-scan allowance, 4.2-second trace bound,
30-second collection window, and 15-second forced-reset margin. The
69.2-second total leaves 5.8 seconds inside the independent 75-second
watchdog.

These markers intentionally perturb timing while CCF's global
`prepare_lock` can be held. V14 is diagnostic-only. It does not resume the
runtime-suspended DISPCC provider, change lock ordering, or implement a GPU
fix.

## Reproducible build and package

Two independently recreated source trees at the accepted commit and two empty
output trees were built with container networking disabled. Their configs,
Images, compressed Images, BTF-bearing `vmlinux` files, CCF and RCG2 objects,
symbol tables, modules, archives, and metadata are byte-identical. The
exported symbol table is also byte-identical to accepted v13.

Two credential-free staging initramfs builds are byte-identical. Two
independently exported ASUS 5.4 source trees then produced byte-identical
configs, embedded initramfs data, metadata, and wrapper Images. Two independent
header-v3/AVB repacks are also byte-identical.

The pinned builder was
`localhost/rog5-kernel-builder@sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c`.

| Artifact | SHA-256 |
|---|---|
| Linux 7.1.4 config | `68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f` |
| Linux 7.1.4 Image | `5759d3d15ca60f260aa89731aa78c94acd5d183eca67dc24c3723f8877f213e3` |
| Linux 7.1.4 Image.gz | `b0e722af9b3777a1f83e546991394026b8337ab5ec06f29f0b305e1eedf79e4b` |
| matching module archive | `9350e5a010c0af11fe4bde48527d056701c83a0072be4ad29cce2565a75204a1` |
| external `gpucc-sm8350.ko` | `9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a` |
| exported symbol table | `008919805fa413eefe4bb42675bcf6467a0a5bcef87158af05deec5e4cf75365` |
| modified CCF object | `116b4322fd0cc013cecc910a4b5443ce0881269ac581e60b13f9cbc4d0b47968` |
| modified RCG2 object | `28cf32faa79b9832337e036471b86b12b29a68d198a285fb88f6c6f2c4df48` |
| Linux build metadata | `beab68a7c0633e84ff5450860fe223ff3dbd85a9edc0023901c2eccbd720c4cc` |
| GPUCC-only DTB | `e6f86c3022f58a765351b5b761c8bc815b093209517adb4678107d542ff5bcb5` |
| target initramfs | `4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac` |
| nested staging initramfs | `eb5b173bb44707aa67c601150b8c40016bb20d277792926028c99ed97a066ee6` |
| ASUS wrapper config | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| ASUS wrapper Image | `8676bbc20e79febfdf38782582a2e3b4bcb7658ee6b49ea4c61df2b9db61b2d0` |
| ASUS wrapper metadata | `15e5723b2e2b86b0d907713f3953fb43e7156c96296b381377f5add183300393` |
| raw header-v3 boot image | `1aa1597c31fb390a62fa8727de0e9b17bfcd05f57df69f0c7d1a916f965b0528` |
| temporary-boot AVB image | `29c3f0e7516e3ef8f7141c527a269d668d53bd9097fbf7e11c507b64010b91b2` |
| fourteen-file manifest | `8628e2d29427135b14e83be0765f045a153fd4e244d4fccaadf7734145eed368` |

The GPUCC-only DTB, target initramfs, mainline config, exported symbol ABI, and
module-archive topology remain unchanged from v13. The matching mainline
Image, module archive, and split-BTF GPUCC module changed because the traced
kernel image and BTF type IDs changed.

## Offline acceptance

The checkpoint passes:

- exact patch, parent commit, final commit/tree, clean-source recreation,
  strict style, source-order, mutation, integration, and timing-budget checks;
- two byte-identical network-isolated mainline builds through BTF, modified
  objects, exported symbols, modules, archive topology, and metadata;
- unchanged exported symbol ABI and module topology versus v13;
- two byte-identical credential-free staging initramfs files, independently
  prepared ASUS wrappers, raw boot images, and AVB packages;
- an exact fourteen-file manifest plus separately pinned external module;
- semantic DT checks with GPUCC `okay` but GPU, GMU, Adreno SMMU, UFS, RTC,
  input, display consumers, and every remote processor disabled;
- absence of GPU firmware and `gpucc-sm8350.ko` from both initramfs archives;
- exact opt-in transport for all three trace flags, with none present in the
  Android boot-image command line; and
- header-v3 payload round-trip, unsigned AVB verification, zero credentials,
  no persistent-write path, and inherited rollback/storage gates.

The local accepted artifact directory remains ignored by Git. No kernel
binary, module, boot image, credential, proprietary firmware, or personal data
is committed.

## Safety and next gate

The AVB footer uses algorithm `NONE`. It is a deterministic temporary-boot
container, not a signed release and never a flash target. SCSI/UFS remains
compiled out of Linux 7.1.4, and the target exposes zero intended physical
storage.

Before one live v14 attempt, the host and phone must be re-audited from the
exact fallback. The attended run must retain the read-only NFS, zero-storage,
exact-DTB, stable-USB, clean-log, strict SSH, thermal, and complete host
cleanup gates. The original 900-second network-root watchdog must remain
armed until an independent 75-second process-group watchdog has been verified.
The byte-identical load action may be replayed at most once after a lost
marker; kexec execute remains one-shot.

Interpret only the first non-returning marker:

- `orphan-get-parent-begin` without `parent-read-begin` keeps the boundary
  before the read;
- `parent-read-begin` without `parent-read-complete` localizes the boundary
  to the existing regmap read but does not by itself prove a hardware fault;
  and
- `parent-read-complete` moves the investigation to the callback's remaining
  local processing and return path.

No source result authorizes a runtime resume under `prepare_lock`, skipping
the orphan scan, forcing a parent, or enabling GPU consumers. GPUCC, DRM/MSM,
A660 firmware, and accelerated desktop remain unaccepted until separately
validated.

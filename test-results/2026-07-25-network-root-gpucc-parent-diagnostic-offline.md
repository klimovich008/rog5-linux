# Network-root v13 GPUCC inner-parent diagnostic — offline acceptance

Date: 2026-07-25

Result: **offline acceptance passed; no live GPU or GPUCC claim**. Network-root
v13 is eligible only for one later attended, RAM-only diagnostic. The phone
was not booted, rebooted, or otherwise touched while this checkpoint was
built. Nothing was flashed.

V12 completed the newly registered `gpu_cc_ahb_clk` orphan, then stopped
inside `__clk_init_parent()` for the pre-existing
`disp_cc_mdss_pclk0_clk_src` orphan. The display RCG's `get_parent()` callback
precedes CCF's cached-parent lookup, but v12 could not distinguish those
operations. V13 adds six bounded markers around that exact inner sequence.

## Source identity and trace boundary

The source chain starts at exact Linux commit
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`:

| Step | Commit or tree |
|---|---|
| GPUCC trace commit | `86f3c68a666446d9bbcb9bd9f90df50f989ba8ea` |
| Qualcomm common-clock trace commit | `d4bb00313e92514f89bc0a9e7a7dffcb4884834f` |
| generic CCF trace commit | `6eef0ab56609f5a5ee6d2de9807178daf1065fa7` |
| per-orphan trace commit | `b2059b161861d6d7d1aeb9b7d93ad86b13d85048` |
| inner-parent trace commit | `f7c0a9d067db77f05a40a5bc242c1e14ac297ac5` |
| final source tree | `adec6b40ce25145e3e18cd82a788aa458514017d` |

The new patch is
`patches/linux-7.1.4/0009-clk-trace-attended-SM8350-GPUCC-orphan-parent-lookup.patch`,
with SHA-256
`6531645c80d9e07e40baf7d8af8ba6732f5ddfc75a3255a6dd75c8c3b8f7b5b5`.
It changes only `drivers/clk/clk.c`, with 59 insertions and 5 deletions, and
passes strict `checkpatch.pl`.

The existing exact-trigger and four-orphan limit remain unchanged. Normal CCF
initialization calls the helper with `NULL, false`, so it emits no new marker.
For one traced orphan, v13 adds:

- `orphan-parent-shape`, encoding
  `(num_parents << 1) | has_get_parent`;
- `orphan-runtime-state`, a read-only bitmask for provider presence,
  `rpm_enabled`, runtime-suspended, and runtime-active state;
- `orphan-get-parent-begin` and `orphan-get-parent-complete`, around the
  existing clock callback; and
- `orphan-parent-cache-begin` and `orphan-parent-cache-complete`, around the
  existing `clk_core_get_parent_by_index()` lookup.

Source contracts preserve exactly one `core->ops->get_parent(core->hw)` call
and one `clk_core_get_parent_by_index(core, index)` call in their original
order. The ordinary core-initialization assignment is split without changing
its right-associative result. The patch adds no clock, regulator, reset,
regmap, MMIO, runtime-PM control, persistent I/O, or early-return operation.
Mutation tests reject missing phases, broad tracing, duplicate callback/cache
lookups, runtime-PM control, and hardware control.

V12 contributes fourteen markers per traced orphan and v13 adds six. Four
orphans at twenty 100 ms markers produce an 8-second maximum trace delay. The
offline budget combines a 20-second pre-scan allowance, 8-second trace bound,
30-second collection window, and 15-second forced-reset margin. The 73-second
total leaves 2 seconds inside the independent 75-second watchdog.

The markers deliberately perturb timing while the global prepare lock can be
held. V13 is diagnostic-only and is not evidence of performance, latency,
stability, callback entry, or a register access until a live trace says so.

## Reproducible build and package

Two independently prepared Linux 7.1.4 source trees and two empty output
trees were built with container networking disabled. The complete configs,
BTF-bearing kernels, modified CCF objects, symbol tables, modules, archives,
and metadata are byte-identical.

Two credential-free staging initramfs builds are byte-identical. Two
independently prepared ASUS 5.4 source trees then produced byte-identical
configs, embedded initramfs data, metadata, and wrapper Images. Two corrected
header-v3/AVB repacks are also byte-identical. The first provisional repack
inherited an older timeout from the template and failed the generic bundle
assertion; it was not accepted. Both accepted repacks explicitly preserve the
reviewed 180-second staging timeout and pass the complete verifier.

The pinned builder was
`localhost/rog5-kernel-builder@sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c`.

| Artifact | SHA-256 |
|---|---|
| Linux 7.1.4 config | `68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f` |
| Linux 7.1.4 Image | `1c5c1bd3841c6fdc2f0ebc29fb19f43099e4d5e70d63d9a183cd9646f6c35c28` |
| Linux 7.1.4 Image.gz | `217f66c1370600542fe6a6b1349ae7e449bceade5ee64d56504e259ee76e0049` |
| matching module archive | `22d069c6d8bea928f5fac6ab3107bb007b2cb76fd95fc85541780cb5d315f199` |
| external `gpucc-sm8350.ko` | `574fefd282fbff6577c921a116a5485546e788ca338802b960b26b9ad9fc6d9c` |
| exported symbol table | `008919805fa413eefe4bb42675bcf6467a0a5bcef87158af05deec5e4cf75365` |
| modified CCF object | `53b960685d79f558f866674ff62325d2a0a20c28f2a39e9f104f5023c2087ddd` |
| Linux build metadata | `81d0aec7670f0127113d455fcae562a61d3d8750634f06fa126e4fc05ac951bd` |
| GPUCC-only DTB | `e6f86c3022f58a765351b5b761c8bc815b093209517adb4678107d542ff5bcb5` |
| target initramfs | `4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac` |
| nested staging initramfs | `0f311f92113f443df395e249f04109539038569e472c1379002a934e5aca8770` |
| ASUS wrapper config | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| ASUS wrapper Image | `99f197cd36a55dce7ae37670ec390cae83e16164ba4b8cac93ee672842b74e38` |
| ASUS wrapper metadata | `7c0b770e86c88f56472a7708ebf21afae3056dea1981df43b0b5db27618740f7` |
| raw header-v3 boot image | `c5ebd75037a4099ba396fb7ea98d84824461c6379986845c5c8b5acf684c9ca2` |
| temporary-boot AVB image | `8433036e89733427b53e33dba8e26b1999b11ef12cbb79433badebe2acc9bedf` |
| fourteen-file manifest | `4b332cb739dee1e4d3cb605f47fcf4dfae6978d25f70c329514b4093d1a14db7` |

The final `Module.symvers` is byte-identical to v12, so the trace changes no
exported kernel ABI. The GPUCC-only DTB, target initramfs, and mainline config
also remain unchanged. The external module binary changed because split BTF
links it against the changed `vmlinux` type IDs; the archive contains exactly
that matching module.

## Offline acceptance

The checkpoint passes:

- exact patch, parent commit, final commit/tree, clean-source recreation,
  strict style, source-order, mutation, and runtime-budget checks;
- two byte-identical network-isolated mainline builds, including BTF,
  modified objects, exported symbols, module topology, and metadata;
- unchanged exported symbol ABI versus v12;
- two byte-identical credential-free staging initramfs files, ASUS wrappers,
  corrected raw boot images, and AVB packages;
- the exact fourteen-file manifest and separately pinned external module;
- semantic DT checks with GPUCC `okay` but GPU, GMU, Adreno SMMU, UFS, RTC,
  input, display, and every remote processor disabled;
- absence of GPU firmware and `gpucc-sm8350.ko` from both initramfs archives;
- exact opt-in transport for the two existing trace flags, with neither flag
  present in the Android boot-image command line; and
- header-v3 payload round-trip, unsigned AVB verification, zero credentials,
  no persistent-write path, and inherited rollback/storage gates.

The local accepted artifact directory remains ignored by Git; no boot image,
kernel binary, module, credential, or proprietary firmware is committed.

## Safety and next gate

The AVB footer uses algorithm `NONE`. It is a deterministic temporary-boot
container, not a signed release and never a flash target. SCSI/UFS remains
compiled out of Linux 7.1.4, and the target exposes zero intended physical
storage.

Before one live v13 attempt, the host and phone must be re-audited from the
exact fallback. The attended run must retain the read-only NFS, zero-storage,
exact-DTB, stable-USB, clean-log, strict SSH, thermal, and complete host
cleanup gates. The original 900-second network-root watchdog must remain
armed until an independent 75-second process-group watchdog has been verified.
The byte-identical load action may be replayed at most once after a lost
marker; kexec execute remains one-shot.

Only the first non-returning inner marker may guide the next source decision.
Until that live result passes rollback and cleanup, GPUCC, DRM/MSM, A660
firmware, and accelerated desktop remain unaccepted.

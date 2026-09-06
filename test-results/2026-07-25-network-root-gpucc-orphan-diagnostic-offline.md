# Network-root v12 GPUCC orphan diagnostic — offline acceptance

Date: 2026-07-25

Result: **offline acceptance passed; no live GPU or GPUCC claim**. Network-root
v12 is eligible only for one later attended, RAM-only diagnostic. The phone
was not booted, rebooted, or otherwise touched while this checkpoint was
built. Nothing was flashed.

V11 completed registration of non-critical index-0 `gpu_cc_ahb_clk` through
orphan insertion, phase, duty, and rate handling, then stopped after
`orphan-reparent-begin`. The generic orphan scan can inspect and invoke
callbacks for clocks unrelated to GPUCC, so that result did not prove direct
GPUCC MMIO. V12 adds a bounded per-orphan trace around parent resolution and
the existing reparent/recalculation operations.

## Source identity and trace boundary

The source chain starts at exact Linux commit
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` and applies the existing GPUCC,
Qualcomm common-clock, and generic CCF traces before the new patch:

| Step | Commit or tree |
|---|---|
| GPUCC trace commit | `86f3c68a666446d9bbcb9bd9f90df50f989ba8ea` |
| Qualcomm common-clock trace commit | `d4bb00313e92514f89bc0a9e7a7dffcb4884834f` |
| generic CCF trace commit | `6eef0ab56609f5a5ee6d2de9807178daf1065fa7` |
| per-orphan trace commit | `b2059b161861d6d7d1aeb9b7d93ad86b13d85048` |
| final source tree | `040d5f9b7be022489079b2ea9cab20a04934d85f` |

The new patch is
`patches/linux-7.1.4/0008-clk-trace-attended-SM8350-GPUCC-orphan-reparent.patch`,
with SHA-256
`bc026e783fe3b7f1f15cb0e3ac6ca914d4b45897da07db0f887565b1722172e6`.
It changes only `drivers/clk/clk.c`, with 82 insertions and 4 deletions, and
passes strict `checkpatch.pl`.

The patch reuses the read-only, default-off `rog5_ccf_register_trace`
parameter. The registration call passes the exact SM8350 GPUCC trigger;
provider-wide orphan scans pass `NULL` and therefore emit no per-orphan
diagnostic. At most the first four orphan entries are traced. Each entry has at
most fourteen 100 ms delivery markers:

- scan entry and completion;
- parent lookup begin, completion, and resolved-parent state;
- `__clk_set_parent_before()` begin and completion;
- `__clk_set_parent_after()` begin and completion;
- accuracy recalculation begin and completion;
- rate recalculation begin and completion; and
- requested-rate assignment completion.

The maximum added trace delay is therefore 5.6 seconds. The offline budget
fixture combines a 20-second pre-scan allowance, that 5.6-second trace bound,
a 30-second collection window, and a 15-second forced-reset margin. The
70.6-second total remains inside the independent 75-second live watchdog.

Source contracts compare the original and instrumented function and preserve
exactly one list walk, parent lookup, before/after reparent callback,
accuracy recalculation, rate recalculation, and requested-rate assignment, in
the same order. No `break`, `continue`, or early return is added. Mutation
tests reject a 64-entry limit, broad trace gate, missing runtime bound,
missing phase, duplicate registration trigger, provider-triggered trace, and
hardware-control additions. The complete modified `drivers/clk/clk.o` also
compiled successfully before the release builds.

The markers deliberately perturb timing while the global prepare lock can be
held. V12 is diagnostic-only and is not evidence of performance, latency, or
stability.

## Reproducible build and package

Two independently prepared Linux 7.1.4 source trees and two empty output
trees were built with container networking disabled. The complete configs,
BTF-bearing kernels, modified CCF objects, symbol tables, modules, archives,
and metadata are byte-identical.

Two credential-free staging initramfs builds are byte-identical. Two
independent prepared ASUS 5.4 source trees then produced byte-identical
configs, embedded initramfs data, metadata, and wrapper Images. Two
header-v3/AVB repacks are also byte-identical.

The pinned builder was
`localhost/rog5-kernel-builder@sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c`.

| Artifact | SHA-256 |
|---|---|
| Linux 7.1.4 config | `68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f` |
| Linux 7.1.4 Image | `49318395c5ed4850d492e4f29ea841885692bd96b6a5b0982925769282b687d9` |
| Linux 7.1.4 Image.gz | `193fc0cafc285bab4ff065c0be624aa11b768ad43685b4605e2a0bcfb96b0bf4` |
| matching module archive | `2c246d8ceed3c37cc2afefa56710ac5bbca2bc1bce0ca0409a361f8f5923a2e8` |
| external `gpucc-sm8350.ko` | `79a7d3b7d81c28821dd5199cdbcfe9b2cea5b8bc59b6d6e983a61a15f05424ba` |
| exported symbol table | `008919805fa413eefe4bb42675bcf6467a0a5bcef87158af05deec5e4cf75365` |
| modified CCF object | `222139326edb85a0dcd3fbf5cdb2c48dabc7b655db0cb1de5ff0c0b292f17d0b` |
| Linux build metadata | `cec539df7e467df74703cde7514649d45e13b7a903d97bd4300cace2da3decb4` |
| GPUCC-only DTB | `e6f86c3022f58a765351b5b761c8bc815b093209517adb4678107d542ff5bcb5` |
| target initramfs | `4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac` |
| nested staging initramfs | `204c0403005dac69fe6b153a41ee69498265afafcbefcb6019c9b15e6263889a` |
| ASUS wrapper config | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| ASUS wrapper Image | `5edd63574f6762380d63665bff5ca1cd29dd868dc4a6dd34b5ebfd6c91c6aab9` |
| ASUS wrapper metadata | `80ccac0cd07f4c260d0d61d80db947d44ab149ccbb19b33fc4a4a335eaff8b8a` |
| raw header-v3 boot image | `97952efb30b3dd037b2179c9079ca31561ff02d31a167d29436025419f2a246e` |
| temporary-boot AVB image | `4cbf626756d8b0ef390c7a915539fb59863a3d6152d2ba9daa0cec5ab5f6c8df` |
| fourteen-file manifest | `234f8ab909fd8804cf400a3aa1fb8a88e6633047b7680ba331ac308019a3ec04` |

The final `Module.symvers` is byte-identical to v11, so the trace changes no
exported kernel ABI. The GPUCC-only DTB, target initramfs, and mainline config
also remain unchanged. The external module binary changed even though its
driver source did not: split BTF links it against the changed `vmlinux` type
IDs. The archive contains exactly that matching module.

## Offline acceptance

The checkpoint passes:

- exact patch, parent commit, final commit/tree, clean-source recreation,
  strict style, source-order, mutation, and runtime-budget checks;
- two byte-identical network-isolated mainline builds, including BTF,
  modified objects, exported symbols, module topology, and metadata;
- unchanged exported symbol ABI versus v11;
- two byte-identical credential-free staging initramfs files, ASUS wrappers,
  raw boot images, and AVB packages;
- the exact fourteen-file manifest and separately pinned external module;
- semantic DT checks with GPUCC `okay` but GPU, GMU, Adreno SMMU, UFS, RTC,
  input, display, and every remote processor disabled;
- absence of GPU firmware and `gpucc-sm8350.ko` from both initramfs archives;
- exact opt-in transport for the two existing trace flags, with neither flag
  present in the Android boot-image command line; and
- header-v3 payload round-trip, unsigned AVB verification, zero credentials,
  no persistent-write path, and the inherited rollback/storage gates.

The local accepted artifact directory remains ignored by Git; no boot image,
kernel binary, module, credential, or proprietary firmware is committed.

## Safety and next gate

The AVB footer uses algorithm `NONE`. It is a deterministic temporary-boot
container, not a signed release and never a flash target. SCSI/UFS remains
compiled out of Linux 7.1.4, and the target exposes zero intended physical
storage.

Before one live v12 attempt, the host and phone must be re-audited from the
exact fallback. The attended run must retain the read-only NFS, zero-storage,
exact-DTB, stable-USB, clean-log, strict SSH, thermal, and complete host
cleanup gates. The original 900-second network-root watchdog must remain
armed until an independent 75-second process-group watchdog has been verified.
The byte-identical load action may be replayed at most once after a lost
marker; kexec execute remains one-shot.

Only the first non-returning per-orphan marker may guide the next source
decision. Until that live result passes rollback and cleanup, GPUCC, DRM/MSM,
A660 firmware, and accelerated desktop remain unaccepted.

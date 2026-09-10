# Network-root v15 CCF orphan runtime-PM candidate — offline acceptance

Date: 2026-07-25

Result: **offline acceptance passed; no live GPU, GPUCC, DISPCC, runtime-PM,
or register-access success claim**. Network-root v15 is eligible only for one
attended, RAM-only, zero-storage probe. The phone was not booted, rebooted, or
otherwise touched while this checkpoint was designed, tested, built, and
packaged. Nothing was flashed.

V14 localized late GPUCC registration's first non-returning operation to the
existing `regmap_read()` in `clk_rcg2_get_parent()` for the pre-existing
`disp_cc_mdss_pclk0_clk_src` orphan. Its DISPCC provider was
runtime-PM-enabled and suspended. The global CCF orphan scan ran beneath
`prepare_lock`, so directly resuming that provider at the read site would
introduce an ABBA lock-order risk when a provider resume callback needs the
same lock. V15 tests a general CCF ordering candidate instead: hold temporary
runtime-PM references for registered clock-provider devices before taking
`prepare_lock`, run the unchanged orphan scan, unlock, and then release the
references.

## Source identity and candidate boundary

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
| runtime-PM candidate commit | `d9ac316489f4258d389d6298659d5e9c22183400` |
| final source tree | `c796deb1cc54e942f8bb46a2c76a7199e19e5c92` |

The new patch is
`patches/linux-7.1.4/0011-clk-guard-orphan-reparent-with-runtime-PM.patch`,
with SHA-256
`a309fe55dc6221f4475c22beb43018dde0f2eb107fa60e84f8e43f28e17a4a25`.
It changes only `drivers/clk/clk.c`, with 33 insertions and 14 deletions.

The candidate is an **experimental partial backport**, not an accepted
upstream fix. It follows the relevant ordering proposed in Miquel Raynal's
March 2025 CCF runtime-PM RFC:

- [move all-provider runtime-PM acquisition outside `prepare_lock`](https://www.spinics.net/lists/linux-clk/msg111885.html);
- [guard both OF provider orphan scans](https://www.spinics.net/lists/linux-clk/msg111883.html); and
- [upstream review discussion](https://www.spinics.net/lists/linux-clk/msg112623.html).

The exact behavioral change is limited to three existing orphan-reparent
paths:

1. `__clk_core_init()` calls `clk_pm_runtime_get_all()` before
   `clk_prepare_lock()`, keeps the existing orphan scan beneath that lock,
   unlocks, and then calls `clk_pm_runtime_put_all()`.
2. `of_clk_add_provider()` holds the same all-provider references across its
   existing orphan scan.
3. `of_clk_add_hw_provider()` does the same.

An all-provider acquisition failure returns before taking `prepare_lock`. In
the two OF registration paths, the just-added provider is removed on that
failure. Every successful acquisition has exactly one release.

V15 deliberately does not add a direct runtime-PM call at the display RCG,
device-specific code, a forced parent, an orphan skip, a new register access,
or any regulator, reset, power-domain, interconnect, MMIO, DT, storage, GPU,
or display-consumer change. The v14 tracing remains default-off. Four new
exact-trace phases bracket the generic all-provider calls:

- `runtime-get-all-begin`;
- `runtime-get-all-complete`;
- `runtime-put-all-begin`; and
- `runtime-put-all-complete`.

## Test-first ordering proof

The source contract was first run without the candidate patch and failed as
intended. After implementation, the complete focused suite passed:

- an exhaustive standard-library finite-state model of the CCF prepare lock,
  runtime-PM provider list lock, provider callback, and orphan scan;
- deterministic source and integration contracts for all three changed
  paths;
- patch verification against the exact v14 parent source;
- mutation tests that reject the old ordering, acquiring references beneath
  `prepare_lock`, releasing them before unlock, missing releases, omitted OF
  paths, skipped orphan scans, device-specific branches, direct runtime-PM
  calls, and extra regmap operations; and
- exact build and complete bundle verifier contracts.

In the model, both the old order and the
all-provider-get-beneath-`prepare_lock` mutation reach the modeled ABBA
deadlock. A release-before-unlock/missing-release mutation leaks or violates
the provider-list lock state. The candidate ordering for core registration
and both OF paths reaches neither modeled deadlock nor reference leak.

The clock KUnit suite also passes in the pinned rootless builder:

| KUnit result | Count |
|---|---:|
| total tests | 118 |
| passed | 114 |
| pre-existing skips | 4 |
| failed | 0 |

This finite-state and KUnit evidence proves the encoded source/locking
contract, not that every real provider callback or hardware interaction is
safe.

## Reproducible build and package

Two independently prepared source trees at the exact candidate commit and two
empty ARM64 output trees were built in the pinned rootless container with
networking disabled. Different host parallelism settings were used. Their
configs, Images, compressed Images, BTF-bearing `vmlinux` files,
`System.map`, `Module.symvers`, CCF/QCOM objects, GPUCC module, complete
module archives, and metadata are byte-identical.

The pinned builder was
`localhost/rog5-kernel-builder@sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c`.

| Mainline artifact | SHA-256 |
|---|---|
| Linux 7.1.4 config | `68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f` |
| Linux 7.1.4 Image | `d30df38804750ded48607135a7d23d4f95e0947c49b68395a8f6818c4a27c54b` |
| Linux 7.1.4 Image.gz | `a620dd40df6d495e00a8f7f84e707c9ceb7483f0828afb2372792985e69f008e` |
| matching module archive | `9350e5a010c0af11fe4bde48527d056701c83a0072be4ad29cce2565a75204a1` |
| external `gpucc-sm8350.ko` | `9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a` |
| exported symbol table | `008919805fa413eefe4bb42675bcf6467a0a5bcef87158af05deec5e4cf75365` |
| modified CCF object | `96b4831bbaabe996c950a31907039e5374547069ec502ce08a8056b9a5bdf193` |
| unchanged RCG2 object | `28cf32faa79b9832337e036471b86b12b29a68d198a285fb88f6c6b6f2c4df48` |
| Linux build metadata | `21deef91a5fc0864b9c43389cec6ea0f326e1f68e47265f2514986f2f13712f1` |

The module archive, split-BTF GPUCC module, exported symbol table, and RCG2
object are byte-identical to accepted v14. Only the mainline Image and generic
CCF object changed. This preserves the tested module ABI and isolates the
candidate to generic CCF behavior.

Two credential-free staging initramfs builds are byte-identical. Two
independently prepared ASUS 5.4.210 source trees then produced byte-identical
configs, embedded initramfs data, metadata, and wrapper Images. Two
independent header-v3 and AVB repacks are also byte-identical.

| Nested/package artifact | SHA-256 |
|---|---|
| GPUCC-only DTB | `e6f86c3022f58a765351b5b761c8bc815b093209517adb4678107d542ff5bcb5` |
| target initramfs | `4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac` |
| nested staging initramfs | `68b8729c5aef7f9a3eacba07685fe952f4df6cac29eb8c35d9559fda98722fab` |
| ASUS wrapper config | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| ASUS wrapper Image | `bf4abdad89941b34f769af25f80d8b93ac202a77c31005d572bc559255d61b7e` |
| ASUS wrapper metadata | `6d4fb05543baf583fec25cc152fcbab5b1cc59325f2d417687bab292cb27aaa3` |
| raw header-v3 boot image | `392ee5b0aa674f95da1b2dd544d25aab8d201f8d5a310fda2c8ab805fc1a6793` |
| temporary-boot AVB image | `bb4a6e34c98475f991a9575defe57c52ac732da0cea96a10585ee0bb92ae7730` |
| fourteen-file manifest | `a739f975f87ac30918625178007b4cd7302449ae96c26e5c42185e9e1a0425cc` |

The first copied package intentionally failed the exact verifier because its
embedded stage still carried the v14 mainline Image. It was rejected and
replaced by the two independently rebuilt, byte-identical v15 paths above.
This is evidence that the nested-payload verifier detects a stale inner
kernel rather than accepting only a changed outer manifest.

## Offline acceptance

The checkpoint passes:

- red/green source-contract execution plus exhaustive lock-state,
  source-order, integration, mutation, and exact-patch tests;
- deterministic source recreation at the exact commit and tree;
- 118 clock KUnit tests with zero failures;
- two byte-identical network-isolated ARM64 builds through BTF, symbols,
  CCF/QCOM objects, modules, archives, and metadata;
- unchanged exported symbol ABI, module archive, GPUCC module, and RCG2 object
  versus accepted v14;
- two byte-identical credential-free nested staging archives, independently
  prepared ASUS wrappers, raw boot images, and AVB packages;
- exact fourteen-file manifest and nested-mainline-payload verification;
- semantic DT checks with GPUCC `okay` but GPU, GMU, Adreno SMMU, UFS, RTC,
  input, display consumers, and every remote processor disabled;
- absence of GPU firmware and `gpucc-sm8350.ko` from both initramfs archives;
- default-off transport for all trace parameters, with none present in the
  Android boot-image command line; and
- header-v3 payload round-trip, unsigned AVB verification, zero credentials,
  no persistent-write path, and inherited rollback/storage gates.

The accepted artifact directory remains ignored by Git. No kernel binary,
module, boot image, credential, proprietary firmware, private identifier, or
personal data is committed.

## Residual risk and one-shot live gate

The RFC remains unmerged and experimental. `clk_pm_runtime_get_all()` resumes
every registered runtime-PM clock-provider device and holds
`clk_rpm_list_lock` while doing so. That is wider and potentially more
expensive than the one suspended DISPCC provider implicated by v14. The
finite-state model cannot enumerate arbitrary provider callbacks, external
subsystem locks, firmware latency, or hardware faults. V15 therefore receives
only one attended diagnostic attempt, not normal coldplug acceptance.

The AVB footer uses algorithm `NONE`. It is a deterministic temporary-boot
container, not a signed release and never a flash target. SCSI/UFS remains
compiled out of Linux 7.1.4, and the target exposes zero intended physical
storage.

Before the one live attempt, the host and phone must be re-audited from the
exact persistent fallback. The attended run must retain the read-only NFS,
zero-storage, exact-DTB, stable-USB, clean-log, strict SSH, thermal, and
complete host-cleanup gates. The original 900-second network-root watchdog
must remain armed until an independent 75-second process-group watchdog has
been verified. Kexec execute remains one-shot. V14 must not be rerun.

Interpret the single v15 outcome as follows:

- if GPUCC module registration/probe returns, the result supports the
  lock/runtime-PM hypothesis; first prove exact fallback and complete cleanup,
  then repeat only the ordinary baseline gates before considering later,
  separately isolated GPU tiers;
- if a new marker or error is the first non-returning boundary, record it and
  do not retry this candidate; or
- if transport or collection fails independently of the candidate, let the
  watchdog restore the exact fallback and treat the attempt as consumed
  unless the one-shot procedure itself proves execute never occurred.

No v15 result by itself accepts DRM/MSM, A660 firmware, accelerated graphics,
normal GPUCC coldplug, persistent boot, or desktop use.

# Network-root v11 GPUCC generic CCF diagnostic — offline acceptance

Date: 2026-07-25

Result: **offline acceptance passed; no live GPU or GPUCC claim**. Network-root
v11 is eligible only for a later attended, RAM-only diagnostic. The phone was
not booted, rebooted, or otherwise touched while this checkpoint was built.
Nothing was flashed.

V10 stopped after
`clock-regmap-register-begin index=0 ret=0`, while registering the
non-critical `gpu_cc_ahb_clk`. V11 adds a default-off trace around the
Qualcomm regmap wrapper and generic common-clock-framework registration path
needed to localize that one non-returning call. GPUCC remains rejected for
normal coldplug.

## Source identity and trace boundary

The source chain starts at exact Linux commit
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`. Applying the existing GPUCC
driver trace and Qualcomm common-clock trace, followed by the v11 generic CCF
trace, produces:

| Step | Commit or tree |
|---|---|
| GPUCC trace commit | `86f3c68a666446d9bbcb9bd9f90df50f989ba8ea` |
| Qualcomm common-clock trace commit | `d4bb00313e92514f89bc0a9e7a7dffcb4884834f` |
| generic CCF trace commit | `6eef0ab56609f5a5ee6d2de9807178daf1065fa7` |
| final source tree | `743a976fd13c1a5c30d93c7dac9b9b4d1cbc3b11` |

The new patch is
`patches/linux-7.1.4/0007-clk-trace-attended-SM8350-GPUCC-CCF-registration.patch`,
with SHA-256
`5f0be38bf3773f0cc541d7a52f930bc05dc979ee1a086198f3148aa14552dbc9`.
It changes four files with 173 insertions and 9 deletions and passes strict
`checkpatch.pl`.

The `rog5_ccf_register_trace` core parameter is boolean, read-only (`0400`),
and default-off. Every marker is additionally gated to the exact
`qcom,sm8350-gpucc` compatible. The patch emits:

- 63 boundaries through managed-resource allocation, `__clk_register()`,
  `__clk_core_init()`, prepare locking, runtime PM, duplicate/ops checks,
  parent/orphan/hash topology, phase/duty/rate, critical handling, orphan
  reparenting, unlock, debug registration, and return; and
- 9 Qualcomm regmap-wrapper boundaries for device/parent regmap lookup and the
  managed CCF call.

The existing 23 coarse Qualcomm probe phases and the GPUCC module trace remain
present. Every v11 marker has a 100 ms delivery settle. This delay can hold or
extend the CCF prepare-lock interval by several seconds for one clock and is
deliberately timing-perturbing. The candidate is diagnostic-only and must not
be used as a performance, latency, or stability result.

The source contracts compare the original and instrumented functions and
require the same exact single-call counts for `__clk_core_init()`,
`clk_prepare_lock()`, `clk_pm_runtime_get()`, orphan reparenting, debug
registration, devres allocation/commit, regmap lookup, and the managed clock
registration calls. The patch adds no clock enable, register write/update,
reset, regulator, power-domain action, storage operation, mount, or persistent
state change. Mutation tests reject writable, broad, non-settling, incomplete,
duplicate-call, and hardware-changing variants.

Some `ret` fields intentionally encode live state rather than an error:
runtime-PM enabled, parent-present, and orphan-state markers use `0` or `1`.
Also, `clk_core_reparent_orphans_nolock()` may invoke already existing
callbacks for other orphan clocks. Bracketing that function localizes the CCF
phase; it does **not** prove a direct GPUCC MMIO access.

## Transport hardening

The staging loader now transports both opt-in parameters:

- `rog5_qcom_cc_probe_trace=1`
- `rog5_ccf_register_trace=1`

Neither parameter appears in the temporary Android boot image command line,
and neither is added by the normal loader path. The fixed
`load-gpucc-diagnostic` action enables both only when explicitly selected.

The ACM helper now treats a missing PASS marker as a bounded staging
re-enumeration failure. For a fixed idempotent load action, it rediscovers a
stable ACM endpoint and retries the **same byte-identical action exactly
once**. A second missing marker fails. The `execute` action is never retried.
Nine Python tests pass, including mocked one-retry/bounded-failure cases,
one-shot execute, and a real two-pseudo-terminal test in which the first
endpoint drops and the second receives the byte-identical load command.

This is transport hardening only. It does not establish a GPUCC result and
does not make kexec execution idempotent.

## Reproducible build and package

Two clean Linux 7.1.4 source volumes and two empty output volumes were built
with container networking disabled. Two independently prepared ASUS source
volumes and two empty wrapper output volumes were then built the same way.
The target initramfs, GPUCC-only DTB, nested staging initramfs, Linux kernel
and modules, ASUS wrapper, header-v3 image, and AVB package all match
byte-for-byte between the two paths.

The pinned builder was
`localhost/rog5-kernel-builder@sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c`.

| Artifact | SHA-256 |
|---|---|
| Linux 7.1.4 config | `68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f` |
| Linux 7.1.4 Image | `d6bb0a9a7c4d4496aac8593df1727c916f130a10741b2691eebbf28555527021` |
| Linux 7.1.4 Image.gz | `f4138e28b224423eaf0de334344fead6204ac9a0f141dbd8d8f0652d493c73ac` |
| matching module archive | `b1c2bd02d67773e2b213c8aec2e30378580f8bcc638ff378650182a335f6f5d0` |
| external `gpucc-sm8350.ko` | `3c663bed417bb3bd7438b422ebf3531eca48e53afebc66a4574c7d87f7a8f421` |
| exported symbol table | `008919805fa413eefe4bb42675bcf6467a0a5bcef87158af05deec5e4cf75365` |
| Linux build metadata | `f0bce6e0a4611c7a7de328fc687bc7453dcf669da8782ef50bfdde05809ded6c` |
| GPUCC-only DTB | `e6f86c3022f58a765351b5b761c8bc815b093209517adb4678107d542ff5bcb5` |
| target initramfs | `4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac` |
| nested staging initramfs | `1d84c11edf9867d59dd473c0a958514e33b1f071a36cdda2f6ac39c2d5d48a7d` |
| ASUS wrapper Image | `1ea673e292447e4f03dceb43f8b1d19dd06c6382b279a950fa990f7a4c5fb7b0` |
| ASUS wrapper metadata | `cd0c821420f4923ecd0c5a8184d96780f0c05493f60cd80caaed513b8a181cd9` |
| raw header-v3 boot image | `3974476d879e1fa41296e64390324f959043fcd771bea5e166be93bff0796b95` |
| temporary-boot AVB image | `ed80c46e4d23caa258d3ef07ffddad254d9cba461165751e55476864044fdc42` |

The final `Module.symvers` hash is identical to v10, proving that the v11
trace adds no exported kernel ABI. The target initramfs and GPUCC-only DTB
also remain byte-identical to v10. The staging initramfs, wrapper, and package
change only because they carry the new Linux image and dual-trace loader.

During source review, two earlier output builds were stopped after a rendered
diff made the already single `__clk_core_init()` call appear duplicated.
Inspection of the raw patch and applied source proved there was exactly one
call. Those output volumes were discarded and recreated empty; all hashes
above come only from the final two fresh builds. The verifier and mutation
suite now assert the exact single-call count explicitly.

## Offline acceptance

The checkpoint passes:

- exact patch hashes, parent commits, final tree, clean-source recreation, and
  strict patch/style checks;
- deterministic source contracts and mutation rejection;
- two byte-identical clean mainline builds, including modified clock objects,
  final images, modules, metadata, BTF module, and module topology;
- unchanged exported symbol ABI versus v10;
- two byte-identical credential-free staging initramfs files, ASUS wrapper
  builds, raw boot images, and AVB packages;
- the fourteen-file base manifest plus the separately pinned external module;
- semantic DT checks with GPUCC `okay` but GPU, GMU, Adreno SMMU, display,
  UFS, RTC, input, and every remote processor still disabled;
- absence of GPU firmware and `gpucc-sm8350.ko` from both initramfs archives;
- all normal shell/source tests, the real-DTB mutation test, and shell syntax
  checks;
- all nine ACM pseudo-terminal/unit tests; and
- the privileged fail-closed VPN/hotspot test in a pinned, network-isolated
  container.

The dedicated verifier pins every final artifact hash, all 72 new generic and
wrapper CCF phase strings, both opt-in loader flags, the exact DT state,
matching split-BTF module, and absence of a persistent-write path.

## Safety and next gate

The bundle contains no SSH key, host key, credential, personal data,
proprietary GPU firmware, or persistent-storage payload. SCSI/UFS remains
compiled out of Linux 7.1.4, and the target exposes zero intended physical
storage. The AVB footer uses algorithm `NONE`; it is a deterministic
temporary-boot container, not a signed release and never a flash target.

Before a live v11 attempt, the host and phone must be re-audited from the exact
persistent fallback. The later test must retain the full read-only NFS,
zero-storage, exact-DTB, stable-USB, clean-log, independent SysRq watchdog,
strict fallback SSH, and complete host-cleanup gates used by v10. The two load
flags may be sent once through the bounded idempotent load action; kexec
`execute` remains one-shot.

Only the first non-returning v11 marker may guide the next source decision.
Until that live result passes rollback and cleanup, GPUCC, DRM/MSM, A660
firmware, and accelerated desktop remain unaccepted.

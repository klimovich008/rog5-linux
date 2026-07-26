# A660 first-open firmware-only boundary — offline source acceptance

Date: 2026-07-26

Result: **the exact Linux 7.1.4 source has a narrow seam that can request the
reviewed A660 SQE and GMU firmware, then deliberately reject the first DRM
open before ucode mapping, runtime power, GPU hardware initialization, GMU
firmware/HFI startup, or ZAP/SCM authentication**. No diagnostic kernel has
been patched or built yet. The phone was not contacted, NFS stayed inactive,
and nothing was flashed.

This acceptance corrects the earlier shorthand “firmware provisioning without
DRM open.” Copying firmware files into a root filesystem causes no kernel
request. In the pinned driver, `msm_open()` is the only lazy entry into
`load_gpu(dev)`, so a live request test necessarily attempts an open. The safe
diagnostic must make that open fail before a file context or descriptor can
exist.

## Exact accepted inputs

The source is clean Linux commit
`d9ac316489f4258d389d6298659d5e9c22183400`, tree
`c796deb1cc54e942f8bb46a2c76a7199e19e5c92`. The verifier pins the exact
MSM/Adreno driver files, A6xx catalog, A6xx GPU and GMU paths, SM8350 DTS, and
HDK firmware override.

This tier inherits the consumed A660 registration v3 live acceptance:

- report SHA-256
  `2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79`;
- marker SHA-256
  `8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f`;
- one unopened headless render node, two IOMMU attachments, zero firmware
  requests, zero DRM descriptors, zero storage/display activity, exact
  fallback, and complete cleanup.

The reviewed local firmware inputs remain:

| Firmware | Size | SHA-256 | v4 target policy |
|---|---:|---|---|
| `qcom/a660_sqe.fw` | 43,292 | `d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76` | install mode `0644`; request exactly once |
| `qcom/a660_gmu.bin` | 55,252 | `8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7` | install mode `0644`; request exactly once |
| `qcom/sm8350/a660_zap.mbn` | 1,054,648 | `5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d` | keep host-side; do not place in v4 target |

The input firmware files currently have permissive artifact modes. A future
export builder must use `install -m 0644`; it must never preserve those input
modes.

## Proven source order

The verifier proves the exact definition-plus-call counts and this order:

1. `msm_open()` calls `load_gpu(dev)` before `context_init()`.
2. `load_gpu()` calls `adreno_load_gpu(dev)`.
3. `adreno_load_gpu()` calls `adreno_load_fw(adreno_gpu)`.
4. The A660.1 catalog contains exactly `a660_sqe.fw` and `a660_gmu.bin`.
5. `adreno_load_fw()` only requests and retains those firmware objects.
6. Only afterward can `ucode_load`, `pm_runtime_enable`,
   `pm_runtime_get_sync`, and `msm_gpu_hw_init` run.
7. GMU firmware start and HFI are behind the later runtime-resume path.
8. ZAP loading and `qcom_scm_pas_auth_and_reset()` are behind later hardware
   initialization.

Therefore a small diagnostic branch immediately after successful
`adreno_load_fw()` can return a fixed error without reaching a GPU/GMU power
or hardware boundary. This is a source-level design proof, not yet a live
result.

## Required v4 diagnostic design

The smallest acceptable patch will:

- add one read-only module parameter, disabled by default and enabled only at
  `msm.ko` insertion;
- expose one helper that resolves the already registered A660 device and calls
  only `adreno_load_fw()`;
- consume at most one open attempt atomically;
- return a fixed error after both requests succeed, before `context_init()`;
- return the real firmware error on request failure, with no retry;
- leave `priv->gpu` unset and create no persistent DRM descriptor;
- emit bounded, exact success/failure markers suitable for a strict gate; and
- preserve normal upstream behavior byte-for-byte when the parameter is off.

The v4 export will contain only the exact SQE and GMU files. ZAP firmware must
remain absent so this tier cannot accidentally satisfy a later secure-world
path. The target gate must begin from the accepted v3 baseline, verify no DRM
descriptor, invoke one tiny open helper once, require the expected failed-open
error and two exact firmware loads, and reject ucode, power, HFI, ZAP/SCM,
fault, storage, mount, display, or second-open evidence. Independent watchdog,
immediate normal reboot, exact fallback, full host cleanup, private evidence,
and consumed-root lockout remain mandatory.

Nothing in this report authorizes a live cycle. Source mutation tests, two
clean kernel/module builds, two sanitized exports, duplicate stages/wrappers/
temporary-boot packages, and a complete one-shot host/target gate must pass
before deciding whether to run v4.

## Test-first evidence

Commit `bd81b3f2bf3d7da0fe607a64977cfaa2e6b1fe08` records the fail-first
contract. Before the verifier existed it returned exactly:

`FAIL missing executable A660 firmware-only boundary verifier`

The implemented verifier and wrapper test now return:

`PASS firmware request can be isolated before ucode, runtime power, hardware init, HFI, and ZAP/SCM`

`PASS A660 first-open firmware request is source-isolatable before every GPU power, hardware, HFI, and ZAP/SCM step`

Both scripts pass POSIX shell syntax, ShellCheck 0.10.0, and
`git diff --check`. The verifier controls no phone, transport, mount, or block
device.

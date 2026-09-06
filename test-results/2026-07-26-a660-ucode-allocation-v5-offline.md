# A660 ucode-allocation v5 — offline root and gate acceptance

Date: 2026-07-26

Result: **the fresh root-owned export, PID-filtered trace design,
mutation-tested target gate, overlapping watchdogs, duplicate kernel builds,
and unchanged temporary-boot package pass their complete offline
contracts**.

This is not a live GPU-allocation result. The phone was not contacted, NFS
was not started, no boot command ran, and nothing was flashed. The new root is
deliberately absent from the NFS allowlist, and no live host runner exists.

## Fail-first checkpoint

Commit `0e5505d0af060a2f3ed7b7cb6d4a006901e438c5` recorded the missing
root/gate contract before implementation. It returned:

```text
FAIL missing executable A660 ucode-allocation v5 tool: .../check-network-root-a660-ucode-allocation-baseline.sh
```

The contract requires:

- a fresh
  `/var/lib/rog5-network-root-a660-ucode-allocation-v5` derived only from the
  accepted registration-v3 root;
- the exact accepted ucode-allocation module archive and `msm.ko`;
- exact SQE and GMU firmware, with ZAP absent;
- the accepted 896-byte one-open helper under a new diagnostic-only name;
- `separate_gpu_kms=1 ucode_allocation_only=1` with
  `firmware_request_only=N`;
- one stopped helper process released only after its PID is installed in
  tracefs `set_event_pid`;
- exact, pointer-matched map/unmap/close, GEM-free, CPU-vmap, and firmware
  reference evidence;
- byte-identical pre/post MSM GEM debugfs snapshots;
- zero GPU runtime-resume, GMU/HFI, hardware-init, ZAP, SCM, storage,
  display, warning, fault, or surviving-DRM-descriptor evidence;
- nested SysRq fallback watchdogs and immediate normal reboot;
- the unchanged accepted Image, DT, nested initramfs, ASUS wrapper,
  header-v3 image, and AVB footer; and
- no NFS allowlist entry, live runner, phone transport, or flash path.

Implementation commit
`1d7ac767aa182ecf61c21df2ae7b552df52a84c3` satisfies the
source-level contract.

## Trace-backed runtime design

The accepted kernel config contains:

```text
CONFIG_KPROBE_EVENTS=y
CONFIG_KALLSYMS_ALL=y
CONFIG_DEBUG_FS=y
```

The gate loads the same exact seven-module registration chain, with only the
new `msm.ko`, and waits for the SMMU and GMU devices to remain runtime
suspended. Before opening DRM it mounts RAM-backed tracefs/debugfs as needed,
requires an empty dynamic-event namespace, and verifies every required
built-in and `msm` symbol through kallsyms.

The helper is started as a stopped child. Its exact PID is written to
`set_event_pid`; only then is tracing enabled and the child continued into
the one fixed `openat()` call. This excludes unrelated process activity from
the evidence window.

A future sole live invocation must produce:

| Evidence | Required count |
|---|---:|
| `adreno_load_ucode_only` entry / successful return | 1 / 1 |
| `msm_gem_vma_map` entry / successful return | 3 / 3 |
| `msm_gem_vma_unmap` | 3 |
| `msm_gem_vma_close` | 3 |
| `msm_gem_unpin_iova` | 3 |
| `msm_gem_free_object` | 3 |
| `msm_gem_get_vaddr` / `msm_gem_put_vaddr` | 4 / 4 |
| `msm_gem_kernel_put` | 2 |
| `a6xx_ucode_unload` | 1 |
| `request_firmware_direct` / `release_firmware` | 2 / 2 |

The sorted VMA pointer sets for map, unmap, and close must be identical. The
sorted GEM pointer sets for unpin and free must be identical. CPU vmap/vunmap
pointer multisets must also be identical.

Nine PID-filtered forbidden probes must all remain at zero:

- `msm_gpu_pm_resume`;
- `adreno_runtime_resume`;
- `a6xx_pm_resume`;
- `a6xx_gmu_resume`;
- `adreno_hw_init`;
- `a6xx_hw_init`;
- `a6xx_zap_shader_init`;
- `qcom_scm_pas_auth_and_reset`; and
- `qcom_scm_set_gpu_smmu_aperture`.

The render-minor `gem` debugfs file is captured before and after the failed
open and settle interval. The files must compare byte-for-byte. The helper
must return exact `EUCLEAN` status/output 117, produce exactly one success
marker, leave no DRM descriptor, and preserve suspended SMMU/GMU runtime
state.

The runtime verifier rejects mutations that enable the wrong or both
diagnostic modes, add a second open, change errno, remove PID filtering,
accept two maps, remove unmap or SCM probes, bypass the GEM snapshot, change
SQE firmware, or insert a probe-level reboot.

## Root-owned export

PolicyKit created:

```text
/var/lib/rog5-network-root-a660-ucode-allocation-v5
```

The directory is root-owned mode `0555`, derives by Btrfs reflink from the
accepted registration-v3 root, and passed the full protected whole-tree
verifier twice: once before atomic promotion and once as an independent
read-only verification.

Its Btrfs accounting is:

| Root | Logical bytes | Exclusive bytes | Set-shared bytes |
|---|---:|---:|---:|
| registration v3 | 5,593,767,936 | 12,374,016 | 3,004,542,976 |
| ucode-allocation v5 | 5,593,899,008 | 12,390,400 | 3,004,641,280 |

The candidate changes only the reviewed controls, exact firmware, and
`msm.ko`; undeclared metadata and file hashes remain equal to the base.
Credentials and SSH host identity are preserved exactly.

| Export input | Mode | SHA-256 |
|---|---:|---|
| export seal | `0444` | `6d057b0555393781238edebe7783f8aa1887a45f4083e0b07f2cda137e50ca9f` |
| registration-v3 marker | `0444` | `8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f` |
| ucode-allocation `msm.ko` | `0644` | `fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45` |
| one-open helper | `0755` | `d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae` |
| baseline | `0755` | `4f2e50fd492c9fff06198396c1fd80fa877b1447f18920d9895ad82c4034e041` |
| probe | `0755` | `63adc85bdd3b4f5b08130722d30615fad1a439eb3aa2a43a4b161e826c36c3ef` |
| `qcom/a660_sqe.fw` | `0644` | `d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76` |
| `qcom/a660_gmu.bin` | `0644` | `8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7` |
| `qcom/sm8350/a660_zap.mbn` | absent | pinned input `5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d` |

The independent export verifier returned:

```text
PASS A660 ucode-allocation v5 export modules=7 firmware=2 zap=absent helper=exact trace=balanced gem_snapshot=equal credentials=preserved base=registration-v3 root-owned mode 0555
```

After verification, `nfs-server.service` and `rpcbind.service` remained
inactive. There were no NFS mounts, port 111/2049 listeners, `rpc.mountd`,
or `rpc.nfsd` processes.

## Kernel and boot-package replay

The real-artifact build verifier and comparator were rerun against both clean
accepted builds. They returned:

```text
PASS accepted firmware-only Image is unchanged; ucode-allocation MSM module differs exactly; config, ABI, every other module, storage exclusion, and zero embedded firmware remain accepted
PASS two clean A660 ucode-allocation builds are byte-identical and the ucode-allocation MSM module differs only from its accepted firmware-only predecessor
PASS A660 ucode-allocation kernel build is exact-stack, unchanged-Image, modular, firmware-clean, rollback-safe, and reproducible by contract
```

Because the Image remains byte-identical, no boot package was rebuilt. The
complete real-artifact verifier rechecked the exact source, DT, modules,
nested initramfs, ASUS wrapper, Android boot header v3, AVB footer, and all
fourteen manifest entries. It returned:

```text
PASS exact live-accepted A660 registration bundle; exact SMMU reprobe, four nodes, seven modules, unopened render, zero firmware/storage/display, consumed and reproducible
PASS A660 registration bundle contract pins predecessor, source, DT, modules, wrappers, package, and source lock
```

The reused temporary-boot image is exactly 100,663,296 bytes with SHA-256
`c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c`.
Its fourteen-file manifest SHA-256 is
`c4b9a2ec5afdd73a555031425a5eaedf5ab97a36a69eeefdcfede279ad7ffcd0`.

## Consolidated offline result

All new shell tools pass POSIX/Bash syntax, ShellCheck 0.11.0, mutation
tests, and `git diff --check`. The umbrella suite ends with:

```text
PASS A660 ucode-allocation v5 contract is exact-root, trace-balanced, snapshot-clean, watchdog-guarded, storage-isolated, package-accepted, non-runnable, and non-flashing
```

## Decision

Offline preparation is accepted. Live use is not accepted by this report.

Before any phone boot, make a separate attended go/no-go decision, create and
test an exact one-invocation host runner, add the root to the NFS allowlist
only at that reviewed checkpoint, and recheck clean synchronized Git state,
inactive NFS, persistent Android fallback, exact SSH identity, watchdog
inputs, and complete cleanup. Any permitted run remains RAM-only
`fastboot boot`, never flash, exactly one failed open, immediate reboot, and
permanent root consumption regardless of result.

# A660 ucode-allocation v6 — safe live rejection

Date: 2026-07-26

Result: **the sole permitted v6 RAM-only cycle reached the exact firmware
allocation diagnostic, loaded SQE and GMU firmware, emitted the kernel's
successful allocation-and-rollback marker, and produced three successful
`msm_gem_kernel_new()` traces. The userspace gate then rejected the result
because it compared raw function-entry sizes with page-rounded object sizes.
It observed `43288`, `4`, and `4096`, while its oracle expected `45056`,
`4096`, and `4096`. The gate stopped before its settle period and pre/post GEM
snapshot comparison, so v6 does not pass. The transition watchdog restored
the exact persistent fallback, complete host cleanup passed, and v6 is
consumed, non-runnable, and forbidden from retry. This is an oracle rejection,
not evidence of a kernel allocation or rollback failure.**

## Exact attended boundary

The live cycle started from the clean, pushed, draft-PR checkpoint
`45372ad616692d70f873b51af736e570e1f25556`. The exact temporary-boot input
was:

| Input | Size | SHA-256 |
|---|---:|---|
| temporary-boot AVB image | 100,663,296 | `c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c` |
| accepted MSM module | — | `fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45` |
| v6 root seal | — | `e9a9bf460b62d91c44fa15b8258ae5a5660ef387846530e8cf93fce67f7f17ea` |

Before phone contact, the protected root passed its full ownership, module,
firmware, credential, predecessor, compiler-relocation, runtime-source, and
seal verifier. The host had no NFS/RPC service, export, listener, mount,
temporary firewall state, or nonlocal-bind setting. Firewalld,
NetworkManager, and ModemManager were healthy. The exact persistent-fallback
preflight passed.

The guarded fallback helper requested bootloader mode and reached the exact
`lahaina` fastboot product. Recovery preflight independently verified the
temporary-boot image. One `fastboot boot` command loaded it into RAM.
**Nothing was flashed.**

The fixed recovery ACM helper ran once. Its one tested load-marker
rediscovery occurred inside that same invocation; it then verified the
network-root payload and executed kexec. The NFS server accepted only the
exact v6 gadget and root. Strict key-only SSH with the pinned, distinct
network-root host identity passed before the host runner was invoked exactly
once. There was no gate retry.

## Passing baseline

Before the one-open diagnostic, the target reported:

`PASS A660-ucode-allocation-v6 baseline storage=0 mounts=0 firmware_files=2 firmware_requests=0 firmware_releases=0 zap=absent render=0 drm_fds=0 maps=0 unmaps=0 closes=0 gem_frees=0 failed_units=0 thermal_zones=29 thermal_max_mC=37800 module_files=7 helper=exact compiler=relocations watchdog=armed`

This proves the read-only NFS and volatile OverlayFS boundary, zero phone
storage access, exact two-file firmware input, unopened render node, empty
diagnostic trace, healthy systemd state, pinned compiler contract, safe
thermal state, and armed rollback authority before the probe.

The compound gate then armed its 240-second transition watchdog and safely
froze, terminated, and marked the earlier network-root watchdog disarmed.
The inner diagnostic retained its separate 110-second bound.

## Delivered live trace

The target registered GPUCC, reprobed the exact Adreno SMMU, attached GPU and
GMU to their separate IOMMU groups, loaded the reviewed MSM module, and
created one unopened DRM render node. It then ran one helper open.

SQE and GMU firmware were each requested once. The kernel diagnostic entered
and returned zero, then emitted:

`A660 ucode-allocation-only passed and rolled back; reject open`

The PID-filtered trace contains these observed events:

| Event | Observed count/result |
|---|---:|
| diagnostic entry / return | `1 / 1`, return `0` |
| firmware request / release | `2 / 2` |
| `msm_gem_kernel_new` entry / successful return | `3 / 3` |
| VMA map entry / successful return | `3 / 3`, all return `0` |
| public `msm_gem_get_vaddr` / `put_vaddr` | `1 / 2` |
| `msm_gem_kernel_put` | `2` |
| GEM unpin / VMA unmap / VMA close / GEM free | `3 / 3 / 3 / 3` |
| ucode unload | `1` |

The three successful kernel-new return values were distinct and non-error.
The trace also shows three distinct rollback objects. No runtime-power, GMU
HFI, ZAP/SCM, render-open, storage, mount, fatal-kernel, or failed-systemd-unit
event appears in the collected evidence.

These are observations from the complete trace, not a v6 acceptance claim.
The userspace probe stopped before running all pointer-union assertions, the
20-second settle interval, and the post-run debugfs GEM snapshot comparison.
In particular, **no live `gem_snapshot=equal` claim is made**.

## Size-oracle diagnosis

V6 attached a kprobe to the entry of `msm_gem_kernel_new()` and recorded its
raw `size` argument. The sorted expected file contained:

```text
4096
4096
45056
```

The live entry probe instead observed, in call order:

```text
43288
4
4096
```

The pinned source and firmware contract explains every value:

1. `adreno_fw_create_bo()` passes `fw->size - 4`. The accepted
   `a660_sqe.fw` is 43,292 bytes, so the raw request is 43,288 bytes.
2. The A660 catalog does not enable automatic preemption, leaving one ring.
   The shadow allocation passes `sizeof(u32) * gpu->nr_rings`, which is four
   bytes.
3. The power-up register-list allocation passes `PAGE_SIZE`, which is 4,096
   bytes.
4. `msm_gem_kernel_new()` forwards each raw argument to `msm_gem_new()`.
   `msm_gem_new()` then executes `size = PAGE_ALIGN(size)` before initializing
   the GEM object.

Therefore the raw entry sizes `43288`, `4`, and `4096` become object sizes
`45056`, `4096`, and `4096`. V6 compared values from two different abstraction
layers. The kernel trace is consistent with the exact pinned source; the
userspace oracle is not.

This diagnosis does not retroactively accept v6. The gate correctly failed
closed on a mismatched invariant, and the mandatory equal settled GEM
snapshot was never reached.

## Watchdog fallback and host cleanup

Because the size check failed, the target did not emit the compound PASS or
request its normal reboot path. The already armed transition watchdog
remained authoritative and rebooted the phone. The host runner returned:

`FAIL target ucode-allocation v6 probe did not pass`

It was not invoked again. The NFS server detected the exact network-root
gadget departure and reported:

`PASS network-root gadget departed; ending attended export`

It then removed the NFS export, listener, mounts, temporary firewall rules,
USB addressing, and nonlocal-bind state. ModemManager and the temporary
fallback NetworkManager profile were restored.

The persistent Alpine fallback returned and passed its exact verifier:

`PASS exact persistent fallback ready for guarded bootloader reboot`

Final host checks found:

- firewalld, NetworkManager, and ModemManager active;
- NFS server and rpcbind inactive;
- zero NFS exports, listeners, mounts, `rpc.mountd`, or `rpc.nfsd`;
- no runtime export mount or drop-zone interface/rich rule;
- `net.ipv4.ip_nonlocal_bind=0`;
- the fallback USB profile active at the expected host address;
- no fastboot device and no ADB device; and
- a clean branch synchronized with GitHub.

## Private evidence

Raw logs remain outside Git in a caller-owned mode-`0700` directory. Both
files are mode `0600`. Their nonsecret identities are:

| Private evidence | Size | SHA-256 |
|---|---:|---|
| v6 live-gate log | 10,880 | `489f68c71220c67b23c8ca87f7faecc4a26d1439fbe2bf9c05ac540c0a118be4` |
| staging ACM log | 489 | `bcf1743eafc31fbc16e947375766368cc75afbf1980f68db7525032669db21b3` |

No private path, serial, MAC address, boot ID, process ID, kernel pointer,
credential, SSH key, or raw private log is committed.

## Consumed tier and v7 boundary

Fail-first commit `b72076a` proves the v6 root was still runnable before
lockout. Commit `664fd09` removes its NFS case and live-window test, adds it
to the generic consumed-root set, and passes the permanent non-runnable
contract:

`PASS A660 ucode-allocation v6 is consumed and absent from the bounded NFS server`

V6 must never be re-enabled or retried.

Before any later GPU hardware tier, a separately versioned v7 must:

1. derive from the unchanged accepted v6 module and consumed root without
   editing either;
2. pin this rejection report and forbid inherited v6 authorization;
3. expect raw kernel-new entry sizes `4`, `4096`, and `43288`, while separately
   source-pinning their page-rounded object sizes;
4. retain three successful kernel-new returns, two kernel puts, public wrapper
   counts `1 / 2`, and logical vmap balance `4 / 4`;
5. retain exact pointer-union, map/unmap/close, unpin/free, firmware,
   forbidden-event, storage, one-open, thermal, systemd, and overlapping
   watchdog constraints;
6. complete the full settle interval and require an equal pre/post GEM
   snapshot before PASS;
7. use a fresh protected root, seal, mock-tested one-shot runner, and
   default-off NFS boundary; and
8. require a new explicit offline HOLD/GO review before one attended
   RAM-only cycle.

GPUCC/CCF, the idle Adreno SMMU, A660 registration, and exact SQE/GMU request
tiers remain accepted. Ucode-allocation acceptance, GMU resume/HFI,
ZAP/SCM authentication, successful render open, command submission,
Mesa/Freedreno/Turnip, display, suspend, and accelerated desktop remain
pending.

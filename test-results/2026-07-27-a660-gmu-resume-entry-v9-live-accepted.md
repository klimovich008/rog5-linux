# A660 GMU resume-entry v9 — live acceptance

Date: 2026-07-27

Result: **the sole permitted v9 RAM-only cycle passed. The corrected
userspace oracle accepted one GPU-device runtime-PM transition, signed
`-EUCLEAN` through the A660 GMU resume path, exact firmware/allocation/mapping
rollback, and an equal settled GEM snapshot. Specific inner power, clock,
IRQ, HFI, devfreq, LLC, hardware-init, ZAP, and SCM probes remained zero.
Exact persistent fallback and complete host cleanup passed. V9 is now
permanently consumed and cannot be served or retried.**

This accepts only the pre-resource GMU resume-entry boundary and its
rollback. It does not accept GMU/CX or GX power activation, clocks, MMIO,
interrupts, HFI, firmware execution, a successful DRM open, submission,
rendering, display, suspend, or persistent installation.

## Exact attended boundary

The cycle started from clean, pushed checkpoint
`17e7b25537b2198e3e1fbaa1658592b40e077757`. Every transition-time
prerequisite passed:

- the complete protected-v9-root verifier and mutation suite;
- the one-invocation/no-retry host-runner mock;
- the verifier-first, explicit-opt-in NFS-window test;
- the unchanged fourteen-file temporary-boot package verifier;
- exact local client/server credential agreement and distinct pinned
  fallback/network-root SSH identities;
- clean synchronized Git and residue-free host state; and
- a current identity-pinned fallback health check covering the exact vendor
  kernel, BusyBox PID 1, compatible, ext4 root, empty pstore, zero project
  modules or fatal signatures, safe thermals, and Python availability.

Immutable live inputs were:

| Input | SHA-256 |
|---|---|
| temporary-boot AVB image | `c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c` |
| unchanged v8/v9 MSM module | `b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861` |
| v9 export seal | `137eb101708a8f96c063ed068caf7f8265641c43c228501fc578d5076be02bd5` |
| protected-root verifier | `a3f526c6aa5e2f75af49a5b72b89ee24958ce23898e410e43749b482dde3179c` |
| target compound gate | `3922fdb46b587e543940b6703382568a81601fb50189f6b66231d1b62de629d2` |
| one-invocation host runner | `40276c91803d1890b70152064ac47b56ddead96880f52932f11c16feb4ce485b` |

One verifier-first, exact-peer, read-only NFSv4.2 window was opened. The
guarded fallback helper sent Linux `RESTART2("bootloader")`, exactly one
fastboot device reported product `lahaina`, and one manifest-pinned
`fastboot boot` loaded the image into RAM. Nothing was flashed.

The fixed `confirm-gpucc` ACM sequence ran once. Its one permitted
load-marker rediscovery happened inside the same invocation, after which the
payload loaded and kexec executed. Strict key-only SSH then accepted the
distinct pinned network-root identity. The target reported the exact
`7.1.4-rog5-a660reg1` kernel, systemd PID 1, writable OverlayFS over the
read-only `169.254.77.1:/` NFSv4.2 lower root, zero failed units, and an
armed rollback watchdog.

The v9 host runner was invoked exactly once and was never retried.

## Passing zero-action baseline

Before the one-open probe, the target reported:

```text
PASS A660-gmu-resume-entry-v9 baseline storage=0 mounts=0 firmware_files=2 firmware_requests=0 firmware_releases=0 zap=absent render=0 drm_fds=0 maps=0 unmaps=0 closes=0 gem_frees=0 runtime_resume=0 gmu_resume=0 inner_runtime_pm=0 clocks=0 irq=0 hfi=0 hw_init=0 scm=0 failed_units=0 thermal_zones=29 thermal_max_mC=37100 module_files=7 helper=exact compiler=v8-relocations oracle=v9-s32-device watchdog=armed
```

This proves the read-only NFS/volatile-overlay boundary, zero phone storage,
the exact two-file firmware input, no render node or DRM file descriptor,
empty diagnostic trace, healthy services, safe thermals, and active rollback
before the probe.

## Accepted live observation

GPUCC and both Adreno SMMUs registered before the exact MSM module. The
helper made one failed DRM open. SQE and GMU firmware were each requested
once. The kernel reached the diagnostic stop at the first line of
`a6xx_gmu_resume()` and deliberately returned `-EUCLEAN` before
`gmu->hung = false`, GMU/GX runtime PM, clock rates/enables, secure init,
MMIO, IRQs, firmware start, HFI, devfreq, LLC, or hardware initialization.

The signed-32/device-scoped v9 oracle accepted:

| Event | Observed count/result |
|---|---:|
| DRM open / errno | `1 / 117` |
| `adreno_load_gpu()` entry / return | `1 / 1`, rollback return `0` |
| `adreno_runtime_resume()` | `1`, signed return `-117` |
| `a6xx_gmu_pm_resume()` | `1`, signed return `-117` |
| `a6xx_gmu_resume()` | `1`, signed return `-117` |
| exact GMU-entry marker / rollback marker | `1 / 1` |
| GPU-device outer runtime-PM transition | `1` |
| all process-scoped generic runtime-PM calls | `20`, device-classified |
| firmware request / release | `2 / 2` |
| VMA map / unmap / close | `3 / 3 / 3` |
| GEM allocation / free | `3 / 3` |
| public CPU-vmap get / put | `1 / 2` |
| logical CPU-vmap get / put | `4 / 4` |
| pre/post settled GEM snapshot | equal |
| inner GPU/GMU PM, clocks, IRQ, HFI | `0 / 0 / 0 / 0` |
| devfreq, LLC, hardware init, ZAP, SCM | `0 / 0 / 0 / 0 / 0` |
| physical storage / block-backed mounts | `0 / 0` |
| final DRM file descriptors | `0` |

The post-probe target remained healthy at 36.8 C. Both Adreno SMMUs were
present, exact reprobe passed, the driver override returned to its null
representation, and the dynamically registered render node had no open file
descriptor. The full private gate log contains zero `FAIL` lines.

The compound gate ended with:

```text
PASS compound A660 GMU resume-entry v9 gate open_errno=117 gmu_resume_entry_only=Y firmware_request_only=N ucode_allocation_only=N firmware_requests=2 firmware_releases=2 gmu_resume=1 rollback=1 gpu_runtime_pm=1 generic_runtime_pm=device-classified inner_runtime_pm=0 clocks=0 irq=0 hfi=0 devfreq=0 llc=0 hw_init=0 scm=0 maps=3 unmaps=3 closes=3 gem_frees=3 kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal transition_watchdog=armed reboot=requested
```

## Fallback and host cleanup

The gate requested immediate normal reboot. The network-root gadget departed,
the bounded server removed its export, NFS threads, mount daemon, bind mount,
runtime firewall rules, USB `/30` address, and temporary
`ip_nonlocal_bind` change, and the persistent Alpine gadget returned.

The strict fallback health verifier passed again with empty pstore, zero
project modules or fatal signatures, and safe thermals. ModemManager was
restored. Final host state had firewalld, NetworkManager, and ModemManager
active; NFS and rpcbind inactive; zero exports, NFS mounts, RPC processes,
listeners, temporary firewall state, fastboot devices, or changed sysctls;
and clean synchronized Git.

## Private evidence

Raw evidence remains outside Git in one caller-owned mode-`0700` directory.
Every file is mode `0600`. Only redacted identities are published:

| Private evidence | Size | SHA-256 |
|---|---:|---|
| v9 live-gate log | 4,449 | `a476548e5e55a5500b9c7726c788b9830cc66dc5b1e0084dcf6282cec09e32e5` |
| host-runner log | 199 | `c3a626577b295290f1ee552025e3eb39644c3b11902135e59f70ec41e6b7ca68` |
| bounded NFS host log | 596 | `05b7316dd46e1cc04930255e67253c30253745727494578e9826389927691823` |
| staging ACM log | 489 | `bcf1743eafc31fbc16e947375766368cc75afbf1980f68db7525032669db21b3` |
| temporary-boot log | 864 | `1b9d828740b47dc8a4f804058d2b231f52e3306d86a46c61f2560bf9c2bf07d7` |

No private path, key, fingerprint, phone identifier, MAC address, boot ID,
process ID, kernel pointer, or raw log is committed.

## Permanent consumption and next boundary

Fail-first commit `ef10b62` proves v9 was still server-runnable immediately
after acceptance:

```text
FAIL consumed v9 remains server-runnable: /var/lib/rog5-network-root-a660-gmu-resume-entry-v9)
```

Commit `3d708cd` removes the v9 NFS case and live-window test, adds v9 to the
generic consumed-root set, and passes:

```text
PASS A660 GMU resume-entry v9 is consumed and absent from the bounded NFS server
```

V9 must never be re-enabled or retried.

The next separately versioned tier is GMU/CX runtime-PM preparation. Before
any live test, it must have a fail-first offline suite and a fresh protected
root. It should isolate the first `pm_runtime_get_sync(gmu->dev)` and its
balanced rollback, classify the exact GMU and CX-domain transitions, retain
all v9 firmware/allocation/mapping/snapshot/storage/watchdog gates, and prove
zero GX-domain, clock-rate/enable, secure-init, MMIO, IRQ, firmware-start,
HFI, devfreq, LLC, ZAP, and SCM activity. No live authority for that tier
exists yet.

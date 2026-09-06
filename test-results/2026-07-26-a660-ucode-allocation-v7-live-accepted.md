# A660 ucode-allocation v7 — accepted live boundary

Date: 2026-07-26

Result: **the sole permitted v7 RAM-only cycle passed the complete
ucode-allocation boundary.** The target delivered the source-pinned raw
kernel-new sizes `4/4096/43288`, three successful and distinct GEM
allocations, exact map/unmap/close/unpin/free object sets, compiler-aware
logical vmap balance `4/4`, one successful allocation-and-rollback marker,
and an equal pre/post GEM snapshot after the mandatory 20-second settle.
It then requested normal fallback reboot.

This accepts only SQE/shadow/register-list allocation and complete rollback
before GPU/GMU runtime power, HFI, ZAP/SCM, hardware initialization, successful
DRM open, command submission, or rendering. It does not establish accelerated
graphics, display, suspend, or a persistent installation.

The exact persistent fallback returned, complete host cleanup passed, and v7
is consumed, non-runnable, and forbidden from retry.

## Exact attended boundary

The live cycle started from the clean, pushed, draft-PR checkpoint
`656f2cda32e13054af8dc20ccd19d142ddb92efe`.

| Input | Size | SHA-256 |
|---|---:|---|
| temporary-boot AVB image | 100,663,296 | `c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c` |
| accepted MSM module | — | `fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45` |
| v7 root seal | — | `c679ff6cbed6aefb28b7537cd30c561948e4d4672cd9320a8e70fd3d79b4f046` |
| target compound gate | — | `f7f223b62521306007c9ac224f008c0a9e6f85fdbdcac1529bf7c8e3a9ea3d1e` |
| one-invocation host runner | — | `b6800410bb0692e876129bb2d40d8cde23e60005a3d2c90959f730be7aee510a` |

Before phone contact:

- the protected root passed exact ownership, module, firmware, credential,
  predecessor, compiler-relocation, generated-runtime, raw/object-size, and
  seal verification;
- the runner mock, NFS-window contract, temporary package, and clean
  synchronized Git checks passed;
- the host had no NFS/RPC service, export, listener, mount, temporary firewall
  state, target address, or nonlocal-bind setting; and
- strict fallback SSH verified the exact vendor kernel, BusyBox init,
  compatible, ext4 root, empty pstore, zero project modules, safe thermals,
  and no fatal signature.

One explicit 1,200-second NFSv4.2 window accepted only the exact protected v7
root. The pinned fallback helper sent Linux `RESTART2("bootloader")` and
reached exactly one `lahaina` fastboot device. Recovery preflight independently
verified the image, and one `fastboot boot` command loaded it into RAM.
**Nothing was flashed.**

The fixed `confirm-gpucc` ACM sequence ran once. Its one tested load-marker
rediscovery occurred inside that same invocation; it verified the payload and
executed kexec. The server accepted only the exact network-root gadget. A
separate strict network-root SSH check proved the pinned host identity,
Linux `7.1.4-rog5-a660reg1`, OverlayFS over the read-only NFS lower root,
the v7 seal, and zero block devices. The v7 host runner was then invoked
exactly once.

## Passing zero-action baseline

Before arming the inner transition and opening the render node, the target
reported:

```text
PASS A660-ucode-allocation-v7 baseline storage=0 mounts=0 firmware_files=2 firmware_requests=0 firmware_releases=0 zap=absent render=0 drm_fds=0 maps=0 unmaps=0 closes=0 gem_frees=0 failed_units=0 thermal_zones=29 thermal_max_mC=38100 module_files=7 helper=exact compiler=relocations watchdog=armed
```

This proves the read-only NFS plus volatile OverlayFS boundary, zero physical
storage, exact two-file firmware input, unopened render node, empty diagnostic
trace, healthy systemd state, pinned compiler contract, safe thermal state,
and armed rollback authority.

The compound gate then armed its independent 240-second transition watchdog,
safely handed off from the earlier network-root watchdog, and retained the
probe's separate 110-second bound.

## Accepted allocation and rollback

The target registered GPUCC, performed one exact Adreno SMMU reprobe, attached
GPU and GMU to two IOMMU groups, loaded the seven reviewed modules, and
created one headless `/dev/dri/renderD128`. No display connector or prior DRM
descriptor existed.

One helper performed one DRM open. SQE and GMU firmware were each requested
once. The diagnostic returned zero and emitted exactly one:

```text
A660 ucode-allocation-only passed and rolled back; reject open
```

The helper then returned the intentional `EUCLEAN` value `117`.

The PID-filtered live trace passed:

| Event or invariant | Accepted observation |
|---|---:|
| diagnostic entry / return | `1 / 1`, return `0` |
| firmware request / release | `2 / 2` |
| kernel-new entry / successful return | `3 / 3` |
| raw kernel-new size set | `4 / 4096 / 43288` |
| VMA map entry / successful return | `3 / 3`, all return `0` |
| VMA unmap / close | `3 / 3` |
| GEM unpin / free | `3 / 3` |
| public wrapper get / put | `1 / 2` |
| kernel GEM put | `2` |
| compiler-aware logical get / put | `4 / 4` |
| ucode unload | `1` |
| runtime power, HFI, hardware init, ZAP, SCM | `0` |

All three kernel-new return values were distinct, non-null, and non-error.
The three map, unmap, and close pointer sets were equal. The three unpin and
free object sets were equal. The one public-wrapper object plus two
kernel-put objects formed three unique logical rollback objects, exactly
matching the unpinned object set. This resolves the wrapper-inlining blind
spot exposed by v5 while preserving the compiler relocation contract.

The raw sizes also resolve the v6 oracle mismatch:

1. SQE firmware payload allocation entered with `43288`.
2. The one-ring shadow allocation entered with `4`.
3. The register-list allocation entered with `4096`.
4. The separately source-pinned page-rounded object sizes remain
   `45056/4096/4096`.

After the exact pointer and logical checks, the target settled for 20 seconds.
The render-minor GEM debugfs snapshot was byte-equal before and after the
open. The success marker stayed singular; the failed-open helper left no DRM
descriptor; GPU and GMU remained runtime-suspended; systemd remained healthy;
USB/NFS stayed stable; storage and block-backed mounts remained zero; and no
warning, call trace, fault, or fatal kernel signature appeared.

The accepted probe line was:

```text
PASS A660 ucode-allocation-v7 open_invocations=1 open_errno=117 firmware_requests=2 firmware_releases=2 success_markers=1 maps=3 unmaps=3 closes=3 gem_frees=3 kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal zap=absent power=0 hfi=0 scm=0 drm_fds=0 storage=0 mounts=0 failed_units=0 iommu=2 render=1 thermal_zones=29 thermal_max_mC=37800 exact_reprobe=1 driver_override=unset-null-representation watchdog=disarmed
```

The compound gate retained its transition watchdog and requested immediate
normal reboot:

```text
PASS compound A660 ucode-allocation v7 gate open_errno=117 maps=3 unmaps=3 closes=3 gem_frees=3 kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal transition_watchdog=armed reboot=requested
```

The host runner returned status zero and was not invoked again.

## Fallback and host cleanup

The normal reboot removed the network-root gadget. The attended server
reported gadget departure and removed its NFS export, listener, kernel
threads, mount daemon, bind mount, temporary firewall rules/interface
assignment, and `ip_nonlocal_bind` change.

The exact Alpine fallback gadget returned and passed its strict verifier:

```text
PASS exact persistent fallback ready for guarded bootloader reboot
```

Final host checks found:

- firewalld, NetworkManager, and ModemManager active;
- NFS server and rpcbind inactive;
- zero NFS exports, listeners, mounts, `rpc.mountd`, or `rpc.nfsd`;
- no runtime export mount or drop-zone interface/rich rule;
- `net.ipv4.ip_nonlocal_bind=0`;
- the fallback USB profile active at its expected link-local address;
- no fastboot device and no ADB device; and
- a clean branch synchronized with GitHub.

## Private evidence

Raw logs remain outside Git in a caller-owned mode-`0700` directory. Every
file is mode `0600`. Their nonsecret identities are:

| Private evidence | Size | SHA-256 |
|---|---:|---|
| v7 live-gate log | 3,572 | `61aa5913c79cd8ddff140f206d8ffa3ec3a69f6ad3cb5bbdb3302da5b0ba16a0` |
| staging ACM log | 489 | `bcf1743eafc31fbc16e947375766368cc75afbf1980f68db7525032669db21b3` |
| attended NFS host log | 580 | `15422c8b5ccbce2f92399e3bf0f3083f837571a8e7b56c1041cffbcd19fcbef9` |

No private path, serial, MAC address, boot ID, process ID, kernel pointer,
credential, SSH key, or raw private log is committed.

## Consumed tier and next boundary

Fail-first commit `08ca0157d3ec012c7b3e4063f02b91e15376f608` proves the accepted
v7 root was still runnable before lockout. Commit
`12ad39c8227f880e65db62086a0d5c80260f1d4f` removes its NFS case and
live-window test, adds it to the generic consumed-root set, and passes:

```text
PASS A660 ucode-allocation v7 is consumed and absent from the bounded NFS server
```

V7 must never be re-enabled or retried. Its protected root and verifiers
remain offline evidence only.

The accepted Linux 7.1 foundation now includes isolated GPUCC registration,
idle Adreno SMMU binding, A660/GMU registration, exact SQE/GMU firmware
requests, and complete ucode allocation/rollback. The next separately
versioned tier must begin at the still-unaccepted runtime-power/GMU boundary.
It must:

1. retain every v7 storage, thermal, firmware, pointer, snapshot, systemd,
   watchdog, one-open, and no-display constraint;
2. keep command submission and rendering disabled;
3. distinguish runtime-PM, GMU resume/HFI, ZAP/SCM authentication, and hardware
   initialization as independently observable stop points;
4. fail closed on the first unreviewed event or error;
5. use a fresh protected root, default-off server case, one-shot runner, and
   new HOLD/GO review; and
6. run at most one attended RAM-only cycle before permanent consumption.

Successful render open, command submission, Mesa Freedreno/Turnip, display,
suspend, accelerated desktop, and persistent installation remain pending.

# A660 GMU resume-entry v8 — safe live rejection

Date: 2026-07-26

Result: **the sole permitted v8 RAM-only cycle reached the exact normal A660
GMU resume entry, returned deliberate `EUCLEAN` through
`a6xx_gmu_resume()`, `a6xx_gmu_pm_resume()`, and
`adreno_runtime_resume()`, and ran the accepted allocation rollback. The
userspace oracle rejected those returns because arm64 supplied the
32-bit-negative value in a zero-extended register and the trace declared it
as signed 64-bit. It therefore observed `4294967179` rather than `-117`.
Complete trace review also found 21 process-scoped
`__pm_runtime_resume()` calls, not the oracle's assumed one; those calls span
GEM mapping, the GPU resume callback, and rollback. Specific inner GPU/GMU
power callbacks, clocks, IRQ, HFI, devfreq, LLC, hardware initialization,
ZAP, and SCM remained absent. The gate failed closed before settling and
snapshot comparison, exact fallback and complete host cleanup passed, and v8
is permanently consumed, non-runnable, and forbidden from retry.**

This is a userspace trace-oracle rejection. It is not v8 acceptance and is
not evidence that GMU resource activation succeeded.

## Exact attended boundary

The live cycle started from clean, pushed draft-PR checkpoint
`c6fd2cca364d8189851ad61d5b0e89742268613b`. The immutable transport inputs
were:

| Input | Size | SHA-256 |
|---|---:|---|
| temporary-boot AVB image | 100,663,296 | `c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c` |
| v8 MSM module | — | `b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861` |
| v8 export seal | — | `a6c14600ed17a52641f8700393d095e7cd86f2aa0d01c1f1f6bf649e283f2923` |
| protected-root verifier | — | `fe45a420b7241bea6dc3f37fc4beba5397221a8e27d747bd64baab0971181972` |

Before phone contact, the complete protected-root suite, five hostile
mutations, unchanged fourteen-file package verifier, exact credentials,
distinct pinned SSH identities, strict fallback health, clean Git, and
inactive NFS/RPC checks passed. The transition-time root verifier passed
again at the exact checkpoint.

One verifier-first, exact-peer, read-only NFSv4.2 window was opened. The
guarded fallback helper entered bootloader mode and exactly one fastboot
device reported product `lahaina`. One manifest-pinned `fastboot boot`
loaded the image into RAM. **Nothing was flashed.**

The fixed recovery ACM sequence ran once. Its one accepted load-marker
rediscovery occurred within that invocation, after which staging passed.
Strict key-only SSH then verified the distinct network-root identity, root
health, and zero phone-storage exposure. The v8 runner was invoked exactly
once and was never retried.

## Passing zero-action baseline

Before the one-open probe, the target reported:

```text
PASS A660-gmu-resume-entry-v8 baseline storage=0 mounts=0 firmware_files=2 firmware_requests=0 firmware_releases=0 zap=absent render=0 drm_fds=0 maps=0 unmaps=0 closes=0 gem_frees=0 runtime_resume=0 gmu_resume=0 inner_runtime_pm=0 clocks=0 irq=0 hfi=0 hw_init=0 scm=0 failed_units=0 thermal_zones=29 thermal_max_mC=37800 module_files=7 helper=exact compiler=v8-relocations watchdog=armed
```

This proves the read-only NFS and volatile OverlayFS boundary, zero physical
storage, exact two-file firmware input, no open render node, empty diagnostic
trace, healthy services, safe thermal state, and armed rollback authority
before the probe.

The compound gate then armed its independent 240-second transition watchdog,
safely froze and terminated the initial network-root watchdog, marked it
disarmed, and started the inner 110-second probe bound.

## Delivered live boundary

GPUCC and both Adreno SMMUs registered before the exact MSM module. The helper
performed one failed DRM open. SQE and GMU firmware were each requested once.
The kernel emitted:

```text
A660 GMU resume entry reached before resource activation; reject resume
Couldn't power up the GPU: -117
A660 GMU resume entry passed and rolled back; reject open
```

The helper itself returned the expected:

```text
OPEN_ERRNO=117
```

The PID-filtered trace contains these observations:

| Event | Observed count/result |
|---|---:|
| `adreno_load_gpu()` entry / return | `1 / 1`, return `0` after rejected resume |
| `adreno_runtime_resume()` entry / return | `1 / 1`, trace return `4294967179` |
| `a6xx_gmu_pm_resume()` entry / return | `1 / 1`, trace return `4294967179` |
| `a6xx_gmu_resume()` entry / return | `1 / 1`, trace return `4294967179` |
| exact GMU-entry one-shot hit / result | `1 / 1`, result `1` |
| accepted GPU-load rollback entry / return | `1 / 1`, return `0` |
| firmware request / release | `2 / 2` |
| VMA map entry / successful return | `3 / 3`, all return `0` |
| VMA unmap / close | `3 / 3` |
| GEM unpin / free | `3 / 3` |
| `msm_gem_kernel_new()` entry / successful return | `3 / 3` |
| public CPU-vmap get / put | `1 / 2` |
| `msm_gem_kernel_put()` | `2` |
| ucode unload | `1` |
| process-scoped `__pm_runtime_resume()` | `21` |
| `msm_gpu_pm_resume()` / `a6xx_pm_resume()` | `0 / 0` |
| clock-rate / IRQ activation | `0 / 0` |
| HFI / devfreq / LLC / initial-frequency | `0 / 0 / 0 / 0` |
| Adreno / A6xx hardware initialization | `0 / 0` |
| ZAP / four SCM probes | `0 / 0` |

The allocation, mapping, and rollback counts are observations from the
complete captured trace, not acceptance assertions. The oracle stopped at
the first return-value mismatch, before its pointer-set assertions,
20-second settle interval, post-open safety checks, and pre/post debugfs GEM
snapshot comparison. **No live `gem_snapshot=equal` claim is made.**

## Return-value diagnosis

All three affected kernel functions return `int`. On arm64, writing a return
value to `w0` zeroes the upper half of `x0`. The v8 kretprobes nevertheless
declared `$retval` as `s64`, so the 32-bit two's-complement value was treated
as a positive 64-bit integer:

```text
2^32 - 117 = 4294967179
```

The kernel log, helper exit status, exact diagnostic source, and all three
return traces therefore agree on deliberate `-EUCLEAN`. The failed check:

```text
FAIL Adreno runtime resume did not return EUCLEAN
```

compared different integer widths. It failed safely and must not be bypassed.

## Generic runtime-PM diagnosis

The v8 oracle also expected one process-scoped probe hit on
`__pm_runtime_resume()`. The complete event order instead contains 21:

- calls occur during all three GEM/VMA setup paths;
- one occurs immediately before `adreno_runtime_resume()`; and
- calls recur during unmap, close, free, and final rollback.

The probe captured no device argument, so it cannot distinguish the one GPU
device transition from unrelated runtime-PM calls made in the same helper
syscall. A global count of one is therefore not a valid device-specific
invariant. This does not weaken the specific zero-work evidence: direct
probes on `msm_gpu_pm_resume()`, `a6xx_pm_resume()`, clocks, IRQ, HFI,
devfreq, LLC, hardware initialization, ZAP, and SCM all remained zero.

## Fallback and host cleanup

The runner returned:

```text
FAIL target GMU resume-entry v8 probe did not pass
```

It was not invoked again. The transition watchdog returned the phone to the
exact persistent Alpine fallback. The NFS server observed gadget departure
and removed its export, listener, NFS threads, mount daemon, bind mount,
temporary firewall rules, USB addressing, and nonlocal-bind state.

The strict fallback verifier passed:

```text
PASS exact persistent fallback ready for guarded bootloader reboot
```

The final privileged check passed:

```text
PASS exact fallback and complete host cleanup after sole v8 cycle
```

Final state had firewalld, NetworkManager, and ModemManager active; NFS and
rpcbind inactive; zero exports, RPC processes, listeners, mounts, temporary
firewall state, or nonlocal bind; no fastboot device; and a clean branch
synchronized with GitHub.

## Private evidence

Raw evidence remains outside Git in a caller-owned mode-`0700` directory.
Each file is mode `0600`. Only redacted identities are published:

| Private evidence | Size | SHA-256 |
|---|---:|---|
| v8 live-gate log | 15,005 | `c736777696559f5f135e70483fa5a4e331ef33ab993b25aa0c0e12706b07231d` |
| staging ACM log | 489 | `bcf1743eafc31fbc16e947375766368cc75afbf1980f68db7525032669db21b3` |
| bounded NFS host log | 549 | `1acbbb8ebcec94f084e269009a96ebce3cbc99e185c8e1a3d2e2ecfdbaaffc85` |

No private path, phone identifier, MAC address, boot ID, process ID, kernel
pointer, credential, SSH key, or raw private log is committed.

## Permanent consumption and next boundary

Fail-first commit `8d06e8022a861e26b6fab9aa50834f5f8c86d5d4`
proves v8 was still server-runnable before lockout:

```text
FAIL consumed v8 remains server-runnable: /var/lib/rog5-network-root-a660-gmu-resume-entry-v8)
```

Commit `ff1250f3e99b8d6c370ae0e5bcfb31df3af5fe65` removes the v8
NFS case and live-window test, adds v8 to the generic consumed-root set, and
passes:

```text
PASS A660 GMU resume-entry v8 is consumed and absent from the bounded NFS server
```

V8 must never be re-enabled or retried.

Before any GMU power-preparation or later hardware tier, a separately
versioned v9 userspace oracle must:

1. derive from the unchanged v8 kernel module and consumed root without
   editing either;
2. pin this rejection report and forbid inherited v8 authorization;
3. capture the three `int` returns as signed 32-bit values and fail-first
   test zero-extension, exact `-117`, non-`EUCLEAN`, and malformed inputs;
4. capture the device argument for both `__pm_runtime_resume()` and
   `adreno_runtime_resume()`, require exactly one matching GPU-device outer
   transition, and tolerate no unclassified GPU-device transition;
5. retain the specific zero inner-PM, clock, IRQ, HFI, devfreq, LLC,
   hardware-init, ZAP, and SCM probes;
6. retain exact allocation, pointer-union, mapping, rollback, firmware,
   storage, thermal, service, one-open, and overlapping-watchdog checks;
7. complete the full settle interval and require equal pre/post GEM snapshots
   before PASS;
8. use a fresh protected root, seal, mock-tested no-retry runner, and
   default-off NFS boundary; and
9. require a new offline HOLD/GO review before any one-cycle authorization.

No GMU power-preparation tier is authorized yet. Successful render open,
HFI, ZAP/SCM authentication, command submission, Mesa/Freedreno/Turnip,
display, suspend, and accelerated desktop remain pending.

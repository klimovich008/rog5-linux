# A660 GMU resume-entry boundary — offline source audit

Date: 2026-07-26

Status: **PASS for source isolation; no build or live run is authorized by
this report**

## Outcome

The next safe tier is a one-shot stop at the entry of `a6xx_gmu_resume()`.
It proves that the accepted firmware and ucode path reaches the real
first-open runtime-resume call graph while deliberately returning `EUCLEAN`
before the first GMU software mutation or resource activation.

The stop belongs after the existing `gmu->initialized` validation and before
`gmu->hung = false`. At that point it excludes:

- the GMU CX and GX runtime-PM gets;
- core and hub clock-rate changes;
- bulk clock enable;
- secure initialization and any SCM-dependent setup;
- initial bandwidth votes;
- GMU register reads or writes and IRQ enable;
- GMU firmware start and HFI start;
- GPU hardware initialization, ZAP authentication, command submission, and
  rendering.

The outer GPU runtime-PM call has begun by the time this seam is reached.
The unmodified error path balances that software state with
`pm_runtime_put_noidle()` and `pm_runtime_disable()`. A diagnostic must then
reuse the accepted v7 cleanup to release the SQE, shadow, power-up reglist,
their three IOMMU mappings and CPU vmaps, plus both firmware references.

## Pinned prerequisite

This audit requires the consumed v7 live report with SHA-256
`ea4a4a87a264728be3bfcd86a2f12888496dd51c7421cbee166ad19afdb5ee6a`
and a successful run of the v7 umbrella contract. V7 already proved exact
A660.1 firmware request, three-object ucode allocation, compiler-aware vmap
accounting, pointer-set equality, complete rollback, equal GEM snapshots,
zero runtime power/HFI/SCM activity, fallback return, and complete host
cleanup.

The source remains pinned to Linux commit
`d9ac316489f4258d389d6298659d5e9c22183400` and tree
`c796deb1cc54e942f8bb46a2c76a7199e19e5c92`.

## Exact first-open propagation

The source verifier proves this order:

1. `msm_open()` calls the lazy `load_gpu()`;
2. `adreno_load_gpu()` requests firmware and allocates ucode;
3. it enables GPU runtime PM and calls `pm_runtime_get_sync()`;
4. `adreno_runtime_resume()` dispatches the A660 `pm_resume` callback;
5. `a6xx_gmu_pm_resume()` calls `a6xx_gmu_resume()` under the GMU lock;
6. a negative return propagates before devfreq or LLC activation;
7. `adreno_load_gpu()` balances the failed outer runtime-PM get and disables
   runtime PM;
8. GPU hardware initialization is never called.

The first unaccepted normal-path operation inside `a6xx_gmu_resume()` is
`gmu->hung = false`, immediately followed by the GMU PM-domain and clock
sequence. The diagnostic stop therefore precedes all of them.

## Required diagnostic contract

The implementation and later runtime gate must require:

1. a default-off, read-only kernel option;
2. exact chip ID `0x06060001`;
3. mutual exclusion with all earlier diagnostics;
4. independent atomic consumption of the DRM-open attempt and the GMU-entry
   hit;
5. exactly one entry marker and deliberate `EUCLEAN`;
6. no successful DRM file descriptor;
7. outer runtime-PM error rollback;
8. complete v7-proven ucode and firmware cleanup;
9. zero GMU inner runtime-PM, clocks, MMIO, IRQ, firmware start, HFI, hardware
   init, ZAP, SCM, submit, or render events;
10. the existing storage-free network root, thermal checks, systemd health,
    transition watchdog, immediate fallback reboot, host cleanup, and
    permanent tier consumption.

## Fail-first result

Before the implementation patch existed, the patch suite returned:

```text
FAIL missing A660 GMU resume-entry diagnostic patch
```

The source-only boundary verifier is expected to pass independently:

```text
PASS A660 GMU resume has an entry-only seam after initialization validation and before software mutation, PM domains, clocks, MMIO, IRQ, firmware start, HFI, hardware init, ZAP, or SCM
PASS A660 GMU resume-entry boundary is source-pinned, v7-dependent, error-propagating, and pre-power
```

No phone, ADB, fastboot, SSH, storage, root privilege, build, export, or live
operation is used by this audit.

## Decision

The entry-only source boundary is accepted for fail-first patch development.
The later power-preparation tier remains separate: it may begin with GMU
PM-domain and clock activation only after this entry tier is built,
offline-verified, reviewed through HOLD/GO, run at most once from RAM, and
permanently consumed.

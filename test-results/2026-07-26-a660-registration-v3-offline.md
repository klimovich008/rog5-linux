# A660 registration v3 — exact SMMU reprobe and one-shot gate

Date: 2026-07-26

Result: **PASS offline. Registration v3 carries the live-accepted v21
exact-device SMMU reprobe into the A660 probe, creates a new independently
verified root-owned export, and adds a fail-first target/host control plane
with nested watchdogs, one invocation, private evidence, and immediate normal
fallback. The complete unchanged binary package passes its exact verifier
again. The phone was not contacted, NFS remained inactive, and nothing was
booted or flashed.**

This is a live-eligibility result, not a live A660 registration result. GPU
firmware, first DRM open, rendering, display, suspend, and acceleration remain
locked.

## Defect found before live use

Registration v2 expected the built-in Adreno SMMU to bind automatically as
soon as the GPUCC module loaded. The accepted v21 evidence had already shown
that ordinary autoprobe left `3da0000.iommu` unbound and one exact platform
`drivers_probe` request was required.

V3 fixes that mismatch before any phone action:

1. validate the exact `3da0000.iommu` identity;
2. require exact unset-null `driver_override` through the accepted read-only
   checker;
3. require enabled platform autoprobe, root-owned mode-`0200`
   `drivers_probe`, and absent ARM SMMU force-bind controls;
4. load accepted GPUCC and permit five seconds of ordinary autoprobe;
5. if still unbound, write only `3da0000.iommu` once;
6. require the exact `arm-smmu` bind before loading DRM dependencies or MSM;
   and
7. report `exact_reprobe=0|1` and the exact override classification.

The host acceptance path requires `exact_reprobe=1`, matching the observed
v21 hardware path. Broad rescan, global timeout changes, force-bind, unload,
retry, firmware, DRM open, and storage access remain absent.

## Fail-first results

Tests were changed before implementation and rejected v2 at four independent
boundaries:

```text
FAIL A660 registration baseline omits: rog5-adreno-smmu-driver-override-check
FAIL A660 export path omits: /var/lib/rog5-network-root-a660-registration-v3
FAIL network-root host contract missing: /var/lib/rog5-network-root-a660-registration-v3)
FAIL A660 registration bundle verifier omits: check-adreno-smmu-driver-override-state.sh
```

The watchdog handoff and host-runner tests also failed before their
implementations existed:

```text
FAIL missing A660 network-root watchdog disarm tool
FAIL missing compound A660 registration gate
FAIL missing host A660 registration live-gate runner
```

All now pass, including ordering/count checks and mocked one-invocation SSH
transport.

## V3 target contracts

| Input | SHA-256 |
|---|---|
| baseline | `6e6f7ba046c7db642bdd18905396877a68fd042a92d5ea9383f5be52701c76e8` |
| registration probe | `0e0d8894b1a54d070458483d3752ee2d1a0a167b2bfe3992853284e91d7607e6` |
| NULL-override checker | `884dfcd287dd892ec0698bedaa4475045967459282811da640e48f5f7d503e45` |
| A660 watchdog disarm | `733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc` |
| compound target gate | `13224d8ac0a6eafddac6554a77d08d381312ead2730268859b3a375b778b3364` |

The read-only baseline keeps the original network-root watchdog armed while
checking the exact kernel, four unbound devices, unloaded seven-module set,
accepted marker, exact SMMU override/reprobe controls, zero firmware/render/
DRM descriptors/storage/mounts/failed units, quiet kernel log, and safe
thermals.

After baseline, the compound target gate:

1. arms an independent 180-second SysRq transition watchdog;
2. freezes, terminates, and marks the original watchdog disarmed through the
   A660-release-specific helper;
3. invokes the 90-second independently watched registration probe exactly
   once;
4. leaves transition rollback armed after probe success; and
5. immediately requests nonblocking normal systemd reboot.

The transition watchdog never gets disarmed in the target gate. If normal
reboot does not remove the network root, it resets the target.

## One-shot host contract

Host runner SHA-256:

`512ab814fdc17d25ff8ee555b4b515059695ab95052be85c76a10d26470d7315`

Its test SHA-256:

`863d234959315ae014e73641e53ab21fc12e259a184149f75cdf3a793596c374`

The runner requires:

- exact guard values for registration and immediate fallback;
- clean `agent/linux-recovery-host` Git state synchronized with its
  remote-tracking checkpoint;
- exact temporary-boot image SHA-256
  `c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c`;
- independently verified v3 and v1 exports through PolicyKit;
- private SSH key and known-hosts metadata;
- exact strict host identity and no SSH fallback;
- a fresh caller-owned mode-`0700` evidence directory;
- exactly two hash-pinned mode-`0500` tmpfs controls;
- exact v3 seal and acceptance marker from the immutable NFS lower;
- one remote compound-gate invocation with no retry; and
- a mode-`0600` private log containing baseline, registration,
  `exact_reprobe=1`, and guarded-reboot passes.

The mock transport proves one PolicyKit verifier call, one SSH preparation,
one SCP, one remote verification, one gate invocation, expected reboot
disconnect, and no retry.

## New isolated export

PolicyKit created:

`/var/lib/rog5-network-root-a660-registration-v3`

V1, the old A660 root, v2, and all SMMU diagnostic roots remain preserved.
Only persistent v1 and A660 v3 are server-allowlisted.

Independent verification reports:

```text
PASS v21-accepted exact-reprobe A660 registration v3 export modules=7 firmware=0 credentials=preserved base=unchanged
```

The root state is:

- root-owned mode `0555`;
- root-owned mode-`0444` seal SHA-256
  `33204e2740956caf0b63a946bc377c6800c0a97106401f156394bb2593f0268f`;
- baseline SHA-256
  `6e6f7ba046c7db642bdd18905396877a68fd042a92d5ea9383f5be52701c76e8`;
- probe SHA-256
  `0e0d8894b1a54d070458483d3752ee2d1a0a167b2bfe3992853284e91d7607e6`;
- checker SHA-256
  `884dfcd287dd892ec0698bedaa4475045967459282811da640e48f5f7d503e45`;
- exact v21 acceptance marker;
- exactly seven registration modules;
- zero A660 firmware;
- preserved credentials and unchanged v1 base; and
- seal value `smmu_reprobe=EXACT_PLATFORM_DEVICE_AT_MOST_ONCE`.

The actual privileged root test passed separately. NFS stayed inactive, there
was no export, and `ip_nonlocal_bind` remained zero.

## Complete bundle verification

The exact verifier rechecked the pinned Linux source, accepted v21 predecessor,
v21 report/marker, kernel build, all seven modules, DT, target and nested
initramfs, ASUS wrapper, raw/header-v3/AVB package, v3 export contracts, target
watchdog/gate, and host runner.

It returned:

```text
PASS exact v21-accepted A660 registration bundle; exact SMMU reprobe, four nodes, seven modules, zero firmware/storage/display, reproducible and offline-only
```

All fourteen binary identities remain unchanged from the original reproducible
registration build.

## Live decision boundary

Registration v3 is eligible for one final read-only host/fallback preflight.
If that passes from a clean pushed checkpoint, one attended RAM-only cycle is
technically justified because:

- every new hardware action is under independent reset authority;
- the only direct bus-control write is one exact SMMU device name;
- module order and hashes are exact;
- firmware and DRM opens are forbidden;
- storage is compiled out and checked repeatedly;
- success requests immediate normal fallback; and
- v3 will be consumed regardless of pass or fail.

The live cycle must use `fastboot boot`, never flash, and must not be retried.
Fallback health and complete privileged host cleanup remain separate mandatory
acceptance conditions.

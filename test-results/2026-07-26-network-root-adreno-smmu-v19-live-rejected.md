# Network-root v19 Adreno SMMU — safe no-bind rejection

Date: 2026-07-26

Result: **the corrected baseline passed and GPUCC registered, but the Adreno
SMMU did not bind. Both rollback watchdogs were armed and automatic fallback
plus complete host cleanup passed. V19 is consumed and must not be retried.
The baseline proved zero firmware, GPU/GMU consumers, render nodes, and
storage; the post-failure log showed no indication that any appeared. No
flash, warning, IOMMU fault, fatal signature, failed unit, or unsafe thermal
state occurred.**

## Exact attended boundary

The cycle used the unchanged, manifest-pinned v18/v19 binary through one
temporary `fastboot boot`; nothing was flashed. The image SHA-256 was:

`37e607795794713472d6944cfbc691211365184a2b674118a17c5d9763b893bf`

Recovery ACM enumerated, the existing atomic `confirm-gpucc` transport loaded
the payload and transmitted one non-retryable execute, and
`7.1.4-g7a5cef0db479` reached its exact USB/NFS network root. As in the prior
cycle, the permitted missing-marker race caused one identical staging-load
replay before execute. Strict pinned SSH then verified running systemd with
zero failed units.

The v19 compound gate was invoked once. Its corrected pre-disarm baseline
passed:

`PASS Adreno-SMMU baseline storage=0 mounts=0 firmware=0 render=0 failed_units=0 thermal_zones=29 thermal_max_mC=37100 module_files=1008 pstore_records=1 watchdog=armed smmu=deferred`

The single pstore record existed before the v19 probe. No pstore record was
visible through either accepted fallback pstore path before or after the
cycle, so it is not classified as v19 probe evidence.

After baseline PASS:

1. the 120-second transition watchdog armed;
2. the original network-root watchdog was frozen, terminated, and marked
   disarmed only after that handoff;
3. the independent 75-second probe watchdog armed;
4. the exact external GPUCC module loaded once; and
5. GPUCC reached `registration-complete ret=0` and `insmod` returned.

The probe then waited its full 30-second settling interval. The exact Adreno
SMMU platform device still had no driver link, so the gate returned:

`FAIL Adreno SMMU did not bind after GPUCC registration`

## Failure evidence

The post-failure snapshot reported:

- systemd state `running`;
- zero failed units;
- 29 thermal zones with a maximum of 36.8 C;
- no SMMU probe message after GPUCC registration;
- no warning, call trace, IOMMU fault, fatal signature, firmware request, GPU
  or GMU consumer message, render message, or storage message.

The new kernel log contained only the probe marker and successful GPUCC
registration markers. Because the probe stopped at the driver-link assertion,
it did not rerun its later direct render/storage checks; those are accepted
only as pre-load baseline facts. This is a clean no-bind result, not an SMMU
register access crash.

The complete private gate output remains outside Git in a caller-owned
mode-`0600` evidence file. Device serials, MAC addresses, boot IDs,
credentials, and private evidence are not included here.

## Automatic rollback and host cleanup

The failing probe deliberately left its watchdog armed. The network-root USB
gadget then departed automatically, the bounded NFS process unexported the
root, stopped its private RPC/NFS processes, removed its read-only bind mount,
restored `ip_nonlocal_bind`, removed the temporary address and firewall state,
and exited.

The ordinary fallback host profile and ModemManager were restored. Strict
fallback verification then passed the exact vendor kernel/init/ext4 identity,
zero project modules, zero pstore records, no fatal signature, and safe
thermal telemetry. A separate redacted query reported 70 readable thermal
zones, 38.5 C maximum, zero pstore records, and zero project modules. The host
also verified:

- NFS inactive;
- zero exports and listeners;
- no mount daemon or export mount;
- zero active NFS threads;
- `ip_nonlocal_bind=0`; and
- firewalld and ModemManager active.

## Source diagnosis

The live evidence proves that registering GPUCC alone did not cause this
already-created platform device to attach to the built-in `arm-smmu` driver.
The exact Linux source shows:

- `arm_smmu_device_probe()` obtains all seven DT clocks through
  `devm_clk_bulk_get_all()`;
- a missing GPUCC clock provider initially returns `-EPROBE_DEFER`;
- the accepted kernel uses
  `CONFIG_DRIVER_DEFERRED_PROBE_TIMEOUT=10`;
- GPUCC was intentionally loaded much later, at target uptime 193 seconds;
- successful driver bind normally triggers the deferred-probe workqueue; and
- the `arm-smmu` driver suppresses its per-driver manual `bind` attribute.

The v19 gate did not capture `/sys/kernel/debug/devices_deferred`,
`waiting_for_supplier`, or device-link state, so it cannot distinguish a
device that left the deferred list from one still blocked by a stale supplier
relationship. It is therefore not safe to claim that changing only the global
timeout would fix the issue. A long global timeout would also retry unrelated
deferred devices and is broader than this test requires.

The platform bus exposes a narrower `drivers_probe` path. In the pinned source
it resolves one exact unbound device and calls `device_attach()`; it does not
force-bind a named driver or rescan every device. That path is a candidate for
the next separately versioned control plane, but it must be test-first,
source-pinned, watchdog-bounded, exact-device-only, and preceded by read-only
deferred/supplier evidence. V19 must not be reused for that experiment.

## Current boundary

GPUCC/CCF remains live-accepted from v17. The Adreno SMMU remains **not
accepted**. A660 registration, first DRM open, firmware loading, GMU resume,
ZAP/SCM authentication, rendering, Mesa/Freedreno, display, suspend, and
accelerated desktop remain locked.

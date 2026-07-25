# Network-root v9 GPUCC-only diagnostic — live result

Date: 2026-07-25

Result: **bounded diagnostic failure with successful rollback**. The SM8350
GPU clock controller still stopped system progress when it was the only
newly enabled hardware block. MMIO mapping and both existing Lucid PLL
configuration calls completed. The following clock/reset/GDSC registration
boundary did not return before USB and SSH stopped responding.

The independent SysRq watchdog reset the phone to the exact persistent
fallback. Nothing was flashed, no phone storage was exposed to Linux 7.1,
and all host NFS/firewall state was removed.

## Scope and safety boundary

- Temporary `fastboot boot`, followed by a separately authorized RAM kexec.
- Linux `7.1.4-g7a5cef0db479` with OverlayFS over a read-only NFSv4.2 lower.
- SCSI/UFS absent from the kernel, zero physical block devices, and zero
  block-backed mounts.
- Only `/soc@0/clock-controller@3d90000` changed from `disabled` to `okay`.
- GPU, GMU, Adreno SMMU, display, UFS, RTC, power key, and every remote
  processor remained explicitly disabled.
- The traced GPUCC module was supplied only from target tmpfs, root-owned,
  mode `0400`, and hash-pinned.
- The normal network-root rollback watchdog remained armed through the full
  baseline gate. It was then disarmed and replaced by the probe's independent
  75-second process-group SysRq watchdog before `insmod`.
- No GPU firmware, credential, personal data, or private device identifier
  entered the bundle or this report.

## Reproducible candidate

Two independent GPUCC-trace kernel builds used the exact accepted source and
output paths needed to preserve the vDSO build identity. Their complete build
trees, ordinary Images, configs, module archives, and external traced modules
matched byte-for-byte. The ordinary network-root Image remained identical to
the accepted build; only the external diagnostic module contained the
default-off trace.

Two GPUCC-only DTB builds, two nested staging initramfs builds, two ASUS
wrapper builds, and two Android header-v3/AVB repacks also matched
byte-for-byte. The complete specialized bundle verifier passed.

| Artifact | SHA-256 |
|---|---|
| accepted Linux 7.1.4 Image | `349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf` |
| accepted module archive | `5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9` |
| GPUCC-only DTB | `e6f86c3022f58a765351b5b761c8bc815b093209517adb4678107d542ff5bcb5` |
| nested staging initramfs | `bfc082865cd7f0c7d426d81ed7340b018757107d2cd16040c6f2f41f547cf76f` |
| ASUS wrapper Image | `2c0c913753c8e52cfceb3dd2c62283fb55bd216dcd4103c17615a8632581b1e4` |
| raw boot image | `537b3676b95b20d5868582adb8ecda64889b1c06360325694cbf656dc0ace017` |
| temporary-boot AVB image | `43d3590c7ec0434f7b2d7d719690a66cde2597e09d8883a1f0f20af190486e21` |
| external traced `gpucc-sm8350.ko` | `5f7018e53eb576579fe8d199171ae6e17c4e9d31ad099a330d21e050c0ad4454` |

The trace patch is SHA-256
`50ec8d394583951ab00e65c38686775031d0abadc6a3faf1730edda13eb7be94`.
It applies to base commit `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`
and produces tree `e22549ee4d4d788b6898f374e8edecfc714797ac`.
The module parameter is read-only, defaults off, and does not add, skip, or
change a hardware access.

## Live baseline

Before watchdog disarm, the target passed:

- exact Linux 7.1.4 and systemd PID 1 in `running` state;
- runtime masks on only `systemd-udev-trigger` and
  `systemd-modules-load`;
- zero failed units and zero fatal kernel signatures;
- OverlayFS `/`, exact read-only NFSv4.2 lower, and stable USB carrier;
- a complete read of all 1,008 files in the matching module tree;
- zero physical block devices and zero block-backed mounts;
- GPUCC `okay`, with all listed consumers and unrelated hardware disabled;
- no loaded GPUCC module and no DRM render node; and
- the original rollback watchdog present and armed.

The copied probe, watchdog-disarm helper, and module matched their host hashes
and exact tmpfs ownership/modes before execution.

## Probe trace

The host received these ordered phase markers:

```text
begin
map-complete
pll0-begin
pll0-complete
pll1-begin
pll1-complete
```

No `registration-begin`, `registration-complete`, or `insmod` return marker
reached the host. USB NCM and SSH then became unresponsive. Because the
transport failed at the same boundary, absence of `registration-begin` does
not prove that `qcom_cc_really_probe()` was never entered; its final log line
may have been lost with the transport.

The probe watchdog reset the phone. Strict key-only SSH then verified the
exact fallback kernel and ext4 root. Standard pstore was mounted read-only
for inspection and contained no retained file, so it cannot narrow the final
sub-phase.

## Cleanup

The attended NFS process observed target departure and removed its export,
listener, bind mount, NFS threads, temporary sysctl, firewall rules, and
`/30` address. The fallback profile is intentionally non-autoconnecting, so
the host reactivated that one exact `/16` USB profile after cleanup.

Final checks passed:

- exact fallback kernel and strict SSH;
- zero Fastboot and ADB devices;
- inactive system NFS service and mount daemon;
- zero exports, NFS/mountd listeners, and NFS threads;
- no network-root bind mount or temporary firewall rule;
- restored nonlocal-bind sysctl;
- clean drop zone and active ModemManager; and
- no retained pstore fatal signature.

## Decision and next gate

The GPUCC-only tier is **rejected for normal coldplug**. Disabling GPU, GMU,
SMMU, display, and remote processors does not remove the stall, so consumer
binding was not the cause of the earlier failure.

The next candidate must keep the same DT and zero-storage boundary while
instrumenting the built-in Qualcomm common-clock path around:

1. generic power-domain attachment;
2. reset-controller registration;
3. GDSC allocation and registration;
4. each hardware-clock and regmap-clock registration; and
5. clock-provider publication.

That kernel must first have two byte-identical clean builds and mutation tests
which prove tracing is default-off and diagnostic-only. A second live attempt
is not justified until those finer phase markers, the independent watchdog,
and the unchanged consumer-disabled DT contract all pass offline.

# Network-root v7 ADSP prerequisite — live result

Date: 2026-07-25

Result: **passed for ADSP-only bring-up**. The stock-owned RAM map fixed the
secure-loader rejection, ADSP remained running through the guarded settle
window, and the phone returned to the exact persistent fallback. Battery
telemetry, PMIC GLINK, charging, Type-C control, display, GPU, UFS, and the
other remote processors were not enabled by this test.

## Scope and safety boundary

- Temporary `fastboot boot` followed by an attended RAM kexec; nothing was
  flashed.
- Linux `7.1.4-g7a5cef0db479` with OverlayFS over a read-only NFSv4.2 lower.
- UFS/SCSI absent from the kernel, zero physical block devices, and zero
  block-backed mounts.
- PMK8350 RTC disabled and never written.
- Only the ADSP DT node changed from disabled to okay.
- Modem, CDSP, SLPI, GPU, display, PMIC GLINK, battery, UCSI, and alt-mode
  paths remained disabled or unloaded.
- The 29-file stock ADSP firmware set was copied only to target tmpfs. It and
  all private SSH material remained outside Git and all boot artifacts.
- A target SysRq watchdog was armed before firmware selection or module load.

## Reproducible candidate

The accepted v5 recovery DTB first received only these stock-owned
reservations:

| Start | Size | Runtime mapping |
|---|---:|---|
| `0xcbc00000` | 68 MiB | mapped |
| `0xd8000000` | 8 MiB | `no-map` |
| `0xedc00000` | 288 MiB | mapped |

The ADSP candidate then changed only
`/soc@0/remoteproc@3000000/status` from `disabled` to `okay`.

Independent builds produced:

- memory-safe DTB SHA-256
  `80a27e3464c5536ec4f14cda44f3deb76fca80d6a805b83a33b77919a2d5eb13`;
- ADSP DTB SHA-256
  `4c0a3bd76e0d79fcaabfb34c305688886ba856decd434267340b6d968249eeec`;
- nested staging initramfs SHA-256
  `897dca3493f317350d9ce8b8fb4359d67c9cd64f002be69c4f74693e43c396ea`;
- ASUS wrapper Image SHA-256
  `0c2cf72b46695ec505376a7c62b3bd7115e7678de71964fb595314d09ab1775b`;
- raw header-v3 image SHA-256
  `1b3d738256327c636fe5487c65ae55f4e3d8443be266c4c35fd8a39a99b264f1`;
  and
- AVB-sized temporary boot image SHA-256
  `31c33cf4aeea960b41c72d3e2eaf4a8b0e7f9832e574f137a61b19076fd3d68c`.

Both clean kernel builds, both nested initramfs builds, both ASUS wrappers,
and both Android image repacks were byte-identical. The complete bundle
verifier passed, and no private firmware was present in the artifact tree.

## Root cause

Two earlier ADSP-only attempts reached `qcom_scm_pas_init_image()` but secure
firmware returned `-EINVAL`. Kprobe evidence recorded the metadata DMA
address as `0xfe400000`.

The candidate memory banks treated that address as ordinary RAM. The stock
runtime FDT and `/proc/iomem`, however, reserve
`0xedc00000-0xffbfffff`. Existing upstream nodes already covered the other
vendor/hypervisor spans, leaving exactly the three board-specific ranges
listed above absent from the mainline DTS.

With those ranges reserved, the first v7 live run allocated metadata at
`0xec000000`, outside every stock-owned range. The outer PAS call and the
underlying SCM call both returned `0`, and remoteproc reached `running`.
This isolates the rejected runs to an incomplete board memory contract, not
bad firmware, signatures, or a stale secure state.

## Guarded live runs

The first v7 run passed the hardware gates but the test harness rejected one
new module, `qrtr`. That is the expected Qualcomm IPC router core exposed by
the ADSP `IPCRTR` RPMsg endpoint. No power-supply device, physical block
device, warning, fault, remoteproc crash, or fatal signature appeared. The
still-armed watchdog reset the phone and complete host cleanup passed.

The probe was tightened so `qrtr` must be absent before ADSP startup, present
afterward, and remain the only additional IPC core allowed by this tier. A
second boot of the same candidate then passed:

- ADSP remoteproc state `running`;
- exact stock firmware name;
- all expected PAS/GLINK dependencies, including `qrtr`;
- zero power-supply devices;
- zero physical block devices and zero block-backed mounts;
- read-only NFS lower and stable USB carrier;
- running systemd with zero failed units;
- no new warning, call trace, IOMMU fault, remoteproc crash, or fatal
  signature;
- no unreviewed module; and
- clean trace-probe and independent-watchdog teardown.

Normal systemd reboot returned to
`5.4.134-qgki-perf-00001-g6c308144c23e` Alpine fallback. ModemManager, the
fallback `/16`, and strict key-only SSH were restored. The attended NFS
export, listener, kernel threads, `/30`, temporary firewall state, and all
target tmpfs inputs were absent afterward.

The same cycle also live-validated the host disconnect fix:
`serve-network-root.sh` configures the exact USB interface once, then only
monitors it. Gadget departure ended the attended export normally instead of
racing a redundant interface update.

## Accepted and pending

Accepted:

- the three ASUS stock-owned memory reservations in the board DTS;
- ADSP authentication/startup as a prerequisite for read-only battery
  telemetry; and
- `qrtr` as the exact expected IPC core in the ADSP-only module set.

Still pending:

1. build and independently reproduce the telemetry DTB with only PMIC GLINK;
2. use the battery-only PMIC GLINK diagnostic module;
3. expose only the three read-only Qualcomm battery-manager supplies;
4. validate capacity, voltage, current direction, temperature, and status;
5. keep UCSI, alt-mode, charge thresholds, charging control, RTC, storage,
   and every other remote processor absent; and
6. repeat normal rollback and complete host cleanup.

No charging or Type-C-control experiment is authorized by this ADSP result.

# Read-only UFS discovery v1 offline result

Status: **PASS offline; live gate pending**. This bundle is for one attended
temporary `fastboot boot` and kexec test. It must never be flashed.

## Safety boundary

- Linux 7.1.4 commit `44fd886a77b8edd4ea2abda8f72835045d877e18`
  contains the two-patch compile-time discovery boundary.
- SCSI/UFS userspace write paths are removed, data-to-device and
  bidirectional commands are rejected, and the SCSI/query whitelists are
  exact.
- Every physical disk and partition is forced and verified read-only before
  USB is exposed.
- The target performs no `blkid`, filesystem probe, mount, fsck, raw-device
  read, partition operation, or write test. Its inventory is sysfs-only.
- Both initramfs layers are credential-free and arm independent forced-reboot
  watchdogs.

An earlier local build was rejected before packaging or phone use because
`CONFIG_PHY_QCOM_QMP_UFS=m`. The accepted config promotes the QMP parent and
UFS PHY to built-ins, verifies the complete UFS power/reset/interconnect path
as built-in, and disables the unused QMP Combo, PCIe, and USB drivers.

## Reproducibility and verification

- The patch/config/object verifier passes against pinned Linux v7.1.4.
- Two fresh mainline output volumes produce identical config, `Image`,
  `Image.gz`, and metadata.
- The target initramfs and reviewed UFS/USB2 DTB each reproduce byte-for-byte.
- Two fresh ASUS wrapper builds produce identical config, embedded initramfs,
  `Image`, and metadata.
- Two header-v3 repacks and their unsigned AVB images are byte-identical.
- The exact thirteen-file manifest passes the complete verifier with
  container networking disabled.
- The final verifier reconstructs the DTB, extracts both initramfs layers,
  validates nested payload hashes, checks credential absence and execution
  ordering, confirms the exact boot command line, and verifies the AVB footer.

No discovery artifact was transferred to or booted on the phone during this
offline phase. Nothing was flashed or written to a phone partition.

## Candidate products

| Product | Size | SHA-256 |
|---|---:|---|
| ASUS wrapper Image | 69,372,416 | `7076e4e8ba5f9a45973548d0d5a39053b34c4073339439e0416f5e3de64ee0f1` |
| ASUS wrapper config | 185,763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| embedded/staging initramfs | 26,605,982 | `b7167128595e03122fcfb393b5d8e7b1909ec2217a59bad52909879217ede5fd` |
| Linux 7.1.4 discovery Image | 38,406,656 | `65a31b61d4c81c6c4d46825f0111de66ecb1eb668331a89ba0e7f8154a89aa68` |
| Linux 7.1.4 discovery config | 242,248 | `f36d92cadc1d9982157143a02631c25a2ea88a71e32034305a59ac26b693c1eb` |
| ASUS base DTB | 102,719 | `e1b7ec966d5ad66febaeb10e7bbff0d92b7e83ab4159d9727e5a175b719bedeb` |
| UFS/USB2 discovery DTB | 102,766 | `36802458928e2970a0043f6a27d106e6aa4911fd89b2f548e7c08275d164aaf0` |
| target initramfs | 5,840,536 | `18041cc1c87eb7ee2b22583ce086ae29b498d3961e09942d6e1d30114189a813` |
| raw header-v3 image | 95,985,664 | `e79f5d6184d6ba69ba50e4a1ed5412234906bf76a0ca12563047a5add4e73130` |
| unsigned AVB image | 100,663,296 | `a991f1d2bbd7b63ce854e9d8d4bcde17fffc125fcd2928629213dc72a53f17ca` |

The canonical per-file manifest is generated locally as
`artifacts/ufs-discovery-v1/SHA256SUMS`; its thirteen identities are mirrored
in `manifests/artifacts.tsv`.

## Next gate

The live gate is one manifest-pinned temporary boot. Staging must first prove
a RAM root, zero block-backed mounts, complete read-only fallback-visible
storage, exact recovery USB, and an armed watchdog. Loading and executing the
mainline payload remain separate attended commands. The discovery target must
attest its exact kernel/config, enumerate at least one UFS physical disk with
every disk and partition read-only, produce the sysfs-only topology report,
and automatically return to the exact fallback kernel.

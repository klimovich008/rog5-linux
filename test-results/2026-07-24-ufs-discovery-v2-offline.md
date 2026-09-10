# Read-only UFS discovery v2 offline result

Status: **PASS offline; subsequent live gate passed**. The corrected bundle
was eligible only for one attended temporary `fastboot boot` plus separately
authorized kexec execution. It must never be flashed.

## Reason for v2

Discovery v1 safely enumerated all 116 UFS disks and partitions read-only, but
runtime PM attempted three auto-BKOPS `SET_FLAG` queries after enumeration.
The command boundary blocked all three, then upstream UFS error recovery made
orderly shutdown hang.

The deterministic third patch:

- retains the UFS host runtime reference acquired before async scan;
- forbids runtime PM on the host and device WLUN;
- disables auto-hibern8;
- rejects WLUN and host power transitions before BKOPS or suspend calls; and
- skips WLUN shutdown transitions so platform reset can occur with the
  read-only link active.

The target initramfs now checks the three active-link markers and requires
zero blocked query and SCSI commands twice: after stable enumeration and
again immediately before USB binding. Its rollback path arms an independent
five-second SysRq fallback before launching orderly forced reboot in the
background, so a device-shutdown stall cannot block emergency reset again.

## Source and test-first gate

- Base Linux: `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`
  (`v7.1.4`)
- Patched commit: `cfd385a1c754684dd28b63a4559e04baa5e902b1`
- Patched tree: `d2f03d2055227b8b72ab41be949847a066924c5a`
- Third patch SHA-256:
  `5dea8cc5814c9c02bdcf7625fc002ee2917c3261b89dabee8a80d463eb155929`

The strengthened source verifier first failed against the prior two-patch
series. After the containment patch was added, it applied all three patches
to a clean pinned tree, proved each return occurs before the corresponding
power or shutdown operation, enforced the exact command whitelists, and
compiled the guarded SCSI/UFS objects.

The target-init test likewise failed before the marker/count checks existed
and passed after both pre-USB checks were implemented.

## Reproducibility

- Two independently prepared source volumes produced the same patched commit
  and tree.
- Two fresh mainline output volumes produced byte-identical `.config`,
  `Image`, `Image.gz`, and build metadata.
- Two target initramfs builds, two reviewed discovery-DTB builds, and two
  nested staging-initramfs builds were byte-identical.
- Two fresh ASUS wrapper output volumes produced byte-identical config,
  embedded initramfs, Image, and metadata.
- Two Android header-v3 repacks and unsigned AVB images were byte-identical.
- The complete thirteen-file manifest passed with container networking
  disabled.

The final verifier reconstructed the DTB, extracted both initramfs layers,
verified all nested payload hashes and execution ordering, checked that no
credential or SSH identity was embedded, validated the wrapper and mainline
configs and compiled guard markers, reconstructed the boot command line, and
verified the AVB footer.

## Canonical products

| Product | Size | SHA-256 |
|---|---:|---|
| ASUS wrapper Image | 69,372,416 | `0acf9d0058a191a02eeadd554bea05270e30d43f332856c0096fe7480154572c` |
| ASUS wrapper config | 185,763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| embedded/staging initramfs | 26,608,603 | `fcf147c4dc91323caaed4be8767545441f9df31323e4513e62c99ac20ac789e9` |
| Linux 7.1.4 discovery Image | 38,406,656 | `bdc72155b4ff2de3a655f53e0570a18690778025cac86425fccd5d3b9699ac8c` |
| Linux 7.1.4 discovery config | 242,248 | `f36d92cadc1d9982157143a02631c25a2ea88a71e32034305a59ac26b693c1eb` |
| ASUS base DTB | 102,719 | `e1b7ec966d5ad66febaeb10e7bbff0d92b7e83ab4159d9727e5a175b719bedeb` |
| UFS/USB2 discovery DTB | 102,766 | `36802458928e2970a0043f6a27d106e6aa4911fd89b2f548e7c08275d164aaf0` |
| target initramfs | 5,841,750 | `df1d0cdb95513d7ef6d772a3a6165d37b3b226682d92e30a2143409341bbefb1` |
| raw header-v3 image | 95,989,760 | `92bfd8c385cbaa377c9e544aee94d9ba3259691d922913f713c7d1e2df20b189` |
| unsigned AVB image | 100,663,296 | `d22790e5b8aebba0dc78a6704b7d2845b0e4637e1256acd379e7dd6170f1540b` |

The exact local manifest is
`artifacts/ufs-discovery-v2/SHA256SUMS`; all thirteen canonical identities are
mirrored in `manifests/artifacts.tsv`.

No v2 artifact was transferred to or booted on the phone during this offline
phase. The later attended result is recorded in
[`2026-07-24-ufs-discovery-v2-live.md`](2026-07-24-ufs-discovery-v2-live.md).
No partition was mounted, written, resized, formatted, or flashed.

## Completed live gate

The v2 target reached exact release `7.1.4-gcfd385a1c754`, attested the
compile-time guard, reported all 116 physical nodes read-only with zero
block-backed mounts, and exposed both automatic containment passes with:

```text
blocked queries=0 blocked SCSI=0
```

No UFS error handler, blocked command, or fatal signature appeared. The
untouched target watchdog chain automatically returned the phone to the exact
fallback kernel with a changed boot identity and no manual intervention.

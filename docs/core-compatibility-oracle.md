# Core compatibility oracle

The core compatibility oracle turns the proven ASUS 5.4 behavior and accepted
Linux 7.1 network-root result into a reviewable, machine-enforced contract.
It is the entry gate for another 7.1 build and the starting behavioral
contract for any future 6.x/7.x kernel evaluation.

It does not prove a new phone boot. It cannot sign, package, flash, reboot, or
contact the phone.

## Files

- `configs/compatibility/rog5-minimal-headless-v1.json` is the canonical
  profile.
- `configs/compatibility/rog5-minimal-headless-v1.config` is a small committed
  positive Kconfig fixture for hardware-free CI.
- `scripts/host/verify-core-compatibility-oracle.py` is the fail-closed
  verifier.
- `scripts/host/test-core-compatibility-oracle.py` is the mutation and CLI
  regression suite.
- `scripts/device/collect-minimal-headless-runtime.sh` and
  `scripts/host/verify-minimal-headless-runtime.py` turn one future live
  observation into a candidate-bound record without changing the phone.
- `scripts/host/pin-minimal-headless-host-key.py` binds volatile target
  host-key discovery to exact recovery/target USB continuity before the
  strict-SSH runtime runner can use a client key.
- `scripts/device/verify-mainline-network-root-build.sh` invokes the oracle
  against every completed network-root kernel build.

## What the profile means

`phase` describes roadmap scope. It is not a live-result field.
`candidate_status` is the only capability acceptance field.

The six active capabilities have `accepted-ancestry`, meaning their exact
historical evidence, candidate ancestry, configuration requirements, and CI
gates are preserved:

| Capability | Contract |
|---|---|
| `cpu-ram` | ARM64/SMP/PSCI, initrd, cgroups, memory control, CPU idle, and at least eight CPUs |
| `read-only-network-root` | NFSv4/OverlayFS/tmpfs root plus explicit SCSI/UFS/RPMB exclusion; this is the active storage-isolation gate |
| `usb-ncm-network` | IPv4/IPv6 plus Qualcomm DWC3 USB2 and NCM gadget support |
| `init-key-only-ssh` | devtmpfs and embedded-config requirements, paired with the minimal root and strict-SSH CI gates |
| `watchdog-rollback-reboot` | kexec, SysRq, PM, target-init, and guarded recovery-runner gates |
| `thermal-readonly` | thermal framework and Qualcomm TSENS with retained live read-only evidence |

Each active capability now also names the focused target-probe and
host-verifier regression tests. SSH and rollback additionally name the
one-collection strict-SSH runner test. USB and SSH additionally name the
credential-free host-key bootstrap suite. This links compile-time ancestry to
the exact runtime evidence that must pass before the corrected root can move
from `live-pending`.

All six active capabilities additionally name the
[core source/DTB contract](core-source-dtb-contract.md). That gate verifies
the Kconfig declarations, Makefile object paths, OF tables, SM8350 bindings,
source entry points, and corrected DT topology that a config-only check
cannot see.

Future capabilities remain unaccepted:

- display-off operation is baseline evidence only; `CONFIG_PM` is necessary
  but does not prove the OLED is off;
- buttons and battery have baseline diagnostic evidence only, not
  corrected-candidate evidence;
- suspend/resume, sensors, and audio remain pending.

Internal UFS access is not silently accepted by the network-root capability.
The active profile intentionally compiles that path out. Read-only UFS
discovery and any later persistent-root work remain separate hardware and
authorization tiers.

## What is verified

The verifier requires:

- exact profile, baseline, authority, candidate, and integration identities;
- canonical JSON with duplicate-field rejection;
- ordinary in-repository evidence paths with pinned SHA-256 values and
  byte-present markers;
- a pinned artifact-manifest SHA-256 and exact size/hash rows;
- byte-identical accepted/candidate kernel Image identities;
- the exact authority-free corrected candidate JSON and its Image, DTB, and
  initramfs ancestry;
- complete active/future capability coverage;
- canonical Kconfig input, exact positive requirements, integer minima, and
  absent-or-disabled forbidden symbols;
- every active gate as an exact CI-array entry; and
- the exact oracle invocation from the kernel build verifier.

Files are opened once with `O_NOFOLLOW`, bounded with `fstat`, and checked for
change while read. Symlinked inputs, linked path components, path escapes,
control characters, noncanonical LF records, malformed list members, and
cross-capability Kconfig contradictions fail closed.

Historical large artifacts are identity evidence: the profile and pinned
manifest bind their expected size and SHA-256, while GitHub CI does not
require those ignored binary files to exist. Local retained-artifact checks
verify the accepted 7.1 config when it is available. Candidate packaging and
boot gates independently verify actual payload bytes before use.

## Run it

Metadata and ancestry only:

```sh
scripts/host/verify-core-compatibility-oracle.py --metadata-only
```

Verify a completed kernel configuration:

```sh
scripts/host/verify-core-compatibility-oracle.py \
  --kernel-config /path/to/kernel-output/.config
```

Run the mutation suite:

```sh
scripts/host/test-core-compatibility-oracle.py
```

Run the complete hardware-free repository gate:

```sh
scripts/host/test-repository-linux.sh ci
```

The CLI requires either `--metadata-only` or `--kernel-config`. A metadata-only
pass prints `status=metadata-only`; only a verified Kconfig prints
`status=ready`. Both retain `new_root_state=live-pending` and
`authority=none`.

## Applying it to another kernel

1. Start with a reproducible source, toolchain, config, Image, modules, and
   DTB build.
2. Make the new config pass the active oracle without weakening an active
   requirement.
3. Run the hardware-free build, DTB, rootfs, recovery, QEMU, and mutation
   suites.
4. Treat every changed kernel, DTB, initramfs, or root component as a new
   runtime combination. Historical bundle behavior does not transfer merely
   because one component is byte-identical.
5. Add one bounded runtime capability at a time and promote its evidence only
   after rollback and fallback pass.

A compile or oracle pass is necessary ancestry evidence. It is never a
substitute for phone-side CPU/RAM, storage, USB, SSH, lifecycle, thermal, or
hardware acceptance.

The
[minimal-headless runtime acceptance contract](minimal-headless-runtime-acceptance.md)
defines that next phone-side record and its offline mutation coverage.

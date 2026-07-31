# Core kernel-source and DTB contract

The core source/DTB contract detects missing kernel integration before a
future ROG Phone 5 kernel candidate is built or booted. It complements the
[core compatibility oracle](core-compatibility-oracle.md): the existing
oracle checks evidence, payload ancestry, Kconfig, and CI wiring, while this
contract checks that the selected source tree still contains the driver,
binding, and object-build paths needed by the corrected headless DTB.

The accepted Linux 7.1.4 source and corrected DTB pass the contract. This is
hardware-free compatibility evidence, not permission to boot and not evidence
that a changed kernel works on the phone.

## Covered boundary

The machine-readable profile is
`configs/compatibility/rog5-core-source-dtb-v1.json`. It is bound to the six
active minimal-headless capabilities:

- CPU/RAM and Qualcomm EPSS CPU frequency control;
- read-only NFS/OverlayFS network root with UFS isolated;
- Qualcomm USB2 DWC3, FEMTO PHY, ConfigFS, and NCM;
- devtmpfs and embedded Kconfig visibility used by the key-only SSH root;
- kexec, reboot, SysRq, and PM rollback primitives; and
- generic thermal support, Qualcomm TSENS, CPU thermal cooling, and static
  PMIC temperature-alarm integration.

Forty-three source checks cover:

- canonical Kconfig declarations;
- Makefile object wiring;
- comment-aware OF match-table compatibles, module aliases, attachment to the
  registered platform driver, and driver registration;
- primary SM8350 compatibles in DT binding YAML; and
- source entry points that implement NFS root, OverlayFS, NCM, devtmpfs,
  embedded config, kexec/reboot/SysRq, TSENS v2 critical interrupts, PMIC
  temperature alarms, thermal critical trips, and the default hardware
  protection shutdown path.

Twenty-three DT checks cover:

- exact ASUS/SM8350 board identity, root address/size cell widths, and the
  accepted four-bank memory geometry, including the retained zero-sized
  terminal range;
- the `/cpus` address/size cell widths and all eight CPU nodes, including
  exact two-cell `reg`/MPIDR, `device_type`, PSCI enable method, cooling-cell
  width, and exact `clocks` and `qcom,freq-domain` mappings;
- the EPSS cpufreq node and exact provider cell widths, yielding domains
  `0-3`, `4-6`, and `7`;
- disabled UFS controller and UFS PHY;
- enabled USB2 PHY and primary high-speed peripheral DWC3 path, including
  enabled ancestors, mandatory zero PHY cells, and the exact
DWC3-to-USB2-PHY phandle;
- disabled USB3/QMP and secondary USB paths;
- PSCI reset; and
- both accepted TSENS nodes and their exact sensor counts.

The thermal policy adds an exact cross-node contract above the 23 generic DT
checks. It requires both enabled TSENS controllers, their `uplow` and
`critical` PDC routes, the PDC-to-GIC parent, all 12 CPU thermal zones, exact
90/95 C passive and 110 C critical trips, 250 ms passive polling, two
step-wise cooling maps per zone, the correct four-CPU cooling cluster, and
unbounded cooling-state selectors. It also requires five enabled
`qcom,spmi-temp-alarm` nodes and their exact PMIC zones, interrupts, 95 C
passive trips, 115 C critical trips, and 100 ms passive polling. Sensor
references are range-checked and globally unique.

The PMIC critical trip node names are verbatim from the exact accepted DTB:
several zones intentionally share `pm8350c-crit` or `pmr735a-crit`. They are
not normalized to match the surrounding zone name.

This is static structure only. The accepted config builds
`qcom-spmi-temp-alarm` as a module, and its emergency poweroff delay is zero.
The contract therefore does not claim that PMIC alarms bind early enough or
that forced shutdown follows a failed orderly shutdown. Those are separate
future compatibility capabilities.

Global CPU and system-memory inventories reject an additional `cpu@` child,
any node with `device_type = "cpu"`, an additional root `memory@` node, or any
node with `device_type = "memory"`, even when it lies outside the listed
paths.

The source check reads every required file through a bounded, no-follow
descriptor. It rejects path escapes, linked inputs, dirty or non-root Git
worktrees, untracked files, duplicate JSON, missing build rules, missing
driver registration or match-table attachment, commented-out source tokens,
and narrowed capability coverage. The shared DTB parser likewise reads one
bounded descriptor and rejects linked, changing, malformed, truncated,
overlapping, or non-v17 DTBs. A global inventory also rejects any effectively
enabled SM8350 UFS or QMP USB3 controller/PHY compatible, including duplicate
nodes outside the 23 accepted paths.

## Baseline mode

Baseline mode requires both accepted identities:

```sh
scripts/host/verify-core-source-dtb-contract.py \
  --kernel-source /path/to/clean/linux-7.1.4 \
  --source-role baseline \
  --dtb artifacts/network-root-v3/sm8350-asus-rog-phone5-recovery.dtb \
  --dtb-role baseline
```

The source must be an exact clean Git worktree at
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`. The DTB must be exactly
102,870 bytes with SHA-256
`86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46`.
A pass reports `status=baseline-verified`.

The retained source tree and ignored DTB are optional local artifacts. The
current host copy is the rootless Podman volume
`rog5-mainline-v19-source`; it is a retained compatibility-oracle input and
must not be included in a host cleanup plan. A fresh GitHub checkout runs the
complete synthetic mutation suite without requiring either large retained
input.

## Candidate mode

Candidate mode evaluates a clean new kernel tree or a newly built DTB against
the same active contract:

```sh
scripts/host/verify-core-source-dtb-contract.py \
  --kernel-source /path/to/clean/candidate-linux \
  --source-role candidate \
  --dtb /path/to/candidate-board.dtb \
  --dtb-role candidate
```

Source and DTB roles are independent, so a rebase can compare one changed
side at a time. Candidate mode requires semantic compatibility but does not
require the accepted commit or byte-identical DTB. Its result is deliberately
`status=compatible-not-accepted`, `hardware_acceptance=unproven`, and
`authority=none`.

If an upstream reorganization moves a source path or replaces a compatible,
the contract fails. Review the new driver, binding, Kconfig dependency,
Makefile wiring, and generated DTB before updating the profile. Do not weaken
the profile merely to make a rebase pass.

## Tests

Run the focused suite:

```sh
scripts/host/test-core-source-dtb-contract.py
```

To include the retained accepted source and DTB positive case:

```sh
ROG5_ACCEPTED_KERNEL_SOURCE=/path/to/clean/linux-7.1.4 \
  scripts/host/test-core-source-dtb-contract.py
```

Run all hardware-free repository checks:

```sh
scripts/host/test-repository-linux.sh ci
```

The 74-case focused suite creates disposable synthetic Git trees and DTBs. It
does not build a kernel, contact the phone, use a credential, change host
network state, delete storage, or grant live authority.

See the
[static thermal-policy result](../test-results/2026-07-31-thermal-policy-static-oracle-offline.md),
[CPU/RAM topology result](../test-results/2026-07-29-cpu-ram-topology-offline.md)
and the earlier
[source/DTB result](../test-results/2026-07-29-core-source-dtb-contract-offline.md).

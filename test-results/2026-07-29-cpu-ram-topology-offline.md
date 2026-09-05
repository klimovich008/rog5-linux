# CPU/RAM topology and CPUfreq acceptance — offline

Date: 2026-07-29

Result: **PASS hardware-free; accepted source and corrected DTB verified;
runtime hardware acceptance pending; authority=none**

## Outcome

The minimal headless compatibility gate now treats CPU/RAM behavior as an
exact device contract instead of only requiring a CPU-count and memory floor.
It binds the accepted Linux 7.1.4 source, corrected DTB, kernel configuration,
and next live runtime observation without contacting the phone.

The kernel configuration requires:

- `CONFIG_ARM_QCOM_CPUFREQ_HW=y`;
- `CONFIG_CPU_FREQ=y`;
- `CONFIG_CPU_FREQ_DEFAULT_GOV_SCHEDUTIL=y`; and
- `CONFIG_CPU_FREQ_GOV_SCHEDUTIL=y`.

The corrected DTB contract now checks 23 nodes. Its CPU/RAM portion requires:

- exact root address/size cell widths and the accepted four-entry memory
  `reg`, including its zero-sized final entry, without interpreting that entry
  as usable RAM;
- exact `/cpus` address/size cell widths and eight enabled CPU nodes with
  exact two-cell `reg`/MPIDR plus Cortex-A55, Cortex-A78, and Cortex-X1
  identities;
- `device_type = "cpu"`, `enable-method = "psci"`, and
  `#cooling-cells = <2>` on every CPU;
- both `clocks` and `qcom,freq-domain` to resolve to the exact EPSS provider;
- frequency domain 0 for CPUs 0–3, domain 1 for CPUs 4–6, and domain 2 for
  CPU 7; and
- exact `#clock-cells = <1>` and `#freq-domain-cells = <1>` on the provider.

Global inventories additionally reject any ninth `cpu@` child, any other node
declaring `device_type = "cpu"`, a second root `memory@` node, or any other
node declaring `device_type = "memory"`.

The only compatible-less DT checks are the memory node and `/cpus` container.
The profile validator rejects adding or removing those exceptions, empty
phandle arguments, or phandle-array targets that are not themselves covered
by the contract.

## Runtime acceptance

The read-only runtime record grows from 48 to 55 ordered fields. In addition
to the existing RAM envelope, it now requires:

```text
cpu_online_count=8
cpu_online_set=0-7
cpu_present_set=0-7
cpufreq_policy_count=3
cpufreq_policy_names=policy0;policy4;policy7
cpufreq_policy_cpu_sets=0 1 2 3;4 5 6;7
cpufreq_policy_drivers=qcom-cpufreq-hw;qcom-cpufreq-hw;qcom-cpufreq-hw
cpufreq_policy_governors=schedutil;schedutil;schedutil
```

These values follow the accepted DT domain mapping and the accepted driver's
registered name. They are specified and mutation-tested offline; they have
not yet been observed on the corrected temporary target.

## Verification

The following focused gates pass:

| Gate | Result |
|---|---:|
| core compatibility profile/config | 34 tests passed |
| retained source and corrected DTB contract | 53 tests passed |
| target runtime fixture | golden record plus 13 rejected mutations |
| host runtime verifier | 20 tests passed |
| strict-SSH one-collection runner | passed |
| Python compile, JSON parse, shell syntax, ShellCheck, diff check | passed |
| complete hardware-free repository `ci` tier | passed |

The retained source positive case used exact commit
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`. The corrected DTB remained
102,870 bytes with SHA-256
`86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46`.
The verifier reported 37 source checks, 23 DT checks,
`hardware_acceptance=unproven`, and `authority=none`.

Current source identities:

```text
223436c93ff22f38efdf54dbb4829f48163de35da067a5306ac2b7132e82b11f  configs/compatibility/rog5-minimal-headless-v1.json
630cefe56a3cac3c76d4822a23bf0ef905d2afb8dccb67c65fd3c9c7af6a7c5d  configs/compatibility/rog5-core-source-dtb-v1.json
2724960534955e5187a4af28dd32495cb7daa55d8e9b13ef9fecc09b6048f0fe  scripts/host/verify-core-source-dtb-contract.py
b203f667b591b749e2406102f8badecf5711af8dbda6a4b048f22a0c04dac317  scripts/host/test-core-source-dtb-contract.py
d178b93bef26ab46195510119455eb55c465c1951b6b7a21f35dd2a7fb854521  scripts/device/collect-minimal-headless-runtime.sh
cd5ff7e711f6f30e09be34f2eaf38711dcd34f71c9fddf0bd50296d00fa2ca9b  scripts/host/verify-minimal-headless-runtime.py
77f047a50859127146c0228c145263a462445a94a5e62fd4f8fbb941f748042f  scripts/host/test-verify-minimal-headless-runtime.py
```

## Host storage retention

The current accepted source is retained in rootless Podman volume
`rog5-mainline-v19-source`. Two tracked documentation references now make a
fresh host-storage plan classify it as `retain`. The resulting read-only plan
has 11 retained and 87 detached prune-candidate volumes. Nothing was deleted.

## Safety boundary

- No phone, fastboot, ADB, SSH target, or USB device was contacted.
- No credential, signing key, known-hosts file, or external service was used.
- No retained/accepted kernel source, accepted DTB, phone storage, fallback
  state, host volume, image, cache, or artifact was modified or removed.
- This result does not prove frequency transitions, thermal cooling behavior,
  sustained load, power consumption, or a corrected-candidate phone boot.
- A live observation remains behind fresh explicit authorization and the
  existing temporary-boot, watchdog, and fallback controls.

See the [source/DT contract](../docs/core-source-dtb-contract.md),
[runtime contract](../docs/minimal-headless-runtime-acceptance.md), and
[port status](../docs/port-status.md).

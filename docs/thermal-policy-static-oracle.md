# Static thermal-policy oracle

Status: **offline regression gate complete; runtime thermal control unproven**.

This oracle prevents a future kernel source, config, or DTB change from
silently weakening the accepted Linux 7.1.4 thermal topology. It is an input
to H3 power/lifecycle work, not proof that the phone throttles or shuts down
correctly.

It cannot boot, sign, flash, reboot, contact the phone, load a module, change
a thermal trip, or use a credential.

## Accepted identities

- Linux source release: `7.1.4`
- source commit: `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`
- corrected recovery DTB size: 102,870 bytes
- corrected recovery DTB SHA-256:
  `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46`
- compatibility profile:
  `configs/compatibility/rog5-minimal-headless-v1.json`
- source/DTB profile:
  `configs/compatibility/rog5-core-source-dtb-v1.json`

Baseline mode requires those exact source and DTB identities. Candidate mode
checks the same semantics but reports `compatible-not-accepted`,
`hardware_acceptance=unproven`, and `authority=none`.

## Static topology

The policy binds this accepted structure:

| Boundary | Exact contract |
|---|---|
| interrupt fabric | SM8350 PDC at `/soc@0/interrupt-controller@b220000`, two interrupt cells, parented to the three-cell GIC |
| TSENS0 | 15 sensors; `uplow` PDC interrupt 26 and `critical` interrupt 28 |
| TSENS1 | 14 sensors; `uplow` PDC interrupt 27 and `critical` interrupt 29 |
| little CPU zones | `cpu0-thermal` through `cpu3-thermal`, TSENS0 indexes 1–4, cooling CPUs 0–3 |
| big/prime CPU zones | top and bottom zones for CPUs 4–7, TSENS0 indexes 7–14, cooling CPUs 4–7 |
| CPU trips | passive 90 C and 95 C with 2 C hysteresis; critical 110 C with 1 C hysteresis |
| CPU policy | 250 ms passive polling, two trip-linked maps per zone, step-wise governor, CPUfreq thermal cooling, and `THERMAL_NO_LIMIT` bounds |
| PMIC alarms | five enabled `qcom,spmi-temp-alarm` nodes for PM8350, PM8350C, PM8350B, PMR735A, and PMR735B |
| PMIC zones | passive 95 C, critical 115 C, 100 ms passive polling, and exact SPMI SID/interrupt tuples |

All 12 CPU sensor references and five PMIC references are exact. Every direct
thermal-zone sensor reference is also checked globally for duplication.
Sensor indexes are range-checked against the selected TSENS controller.
Disabled zones/controllers, extra name-shaped CPU zones, and renamed zones
that acquire a CPU cooling device fail.

PMIC trip node names are copied from the exact accepted DTB, including the
shared `pm8350c-crit` and `pmr735a-crit` names. Their provenance is the pinned
DTB identity, not the synthetic fixture.

## Source and config chain

The 43-check source contract now pins:

1. thermal core, CPU thermal, CPUfreq cooling, and step-wise governor Kconfig;
2. Qualcomm TSENS and SPMI temperature-alarm Kconfig/Makefile wiring plus
   registered OF tables attached to their platform drivers;
3. TSENS v2 critical-interrupt feature data and named IRQ registration;
4. PMIC alarm critical-trip and threaded-IRQ source paths;
5. thermal-core critical-trip dispatch;
6. default hardware-protection action, forced-work scheduling, and orderly
   poweroff.

Every required literal in the five load-bearing thermal source checks is
removed individually by a hostile test. The verifier strips C comments and
normalizes whitespace before matching, so a commented or line-spliced token
does not satisfy the contract.

The active `thermal-readonly` profile requires TSENS, CPU thermal cooling, the
Qualcomm hardware CPUfreq driver, and the step-wise governor. This preserves
accepted read-only ancestry and static CPU cooling prerequisites.

## Deliberate future boundaries

The accepted 7.1.4 config contains:

```text
CONFIG_QCOM_SPMI_TEMP_ALARM=m
CONFIG_THERMAL_EMERGENCY_POWEROFF_DELAY_MS=0
```

The first value leaves an unbounded early module-load window. The second
disables the forced emergency fallback if orderly shutdown stalls. The
oracle does not hide either limitation:

- `thermal-pmic-critical-path` remains future and requires
  `CONFIG_QCOM_SPMI_TEMP_ALARM=y`;
- `thermal-emergency-fallback` remains future and requires
  `CONFIG_THERMAL_EMERGENCY_POWEROFF_DELAY_MS` between 10,000 and 30,000.

That range proves only that a bounded fallback is configured. Selecting the
final delay requires measurement of orderly shutdown and rollback behavior.
Neither future capability becomes accepted from a config or static DTB pass.

## Built-in PMIC compile candidate

The optional
`configs/kernel/rog5-thermal-pmic-critical.fragment` now produces a complete
Linux 7.1.4 network-root build with the PMIC temperature-alarm driver built in.
The verifier requires the candidate config to differ from the accepted config
by exactly `CONFIG_QCOM_SPMI_TEMP_ALARM=m` to `y`, requires the emergency delay
to remain zero, proves the driver in `modules.builtin`, rejects a corresponding
loadable module, and checks its probe, IRQ, and init symbols in `vmlinux`.

This closes compile readiness only. PMIC probe/registration, IRQ delivery,
critical-trip handling, orderly shutdown, forced fallback timing, and rollback
behavior remain hardware-unproven. The capability therefore remains
`phase=future`, `candidate_status=pending`, and `authority=none`. The exact
build and timing evidence is in the
[offline thermal-PMIC result](../test-results/2026-08-09-network-root-thermal-pmic-candidate-offline.md).

## Run the offline gate

Metadata only:

```sh
scripts/host/verify-core-source-dtb-contract.py --metadata-only
```

Exact retained baseline:

```sh
PATH="$PWD/build/ci-host-tools:$PATH" \
  scripts/host/verify-core-source-dtb-contract.py \
  --kernel-source "$PWD/build/linux-stable-v7.1.4-source" \
  --source-role baseline \
  --dtb "$PWD/artifacts/network-root-v3/sm8350-asus-rog-phone5-recovery.dtb" \
  --dtb-role baseline
```

Focused mutation suites:

```sh
scripts/host/test-core-compatibility-oracle.py
PATH="$PWD/build/ci-host-tools:$PATH" \
  scripts/host/test-core-source-dtb-contract.py
```

Complete hardware-free repository gate:

```sh
scripts/host/test-repository-linux.sh ci
```

## What must happen on hardware

The next corrected-target thermal gate remains read-only and
temporary-boot-only:

1. prove both TSENS controllers and all expected zones register;
2. prove the PMIC alarm driver is built in and all five PMIC zones bind before
   ordinary userspace startup;
3. observe all three CPUfreq policies and cooling devices;
4. use a bounded workload below the existing safety ceiling to prove
   frequency/cooling response and recovery;
5. measure orderly reboot/poweroff latency before choosing the emergency
   fallback delay;
6. retain the rollback watchdog, fatal-log, pstore, battery, and fallback
   checks.

Do not test the critical trip or emergency shutdown by deliberately
overheating the phone. Use source/unit fault injection or a separately
reviewed synthetic thermal test facility for that path.

Until those observations pass, this result proves compatibility structure
only. It grants no phone action, storage write, signing, credential, retry,
flash, or persistent-install authority.

# Static thermal-policy oracle offline result

Date: 2026-07-31

Status: **PASS**. Focused gates, the exact retained baseline, the complete
hardware-free repository CI tier, and final advisory review pass.

## Outcome

The accepted Linux 7.1.4 source and corrected ROG Phone 5 DTB now have a
fail-closed static thermal-policy contract. It preserves:

- both SM8350 TSENS controllers and their named `uplow`/`critical` PDC
  interrupt routes;
- the PDC-to-GIC interrupt hierarchy;
- all 12 CPU thermal zones, exact sensor indexes, trips, polling delays,
  cooling maps, CPU clusters, and cooling-state bounds;
- five SPMI PMIC temperature alarms and their exact thermal zones, interrupts,
  trips, and polling delays;
- CPU thermal/cpufreq/step-wise governor configuration prerequisites;
- TSENS v2 critical-interrupt registration, PMIC alarm IRQ handling,
  thermal-core critical dispatch, and the default orderly/forced shutdown
  source call chain.

The accepted DTB remains exactly 102,870 bytes with SHA-256
`86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46`.
The retained source remains exactly commit
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`.

## Corrected safety boundary

The accepted config contains:

```text
CONFIG_QCOM_SPMI_TEMP_ALARM=m
CONFIG_THERMAL_EMERGENCY_POWEROFF_DELAY_MS=0
```

Neither value is promoted to runtime safety acceptance. Two future
capabilities now make the gap explicit:

- `thermal-pmic-critical-path` requires
  `CONFIG_QCOM_SPMI_TEMP_ALARM=y`;
- `thermal-emergency-fallback` requires an integer delay from 10,000 through
  30,000 milliseconds.

The upper bound prevents an arbitrarily late forced fallback from satisfying
the profile. The range still needs hardware-informed profiling before
promotion.

## Focused evidence

The compatibility suite passed:

```text
Ran 39 tests in 0.403s
OK
```

The source/DTB suite passed:

```text
Ran 74 tests in 12.678s
OK (skipped=1)
```

The optional skip is the clean-checkout case for retained large accepted
artifacts. That same exact-artifact case was run directly and passed:

```text
profile=minimal-headless-v1
active_capabilities=6
source_checks=43
dt_checks=23
thermal_cpu_zones=12
thermal_pmic_alarms=5
thermal_forced_fallback=pending
source_role=baseline
source_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
dtb_role=baseline
dtb_sha256=86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46
hardware_acceptance=unproven
authority=none
status=baseline-verified
```

The retained accepted 7.1.4 config also passed the active compatibility
profile and reported eight future capabilities.

The final complete hardware-free gate reported:

```text
PASS repository Linux ci tier
```

## Hostile coverage

The focused tests reject:

- removal of every required literal in each of the five new thermal source
  checks and disconnection of either TSENS or PMIC OF registration;
- a missing or renamed TSENS critical interrupt;
- changed PDC interrupt numbers or parent;
- disabled CPU zones, PMIC zones, PMIC alarms, TSENS, or interrupt
  controllers;
- out-of-range and duplicate thermal sensor references;
- changed CPU passive/critical temperature, hysteresis, type, or polling;
- rewired cooling trips, changed cooling limits, extra CPU zones, or renamed
  zones that acquire CPU cooling devices;
- missing PMIC alarms, changed SPMI interrupts, or changed PMIC critical
  trips;
- a removed future PMIC/fallback capability, zero or excessive emergency
  delay, or modular PMIC driver in the future-complete config.

All advertised thermal counters are derived from the validated profiles
rather than printed as fixed constants.

## Advisory review

A bounded, safe-mode, tool-free, nonpersistent Claude Opus review received the
complete credential-free patch. Its first review identified disabled-zone,
partial-mutation, hardcoded-counter, wrong-gate, modular-PMIC, and unbounded
delay weaknesses. Those findings produced the fixes described above.

The complete-diff re-review returned `BLOCKERS: None` and `VERDICT: Approve`.
Its two strongest nonblocking suggestions also landed: explicit registered
OF-driver checks were restored for TSENS and PMIC, and whitespace
normalization was limited to three named multi-line source checks. A final
targeted follow-up reviewed those changes and the live structural policy
checks, again returning `BLOCKERS: None` and `VERDICT: Approve`.

## What this does not prove

This result does not prove:

- TSENS or PMIC interrupt delivery on the phone;
- PMIC alarm driver registration before userspace;
- CPU frequency reduction or cooling-map response under load;
- real trip temperatures, thermal inertia, or sensor calibration;
- orderly shutdown completion or forced shutdown timing;
- suspend, battery, charging, or sustained-load safety; or
- behavior of a changed kernel/DTB on hardware.

No phone, credential, private key, signing key, network service, root
privilege, boot, reboot, flash, wipe, storage write, or deletion was used.
The result grants no live authority.

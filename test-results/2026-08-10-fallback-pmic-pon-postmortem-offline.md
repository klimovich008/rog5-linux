# Fallback PMIC PON postmortem checkpoint — offline

Date: 2026-08-10

Starting exact repository HEAD:
`0cffb510c478d9f26f31fb938100b593706c2702`

Recommendation: **HOLD**

No phone, USB device, fastboot, ADB, ACM/NCM session, phone storage,
credential, signing key, production signature, candidate, policy row,
privileged host action, flash, wipe, slot operation, or boot was used. The
Generation-12 claim remains consumed and non-retryable. The separate
VCNL36866 working tree was not touched.

## Critical-path conclusions

The historical conclusion is unchanged and remains split into two questions.

1. **Why NFS could not mount:** Generation 12 could not mount NFS because the
   host lifecycle cancelled the NFS service before the target enumerated. At
   historical commit `1ee55086ac9c4c8049940d410bcfdf8317a2721b`, the obsolete
   seven-field parser rejected the valid extended PREPARE/COMMIT response
   after COMMIT. Exception cleanup terminated the NFS server at or before
   `21:44:17.442856705 +0200`; the first target frame arrived at
   `21:44:23.437393177 +0200`. The server log has no exact-link-ready record
   and records interrupted sleep, `rpc.mountd` SIGTERM, and cleanup.
2. **Why target USB/reporting disappeared:** still unknown. The omitted Haven
   deactivation is the strongest supported hypothesis, but no retained reset
   reason proves it. The stage-70 records are 250 ms reporter heartbeats. They
   do not reveal whether one mount syscall blocked or mount returned and the
   shell loop retried.

The exact retained timeline remains:

| Time (`+0200`) | Evidence |
|---|---|
| before `21:44:16.261482661` | NFS export/listener prepared before COMMIT |
| `21:44:16.261482661` | durable intent created at the COMMIT-send boundary |
| `21:44:16.268839173` | control log complete; exact `kexec -e` entry was not retained |
| by `21:44:17.442856705` | parser exception cleanup terminated NFS |
| host monotonic `378772.131037` | recovery USB device 64 disconnected |
| host monotonic `378772.555036–378772.772047` | target device 65/NCM/ACM enumerated |
| `21:44:23.437393177` | first target frame, stage 10, target uptime 2.794 s |
| `21:44:23.438406552` | first stage-70 heartbeat, target uptime 3.544 s |
| `21:44:31.957195352` | last frame, stage 70, target uptime 12.547 s |
| by `21:44:39.929046062` | collector classified disconnect; physical loss was earlier or equal |
| not retained | first Alpine reappearance and reset cause |
| by `21:52:16.445235417` | fallback profile restoration complete |
| by `21:52:18.690270778` | fallback identity and strict SSH complete |
| by `21:52:21.518315327` | intent resolved `FALLBACK_RETURNED` |

The later SSH proof does not prove that the phone was absent for the complete
7 minute 39 second gap.

## Reset-reason source audit

The retained ASUS source oracle is Linux 5.4.210. Exact source identities are:

| Source | SHA-256 |
|---|---|
| `drivers/soc/qcom/pmic-pon-log.c` | `3faf7c24591bd1df471c8f5a7d6c799b0f9256c4e25b897d843fe29fce341944` |
| `drivers/input/misc/qpnp-power-on.c` | `48dcf1340685be587f829de4978870cc4eb6c1b3e337f5d51feb6d086c681ead` |
| `drivers/power/reset/qcom-reboot-reason.c` | `7305a60660a03bd1df2cdcb540c14dbae58c4237f85c594c6ee918f4a1487db6` |
| `lahaina-pmic-overlay.dtsi` | `7c2884033f2f9888e3786155510bb4ac2d824cfc3ae3afce5fe79a3ba72ded32` |
| `pmk8350.dtsi` | `8ca3a07d90ced1269ce04ca1832a1bc3f212e99967a123911de18770c75e1d2c` |

The exact recovery-oracle config is 185,763 bytes at
`df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f`
and builds `CONFIG_QTI_PMIC_PON_LOG=y` and
`CONFIG_INPUT_QPNP_POWER_ON=y`.

The PMIC PON driver reads the PMK8350 SDAM FIFO through
`nvmem_device_read()`, walks at most 29 four-byte entries in chronological
ring order, and emits each nonzero entry as `PMIC PON log: ...`. It does not
write NVMEM. Its fixed labels include reset trigger `PMIC_WATCHDOG_S2`, reset
types `WARM_RESET`, `SHUTDOWN`, and `HARD_RESET`, and fault token
`FAULT_WATCHDOG`. The DT supplies `qcom,pmic-pon-log`,
`pmk8350_sdam_5`, and `pon_log`.

The separate `qcom-reboot-reason` driver is not historical evidence. It is a
reboot notifier that writes the requested *next* boot target to the
`restart_reason` NVMEM cell. The postmortem collector never reads it.

Important limitation: the installed Alpine fallback is kernel
`5.4.134-qgki-perf-00001-g6c308144c23e`. No exact retained fallback config,
fresh complete fallback boot log, or matching fallback binary currently proves
that its kernel includes this PMIC PON reader. The 5.4.210 recovery config is a
behavioral oracle, not fallback-availability proof. A future absent log is
therefore `INCONCLUSIVE`, not proof of no reset or no watchdog.

## Offline correction

The signed fallback postmortem protocol and private evidence are bumped to v2.
Before signing, the exact fallback now executes one read-only `/bin/dmesg`
process through a deadline-driven pipe reader:

- 10-second process/read deadline;
- at most 4 MiB plus one refusal byte is read;
- at most 64 syntactically valid PMIC records are considered;
- the ASUS oracle's 29-entry physical FIFO remains the maximum for an exact
  classification;
- timeout, command absence, or nonzero exit is `UNAVAILABLE`;
- missing delimiters, no PMIC lines, duplicate trigger/type, unknown values,
  more than 29 candidate records, or a nonterminal current `PON Successful`
  is `INCONCLUSIVE`;
- only the segment after the penultimate `PON Successful` through the final
  `PON Successful` can be `EXACT`;
- exactly one known reset trigger and one known reset type are required;
- `PRESENT` means that exact segment contains `PMIC_WATCHDOG_S2` or the exact
  `FAULT_WATCHDOG` token;
- `ABSENT` means only that neither fixed PMIC token occurs in an otherwise
  exact segment. It does not prove that Haven, another watchdog, or a reset
  did not occur.

Raw dmesg and PMIC messages never leave the fallback. The signed/private
summary carries state, total record count, SHA-256 of canonical PMIC messages,
selected-cycle entry count, normalized trigger/type, and watchdog-token state.
Both host parser layers independently enforce the exact schema and reject
contradictions such as `PMIC_WATCHDOG_S2` plus `ABSENT`.

The outer strict-SSH bound is 40 seconds: 8 seconds for connection plus the
10-second dmesg deadline, 10-second host-key signing bound, and more than five
seconds of local margin. The existing lifecycle reserves a separate 120-second
post-discovery control margin. No timeout or rendezvous in the target image was
changed.

## What the combined observer can and cannot distinguish

- Matching pstore lineage followed by a fatal token is correlated Linux
  panic/oops evidence.
- An exact PMIC watchdog token is PMIC reset evidence, not attribution to the
  Haven hypervisor watchdog.
- Exact PMIC reset evidence with no correlated pstore can support a reset with
  no Linux crash dump, but still cannot name Haven without an independent
  identity.
- Empty pstore without an independently retained known marker cannot separate
  no crash record from lost retention.
- A different pstore lineage is stale/different-cycle evidence; ambiguous
  PMIC FIFO chronology is separately `INCONCLUSIVE`.
- Observer failure remains visible as unavailable/failed capture. Absence is
  never converted into “no crash.”

The retained Generation-12 evidence predates this collector and contains no
PMIC PON record, PON/warm-reset field, watchdog bark/bite record, bootloader
restart reason, or current-cycle pstore proof. Generation 12 therefore gains
no retrospective reset classification from this code.

## Watchdog, rendezvous, and ramoops assessment

The exact Generation-12 recovery config and binary audit remains unchanged:
Haven watchdog pet interval 9,360 ms, bark 22,000 ms, bite 25,000 ms; no
automatic remove/shutdown/reboot/kexec deactivation occurred in the shell-free
path. Depending on last-pet phase, the nominal bark/bite window overlaps only
part of the observed loss interval. This is timing compatibility, not runtime
proof. The current exact-head recovery responder now performs the reviewed
fail-closed Haven handoff before kexec, but no physical cycle has tested it.

The 14.75-second TCP rendezvous remains unchanged. It is not safe to shorten
it solely to fit an inherited watchdog that the recovery handoff is now
required to disable. TCP acceptance remains only host-port reachability, not
NFS readiness.

The ramoops observer remains technically coherent: persistent-RAM
initialization saves the previous buffer as `old_log` before current reuse.
Physical retention, firmware clearing, stale lineage, and observer failure
remain unproven. An empty pstore result is inconclusive unless a known marker
was independently expected to survive.

## Failure ranking

For NFS non-mount, host parser-cleanup cancellation remains a sufficient known
cause: 100%; all alternatives 0% for that narrow question.

For USB/target-reporting loss, no new live evidence justifies changing the
previous ranking:

| Cause | Weight |
|---|---:|
| undisabled Haven watchdog | 42% |
| target kernel panic/oops | 24% |
| DWC3/NCM/ACM loss while target remained alive | 15% |
| other kexec residual-state problem | 10% |
| host NFS cancellation/parser cleanup directly causing USB loss | 0% |
| NFS/RPC behavior after server disappearance triggering target fault | 5% |
| target userspace watchdog/reset | 0% |
| power/thermal | 1% |
| host reporting artifact | 2% |
| other supported cause | 1% |

## Tests and next action

The original PMIC fail-first suite failed in 3.277 seconds because the v1
record had no PMIC fields, parser, bounded probe, or lifecycle validation. A
second focused fail-first test failed in 0.133 seconds because collection used
post-hoc `subprocess.run()` buffering. After correction:

- fallback control after final review: 72/72 PASS in 3.344 seconds;
- lifecycle after final review fixes: 81/81 PASS in 74.254 seconds;
- retained source/config integration and focused reviewed cases: 10/10 PASS
  in 0.168 seconds.
- complete `scripts/host/test-repository-linux.sh ci`: PASS in 298.559
  seconds before the final child-reap review fix and PASS again in 299.453
  seconds after it.

The exact-head publication result is recorded in the final checkpoint handoff
after this report is committed.

Minimal safe next action: finish local repository CI, perform exact-diff
review, commit this isolated offline correction, and require exact-head GitHub
CI for that commit. Do not issue, sign, admit, authorize, or boot a candidate.
The VCNL36866 work stays isolated. Recommendation remains **HOLD**.

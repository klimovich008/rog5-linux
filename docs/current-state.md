# ROG5 current state

Updated 2026-09-07: V6 startup FAIL; exact V11 fallback SSH/power/storage proof PASS.
V6 is permanently consumed. Do not retry, restage or flash it.

## Goal and authority

Qualify one reliable unattended headless Arch server under the existing
[acceptance contract](release-acceptance.md) and
[mandatory matrix](../configs/release-acceptance.json). Display is optional.
Missing prerequisites/evidence remain BLOCKED or NOT RUN, never PASS.
Keep unrelated work in the backlog. No new architecture review or goal.

Exact phone: `M5AIKN00F0353YH`, product `lahaina`, side USB anchor `1-1.2`.
Preserve official WW33 slot A (`33.0210.0210.200`) as charging/rescue.
Stock charging restoration is complete; no super or stock restoration work.
Preserve identity/slot/topology, signatures, battery/thermal, scoped storage,
backups, independent fallback and permanent experimental one-use protections.
No new flash, GPT or protected-data operation. Destructive scope remains separate.
Private credentials, raw journals and evidence stay outside Git.

## Current phone and installed artifacts

The installed boot-B loader remains unchanged:
`dcc487f17d6b4926ea633cbb242c62b598019e332640a81c1100c2d91087f723`.
Retained previous boot B:
`340f639276d9df3dfc073b8614a72f82507ea18c622c9df5d1e60f2c1622ccad`.
Signed V11 fallback manifest:
`a684bad14f84251ba342a87bde07da1f7b9aea412275ad124f7000716e94bbe2`.

Current fallback kernel `7.1.4-g359318de534f`, bundle `persistent-native-root-v11`,
boot `52cac9c3-8e59-479b-9f1d-f5d796ea4d9b`.
Authenticated USB SSH `10.77.0.2`, pinned alias `169.254.77.2`, fingerprint
`SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
Read-only proof: 117 physical block nodes; only sda/sda23 writable; P24 remains RO.
Fallback snapshot: Good, 30.4°C, 8.573 V, Charging, USB online.
This snapshot is not H03 or a sustained-current qualification.
Fallback uses a temporary root upper; the unmounted persistent upper remains intact.

P24 selector points to consumed V6; P23 V6 trial remains pending, so the loader
selects V11 instead of retrying V6. V5 bundle, selector rollback copy and archived
healthy trial remain preserved. Restore an accepted release only through a
reviewed bounded selector/trial restoration, not by resetting V6 consumption.

## Latest failure and next action

V6 (`headless-server-selector-v6`) reached local root and systemd, then its CPU
policy guard refused at target uptime ~23.105 s. The boot-bound persistent journal
proves `ValueError: unsafe or unavailable thermal state`, followed by OnFailure
and an orderly requested reboot. This is not evidence of kernel panic or host
SSH/parser failure. The trace does not identify the zone, temperature or loop
iteration; do not claim zero writes or a particular CPU temperature.
The transaction's restoration path reported no secondary error, but no failing-
boot frequency readback exists. Empty pstore remains inconclusive.

The original `<60000 mC` limit remains unchanged. A focused diagnostic correction
records the rejected zone/value, distinguishes absent inventory/read failure,
and does not add writes, delays or retries. It is not a thermal-startup fix or a
new deployment. Normal/optimized fail-first fixtures cover the missing evidence.
Exact validation results for this correction are retained in the private
`thermal-diagnostic-ci-r1/result.json` and matching GitHub run, not older V6 CI.
Next: qualify this small correction, then resolve safe boot-time CPU policy
application before another successor. Prefer a bounded experiment on a restored
accepted baseline; do not consume another image merely to rediscover missing data.

The private live work is `rog5-server-cpu-policy-20260907.lwlreSEe`.
V6 manifest:
`61c34cefc6cbb335203a609ee695e3db4638b1a747c22ab235460407ad1713eb`.
Target archive:
`f0c866f10892bc129bbcc421316c243cd67fdc9307e6f7ee76d0e0dfd91b7433`.
Failure boot: `2fb95880-ac79-46ea-8fd5-ceb5b7157e38`.
Other hashes derive from its canonical record and private deployment receipts.

## Mandatory outcomes

One coherent final release must pass all mandatory rows. Component passes from
V5 cannot be combined with V6 into a green release.

| Outcome | Current result / next action |
|---|---|
| A01 / C01 / C02 | V6 offline PASS 93.967 / 144.739 / 76.265 s; physical startup still failed |
| H01 / H02 | V11 fallback SSH/power proof; same-release radio-inactive rescue not qualified |
| H03 regulation | NOT RUN for V6; firmware-Full method is defined, missing fields are not PASS |
| S01 local startup | V6 FAIL; V5 previously PASS |
| S02 transfers | V5 PASS; Wi-Fi upload had little deadline margin; validate final release |
| S03 restart recovery | V5 PASS; validate final release |
| S04 durability | V5 PASS with owned scratch cleanup; prior failed-soak file preserved |
| S05 repeated boots | V5 three ordinary boots PASS in 313.102 s; not V6 evidence |
| S06 powered-off start | Physical powered-off/start qualification outstanding |
| S07 combined load | V5 uncapped FAIL; capped 600.496 s diagnostic is not 60-minute PASS |
| F01 / F02 | V5 offline recovery/Wi-Fi-restart PASS; preserve exact-input evidence |
| R01 recovery | Unplanned V6 fallback is not the separately controlled failed-boot test |

Complete history, exact earlier identities and evidence are in the
[dated report](../test-results/2026-09-05-headless-acceptance.md).
V5 private work: `rog5-server-wifi-ps-20260907.aSQZz23O`.
Never remove its failed-soak scratch, accepted artifacts or archived claims.

## Fast loop and retention

Use [development](development.md): impact/dependency selection, focused edits,
exact assembled/target checks, frozen integration checkpoints and separate
development/release results. Unknown/critical changes retain stronger checks.
V6 implementation source `81596787` passed full local CI 525.864 s. Registry
source `a65fc129` passed full local CI 556.713 s and remote run 34151850294, all
four jobs. Do not relabel these as testing later diagnostic edits.
Unsigned target twins 8.985 s, wrapper reuse 0.481 s, signed packaging 4.669 s.
Private coordinator normal/optimized checks 3.817 s; no repeated full CI.
A01/C01/C02 overlapped registry CI. No kernel/DT/module/wrapper rebuild or flash.

8,280,854,528 B of duplicate old wrapper intermediates were released with verified
twins retained. Exact restoration inventory and relocated V5/V4 previews are
durable under the private V6 `retained-host-inputs`. Old RAM preview paths are
absent; do not rebuild merely to recreate them. Preserve the 3 GiB home reserve.
V6 package/paired preview and other archives remain volatile: no host reboot yet.
Host port 8081 is unrelated SteamOS CEF; leave it untouched.

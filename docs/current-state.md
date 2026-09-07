# ROG5 current state

Updated 2026-09-07: V5 healthy; V7 diagnostic package prepared, not admitted/executed.
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

Current kernel `7.1.4-gf17befd4ef17`, bundle `headless-server-selector-v5`,
boot `660c70d5-f01f-4eda-82fe-4e1d6c9a4a08`.
Authenticated USB SSH `10.77.0.2`, pinned alias `169.254.77.2`, fingerprint
`SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
Read-only proof: 117 physical block nodes; only sda/sda23 writable; P24 remains RO.
Current snapshot: Good, 29.9°C, 8.602 V, Full/100%, battery current 0, USB online.
This snapshot is not H03 qualification. The 16 GiB persistent root upper is active.
Core services and Wi-Fi radio/WPA/DHCP are active; current-boot healthy commit
completed at 59.468 s. Use `rog5-early-sshd` and `rog5-tailscaled`, not generic
service names. Tailscale uses `/run/rog5-tailscale/tailscale` with
`--socket=/run/rog5-tailscale/tailscaled.sock`; peer connectivity is not yet proven.

P24 selector now points to accepted V5; its P23 trial is freshly healthy.
Bounded restoration preserved V6's failed selector and pending record, original
V5 rollback copies, all bundles and permanent claim consumption. P24 was relocked.
One ordinary boot returned to V5; no RAM candidate retry, signing or flash.
V11 remains the independently verified fallback, not the currently running root.

## Latest boundary and next action

The latest ordinary-boot smoke failed in the host checker after V5 returned
authenticated SSH. `expected_files()` compared deployed V5 runtime with newer
checkout bytes. All six deployed files match the canonical V5 reviewed source;
the four initramfs-resident files also match its retained signed archive.
This is an R2/R6 release-expectation error, not a new kernel failure.
The correction requires an explicit candidate, derives expectations from its
canonical exact source commit, disables Git replacement objects, and fails on
missing inputs before credentials. Local-root and durability consumers agree.
The original FAIL remains: full capture 1380.929 s, all four host cleanups PASS.
Correction `e22f606a` passed full local CI **523.918 s** and all four remote jobs
in **34160126847**. Same-boot corrected local-root check PASS **0.921 s**, not
a replacement for the original failed smoke or full S01 qualification.
Next: finish V7 exact composition/registry qualification, then one supervised
startup test of the unchanged thermal gate. No claim or hardware entry exists yet.

V6 (`headless-server-selector-v6`) reached local root and systemd, then its CPU
policy guard refused at target uptime ~23.105 s. The boot-bound persistent journal
proves `ValueError: unsafe or unavailable thermal state`, followed by OnFailure
and an orderly requested reboot. This is not evidence of kernel panic or host
SSH/parser failure. The trace does not identify the zone, temperature or loop
iteration; do not claim zero writes or a particular CPU temperature.
The transaction's restoration path reported no secondary error, but no failing-
boot frequency readback exists. Empty pstore remains inconclusive.

The `<60000 mC` limit remains unchanged. Diagnostic correction `0005794c`
passed full local CI 526.219 s and all four remote jobs in 34155585303; it is not
deployed or a thermal-startup fix. Read-only complete-guard observation on V5
passed for 10 s, peak 36.8°C, unchanged CPU maxima; this does not reproduce startup.
The complete guard plus real cap application/restoration subsequently passed
inside the unchanged service sandbox: **6.635 s** total, 5 s lease, peak **36.8°C**.
Original CPU maxima were independently restored; no service was installed.
This rules out a persistent steady-state guard/sandbox failure, not a transient
startup condition. TSENS is built in; retained pre-boot evidence has no CPU
temperature series. The rejected V6 zone/value remains unknown. No new boot,
claim or flash occurred during that experiment. Optional missing fields never
justify a successor; the remaining startup safety refusal requires discrimination.

V7 changes only the trial descriptor, generated target checksums and the tested
thermal diagnostic message. Thresholds, cap order, timing, kernel/DT/modules and
wrapper are unchanged. Target twins **9.095 s**, wrapper reuse **0.446 s**, sealed
commands **1.431 s**, signed twins/verifier **4.828 s**. Canonical consumer and
rejection tests PASS **11.237 s**. Signed manifest
`4eaeb9f8859f7fa9c64b5e40b3764452da504d0ce5438afd20760305bc23e7b9`;
other identities derive from its one expected record. Expected-record registration
does not create a filesystem claim. Private work: `rog5-boot-cpu-diag-20260907.cnXiH8My`.
The bounded Opus review failed on expired OAuth; no review conclusions were used.

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
| A01 / C01 / C02 | V7 pending; prior V6 results do not qualify the changed archive |
| H01 / H02 | V11 fallback SSH/power proof; same-release radio-inactive rescue not qualified |
| H03 regulation | NOT RUN for V6; firmware-Full method is defined, missing fields are not PASS |
| S01 local startup | V5 healthy; corrected root component PASS 0.921 s; original smoke FAIL preserved |
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
V6 host preview was losslessly archived to private `/tmp/rog5-v6-preview-archive-gkrldufe`;
complete decompression matched its original SHA256. Its raw RAM copy was released
(4,097,179,648 B); never rebuild it merely to recreate the old path. See the dated
report for restoration identity. V6 package and archives remain volatile: no host reboot yet.
Host port 8081 is unrelated SteamOS CEF; leave it untouched.

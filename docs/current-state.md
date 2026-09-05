# ROG5 current state

Updated: 2026-09-05. Single authoritative handoff; measurements are dated
evidence, not a claim of continuous monitoring.

## Objective

Qualify one reliable standalone headless Arch Linux server release. The
[acceptance contract](release-acceptance.md) and
[test manifest](../configs/release-acceptance.json) define completion.
Run `scripts/host/rog5-dev accept` for the results matrix. Missing, skipped or
incompatible-release evidence cannot pass. Display is optional; V15 preparation
stopped without signing or execution. Keep the existing goal and Arch root:
the reproduced recovery failures were project composition/service defects.

## Running recovery and installed baseline

- Exact phone: ROG Phone 5 ZS673KS, product `lahaina`, serial
  `M5AIKN00F0353YH`, anchored side USB `1-1.2`.
- Stock slot A: official WW33 `33.0210.0210.200`, verified charging/rescue.
  [Charging restoration](asus-charging-recovery.md) is complete.
- Installed slot B remains recovery `340f6392…`, selector-v2 primary
  `persistent-native-root-wifi-overlay-v10`, signed
  `persistent-native-root-v11` fallback. This is not the running RAM rescue.
  Installed repeated-failure demotion/verification corrections are pending.
- Running **consumed** RAM rescue: `headless-acceptance-rescue-v5`,
  kernel `7.1.4-g359318de534f`,
  boot `c2149c4a-6ce4-47c6-9c3b-e3ca55ea43fb`. Never execute v1–v5 again.
  Registry/publication `3f4f2e5f4898a061a24eea8df22b6851e2e494da`;
  packaged source `adfe80d7b1d9dd301b12f46cb302b52508679633`.
- Exact hashes belong to canonical claim records and private deployment receipts;
  abbreviated hashes here are navigation only. Both kernels, DTB, 19 modules
  and retained Arch root were reused; no experimental flash occurred.
- P24 `arch_root_a`: immutable native RO lower/bundle store, `norecovery`.
  RAM rescue uses a tmpfs root upper. P23's existing service-state image is
  mounted on /persist. Only sda/sda23 were writable among 117 checked UFS nodes.
  Installed primary additionally uses the bounded 16 GiB persistent root overlay.
  Normal state writes/journal replay are not a zero-storage-write boot.
- Normal pinned USB SSH: `10.77.0.2`, host alias `169.254.77.2`,
  fingerprint `SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
  Credentials/raw evidence remain private. Wi-Fi is intentionally inactive.
  Tailscale service is active; this host lacks a mesh client/route, so remote
  Tailscale reachability is not qualified.

## Latest physical evidence

V5 passed connected admission and its sole RAM boot: fastboot 12.820 s,
pinned SSH 59.298 s. Actual SSH restart passed in 2.547 s with unchanged boot,
P2/state/identity/Tailscale invocation IDs, readiness hashes and normal USB
address. Deployed core unit hashes match the final signed archive.

The bounded startup observer exited successfully. The deployed watchdog logged
current-boot P2+identity acknowledgment at uptime 902.576 s. Capture completed
in 1380.711 s; all four owned host cleanup steps passed. Passive capture remains
NOT RUN for qualification, not an authenticated PASS. After cleanup, pinned
SSH at uptime 1594 s confirmed all five core services active in the same boot.
RAM-only USB transfers of 256 MiB each way passed in 7.429/6.659 s with matching
hashes, unchanged boot and no new interface errors/drops. This is USB component
evidence, not Wi-Fi or complete S02 qualification.

A 600.615 s collection contains 61 samples: 100% Full/Good, 30.0°C,
8.632–8.635 V, 0 µA battery current, unchanged 5116000 µAh counter;
USB online with 500 mA input limit. This is full-battery/core-continuity data,
not net-positive charging or formal H03 PASS. H03 remains BLOCKED pending a
predeclared qualified regulation/current-noise interpretation.

New optional failure: `archlinux-keyring-wkd-sync.service` reached start-limit
after its shell script indexed an empty key list. Rescue has an uninitialized
volatile package keyring; the repository's persistent-keyring helper exists but
is not wired into this composition. Do not hide the failure or infer a kernel
defect. Diagnose/test the intended rescue versus installed update policy before
another candidate.

## Source correction and next work

A02 regression reproduces persistent trial composer trust checks disappearing
under Python -O: wrong base/helper hashes and reused trial identities accepted.
It also reproduces a stray archive when a receipt (including dangling symlink)
already exists. Explicit checks now preserve those guards in both interpreters;
valid archive bytes/receipts are unchanged. This host-only fix needs no kernel
build or phone cycle. Focused normal/optimized tests pass with unchanged valid bytes.
Full local CI now passes in 490.925 s; the quick acceptance matrix passes
A02/B01/G01/G02, with all other rows NOT RUN in that quick run. Published
`c1c1d6315fff7946cbfa902e2add4fe2421f49e5`; all four remote jobs passed
run 33988345153. Test logs are private; the full
suite expects the usual 022 fixture umask, not the 077 log-creation umask.

E01 source checkpoint: safe pre-activation radio refusal now skips WPA/DHCP/trial
commit while allowing qualified P2/state/SSH startup. The 8.4 V activation gate
is unchanged. Exact current-boot refusal plus core identity is required to
suppress radio rollback; unsafe power/thermal state and partial activation remain
fatal. Mixed old/new archive consumers are rejected, including under Python -O.
Host systemd ordering and sealed ARM BusyBox component tests pass; these source
changes are not yet deployed or final-release qualification. Active tier passes
in 15.869 s. Frozen full CI passes in 485.345 s; final sealed replay in 64.087 s.
Published `2fe2a299fd3c6dc731bfbe988b60920ddbb81f4f`; all four remote jobs
passed run 33990202242.

Latest pinned read-only check: same V5 boot at uptime 4091 s, five core services
active, 100% Full/Good, 30.0°C, 8.632 V and 0 µA. Optional keyring refresh still
failed; no reset/masking, new boot, artifact build or phone storage change.

Keyring correction is locally validated and undeployed: refreshed init
stages the existing bootstrap helper/unit and orders WKD refresh after successful
bootstrap. Packaging, paired-archive, sealed runtime (33.329 s), real user-systemd
ordering/failure (2.550 s), and isolated actual ARM key initialization/reuse
(11.775 s) pass. WKD now skips ARM-only keys without the empty-list error; online
refresh is not qualified. On-phone read-only helper preflight passed. Active
tier passes in 15.022 s; full frozen CI passes (approximately 486 s from retained
log timestamps; terminal elapsed-time output unavailable). Publication remains. No package
trust policy or key-generation logic changed; the running failure is untouched.

Latest read-only continuity check: the same V5 boot at uptime 6893 s still has
working pinned SSH and active core services. Battery is 100% Full/Good, 30°C,
8.630 V, 0 µA; USB input is online. Only the known keyring-refresh unit is failed.
This is continuity evidence, not a combined storage/network soak qualification.

Keyring checkpoint published as `3dc02580aa276cbd223ca511bed49655eb143bae`;
CI run 33991878159 passed exact-head and publication, but merge compatibility
failed in the unrelated fetch-concurrency fixture (700 ms success deadline).
A 750 ms fsync injection reproduces exact exit 54; only that fixture's successful
fetch now has a 3 s budget. Production deadlines and timeout tests are unchanged.
Focused fetch suite passes all 35 tests in 9.570 s; active tier passes in
15.041 s. No candidate was issued.
An actual user-systemd WPA/DHCP restart component passes in 1.380 s: restarting
WPA restarts DHCP, hardware activation stays at one, and core identities remain
unchanged. No production dependency fix is needed. F02 still requires real
target address/SSH recovery, not fixture daemon success.

The disposable host OverlayFS test confirms the pre-mount guard rejects the
retained stale-whiteout shape while Linux cleans it on mount. After matching
the phone's observed index/redirect/metacopy-disabled settings, post-unmount
guard, immutable-lower hash and read-only fsck all pass. Earlier host-fixture
failures are retained. This is not target-kernel or journal-replay qualification;
owned mounts/loops are detached and production storage guards are unchanged.

CI fixture correction published as `059afe4f3bad7ed435040edf66d057c2c17c7927`;
all four jobs passed run 33992627778. No publication remains for that checkpoint.

Exact retained kernel QEMU now reproduces and fixes the interrupted OverlayFS
whiteout rejection: before FAIL in 40.255 s; after PASS in 44.040 s, including
actual ext4 journal replay and nine unrelated-entry refusals. The source guard
admits only the kernel's root-owned mode-000 `#%x` character-0:0 scratch entries,
including legitimate hardlinks. Kernel cleanup remains responsible for removal.
The unsigned fixture changed init only in 1.441 s; no kernel build or phone boot.
F01 is now connected to the exact kernel/archive/root receipt; final integrated
QEMU passes in 76.421 s including before/after input hashing, var-only interruption,
post-unmount validation and read-only fsck. Active tier passes in 15.528 s and
frozen full local CI in 485.305 s. Exact-head/merge publication CI remains pending.
This is not installed-release qualification. Same-boot read-only SSH at uptime
9209 s confirms active core services, Full/Good 100%, 30°C and online USB power.

Next: finish this recovery checkpoint and compose the coherent server successor.
Do not assume the old Wi-Fi modules
(kernel `7.1.4-g1eea8970e87f`) match the current rescue kernel. Its retained
soak-qualified kernel/DTB/V3 archive hashes match the historical build record;
22 direct modules and 37 nested radio/dependency modules all report that same
release. Preserve this coherent set for successor composition rather than mixing
it with g359 modules. This is retained-artifact inventory, not new load proof.
Finish final archive/root composition and the remaining
service, journal, Wi-Fi, reboot, soak and isolated physical rollback tests.
Do not treat V5's component passes as an installed release PASS.

## Retained evidence and boundaries

[Acceptance incident](../test-results/2026-09-05-headless-acceptance.md) holds
historical rescue failures and exact tests/timings. Other accepted baselines:
[boot/start](../test-results/2026-09-03-unattended-reboot-v10.md),
[overlay](../test-results/2026-09-02-persistent-root-overlay-v8-live.md),
[updates](../test-results/2026-09-02-persistent-overlay-v8-package-update.md),
[healthd](../test-results/2026-09-02-healthd-persistent-live.md),
[Wi-Fi](../test-results/2026-09-02-persistent-wifi-v3-soak.md),
[NCM](../test-results/2026-08-29-persistent-ncm-two-hour-pass.md),
[Tailscale](../test-results/2026-08-30-persistent-tailscale-v11-live.md).
Earlier evidence is not silently combined with a different release. The original
installed-boot failure and prior PMIC IRQ/UFS emergency-RO incident remain
unproven; successful RAM rescue does not close those questions.

Use [development](development.md), relevant [lessons](development-lessons.md)
and existing scoped authorization. Preserve exact device/slot/topology/boot chain,
power/thermal gates, signatures, backup/storage scope, stock A, signed fallback,
independent rollback and permanent non-retry after COMMIT or ambiguous execution.
No experimental flash, GPT change or protected-data write. Destructive storage
requires a separately reviewed exact operation and explicit approval.
Keep private artifacts/evidence/credentials out of Git; do not delete them.

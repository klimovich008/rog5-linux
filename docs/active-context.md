# Active ROG Phone 5 Linux context

Updated: 2026-08-31

Read `docs/current-state.md` for the baseline and the latest V11 live result.
Historical generations remain in Git; do not reconstruct them here.

## One current question

Enable the observed Wi-Fi hw1.1 revision with matching vendor firmware/BDF.
V14 proved the coherent1350mV hold, WCN sequencing and PCIe Gen3x1. The current
ath11k module rejects hardware1/0x10 before MSI/MHI. V14 is consumed; no successor
is admitted. See `test-results/2026-08-31-wifi-late-activation.md`.

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, anchored at host USB `1-1.2`.
- Active slot: B, running V11 boot
  `22ec3b83-0967-41dd-ba0a-5bea2a93e0a2`; slot A remains rescue.
- V11 passes initial systemd running, V49 high-speed UFS, zero UFS errors,
  NCM, stable key-only SSH, p23 state and exact two-node write scope.
- Latest battery read: Full/Good, 8.608 V, 30.1°C; state/Tailscale active.
- Temporary source ACM disappeared on reboot; V11 currently exposes NCM only.
- Standalone shared mode is `10.77.0.1/30` → `10.77.0.2/30`. Fixed recovery
  management remains a separate `169.254.77.1/30` profile.
- Tailscale 1.102.3 starts automatically from p23 state. It is enrolled and
  online, with no health warnings; its identity survived normal systemd reboot.
- The empty runtime package keyring causes a separate background WKD parser
  failure. Initial systemd checks are not a long-soak zero-failure claim.

## Just-completed checkpoint

V14 reached SSH37.536s after claim entry and qualified coherent S12 voting in
54.303s. PCIe linked at target uptime62.432s. The driver rejected hw1.1 at
63.367s; no firmware boot was reached. Normal fallback restored V11/services
74.901s after the requested reboot. All experimental storage stayed117-RO.

## Cheapest next action

1. Reuse source1eea8970e87f and its qualified archived kit; do not rebuild it.
   Clean twins and cached Image match; base19/Wi-Fi37 module packages and
   initramfs twins match. V14 now qualifies the staged DT/power path physically.
   Matching hw1.1 module twins and QEMU now pass. Verified WW33 vendor firmware
   and an exact PCI/QMI-keyed board2 container are prepared. The actual kernel
   parser passes384 aliases, retaining the original ELF bytes and refusing
   unsupported keys. Assemble/replay a fresh firmware cycle; never infer QMI
   board ID from PCI0108 or treat defaulted IDs as explicitly reported fields.
   Keep the low hold, all117-RO/power/identity gates and matched write ACKs.
   Never rerun V14. Restore shared networking after each future fallback;
   reuse the fixed missing-interface helper and parameterized stage parser.
   Preserve archives/source; disk headroom remains low. Use
   ROG5_TEST_TMP_PARENT for project RAM scratch; never repurpose HOME.
2. The userspace validation client is online; finish its SSH sign-in check and test
   peer-to-phone Tailscale SSH. Do not re-enroll the phone or treat self-ping as
   peer evidence. Log out/remove the temporary client after successful testing.
3. Package-keyring work is preserved at `b9ceb26`: helper/unit and focused test
   pass, but it is not deployed or integrated into boot. Resume it when needed
   for signed Wi-Fi userspace packages; preserve package-signature enforcement.
4. Continue loaded Wi-Fi/power checks and the remaining standalone server MVP.

Opus retry confirmed expired OAuth; no review produced. Retain V11/V10, the stable loader, module kit and compressed V11 image: no GPT or experimental boot-partition flash.
Do not repeat the completed p24 transfer or successful builds.

## Boundaries and Git

Stop on wrong device/topology, unsafe power/temperature, writes outside the
reviewed scope, ambiguous transport during a write or loss of slot-A rescue.
Never expose credentials or private evidence, or retry ambiguous execution.

- Worktree: `/home/deck/.local/state/rog5-haven-clean-ci-20260810`.
- Branch: `agent/linux-recovery-host`; normal pushes authorized, never force-push.
- V11 executable source: `7f7621ce0a11a624d703200e5a65c03127802736`.
- Resolve publication from Git and exact-head CI, not copied last-pushed fields.

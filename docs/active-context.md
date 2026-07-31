# Active development context

Use this page to resume current work. It intentionally links to detailed
contracts and evidence instead of repeating their history.

## Objective

Reach a repeatable native Linux 7.1.4 minimal server on the ASUS ROG Phone 5:
read-only network root, USB NCM, key-only SSH, bounded rollback, and private
postmortem evidence. Keep the installed Alpine fallback untouched and use
temporary `fastboot boot` only.

GPU, display, desktop, browser automation, hotspot, persistent installation,
and newer-kernel rebases remain frozen until the headless core passes.

## Proven boundary

- The shell-free framed recovery protocol, signed runtime bundle, one-shot
  controller, rollback, and fallback cleanup pass hardware-free tests.
- The accepted Linux 7.1.4 source, corrected DTB, and minimal Kconfig pass the
  [compatibility oracle](core-compatibility-oracle.md) and
  [source/DTB contract](core-source-dtb-contract.md).
- The corrected DTB keeps UFS and USB3 isolated while preserving CPU/RAM,
  USB2/NCM, PSCI, and static thermal topology.
- A credential-clean SSH-only Arch root and fixture-key v3 package/candidate
  reproduce offline. Fixture identities can never pass deployment admission.
- The [88-field runtime gate](minimal-headless-runtime-acceptance.md) checks
  CPU/RAM, exact NFS/OverlayFS mounts, zero phone-storage exposure, USB/NCM,
  key-only SSH, thermals, and the armed rollback process.
- Local CI and GitHub Actions cover the generic QEMU boot, recovery protocol,
  candidate packaging, runtime parsers, rollback, and repository policy.

These facts do not prove the corrected candidate on the phone.

## Active deployment checkpoint

The complete non-fixture identity chain is built and passes hardware-free
admission:

- a dedicated Ed25519 SSH public key is embedded in the minimal root;
- the sealed v3 root, candidate, signed manifest, recovery trust root, and
  reproducible wrapper are mutually bound;
- the exact hashes are pinned by `headless-ssh-deployment-v3`; and
- the real artifact preflight passes without contacting the phone.

See the
[deployment-chain result](../test-results/2026-07-31-headless-ssh-deployment-chain-offline.md).

Before the one temporary boot-only lifecycle can start, the host still needs:

1. the reviewed SteamOS export-store remediation committed, pushed,
   reinstalled, and used to publish the no-replace read-only NFS export;
2. a proven private-key path that can reach the installed Alpine fallback, or
   a separately approved fallback-key installation;
3. a clean local/remote branch and passing key, artifact, cleanup, fallback,
   and connected-fastboot preflights.

The reproducible commands and credential metadata rules are in
[Build the non-fixture chain](minimal-headless-live-cycle.md#build-the-non-fixture-chain).

Tracked execution **HOLD**: repository state never records an operator's live
authorization. Credential use and each temporary boot require explicit
invocation-time authorization after every preflight passes.

The authoritative procedure is the
[minimal-headless lifecycle runbook](minimal-headless-live-cycle.md).

## One-cycle acceptance

The controller must:

1. verify one `lahaina` fastboot device and the exact recovery artifacts;
2. use temporary boot only;
3. anchor the recovery and target USB gadgets to the same physical port;
4. transfer one signed bundle, then close the bundle server;
5. start the fixed read-only NFSv4.2 export and issue one non-retryable
   `COMMIT_EXEC`;
6. pin the volatile target host key without TOFU;
7. collect and verify one strict-SSH runtime record while rollback stays
   armed;
8. observe return to the exact Alpine fallback;
9. prove all host network/export state is removed; and
10. resolve the durable intent as accepted or fallback-returned.

Transport loss without enough correlated evidence remains `UNKNOWN`; it
never authorizes another execute.

## After the core cycle

If the core runtime passes, continue in this order:

1. physical power/volume keys and bounded default-off indicator pulse;
2. sustained read-only battery telemetry and charger-state comparison;
3. CPU cooling, PMIC alarm registration, and bounded thermal fallback;
4. panel-off operation, suspend/wake, SSH continuity, and idle power;
5. sensors, then audio, then WCN6855 enumeration and Wi-Fi client mode.

See [ROADMAP.md](../ROADMAP.md) for completion gates and
[port-status.md](port-status.md) for subsystem evidence.

## Safety invariants

- Never flash an experimental partition.
- Never write or mount phone storage during this development tier.
- Never reuse a consumed live payload or retry an ambiguous execute.
- Keep private keys, host pins, firmware, and live evidence outside Git.
- Follow the [credential-isolation policy](security-automation.md).
- Keep rollback armed until fallback has been independently verified.
- Treat QEMU, static DT checks, and green CI as hardware-free evidence only.
- Publish changes only after focused tests, full CI, and independent review.

Historical detail remains available through the
[archive index](archive-index.md),
[current-state evidence ledger](current-state.md), and dated files under
`test-results/`.

# Active development context

Use this page to resume current work. It intentionally links to detailed
contracts and evidence instead of repeating their history.

## Objective

Reach a repeatable native Linux 7.1.4 minimal server on the ASUS ROG Phone 5:
read-only network root, USB NCM, key-only SSH, bounded rollback, and private
postmortem evidence. Keep installed Alpine configuration and authorization
unchanged; any shell-history or read-induced atime effect requires a separate
action-scoped guard. Use temporary `fastboot boot` only.

GPU, display, desktop, browser automation, hotspot, persistent installation,
and newer-kernel rebases remain frozen until the headless core passes.

## Proven boundary

- The shell-free framed recovery protocol, signed runtime bundle, one-shot
  controller, rollback, and fallback cleanup pass hardware-free tests.
- The accepted Linux 7.1.4 source, corrected DTB, and minimal Kconfig pass the
  [compatibility oracle](core-compatibility-oracle.md) and
  [source/DTB contract](core-source-dtb-contract.md). The retained real source,
  DTB, configuration, modules, buttons/indicator contract, and complete
  phone-free successor gate were
  [revalidated together](../test-results/2026-07-31-accepted-core-baseline-revalidation.md).
- The corrected DTB keeps UFS and USB3 isolated while preserving CPU/RAM,
  USB2/NCM, PSCI, and static thermal topology.
- A credential-clean SSH-only Arch root and fixture-key v3 package/candidate
  reproduce offline. Fixture identities can never pass deployment admission.
- The [88-field runtime gate](minimal-headless-runtime-acceptance.md) checks
  CPU/RAM, exact NFS/OverlayFS mounts, zero phone-storage exposure, USB/NCM,
  key-only SSH, thermals, and the armed rollback process.
- Local CI and GitHub Actions cover the generic QEMU boot, recovery protocol,
  candidate packaging, runtime parsers, rollback, and repository policy. The
  local full-system gate additionally executes the production-generated stage
  130/140 units under real AArch64 `systemd 260.2-2-arch`; its SSH service is an
  ordering stub, not a real OpenSSH proof.

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

The consumed signed bundle has now been replaced by the distinct
`headless-ssh-network-root-v3-r2` transfer identity. One guarded production
build from clean pushed checkpoint `81d2736` produced byte-identical twins,
destroyed its private signing-key snapshot, and reproduced manifest
`9ea27452…d630`. The unchanged public trust root and the exact recovery AVB,
raw image, kernel, initramfs, control, fetcher, verifier, host verifier, and
configuration hashes are pinned by the deployment live gate. Its real
artifact preflight passes without fastboot discovery; see the
[signed r2 result](../test-results/2026-07-31-headless-ssh-successor-r2-signed-build.md).

The host deployment boundary now passes:

- the reviewed SteamOS export-store remediation is pushed and installed;
- the no-replace v3 lower is published below the root-owned `/home` store;
- local key admission, sealed-root, fixed NFS, artifact, and
  connected-fastboot checks pass; and
- the first guarded temporary boot reached stable recovery and transferred
  the exact signed bundle, but recovery rejected PREPARE with `FETCH_FAILED`
  at the former 60-second fetch deadline; no commit or kexec occurred.

The lifecycle now uses the dedicated client key over the fallback USB-NCM
link. A persistent, no-gateway NetworkManager profile assigns only
`169.254.77.1/30`; Alpine remains fixed at `169.254.77.2`. Recovery, target,
and fallback now share one host prefix, removing the route replacement race.
This `/30` profile and the single-session SSH transition pass host and
hardware-free gates but have not yet completed a phone cycle; see the
[USB transition result](../test-results/2026-07-31-usb-ssh-transition-hardening.md).
The preceding live fallback proof used the former `/16` profile.
The controller
requires strict host-key checking, sends one nonce-bound read-only health
probe over non-interactive SSH, verifies Alpine's Ed25519 signature, and then
revalidates the exact product, NCM driver, physical recovery USB location,
direct route, and interface. The protocol binds kernel/init/compatible/root,
modules, pstore, dmesg, thermals, Python, boot ID, and physical USB location.
The normal lifecycle no longer enters the legacy BusyBox shell, eliminating
the ACM echo/framing race and shell-history side effect. Read-induced ext4
atime changes remain separately guarded. The signed ACM path remains
available for emergency diagnostics only. The strict-SSH host-only
preflight validates the client key, host pin, fixed tools, wait range, and the
3,600-second contact-start/7,200-second anchor-age contract without phone
contact. The recovery anchor is revalidated after the SSH proof to cover host
suspend.
Nonce-bound phone errors retain their failure class through the last bounded
serial read. Host cleanup validates the root-owned canonical NFS export table
directly; it no longer mistakes unprivileged `exportfs` lock diagnostics for
an active export.

Forty-six fallback transport tests and all twenty-six lifecycle methods
pass. A physical reboot restored the supervised ACM reader. The fresh signed
exchange then exposed a stale thermal assumption: the installed fallback now
publishes 96 contiguous zones, including unsupported auxiliary channels,
rather than exactly 70 universally readable temperatures. The controller now
requires a bounded contiguous topology, a stable readable quorum, named core
CPU/GPU/system sensors, and the unchanged hard temperature ceilings while
ignoring unreadable temperatures only for an exact observed auxiliary-type
allowlist, plus zero and Qualcomm-inactive values.
One fresh nonce-bound preflight passed and its mode-`0600` signed proof is
retained outside Git. After the rejected recovery attempt, the watchdog
returned the same port to Alpine and a second fresh signed fallback proof
passed. See
the [live acceptance](../test-results/2026-07-31-fallback-acm-preflight-live-accepted.md)
and preceding
[reader rejection](../test-results/2026-07-31-fallback-acm-preflight-live-rejected.md).

The first guarded lifecycle attempt is recorded in the
[live fetch-failure result](../test-results/2026-07-31-minimal-headless-live-cycle-fetch-failure.md).
The host completed the one-shot transfer six seconds after control started,
but the old helper returned only generic `FETCH_FAILED` at its exact
60-second end-to-end deadline. PREPARE stayed `IDLE`, so no COMMIT, durable
intent, or kexec occurred. The attempt also exposed an unprivileged-to-root
NFS cancellation bug; the exact process was terminated once with root
authority, full host cleanup was verified, and the temporary PolicyKit rule
was removed. The active fix preserves exact fetch-stage errors, uses coherent
nested budgets, and gives the fixed root server authenticated cancellation.
The real-host
[cancellation integration](../test-results/2026-07-31-network-root-cancel-host-integration.md)
then found and fixed the parent/zombie wait boundary. Its final rerun passed
through the public launcher, removed every NFS artifact, restored SteamOS
read-only protection, and removed the temporary PolicyKit rule.

The rebuilt recovery then completed fetch, PREPARE, and one durable COMMIT in
the [strict-SSH fallback cycle](../test-results/2026-07-31-minimal-headless-live-cycle-ssh-fallback.md).
Target host-key bootstrap rejected Linux's legitimate indented `cache` route
continuation before SSH acceptance. The watchdog returned the same port to
Alpine, the persistent USB profile restored its then-configured fixed `/16`,
strict SSH verified a signed fallback record at 44.1 degrees C without ACM,
and the intent resolved `FALLBACK_RETURNED`. The profile is now standardized
on `/30`. The target parser accepts only the same bounded cache continuation
already covered by the fallback parser.
The consumed v3 manifest is now denied before private-key inspection. A
hardware-free r2 successor keeps the accepted target/root tuple and changes
only the signed bundle identity; base/r2 twin packaging proves all other
manifest fields remain equal. The predicted r2 manifest identity is pinned in
the [offline successor result](../test-results/2026-07-31-headless-ssh-successor-r2-offline.md),
and the real external r2 candidate is now staged outside Git. A
credential-free check binds it to the retained package, exact
Image/DTB/initramfs bytes, and predicted manifest identity; see the
[real-candidate checkpoint](../test-results/2026-07-31-headless-ssh-successor-r2-real-candidate.md).
The reusable preflight and its 22 hostile tests are pushed at
`773a1196cbfad33ab87124c47ed9772f6251c40c`; the formal run against all three
external inputs passed at that exact clean, origin-synchronized checkpoint
with no credential or phone access.
That exact r2 candidate is now signed and twin-built. It reproduced the
predicted manifest, reused the existing public recovery trust root, and its
recovery-wrapper, verifier, and configuration identities are pinned. The
review/publish gates are green. The signed r2 bundle is now installed through
the no-replace path, the consumed predecessor is retained in a private
recoverable archive, and the aggregate key, artifact, privileged-host,
fallback-SSH, and connected-fastboot preflight passes from clean pushed
checkpoint `e635257`. The temporary PolicyKit authorization was removed and
the final host residue audit is clean; see the
[r2 host preflight](../test-results/2026-07-31-headless-ssh-successor-r2-host-preflight.md).
The first r2 temporary boot completed the signed recovery transfer, PREPARE,
and one durable COMMIT. Linux 7.1 exposed the expected USB-NCM product on the
same physical port, then physically disconnected 23 seconds later before the
target host key could be pinned. The watchdog returned the unchanged Alpine
fallback, strict SSH accepted one fresh signed identity record, and the
durable intent resolved `FALLBACK_RETURNED`. A short NetworkManager/udev
observation race in final cleanup is now covered by a bounded continuously
clean dwell; all non-identity cleanup failures remain immediate. r2 is
consumed and must not be retried. See the
[r2 target USB-loss result](../test-results/2026-08-01-minimal-headless-r2-target-usb-loss.md).

The active hardware-free successor is now the distinct
`headless-netroot-early-diag-v1` diagnostic profile. Its shared-init branch is
fixed-identity gated and adds only a write-only ACM reporter, monotonic stage
updates, two volatile post-handoff units, and a bounded five-second terminal
dwell. Normal network-root mode remains reporter/ACM/unit/dwell-free. The
sealed reporter and optional archive integration twin-build locally; the
native bundle verifier requires the helper for the diagnostic profile and
forbids it elsewhere. The corrected Linux 7.1.4 QEMU profile enables the
demonstrated FUTEX, MEMFD_CREATE, SHMEM, and TMPFS requirements. Its clean
local full-system run enters the sealed Arch runtime under real AArch64
`systemd 260.2-2-arch` and executes the exact generated stage 130/140 units.
The test SSH daemon is only an ordering stub, so real OpenSSH and all phone
hardware remain outside this evidence. See the
[systemd QEMU result](../test-results/2026-08-01-arm64-systemd-qemu-gate.md).
The receive-only host collector now starts kernel-event capture before target
enumeration, binds one diagnostic ACM interface to the recovery anchor's port,
parses only validated frames through the shared oracle, and writes one bounded
mode-`0600` JSON record outside Git. Its twenty-one hostile tests, deterministic
subprocess lifecycle test, and real unprivileged journal-reader smoke pass;
see the
[collector result](../test-results/2026-08-01-early-target-host-collector-offline.md).
GitHub rerun is pending. No diagnostic signing, candidate promotion,
credential use, or phone action has occurred.

See the
[real-host deployment result](../test-results/2026-07-31-steamos-deployment-preflight-live.md).
The replacement fallback control boundary is recorded in the
[authenticated ACM result](../test-results/2026-07-31-fallback-acm-control-offline.md).

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
8. verify the returned Alpine fallback through its strict-SSH signed,
   nonce-bound health record;
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
- Never mount phone storage or write it. The active strict-SSH lifecycle does
  not invoke the legacy interactive shell; any emergency ACM use retains its
  separate BusyBox-history/atime authorization boundary.
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

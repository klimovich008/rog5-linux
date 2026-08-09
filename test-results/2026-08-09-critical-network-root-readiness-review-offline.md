# Critical network-root readiness review — offline

Date: 2026-08-09

Result: **HOLD.** A host/target startup race window is reproducible in a
hardware-free ordering model, and the unissued successor now waits for exact
TCP/2049 acceptance before consuming its sole diagnostic NFS mount attempt.
This does not prove that the race caused Generation 12. Physical USB-NCM
timing and lineage-safe independent postmortem evidence remain unproven.

The review started at Git commit
`1a69cd4bf7017e8a96df1a73774965e16bea11d3`. No phone, fastboot, ADB, ACM,
NCM, SSH credential, signing key, administrator credential, candidate,
policy row, phone storage, flash, wipe, slot operation, persistent install,
or phone boot was used. Generation 12 remains consumed and permanently
non-retryable. The active successor remains unissued, offline-only, and has
no boot authority.

## Hypothesis outcome and measured host transitions

The production ordering can expose gadget carrier before the host finishes
its one-second interface-discovery poll, NetworkManager handoff, link-up,
address assignment, firewall classification, and listener revalidation. A
fixture that makes the client active at poll start reproduced that design
window and exercised the production transition functions with injected,
deterministic command latency:

| Transition | Delta | Elapsed from client-active model |
|---|---:|---:|
| gadget interface discovered | 1,010 ms | 1,010 ms |
| NetworkManager unmanaged confirmed | 40 ms | 1,050 ms |
| link up | 40 ms | 1,090 ms |
| exact `169.254.77.1/30` present | 40 ms | 1,130 ms |
| exact `drop` zone confirmed | 50 ms | 1,180 ms |
| sole exact `169.254.77.1:2049` listener confirmed | 30 ms | 1,210 ms |
| exact network-root link ready | 0 ms | 1,210 ms |

These are hardware-free modeled timings, not measurements of Steam Deck USB
enumeration. They prove the race is structurally possible and that every
production transition is now timestamped with monotonic time. Generation 12
showed stage 70 from 3.544 through 12.547 seconds, which is longer than this
modeled window; the evidence therefore cannot select this race over a lower
USB, kernel, or NFS failure.

The firewall order was not changed. The final hostile model measured a 50 ms
interval between exact address insertion and completion of the `public` →
`drop` transition. This is an address-before-drop-zone ordering window in a
deterministic injected-delay model, not a Steam Deck measurement and not a
packet-exposure measurement. The unprivileged fixture does not exercise
active/default-zone packet filtering during that interval. A failed zone
transition now proves that final
readiness is unreachable, and loopback, wildcard, and wrong-address TCP/2049
listeners cannot satisfy the exact-listener check. The server still binds only
`169.254.77.1:2049`, exports only to `169.254.77.2/30`, installs the narrow
NFS allowance into the protected active-zone set, and ultimately moves the
interface into drop-by-default `drop`. Address assignment still precedes the
final zone transition, so a previously unknown/default zone is a residual
security consideration. Reordering needs a dedicated privileged network
namespace/firewalld proof; an unverified suggestion was not applied.

## Target rendezvous and exact diagnostic semantics

`initramfs/network-root-init` now uses the sealed BusyBox `nc` applet with a C
locale and the exact source-bound probe:

```text
nc -n -z -w 1 -s 169.254.77.2 169.254.77.1 2049
```

Only diagnostic mode runs this rendezvous. It performs at most 12 probes and
11 quarter-second sleeps, for a 14.75-second probe/sleep upper bound. Before
and after each failed probe, and once more after success, it verifies the sole
expected `a600000.dwc3` UDC, `usb0`, carrier, sole exact
`169.254.77.2/30` address, and direct source-bound route. TCP acceptance is
reported only as host-port reachability; it is never called NFS readiness.

The sealed BusyBox 1.37.0 `nc` supports `-n -z -w -s`, but both refusal and
some timeout paths can exit 1 without stderr. The target therefore measures
the exact probe against monotonic `/proc/uptime`: a failure lasting at least
900 ms of the one-second connect budget is `host-port-timeout`; an immediate
failure is conservatively `host-port-unreachable` because this applet does
not expose a stable errno distinction. Exit 126/127 or clock/output failure is
`host-port-probe-failed`. This distinguishes timeout where reliable without
mislabeling an unobservable immediate failure as definitely refused.
Transport loss retains its exact UDC, interface, carrier, address, or route
classification.

A final two-axis review found that the three new host-port strings were absent
from both the native reporter and host parser. PID 1 could therefore retain
the right internal reason while stage 200 lost the terminal evidence. A
fail-first round-trip rejected all three values; the fixed native/host test
accepts them, and a clean-twin AArch64 reporter gate compares all three frames
byte-for-byte with the host oracle.

The pinned applet was executed under AArch64 user emulation: refusal returned
status 1 with empty stderr, `nc --help` proved all four required options, and
`sleep 0.25` completed in 267 ms. The builder inherits the applet from the
accepted base hash and the verifier now requires `/usr/bin/nc`; a missing
runtime binary additionally fails as `host-port-probe-failed`.

After rendezvous success, diagnostic mode executes exactly one NFS mount:

- stage 70 immediately before that call;
- stage 75 immediately after it returns;
- transport reclassification after return, success or failure;
- stage 80 only after mount success and read-only lower verification.

Normal non-diagnostic mode retains its bounded 30-attempt behavior. The
already-armed rollback watchdog is neither replaced nor disarmed.

Hostile tests cover delayed readiness, interface disappearance, carrier
loss, wrong route and source address, listener-never, listener-after-deadline,
timeout by measured duration, immediate connection failure, missing probe,
an unrelated endpoint, exact source/endpoint binding, unchanged watchdog
identity, one diagnostic mount maximum, and stage 70/75/80 ordering.

## Exact patch set

- `initramfs/network-root-init`: adds the sealed source-bound TCP rendezvous,
  monotonic failure classification, exact pre/post transport checks, revised
  NFS options, and restores the normal-mode NFS failure default;
- `scripts/device/test-network-root-init.sh`: adds fail-first and hostile
  rendezvous, one-mount, terminal-classification, timeout, missing-probe,
  watchdog, normal-30-attempt, and stage-order regressions;
- `scripts/device/verify-network-root-initramfs.sh`: requires the sealed
  `/usr/bin/nc` applet;
- `scripts/host/serve-network-root.sh`: timestamps and proves every host
  readiness transition without changing firewall order;
- `scripts/host/test-network-root-host.sh`: reproduces client-before-host
  readiness ordering, records per-transition duration, and verifies monotonic
  exact order;
- `tools/qemu-network-root-nfs/init.c`: keeps the QEMU client/server probe
  option identities synchronized with production.
- `tools/early_target_diag/rog5-early-target-diag.c` and
  `scripts/host/early-target-diagnostics.py`: add the exact three host-port
  terminal reasons to the native and host vocabularies;
- reporter/initramfs builders and seals: pin clean-twin reporter
  `26249252…bafa` and clean-twin offline diagnostic initramfs
  `94edd625…cffc`, both with no boot authority;
- signed-DTB verification: binds the accepted latent GENI debug-UART route,
  including exact root cells, ancestor translation, and pinctrl, while making
  no claim that ASUS exposed it physically.

The concrete defects fixed are: carrier was accepted before host reachability;
host setup had no transition timing/proof; diagnostic mode consumed its mount
without a host rendezvous; one-second NFS RPC timing was too narrow for cold
startup; timeout/immediate/probe failures were conflated; and moving the NFS
fault assignment into the diagnostic branch accidentally left normal retry
exhaustion with a stale fault. Each has a regression that fails against the
prior source.

## NFS timeout calculation

The old `timeo=10,retrans=1` gave a two-second first TCP RPC major-timeout
horizon where the NFSv4 client honors retransmission timeout. The new
`timeo=30,retrans=2` starts at three seconds and Linux 7.1.4's linear TCP
calculation sets the first major deadline to
`3 + (3 * 2) = 9` seconds. The suggested `timeo=150,retrans=2` would produce
45 seconds and was not adopted. `nolock` was removed because NFSv4 integrates
locking; repository search found no independent contract requiring that
token, and the production/QEMU option identities remain exact.

Nine seconds is not a complete mount upper bound. The exact Linux 7.1.4 NFSv4
client sets `NFS_CS_NO_RETRANS_TIMEOUT`; after a soft request is sent on an
established transport, it may wait until the transport becomes terminally
broken. The real outer bound remains the already-attested 600-second target
userspace SysRq watchdog. The 14.75-second rendezvous and nine-second first
major window fit inside it, and the prior Generation-12 report observed its
deadline at 602 seconds. No external `timeout mount` wrapper was introduced,
because killing a blocked mount process does not by itself prove clean kernel
RPC/mount teardown.

The exact QEMU client mirror uses the revised option string. QEMU remains a
useful NFS/OverlayFS/systemd/OpenSSH contract, but its Ganesha server, disabled
NFSv4.2 `READ_PLUS`, and TCP forwarding do not model physical USB-NCM or the
Steam Deck kernel NFS server.

## Watchdog audit

The built target config does contain `CONFIG_WATCHDOG=y`,
`CONFIG_WATCHDOG_CORE=y`, `CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y`, and
`CONFIG_QCOM_WDT=m`. The matching modules archive contains `qcom-wdt.ko`, but
the sealed early initramfs contains neither that module nor a module tree. It
contains BusyBox `modprobe` and `watchdog`, yet invokes neither for a hardware
watchdog. The accepted DTB has no matching QCOM watchdog node, and the driver
does not match the recovery/Haven `qcom,hh-watchdog` device.

Consequently, `qcom_wdt` is not available, probed, or opened early enough for
the failure classes under review. Building it in would still lack a matching
device and could conflict with the explicit Haven secure-watchdog handoff in
`load-mainline-recovery.sh`; it is not justified without a separate hardware
ownership and DT review. The target's attested 600-second userspace SysRq
timer remains the active inner rollback layer. Stable recovery's separate
180-second rollback process and Haven watchdog handling remain separate.

## Independent postmortem channel

The target writes a candidate/boot-ID lineage marker, and stable recovery has
built-in pstore/ramoops support plus a bounded read-only snapshot and signed
correlation path. Hostile offline tests correctly refuse to treat empty or
missing pstore as proof that no crash occurred. What is still missing is live
proof that the reserved RAM record survives this exact target → reset →
bootloader/recovery path with unambiguous current-cycle lineage. Installed
Alpine cannot read the target's reserved region, so the fallback alone cannot
close this gap.

Every live progress frame still depends on the USB path under diagnosis. The
accepted target DTB and config contain a coherent GENI debug-UART route through
QUP SE3 to GPIO18/19, and the clean-twin bundle verifier now binds that latent
route. There is still no evidence that ASUS exposed it through USB-C, test
pads, or another connector on anakin. Stable recovery also lacks GENI console
support. UART is therefore a latent assessment item, not an available channel;
any future electrical probe must keep adapter TX disconnected because serial
Magic SysRq remains enabled. See the
[independent observability review](2026-08-09-independent-observability-review-offline.md).

## VCNL36866 and storage disposition

The uncommitted VCNL36866 driver/DT/candidate set is preserved exactly as a
separate working-tree island. Its partial build A is retained; no build B,
candidate, manifest, or clean-twin proof exists. Independent standards and
specification reviews found multiple P1/P2 blockers, including an
unrepresentable exact 3.300 V PM8350C L7 request, missing regulator-mode
decision, a runtime-PM Kconfig mismatch, interrupt-unsafe lock cleanup, and
tracked test registration that refers to untracked scripts. Static self-tests
pass, but they do not qualify the set. See the
[isolated VCNL review](2026-08-09-vcnl36866-working-tree-review-offline.md).

No build data was deleted. `build/` is 203,412,105,198 bytes (189.44 GiB), no
build process or held build lock was found, and two idle containers remain.
The [retention inventory](2026-08-09-build-retention-inventory.md) separates
reproducible evidence, rebuildable caches, historical duplicate builds,
incomplete VCNL state, and a quarantine-first recovery procedure. Material
deletion still requires a separate operator decision.

## Verification and timing

Fail-first tests rejected the old target in 90 ms because the sealed `nc`
contract was absent and rejected the old host in 115 ms because the first
transition was not timestamped. Before implementation, the passing target
and host suites took 1,638 ms and 233 ms. The final focused results are:

- target init/hostile rendezvous suite: PASS, 2.604 s. Its final hostile case
  starts the production `arm_watchdog` path, proves both live watchdog/timer
  PIDs and start times plus the exact eight-field lease hashes before and
  after an unreachable-host rendezvous, and leaves both processes armed;
- host transition/security suite: PASS, 1.358 s, including the 50 ms modeled
  address-before-drop-zone ordering window and fail-closed zone/listener
  cases. This is not a packet-exposure measurement: the unprivileged fixture
  does not exercise active/default-zone packet filtering during the zone
  transition;
- hostile QEMU NFS contract: PASS, 11.139 s;
- native reporter/host parser: fail-first 3/27 failures in 4.759 s; fixed
  27/27 PASS in 4.887 s on the final focused rerun;
- clean-twin AArch64 reporter and three fault/oracle frames: PASS, 13.508 s;
- native bundle verifier: ancestor-bus fail-first 9 hostile failures in
  4.147 s, root-cell fail-first 2 failures in 2.020 s, fixed 26/26 PASS in
  4.335 s;
- clean-twin AArch64 bundle verifier plus QEMU mutations: PASS, 69 s,
  source `f41142a7…60d`, twin binary `33aa65c6…42ef`;
- clean-twin diagnostic initramfs: PASS, 80.187 s;
- runtime bundle packager: 8/8 PASS, 4.279 s;
- recovery prepare/load/execute integration: 2/2 PASS, 5.297 s;
- shell/C syntax and `git diff --check`: PASS;
- VCNL source-oracle tests: 17/17 PASS, 0.701 s;
- VCNL patch contract: 8/8 PASS, 0.973 s;
- VCNL DTB contract: 4/4 PASS, 1.036 s;
- VCNL candidate static contract: PASS, 0.314 s;
- constrained Claude advisory review: identified the sealed-applet behavior
  proof and one real normal-mode fault-default regression; the former was
  executed against pinned BusyBox and the latter was fixed with a hostile
  30-attempt test. Its UDC/interface/carrier fixture objection did not apply
  because those cases inject loss only after the mount returns;
- complete repository Linux `ci` tier: PASS, 456.488 s at the first final
  checkpoint (the preceding pre-root-cell-review checkpoint was 454.528 s).

The increased target/host focused time is the intentional hostile rendezvous
coverage and one-second discovery-order model, not a production performance
measurement.

The final review retained three self-contained UART DTS test fixtures rather
than introducing a shared test helper. This is deliberate isolation: each
packager, native-verifier, and lifecycle integration suite owns its complete
input and can detect local fixture drift without importing another suite.

## Recommendation

**HOLD candidate admission.** The offline patch closes the demonstrated
ordering defect and improves classification without weakening one-shot or
rollback policy. It does not prove Generation 12's cause, does not measure the
physical host transition, and does not yet provide lineage-safe independent
failure evidence. Do not issue, sign, authorize, or boot a successor from
this checkpoint.

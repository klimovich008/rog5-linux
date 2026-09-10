# Network-root v16 trace-free GPUCC confirmation — staging-only live result

Date: 2026-07-25–26

Result: **target not entered; GPUCC not probed; v16 attended cycle consumed**.
The exact persistent fallback and complete host cleanup passed. Nothing was
flashed.

This result contains no Linux 7.1 target, GPUCC registration, module-load,
bind, stability, or acceleration evidence. V15 remains the latest kernel-side
GPUCC evidence.

## Reviewed inputs

The cycle used repository checkpoint
`ae8b4c2c8454c7eb4dc9953c391f83952f61ef8f` and the already accepted v15
kernel/package bundle:

| Input | SHA-256 |
|---|---|
| Linux 7.1.4 Image | `d30df38804750ded48607135a7d23d4f95e0947c49b68395a8f6818c4a27c54b` |
| external `gpucc-sm8350.ko` | `9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a` |
| temporary-boot AVB image | `bb4a6e34c98475f991a9575defe57c52ac732da0cea96a10585ee0bb92ae7730` |
| fourteen-file manifest | `a739f975f87ac30918625178007b4cd7302449ae96c26e5c42185e9e1a0425cc` |

The
[v16 offline report](2026-07-25-network-root-gpucc-confirmation-offline.md)
records the unchanged kernel identity, trace-free target contract, baseline,
probe, and one-shot acceptance criteria.

## Preflight

Before temporary boot:

- strict pinned fallback SSH reached the exact stock kernel and ext4 root;
- standard pstore, current fatal signatures, and project diagnostic modules
  were all zero;
- 73 thermal zones were readable and the maximum was 47.4 C;
- the unique fallback-to-Fastboot helper was privately syntax-checked;
- the candidate, export root, firmware, Git head/upstream, strict SSH files,
  non-autoconnecting fallback profile, and host services were exact;
- NFS, NFS listeners, exports, runtime firewall rules, target addresses, and
  prior inhibitors were absent; and
- a new host sleep/shutdown inhibitor and exact-peer, read-only NFSv4.2
  window were armed before the reboot transition.

Private boot identity, phone identifier, SSH identity, NetworkManager
identifier, full command lines, and helper path remain outside the repository.

## Staging result

Exactly one `fastboot boot` completed. There was no flash command.

The fixed `load-gpucc-confirmation` action contained diagnostic systemd masks,
the 900-second eventual target watchdog, and none of the Qualcomm, CCF, or
RCG2 core trace flags. The first success marker raced ACM re-enumeration, so
the helper rediscovered the endpoint and replayed only the identical
idempotent load action once. The second observation returned the exact load
PASS marker.

The staging recovery itself retained its independent 180-second rollback
watchdog. Temporary boot to completed load evidence took 78 seconds.

No target execute was transmitted:

1. The next host invocation occurred 284 seconds after the load result and
   omitted `ALLOW_ATTENDED_KEXEC=1`. It failed in `main()` before device
   discovery.
2. A guarded invocation 82 seconds later failed while waiting for one stable
   `ROG5_recovery` ACM identity. Source ordering proves this happened before
   `run_serial()` and before a `kexec -e` write.
3. The only ACM then present identified as the persistent Alpine server.
   The staging watchdog had already restored fallback.

The exact NFS server never observed a `ROG5_network_root` link. There is no
target boot identity, strict target SSH session, pre-disarm baseline, staged
GPUCC module, independent 75-second probe watchdog, probe log, or post-load
evidence.

The gap was an operator/control-plane defect: load and execute were separate
host invocations, allowing a task boundary to exceed the staging watchdog.
It is not evidence for or against the v15 kernel candidate.

## Rollback and cleanup

No execute retry and no second temporary boot occurred. The phone returned to
the exact fallback with a changed private boot identity:

- stock kernel and ext4 root exact;
- pstore, current fatal signatures, and project diagnostic modules all zero;
- 73 readable thermal zones, maximum 41.1 C; and
- strict pinned fallback SSH restored.

Complete host cleanup passed:

- NFS threads, listener, mount daemon, export, bind mount, temporary
  filesystem, nonlocal bind setting, and runtime firewall rules removed;
- no target `/30` address, Fastboot target, or ADB target;
- exact fallback `/16` profile active with autoconnect disabled;
- ModemManager and firewalld active;
- host inhibitor removed; and
- Git remained synchronized and clean.

The private evidence directory is mode `0700`; all 29 evidence files are mode
`0600`. No private evidence or binary artifact is committed.

## Required next gate

V16 must not be rerun. V17 may reuse the byte-identical v15 artifacts and v16
target checks only after an offline-tested compound transport:

1. both ACM and attended-kexec guards fail before device discovery;
2. one process runs `load-gpucc-confirmation` and then `execute` immediately;
3. load-marker replay remains bounded to the identical load action;
4. a load failure makes execute unreachable;
5. execute remains non-retryable after its serial call;
6. no operator sleep or mutable command enters the sequence; and
7. the complete v15 artifact verifier and v16 target baseline/probe gates
   remain exact.

One later v17 live cycle must still satisfy all original GPUCC bind,
30-second stability, zero-consumer, zero-storage, warning/fatal, thermal,
rollback, and cleanup criteria. Even a PASS accepts only the GPUCC/CCF
foundation, not GPU acceleration.

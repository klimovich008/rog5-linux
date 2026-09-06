# Generation 12 NFS/watchdog critical-path review — offline

Date: 2026-08-10

Starting repository HEAD:
`91334dcb9ef26f21a66fe55a4ae843d8cc218d7c`

Recommendation: **HOLD**

No phone, fastboot, ADB, ACM/NCM device, phone storage, SSH credential,
signing key, administrator credential, candidate, policy row, flash, wipe,
slot operation, persistent installation, or phone boot was used. The
Generation-12 claim remains consumed and non-retryable. The VCNL36866 working
tree was preserved as a separate island.

## Conclusions

Two distinct failures are now supported by the retained evidence.

1. **Confirmed NFS availability failure.** Generation 12 could not mount NFS
   because the host lifecycle cancelled the NFS service before the target
   enumerated. At historical commit `1ee55086ac9c4c8049940d410bcfdf8317a2721b`,
   the lifecycle started the NFS server before COMMIT, waited for the control
   process, then parsed its output. Its obsolete exact seven-field PREPARE
   parser rejected the valid extended PREPARE record after the one COMMIT had
   already been claimed. The exception path immediately called the privileged
   NFS cancellation helper. The retained server log then records interrupted
   `sleep 1`, `rpc.mountd` receiving SIGTERM, and NFS/firewall cleanup. No
   `exact network-root USB link ready` record exists. This cancellation is
   directly relevant to the failed mount, although it does not by itself
   explain the later USB disappearance.
2. **Separate unresolved USB/target-reporting loss.** The shell-free native
   responder in Generation 12 omitted the Haven watchdog deactivation used by
   every accepted legacy attended loader. The exact recovery kernel enabled
   and periodically petted that hypervisor watchdog; the mainline target could
   not continue the recovery kernel's timer/service path after kexec. This is
   the strongest current USB-loss hypothesis, not a proven reset cause.

The 40 target records are one state change plus native 250 ms heartbeats
carrying the current stage. Stage 70 was emitted once before the old 30-attempt
shell loop. Retained evidence cannot distinguish one blocked `mount(2)` from
one or more returned mount commands followed by shell retries. It does not
prove 40 or nine mount attempts.

## Historical timeline

Times below are Europe/Paris (`+0200`). “Actual” means a timestamp embedded in
the durable record or host kernel event. A file mtime is labelled separately.

| Time | Evidence and interpretation |
|---|---|
| before 21:44:16.261482661 | The NFS server completed export/listener setup and published the private handoff marker. This ordering is proven by the historical `before_commit` callback, but the ready line itself has no timestamp. |
| 21:44:16.261482661 | The durable host intent was created immediately before the single COMMIT wire exchange. This is the earliest retained COMMIT-send boundary, not a byte-level serial timestamp. |
| 21:44:16.268839173 | `recovery-control.log` mtime after the extended PREPARE, valid CLAIMED COMMIT, transmitted UNKNOWN intent, and final PASS line were written. The target invokes execution only after draining the CLAIMED response. The exact `kexec -e` entry time was not retained. |
| by 21:44:17.442856705 | `network-root-server.log` final mtime. Exception cleanup had sent SIGTERM; the log contains interrupted `sleep 1`, `rpc.mountd` SIGTERM, and complete NFS/firewall cleanup. |
| host monotonic 378772.131037 | Recovery USB device 64 disconnected. The collector attached wall time 21:44:22.759940937 when it ingested this event. |
| host monotonic 378772.555036–378772.772047 | Target high-speed USB device 65 enumerated, identified as `ROG5 diagnostic network root`, registered NCM/ACM, and renamed its NCM interface. Collector ingestion began at 21:44:22.868311586. |
| 21:44:23.437393177 | First target frame captured: stage 10 at target boottime 2.794 s. |
| 21:44:23.438406552 | First stage-70 heartbeat captured: target boottime 3.544 s. |
| 21:44:31.957195352 | Last frame captured: stage 70 at target boottime 12.547 s. |
| 21:44:39.929046062 | Collector ended with `disconnected`; this bounds detection, not the precise physical disconnect. The target disappeared sometime after the last frame and no later than this observation. |
| no retained event | The first Alpine USB reappearance was not timestamped. The current journal has no surviving entries for this interval. Its time is therefore unknown, not 7 minutes 39 seconds after the last frame merely because later SSH evidence has that gap. |
| by 21:52:16.445235417 | Fallback-profile-restore log mtime after the exact Alpine profile restoration passed. The start of restoration was not separately timestamped. |
| by 21:52:18.690270778 | Exact fallback identity and strict-SSH preflight were complete. |
| by 21:52:21.518315327 | Durable intent resolution recorded `FALLBACK_RETURNED`. |

No retained file supplies an exact `kexec -e` timestamp. The safe statement is
that it followed the drained CLAIMED response and preceded the observed
recovery-to-target USB transition.

## Watchdog source and runtime audit

The exact retained wrapper kernel is
`895272e87d5a90ae6b9b8df71862b48d819479d5bbf2741fab002126e47d3eae`.
Its exact config is
`df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f`
and contains:

```text
CONFIG_HAVEN_DRIVERS=y
CONFIG_HH_VIRT_WATCHDOG=y
CONFIG_QCOM_SOC_WATCHDOG=y
CONFIG_QCOM_FORCE_WDOG_BITE_ON_PANIC=y
CONFIG_QCOM_WATCHDOG_BARK_TIME=22000
CONFIG_QCOM_WATCHDOG_PET_TIME=9360
```

The exact retained `hh_virt_wdt.o` is
`4f62325761bb950275d19b031d6846106bba0289f15e19fc360b2cc18d5a61df`.
Its LLVM IR and final `vmlinux` prove:

- the fixed driver name is `hh-watchdog` and the exact match compatible is
  `qcom,hh-watchdog`;
- registration programs a 9,360 ms pet interval, enables/resets the watchdog,
  marks it enabled, and schedules its pet timer;
- the configured bark and bite values are 22,000 ms and 25,000 ms;
- `hh_disable_wdt()` performs the Haven SMC and can log
  `failed disabling VDOG, hret = ... ret = ...`;
- the common disable path can clear its software-enabled state even when the
  hypervisor disable reports an error, so readback `1` alone is insufficient;
- the separate secure deactivation path can log
  `Failed to deactivate secure wdog`;
- the platform driver has remove and PM suspend/resume handling, but the exact
  Generation-12 execution path invokes no remove, shutdown, reboot, syscore,
  or kexec deactivation before `kexec -e`.

The exact historical shell-free responder and `recovery-init` contain no
watchdog-disable equivalent. The legacy network-root, recovery, persistent
root, persistent-root-entry, and UFS loaders all explicitly locate, disable,
read back, and kernel-log-check the Haven control before kexec. Historical
successful attended self-kexec evidence used that explicit step. Generation
12 omitted it, but the retained evidence contains no reset-reason register or
post-return current-cycle pstore proof, so correlation is not causation.

If the last recovery pet occurred anywhere in its 9.36-second interval before
kexec, nominal bark/bite boundaries can fall approximately 12.64–22.00 s and
15.64–25.00 s after target takeover. The observed reporting-loss interval is
after 12.547 s and no later than collector detection around 20.519 s of
derived target uptime. The timing is compatible with an inherited watchdog
only for part of the unknown last-pet phase; it does not prove a watchdog
reset, and Kconfig values are not a captured physical runtime countdown.

## Reset-reason and independent-observer evidence

The retained private directory contains no post-return PMIC PON reason,
warm-reset reason, watchdog bark/bite reason, bootloader restart reason, panic
record, or host TCP/RPC snapshot. The surviving host journal has no entries
for this wall-clock interval. USB device numbers prove recovery device 64 was
replaced by target device 65, but no retained event identifies the later
fallback device number or reset cause.

The current ramoops design is not invalidated by the claim that a new recovery
kernel immediately overwrites old console data. Persistent RAM initialization
saves the existing zone into `old_log` before reusing the current buffer, and
ramoops exposes that saved record. The unresolved risks are physical DRAM
retention, firmware/bootloader clearing, stale lineage, and observer failure.
An empty snapshot remains inconclusive. A useful retention experiment must
first write and correlate a known current-cycle marker; it can then distinguish
matching panic data, stale/different data, loss/empty, and observer failure,
but a watchdog reset may legitimately have no Linux crash dump.

## USB-loss ranking

For **why NFS could not mount**, the known host cancellation is a sufficient
cause: host parser-cleanup cancellation 100%; every other category 0%. This
does not assert that the target had no additional fault.

For **why USB/target reporting disappeared**, the current evidence-weighted
ranking totals 100%:

| Cause | Weight |
|---|---:|
| undisabled Haven watchdog | 42% |
| target kernel panic/oops | 24% |
| DWC3/NCM/ACM loss while target remained alive | 15% |
| kexec residual-state problem other than the classified Haven watchdog | 10% |
| host NFS cancellation/parser cleanup directly causing USB loss | 0% |
| NFS/RPC behavior after server disappearance triggering a target fault | 5% |
| target userspace watchdog/reset | 0% |
| power/thermal | 1% |
| host reporting artifact | 2% |
| other supported cause | 1% |

The 602-second target userspace deadline does not fit the observed early loss.
`panic=10` can fit a panic followed by delayed restart. Pure DWC3 loss remains
plausible because every target frame used the transport under diagnosis.

## Offline correction

The native shell-free responder now adds one mandatory handoff after the
CLAIMED response is drained and before `execution-started` is persisted:

1. prove the independent userspace rollback watchdog remains live;
2. open the fixed `/sys/bus/platform/drivers/hh-watchdog` directory with
   no-follow semantics;
3. require exactly one bound device symlink, pin its directory, prove its
   `driver` resolves to the same driver inode, and require the exact binary DT
   compatible `qcom,hh-watchdog\0`;
4. require the exact owner-only `disable` control and initial `0\n` state;
5. establish a `/dev/kmsg` sequence boundary after proving the fixed no-follow
   node is the root-owned/root-group character device `1:11`, singly linked and
   not world-writable (without assuming that recovery `mdev` selects `0600`
   rather than `0644` or `0660`);
6. revalidate identity, perform exactly one two-byte `write("1\n")` with no
   retry, revalidate identity again, and require exact `1\n` readback;
7. reject either new driver failure signature, including the independently
   reviewed readback-1 hypervisor-failure case;
8. only then persist `execution-started` and invoke the fixed executor.

Any refusal durably records `HAVEN_WDOG_FAILED`, unloads the prepared kexec
image, keeps `execution_started=NO`, and leaves the irreversible claim
consumed. Duplicate COMMIT and restart remain non-executing. Production paths
are fixed; test-only path injection is compiled out of the release binary.
The write is byte-count and attempt bounded and remains globally bounded by
the independent rollback process. It is not wrapped in a killable per-syscall
timeout because an in-kernel sysfs/SMC write cannot be safely cancelled by a
userspace deadline; a timeout wrapper would create false certainty.

The protocol/reference model now requires an explicit Haven handoff for every
modeled execution instead of permitting an omitted callback. The sole valid
pre-execution terminal state is `EXEC_FAILED`,
`last_error=HAVEN_WDOG_FAILED`, `execution_started=NO`.

Hostile tests match the legacy loader's exact driver/compatible/readback cases
and extend them with zero and multiple devices, wrong driver inode, extended
compatible lists, unsafe symlinks/modes, already-disabled state, exact short
write with no retry, wrong readback, both new kernel error signatures, stale
pre-boundary signatures, device disappearance, prepared-image unload, durable
failure publication crash boundaries, duplicate-COMMIT refusal, and absence of
test path overrides in the production binary.

## Rendezvous and observer effect

The current diagnostic TCP rendezvous has a 14.75-second probe/sleep bound.
If Generation 12 inherited a watchdog whose remaining life could be only
12.64–15.64 seconds, that wait could move a reset from stage 70 into the
readiness phase and make “host unavailable” look self-confirming. Shortening
the rendezvous in isolation is not the safe correction: it would reintroduce
the proven host-ordering race. The minimal order is to prove the Haven handoff
first, retain exact transport checks and rollback, then reassess physical host
timing. No rendezvous or NFS timeout was changed in this correction.

## Verification checkpoint

The first fail-first native test ran against the old responder and failed in
2.261 s because a missing Haven device still reached execution and recorded
`EXEC_RETURNED`. The fixed suite additionally contains a readback-1
`failed disabling VDOG` case that the first handoff revision would have
accepted.

Focused results before repository-wide CI:

- reference protocol/state model: 53/53 PASS in 0.269 s (0.40 s shell wall),
  including mandatory handoff proof;
- native x86 responder before final review additions: 86/86 PASS in 50.823 s
  (51.14 s shell wall); the pre-change 72-test baseline took 26.842 s in an
  earlier unloaded run, so these wall figures are not a production latency
  comparison;
- both kernel-error signatures, stale-boundary behavior, and production
  strings: 4/4 PASS in 2.718 s;
- ASan/UBSan Haven hostile subset: 15/15 PASS in 3.046 s;
- fixed stable-recovery control: 42/42 PASS;
- timeout lattice: 1/1 PASS;
- recovery-init policy: 12/12 PASS;
- recovery candidate integration with the exact Haven fixture: 2/2 PASS in
  3.158 s;
- `clang --analyze`: completed; its 15 warnings are in pre-existing responder
  areas and none points into the new Haven handoff;
- `git diff --check` and Python byte compilation: PASS.

The final sealed AArch64 clean-twin/QEMU run, reconstructed-base initramfs
composition run, final native count, and complete
`scripts/host/test-repository-linux.sh ci` run occur after this report is
frozen. Their exact hashes and wall timings belong in the checkpoint handoff;
the report will not be edited afterward merely to describe its own test.

## Remaining uncertainty and next action

- No retained reset-reason evidence proves the Haven hypothesis.
- The fixed handoff has not been integrated into, signed into, or booted as a
  recovery candidate.
- Physical ramoops retention and current-cycle lineage remain unproven.
- The GENI UART route remains SoC/DT evidence, not a proven external connector.
- Exact-head GitHub CI cannot attest an uncommitted mixed working tree, and no
  commit is justified while unrelated VCNL36866 work is present.

Minimal safe next action: retain **HOLD**, finish local final CI, then isolate
this correction from the VCNL36866 WIP and obtain exact-head CI on the exact
reviewed commit. Candidate creation and hardware admission remain separate
decisions after that checkpoint.

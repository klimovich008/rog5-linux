# Generation-12 NFS-mount disconnect — live result

Date: 2026-08-04

Result: **FAIL CLOSED and consumed — the sole Generation-12 RAM-only
diagnostic lifecycle reached the Linux 7.1 target's first NFS mount call, then
the target USB gadget disconnected before the mount returned or stage 80
`nfs-mount-ok` was emitted. The independent watchdog returned the phone to the
exact Alpine fallback. No retry, flash, wipe, slot operation, persistent
installation, or project phone-storage write occurred.**

## Exact admission and execution

The lifecycle ran from clean pushed commit
`1ee55086ac9c4c8049940d410bcfdf8317a2721b`. Exact-head GitHub Actions run
`30944062957` passed recovery-core in 4m04s and QEMU in 35s. Connected
preflight, deployment-key admission, exact `lahaina` fastboot identity,
ModemManager state, host listener confinement, NFS prerequisites, and the
unconsumed private claim all passed before execution.

The gate irreversibly entered the private mode-0600 Generation-12
`BOOT_CLAIMED` record before issuing one `fastboot boot` of exact AVB:

```text
615d7498e85be499b80473aa0fd6c0cb341dbd13ef5006d6464b389fedd72cf6
```

Recovery reached exact ACM/NCM, fetched and verified bundle
`headless-netroot-early-diag-v1`, and transferred exactly 46,163,787 bytes.
The receive-only recovery progress stream completed all five ordered records
with `CLEAN_EOF` and `authority=NONE`. The recovery controller returned one
correlated `PREPARED` response and one correlated `CLAIMED` response for
manifest:

```text
4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76
```

Both responses reported `watchdog=ARMED`, `execution_started=NO`, and
`last_error=NONE` at their respective protocol boundaries.

## Target evidence

The receive-only early-target collector produced valid canonical evidence:

| Field | Exact result |
|---|---|
| Capture | `valid`, `end_reason=disconnected` |
| Frames | 40 |
| Dropped host USB events | 0 |
| Dropped target updates | 0 in every frame |
| First stage | 10, `reporter-up`, 2.794 s boottime |
| Address stage | 50, `address-configured`, 3.044 s |
| First mount stage | 70, `nfs-mount-begin`, 3.544 s |
| Last frame | stage 70, 12.547 s, `last_good_code=70`, `fault=none` |
| Missing stage | 80, `nfs-mount-ok` |
| Target watchdog deadline | 602.000 s |

The host had already verified the exact 37,735-entry deployment export with
tree SHA-256
`f4affd6d83f3af48259c7d7f650e91461465b59e045519310ac81bb5d71a0087`
and reported the restricted NFSv4.2 export ready. The target initramfs emits
stage 70 immediately before invoking the first read-only NFSv4.2 mount and
emits stage 80 only after the mount succeeds and read-only state is verified.

This proves that userspace entered the first mount operation and did not
observe its successful return. It does **not** distinguish a kernel hang,
kernel crash, USB-controller loss, network-stack failure, or another lower
transport failure. There was no terminal fault frame, live UART, or
lineage-proven current-cycle pstore record, so this result must not be
described as a proven kernel panic.

## Independent host parser defect

After fallback, the lifecycle reported:

```text
FAIL recovery PREPARE evidence is inconsistent; exact fallback returned and intent resolved as FALLBACK_RETURNED
```

That message was a separate host-side classification defect, not the reason
the target disconnected. `stable-recovery-control.py` had already decoded and
validated the current 18-field response contract, including the five
postmortem fields, before writing the successful PREPARE and COMMIT records.
The outer lifecycle parser still required the obsolete seven-field PREPARE
shape and therefore rejected the valid extended object after COMMIT.

The host-only correction makes both the advisory PREPARED observer and final
transaction parser require the complete exact field set. It validates
PREPARE/COMMIT phase identities, zero/nonzero claim fields, watchdog and error
state, all `PRESENT`/`EMPTY`/`UNAVAILABLE` postmortem bounds, and identical
postmortem tuples across the two responses. Hostile tests remove or add every
field and mutate transaction identities, numeric bounds, digest/tail shape,
state coherence, and cross-response consistency.

Cross-response postmortem equality is source-bound: the native responder loads
`/run/rog5-postmortem.status` exactly once before entering its request loop,
and the host permits PREPARE replay only in the same recovery session. The two
accepted responses therefore expose one immutable in-process snapshot rather
than independently refreshed observations.

The recovery responses contained one `PRESENT` postmortem record with 472,926
bytes and SHA-256
`3ffaea80ae5afca30a77da2e9ba8444856ae12ef1424352f37c1ebd3ebf8a9cf`.
That snapshot existed before target execution and is not accepted as evidence
of the current target failure without a proven boot/timing lineage.

## Rollback and final state

The watchdog returned the exact Alpine USB gadget. The lifecycle restored the
exact fallback NetworkManager profile, passed strict pinned SSH against kernel
`5.4.134-qgki-perf-00001-g6c308144c23e`, removed NFS/runtime firewall state,
and resolved the durable intent as `FALLBACK_RETURNED`. The temporarily stopped
Steam TCP-8081 socket was restored to its prior enabled, active, listening
state. Maximum fallback temperature was 43.1 C.

Generation 12 is now absent from `manifests/temporary-boot-images.tsv`, exact
`consumed` in `manifests/artifacts.tsv`, and permanently represented by its
private `.record.entered` claim. Production diagnostic lifecycle actions fail
before guard, credential, repository, host, or phone inspection. The retained
offline profile and twin artifacts remain regression evidence only.

## Next boundary

Do not create or boot Generation 13 merely to repeat the same mount. First
finish and publish the host parser correction, then design a hardware-free
successor contract that can separate:

1. target userspace immediately before and after the NFS syscall;
2. host TCP/NFS request arrival and response progress;
3. target USB/NCM continuity during the mount; and
4. recovery postmortem lineage for the just-finished target boot.

Only a distinct, reviewed, exact-policy successor may perform another
temporary boot.

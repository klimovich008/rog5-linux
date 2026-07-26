# A660 GMU resume-entry v8 — protected-root offline acceptance

Date: 2026-07-26

Decision: **PASS offline / HOLD live. The consumed-v7-derived protected
root, exact-delta verifier, target compound gate, and negative mutation suite
pass. This report does not authorize NFS, a phone connection, a boot, a
reboot, a live probe, a retry, or flashing.**

The phone was not contacted. NFS/RPC remained inactive, no SSH credential was
used, and no ADB, fastboot, device-storage, or flash command ran. PolicyKit
performed the local root-owned export operation without a sudo password.

## Fail-first checkpoint

The umbrella root contract was added before the v8 export and gate tools. Its
first run refused the absent target gate:

```text
FAIL missing executable A660 GMU resume-entry v8 root tool: scripts/device/run-network-root-a660-gmu-resume-entry-v8-gate.sh
```

After implementation, POSIX/Bash syntax, ShellCheck 0.11.0, the reproducible
runtime suite, target-gate suite, protected-export suite, consumed-v7 lockout,
and root umbrella contract all pass.

## Immutable predecessor and accepted payload

The new root derives only from the immutable, live-accepted, permanently
consumed v7 root:

```text
/var/lib/rog5-network-root-a660-ucode-allocation-v7
```

Before copying, the builder reran the complete v7 verifier and consumption
test. The predecessor remains root-owned mode `0555`, its seal remains
root-owned mode `0444`, and its seal SHA-256 remains:

```text
c679ff6cbed6aefb28b7537cd30c561948e4d4672cd9320a8e70fd3d79b4f046
```

The v8 seal pins these predecessor identities:

| Predecessor evidence | SHA-256 / identity |
|---|---|
| accepted v7 live report | `ea4a4a87a264728be3bfcd86a2f12888496dd51c7421cbee166ad19afdb5ee6a` |
| v7 export verifier | `c3db1233fc644c0019b9337dac9253f3cf7ec1588b237df314ff414c78273939` |
| v7 consumption test | `4945156290345ead855c5abf557db0352d4cbd7ada274050afbea47d594d9a3a` |
| v7 consumption commit | `12ad39c` |
| registration-v3 marker | `8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f` |
| registration-v3 report | `2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79` |

The accepted v8 kernel evidence is also pinned:

| Kernel evidence | SHA-256 |
|---|---|
| module archive | `38045b4c68d85d32dadf7d8db28f6ce1665fa2718ded3a9777dc0429035da6e7` |
| GMU resume-entry source boundary | `41c06dcd895fcc873638ddf40dce0b0d5dd5bbf9e148f5d3abd5521b072c320d` |
| reproducible kernel build report | `6c50a822d30368bba4564daa77633b6e22ae1e167cd3486670b786e430153b7c` |
| accepted kernel patch | `a179ff9e31792238a3bd254297008d805e6a37b5d08125712c0151b1f39b3051` |
| accepted v8 `msm.ko` | `b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861` |

## Protected copy-on-write root

PolicyKit created:

```text
/var/lib/rog5-network-root-a660-gmu-resume-entry-v8
```

The builder used:

```text
cp -a --reflink=always
```

It removed exactly the consumed v7 helper, baseline, probe, and seal. It then
installed the versioned v8 counterparts and replaced exactly one payload
file, `usr/lib/modules/7.1.4-rog5-a660reg1/kernel/drivers/gpu/drm/msm/msm.ko`.
No other module, firmware, boot-package, credential, host identity, service,
or rootfs file is permitted to differ.

The final root is root-owned mode `0555`. Its installed v8 inputs are:

| Export input | Mode | Size | SHA-256 |
|---|---:|---:|---|
| v8 export seal | `0444` | 2,443 | `a6c14600ed17a52641f8700393d095e7cd86f2aa0d01c1f1f6bf649e283f2923` |
| one-open helper | `0755` | 896 | `d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae` |
| generated baseline | `0755` | 12,189 | `3a4bcdcd9a96b896f22fda3be3f73c68a3b16e5d154558da9ad299c969faaf23` |
| generated probe | `0755` | 38,110 | `832a96db228a9f0771c0ff364ed943100f243fbbce51ec4c0e2532e211a9e255` |
| v8 `msm.ko` | `0644` | 12,397,072 | `b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861` |

The exact firmware set remains two files:

| Firmware | SHA-256 |
|---|---|
| `qcom/a660_sqe.fw` | `d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76` |
| `qcom/a660_gmu.bin` | `8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7` |
| `qcom/sm8350/a660_zap.mbn` | absent; reference `5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d` |

All six non-MSM modules remain byte-identical to v7. The verifier also
regenerates the runtime, checks its compiled AArch64 relocation oracle,
requires all GMU-entry and forbidden-work trace symbols exactly once, and
pins the three mode-`0400` diagnostic parameters.

## Exact-delta and credential verification

The verifier compares the complete candidate and predecessor trees. Outside
the declared controls, seal, and MSM-module path, every regular-file hash,
object type, mode, owner, group, size, and symlink target must match.

It separately compares:

- both authorized-key files;
- the Ed25519 server host key and public key;
- the accepted registration-v3 marker;
- all seven module identities and metadata;
- exact SQE/GMU firmware with ZAP absent;
- generated baseline and probe bytes and modes; and
- the static AArch64 one-open helper, including exact `OPEN_ERRNO=117`.

The verifier passed during staged construction and twice against the final
path:

```text
PASS A660 GMU resume-entry v8 export modules=7 firmware=2 zap=absent helper=exact compiler=v8-relocations gmu_entry=EUCLEAN logical_vmap=4/4 gem_snapshot=equal credentials=preserved base=consumed-v7 root-owned mode 0555
```

## Negative mutation suite

Each mutation used a separate copy-on-write candidate. The complete verifier
rejected all five:

1. changed `v7_live_accepted_consumed` to a pending predecessor;
2. changed `gmu_entry_parameter_mode=0400` to `0600`;
3. changed the pinned kernel-build report hash;
4. weakened the PID-filtered GMU/logical-vmap trace policy; and
5. replaced the v8 MSM module with the consumed v7 module.

Every mutation and partial-export tree was removed afterward. The accepted v8
root and consumed v7 predecessor retained their original seals and modes.

## Compound target gate

The target gate and its offline suite are:

| Input | SHA-256 |
|---|---|
| compound target gate | `62050d15c16cc3a6e4bc11bd7ad3eeee4eb5026de51c4a51d6c61762764182d8` |
| target-gate suite | `f399c6df074c16243ae9c01e2394396631b180d6a15b1c55ff7693ba132cdf5c` |

The gate requires both exact values:

```text
ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_GATE=1
ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_REBOOT=1
```

It verifies Linux `7.1.4-rog5-a660reg1`, running systemd, storage-free
OverlayFS, the exact read-only NFS lower, and pinned baseline/probe/watchdog
inputs. It runs the baseline while the initial SysRq watchdog remains armed,
starts an independent 240-second transition watchdog, hands off the initial
watchdog, invokes the v8 probe exactly once, and requests normal reboot only
after every probe invariant passes.

The expected probe remains one exact failed open with `EUCLEAN`, one outer and
zero inner runtime-PM calls, exact GMU entry and rollback, accepted logical
`4/4` allocation cleanup, equal GEM snapshots, and zero clock, IRQ, HFI,
devfreq, LLC, hardware-init, ZAP, or SCM activity.

No host runner installs or invokes this gate. The gate has no ADB, fastboot,
module-removal, or storage-write path.

## Consolidated offline result

Exact tool identities at this checkpoint are:

| Tool | SHA-256 |
|---|---|
| root umbrella contract | `129141897542b6fa678aa58a69ce9b78075c6d36719d778b4c89517ef4cc9fc8` |
| protected-root builder | `90fae2f21af1836cb386a8e89a1e4654aeba4f66f0067181af22f49dee6bc092` |
| protected-root verifier | `fe45a420b7241bea6dc3f37fc4beba5397221a8e27d747bd64baab0971181972` |
| protected-root mutation suite | `c8c2e626755e0c72909813d66500d255a4b9812ff3bac63eab25d9d7965b2544` |

The root umbrella suite ends with:

```text
PASS A660 GMU resume-entry v8 root is consumed-v7-derived, exact-delta, mutation-tested, storage-free, non-runnable, and HOLD
```

At the final check:

- `nfs-server.service`, `rpcbind.service`, and `rpcbind.socket` were inactive;
- there were no NFS exports, mounts, or listeners on ports 111/2049;
- the bounded server had no v8 case;
- no v8 host live runner existed;
- no partial or mutation root remained; and
- the phone had not been contacted.

No credential, key material, phone identifier, or private evidence path is
committed.

## HOLD boundary

The protected root and target gate are accepted offline. Hardware use is not.

The next authorized work is still offline:

1. fail-first test and implement a strict one-invocation host runner;
2. pin the root seal, target gate, watchdog helper, unchanged RAM-only boot
   package, repository state, credentials, and private evidence boundary;
3. prove with a mock transport that there is exactly one prepare, copy,
   remote verification, and gate call, with no retry;
4. prove an actual unarmed runner invocation refuses before SSH or host-state
   mutation; and
5. record a separate pre-live HOLD checkpoint.

Only a later attended GO review may add one verifier-before-state,
exact-root, explicit-opt-in NFS case and decide whether one RAM-only cycle is
justified. Nothing here authorizes flashing or reusing any v7 live
authorization.

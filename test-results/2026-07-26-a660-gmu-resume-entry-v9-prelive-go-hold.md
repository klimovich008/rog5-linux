# A660 GMU resume-entry v9 — attended GO review HOLD

Date: 2026-07-26

Decision: **HOLD. The verifier-first exact-v9-root NFS case and every local
GO prerequisite pass, but the phone is physically absent. The mandatory
identity-pinned persistent-fallback health check cannot run, so no live cycle
is authorized.**

No NFS window was opened. The phone was not contacted, no SSH authentication
occurred, no boot or reboot command ran, and nothing was flashed.

## Fail-first bounded NFS window

Commit `02e5f94` records the missing v9 live-window case:

```text
FAIL bounded NFS server omits v9 live-window contract: /var/lib/rog5-network-root-a660-gmu-resume-entry-v9)
```

Commit `f6a4b78c0de84466966bde0c3da9f1f774d4079b` adds only one
explicit-opt-in v9 case. It requires:

```text
ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_NFS=1
```

The guard precedes the complete protected-root verifier, and that verifier
precedes the first export-table, NFS, firewall, bind-mount, interface, or
sysctl state line. The v9 root is checked against immutable consumed v8.
Persistent v1 remains the only generic root; v8 and every earlier consumed
A660/SMMU root remain absent.

Exact control identities are:

| Input | SHA-256 |
|---|---|
| bounded NFS server | `6b527dbae550f3624dfa3f48135a68cf6ca645250c2e13d267d4e2b128e6c610` |
| v9 live-window test | `638571c5792f34f9c9b779fd5e1525e0910378dbc0d77a17a1de1356548abd83` |
| one-invocation host runner | `40276c91803d1890b70152064ac47b56ddead96880f52932f11c16feb4ce485b` |
| host-runner mock | `81b30b738d9f63919116d9795ff9d16d6dbc520438902e8d290c4a25cf31354f` |
| target compound gate | `3922fdb46b587e543940b6703382568a81601fb50189f6b66231d1b62de629d2` |
| watchdog-disarm helper | `733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc` |
| protected-root verifier | `a3f526c6aa5e2f75af49a5b72b89ee24958ce23898e410e43749b482dde3179c` |
| v9 export seal | `137eb101708a8f96c063ed068caf7f8265641c43c228501fc578d5076be02bd5` |
| unchanged RAM-only AVB image | `c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c` |
| fourteen-file package manifest | `c4b9a2ec5afdd73a555031425a5eaedf5ab97a36a69eeefdcfede279ad7ffcd0` |
| v9 pre-live control report | `ef427c37bd3c9d25917171dd48ccc014628cd462da3a14fabbe783f7af1e56a9` |

The bounded server remains exact-peer, read-only, runtime-only,
NFSv4.2-only, bound to `169.254.77.1:2049`, firewalled to
`169.254.77.2`, and bounded to 60–86,400 seconds. It has no ADB, fastboot,
boot, or flash command.

## Actual unarmed refusal

An actual PolicyKit invocation against the exact v9 root without the opt-in
returned:

```text
FAIL set ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_NFS=1 for the attended v9 window
```

A before/after snapshot covering services, exports, NFS mounts and
processes, ports 111/2049/32767, runtime firewall state, IPv4 addresses,
`ip_nonlocal_bind`, and the temporary export mount was byte-identical.

The offline live-window suite ends with:

```text
PASS A660 GMU resume-entry v9 NFS window is exact-root, opt-in, verifier-first, bounded, and non-flashing
```

## Revalidated immutable inputs

At clean synchronized checkpoint
`f6a4b78c0de84466966bde0c3da9f1f774d4079b`:

- the complete protected v9 root verifier passed again;
- the runtime suite reproduced both controls and rejected all signed-width,
  device-scope, oracle, global-PM, inner-PM, snapshot, errno, authorization,
  predecessor, mode, and oracle-hash mutations;
- the target-gate ordering and overlapping watchdog contract passed;
- the one-shot host-runner mock passed with exact call counts and no retry;
- the identity-pinned, restart2-only fallback helper mock passed;
- consumed v8 remained absent from the bounded server; and
- Bash/POSIX syntax, ShellCheck, and `git diff --check` passed.

The exact root result remained:

```text
PASS A660 GMU resume-entry v9 export modules=7 firmware=2 zap=absent helper=exact oracle=s32-device compiler=v8-relocations gmu_entry=EUCLEAN gpu_runtime_pm=device-scoped logical_vmap=4/4 gem_snapshot=equal credentials=preserved base=consumed-v8 root-owned mode 0555
```

## Unchanged temporary-boot package

The fourteen-file package was revalidated against:

- exact accepted Linux source commit and tree;
- accepted v18 and v15 predecessor manifests;
- the complete registration build and source contract;
- all wrapper, initramfs, DT, module, and AVB metadata;
- exactly four enabled GPU dependency nodes;
- seven reviewed modules and no display/UFS/storage path;
- no A660 firmware or private key embedded in either initramfs or the module
  archive; and
- the consumed SMMU/registration acceptance chain.

It passed:

```text
PASS exact live-accepted A660 registration bundle; exact SMMU reprobe, four nodes, seven modules, unopened render, zero firmware/storage/display, consumed and reproducible
PASS A660 registration bundle contract pins predecessor, source, DT, modules, wrappers, package, and source lock
```

The AVB image remains exactly 100,663,296 bytes. This verifies only the
unchanged RAM-only transport and does not revive a consumed diagnostic.

## Local host and credential prerequisites

Local checks passed without network access:

- Git was clean and synchronized with GitHub;
- firewalld, NetworkManager, and ModemManager were active;
- `nfs-server.service`, `rpcbind.service`, and `rpcbind.socket` were inactive;
- there were zero NFS exports, mounts, or listeners on ports 111/2049/32767;
- the temporary export mount was absent and `ip_nonlocal_bind` remained `0`;
- the dedicated client key agreed with the protected v9 authorized keys;
- the pinned network-root identity matched the protected v9 server key; and
- the pinned fallback and network-root Ed25519 server identities were
  distinct.

No key, fingerprint, credential path, phone identifier, or private evidence
path is recorded.

## Missing mandatory phone prerequisite

The host observed:

```text
ASUS USB devices: 0
exact network-root USB gadgets: 0
fastboot devices: 0
authorized ADB devices: 0
```

There was no host `169.254.77.1/30` address because no gadget existed. The
non-autoconnecting host profile remained available, but it cannot create a
physical USB device.

The GO process requires a strict, read-only SSH preflight against the
presented `rog5-fallback` identity. That preflight must prove the exact vendor
kernel, BusyBox PID 1, `qcom,lahaina-mtp`, ext4 root, zero project modules,
empty pstore, zero fatal kernel signatures, safe thermal telemetry, and
Python availability. None of those facts may be assumed from an earlier
cycle.

Because the phone is absent, the preflight cannot run. The review therefore
stops at HOLD before:

- creating a private live evidence directory;
- setting the v9 NFS opt-in;
- starting NFS or changing firewall/interface/sysctl state;
- requesting bootloader mode;
- issuing temporary `fastboot boot`;
- opening network-root SSH; or
- invoking the v9 gate.

## Requirement to resume the GO review

Connect the phone by USB and boot its exact persistent Alpine fallback. The
next review must first require one physical device and rerun the
identity-pinned read-only fallback preflight. It must then recheck every local
gate above before deciding GO.

No earlier v8 authorization may be inherited. A future GO may authorize at
most one attended RAM-only v9 cycle, with no retry and never flash. Any failed
or ambiguous prerequisite keeps the decision at HOLD.

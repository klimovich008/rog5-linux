# A660 GMU resume-entry v8 — pre-live GO

Date: 2026-07-26

Decision: **GO for exactly one attended RAM-only v8 GMU resume-entry cycle,
subject to every transition-time check below.**

This lifts the v8 control-plane HOLD. It does not accept GMU power, clocks,
MMIO, IRQ, HFI, devfreq, LLC, hardware initialization, ZAP/SCM, a successful
DRM open, submission, rendering, display, suspend, or persistent
installation.

No phone state changed during this review. The phone was contacted only by
strict identity-pinned, read-only SSH checks against the persistent fallback.
NFS was not started, no boot or reboot command ran, and nothing was flashed.

## Fail-first bounded NFS window

Commit `57f0ee9` records the missing v8 live-window case:

```text
FAIL bounded NFS server omits v8 live-window contract: /var/lib/rog5-network-root-a660-gmu-resume-entry-v8)
```

Commit `7f6e8a8f1a45e0a1e675ae48fd87924f987f72b5` adds only one
explicit-opt-in v8 case. It requires:

```text
ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_NFS=1
```

and runs the complete protected v8 export verifier against immutable consumed
v7 before the first export-table, NFS, firewall, mount, interface, or sysctl
state line. Persistent v1 remains the only generic case. Every consumed
A660/SMMU root remains absent.

Exact control identities are:

| Input | SHA-256 |
|---|---|
| bounded NFS server | `d281fa00e100c24b33c28ad67f160bc6058b197e17a8cb5775ed19ef1fe098ff` |
| v8 live-window test | `3bf294db5b9fd3c883129008f1b0db951e9ef8e0f298d7c3299a9dd32dc3945c` |
| one-invocation host runner | `9aaa6da8e115392f4274cead402f017c7772407ecfa6950220942b0b8181e8c5` |
| host-runner mock | `36d2fc6c6fad6e2a587f4e5a0f380aa826ccada881db25ff854e53f2693f7872` |
| target compound gate | `62050d15c16cc3a6e4bc11bd7ad3eeee4eb5026de51c4a51d6c61762764182d8` |
| watchdog-disarm helper | `733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc` |
| protected-root verifier | `fe45a420b7241bea6dc3f37fc4beba5397221a8e27d747bd64baab0971181972` |
| v8 export seal | `a6c14600ed17a52641f8700393d095e7cd86f2aa0d01c1f1f6bf649e283f2923` |
| integrated export suite | `3cae3a8d97a01a7d5f576823aab11b4f421b282ef9237ed375fc186b6403003a` |
| temporary AVB boot image | `c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c` |
| fourteen-file package manifest | `c4b9a2ec5afdd73a555031425a5eaedf5ab97a36a69eeefdcfede279ad7ffcd0` |

The server remains exact-peer, read-only, runtime-only, NFSv4.2-only, bound
to `169.254.77.1:2049`, firewalled to `169.254.77.2`, and bounded to
60–86,400 seconds. Cleanup removes every export, NFS thread, mount daemon,
bind mount, temporary firewall rule/interface assignment, and
`ip_nonlocal_bind` change.

An actual privileged invocation without the v8 opt-in returned:

```text
FAIL set ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_NFS=1 for the attended v8 window
```

Its complete before/after snapshot was equal. No export, service, process,
mount, listener, firewall, interface, NetworkManager, or sysctl state changed.

## Revalidated immutable inputs

The complete protected-root and mutation suite passes:

```text
PASS A660 GMU resume-entry v8 root is consumed-v7-derived, exact-delta, mutation-tested, host-runner-tested, storage-free, explicit-window-only, and pre-live GO
```

The exact final root verifier passes:

```text
PASS A660 GMU resume-entry v8 export modules=7 firmware=2 zap=absent helper=exact compiler=v8-relocations gmu_entry=EUCLEAN logical_vmap=4/4 gem_snapshot=equal credentials=preserved base=consumed-v7 root-owned mode 0555
```

The suite independently rejected changed predecessor state, writable
GMU-entry mode, changed build-report identity, weakened trace policy, and the
old v7 MSM module. Its runtime mutations, compound target-gate ordering,
one-shot host-runner mock, explicit-window server contract, and consumed-v7
lockout all pass.

The unchanged fourteen-file temporary-boot package was revalidated against
the exact accepted Linux source and tree, duplicate registration build,
v18/v15 predecessors, pinned SQE/GMU/ZAP firmware set, `mkbootimg`, and
`avbtool`:

```text
PASS exact live-accepted A660 registration bundle; exact SMMU reprobe, four nodes, seven modules, unopened render, zero firmware/storage/display, consumed and reproducible
PASS A660 registration bundle contract pins predecessor, source, DT, modules, wrappers, package, and source lock
```

The AVB image remains exactly 100,663,296 bytes. This verification controls
only the unchanged RAM-only transport; it does not revive the consumed
registration diagnostic.

## Host, credential, and fallback preflight

At the GO checkpoint:

- branch `agent/linux-recovery-host` was clean and synchronized with GitHub
  at `7f6e8a8f1a45e0a1e675ae48fd87924f987f72b5`;
- firewalld, NetworkManager, and ModemManager were active;
- `nfs-server.service`, `rpcbind.service`, and `rpcbind.socket` were inactive;
- there were zero NFS exports, mounts, RPC processes, port
  111/2049/32767 listeners, export mounts, runtime drop-zone changes, or
  non-local bind state;
- the caller-owned private key and known-hosts file remained mode `0600`;
- the dedicated private/public client key pair matched both protected v8
  `authorized_keys` files;
- the pinned network-root identity matched the protected v8 server host key;
- `rog5-fallback` and `rog5-network-root` had distinct pinned Ed25519
  identities; and
- strict network-root identity checking rejected the currently presented
  fallback host.

The identity-pinned fallback verifier then passed the exact vendor kernel,
BusyBox init, `qcom,lahaina-mtp`, ext4 root, zero project modules, empty
pstore, zero fatal signatures, safe thermal telemetry, and Python
availability:

```text
PASS exact persistent fallback ready for guarded bootloader reboot
```

The existing non-autoconnecting temporary USB profile had been restored as
active by the PC reboot. It was used only for the read-only fallback checks
and then deactivated. Final state again had zero host link-local addresses,
NFS/RPC processes, exports, mounts, listeners, firewall residue, or changed
sysctls.

An actual unarmed v8 host runner also refused before credentials or phone
contact:

```text
FAIL set ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_LIVE_GATE=1 for the one-shot gate
```

No private key, host key, fingerprint, credential path, phone identifier, or
private evidence path is recorded in this report.

## One authorized transition

GO remains valid only for this sequence:

1. Reconfirm clean synchronized Git and rerun the exact root, runner, package,
   NFS-window, credential, fallback, and inactive-service checks.
2. Create one fresh caller-owned mode-`0700` private evidence directory.
3. Start one 1,200-second exact-peer NFSv4.2 window with only the v8 opt-in.
4. Use the identity-pinned fallback `RESTART2("bootloader")` helper and require
   exactly one fastboot device with product `lahaina`.
5. Issue exactly one manifest-pinned temporary `fastboot boot`; never flash.
6. Run the accepted `confirm-gpucc` network-root staging sequence once and
   require the distinct pinned network-root SSH identity.
7. Invoke the v8 host runner exactly once.
8. Require the zero-action baseline, exact GMU-resume entry and rollback,
   logical `4/4`, equal post-settle GEM snapshot, zero inner
   power/clock/IRQ/HFI/hardware/SCM events, nested watchdog handoff, and
   immediate normal reboot request.
9. Prove exact persistent fallback, zero pstore/project modules, and complete
   NFS/firewall/interface/sysctl/service cleanup.
10. Consume v8 and remove its server case regardless of pass or rejection.

Any failed or ambiguous prerequisite returns the decision to HOLD without
retrying the hardware gate. No v7 authorization can be reused.

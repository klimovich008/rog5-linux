# A660 ucode-allocation v7 — pre-live GO

Date: 2026-07-26

Decision: **GO for exactly one attended RAM-only v7 ucode-allocation cycle,
subject to every transition-time check below.**

This lifts the v7 control-plane HOLD. It does not accept ucode allocation on
hardware, GPU/GMU power, HFI, ZAP/SCM, a successful DRM open, rendering,
display, suspend, or persistent installation.

No phone state changed during this review. The phone was contacted only by
strict identity-pinned, read-only SSH checks against the persistent fallback.
NFS was not started, no boot or reboot command ran, and nothing was flashed.

## Fail-first bounded NFS window

Commit `6c209aeaffb9b60414f363b057df46f2cb7da69c` records the missing
v7 live-window case:

```text
FAIL bounded NFS server omits v7 live-window contract: /var/lib/rog5-network-root-a660-ucode-allocation-v7)
```

Commit `d4b21acef2ab5fb1145032e0377d745d49e48c5d` adds only one
explicit-opt-in v7 case. It requires:

```text
ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_NFS=1
```

and runs the complete protected v7 export verifier against immutable consumed
v6 before the first `etab`, NFS, firewall, mount, interface, or sysctl state
line. Persistent v1 remains the only generic case. Every consumed
A660/SMMU root, including v5 and v6, remains absent.

Exact control identities are:

| Input | SHA-256 |
|---|---|
| bounded NFS server | `fe0df18328f7a74b915a4f08de79f400afe246b745581b656738f24ef43f97f2` |
| v7 live-window test | `b0e5381b044c64652a08ed86811754156e6811cfd76261cadaf9bd770fd46a3f` |
| one-invocation host runner | `b6800410bb0692e876129bb2d40d8cde23e60005a3d2c90959f730be7aee510a` |
| host-runner mock | `d1c7c18cd1ffdf5a3e0b76fd5bb9be0fa2b72299be8d6af4751e81e6212cdfc4` |
| target compound gate | `f7f223b62521306007c9ac224f008c0a9e6f85fdbdcac1529bf7c8e3a9ea3d1e` |
| watchdog-disarm helper | `733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc` |
| v7 export seal | `c679ff6cbed6aefb28b7537cd30c561948e4d4672cd9320a8e70fd3d79b4f046` |
| temporary AVB boot image | `c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c` |

The server remains exact-peer, read-only, runtime-only, NFSv4.2-only, bound
to `169.254.77.1:2049`, firewalled to `169.254.77.2`, and bounded to
60–86,400 seconds. Cleanup removes every export, NFS thread, mount daemon,
bind mount, temporary firewall rule/interface assignment, and
`ip_nonlocal_bind` change.

An actual privileged invocation without the v7 opt-in returned:

```text
FAIL set ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_NFS=1 for the attended v7 window
```

Its before/after snapshots were equal: inactive NFS and rpcbind, zero mount
daemon, exports, export mount, NFS/mountd listeners, host link-local address,
drop-zone interface assignments, or drop-zone rich rules, with
`net.ipv4.ip_nonlocal_bind=0`.

## Revalidated immutable inputs

The report-aware v7 umbrella suite passes:

```text
PASS A660 ucode-allocation v7 is raw-size-pinned, compiler-pinned, logical-vmap-balanced, snapshot-guarded, host-runner-tested, storage-isolated, explicit-window-only, and pre-live HOLD
```

The protected root verifier and changed-predecessor plus rounded-as-raw
mutation cases pass:

```text
PASS A660 ucode-allocation v7 export modules=7 firmware=2 zap=absent helper=exact raw_sizes=4,4096,43288 object_sizes=4096,4096,45056 compiler=relocations logical_vmap=4/4 gem_snapshot=equal credentials=preserved base=consumed-v6 root-owned mode 0555
```

The accepted root contains only the exact seven modules, SQE/GMU firmware,
no ZAP, generated baseline/probe, one-open helper, accepted registration
marker, and preserved SSH identities. Its distinct raw entry
`4/4096/43288` and page-rounded object `4096/4096/45056` layers remain
separate. The module contract still requires three kernel-new operations,
two kernel puts, wrapper `get=1, put=2`, logical `4/4`, exact rollback object
sets, and an equal post-settle GEM snapshot.

The unchanged temporary image is exactly 100,663,296 bytes. Its fourteen-file
manifest SHA-256 remains
`c4b9a2ec5afdd73a555031425a5eaedf5ab97a36a69eeefdcfede279ad7ffcd0`.

## Host, credential, and fallback preflight

At the GO checkpoint:

- branch `agent/linux-recovery-host` was clean and synchronized with GitHub
  at `d4b21acef2ab5fb1145032e0377d745d49e48c5d`;
- firewalld, NetworkManager, and ModemManager were active;
- `nfs-server.service`, `rpcbind.service`, and `rpcbind.socket` were inactive;
- there were zero NFS exports, mounts, port 111/2049/32767 listeners, RPC
  server processes, export mount, temporary host address, or runtime
  drop-zone changes;
- `net.ipv4.ip_nonlocal_bind` was zero;
- the caller-owned private key and known-hosts file remained mode `0600`;
- the dedicated private/public key pair matched both protected v7
  `authorized_keys` files;
- the pinned network-root host identity matched the protected v7 host key;
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

The temporary fallback host profile was deactivated after the check, restoring
zero host link-local addresses and the inactive, residue-free NFS boundary.
An actual unarmed v7 host runner also refused before phone contact:

```text
FAIL set ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_LIVE_GATE=1 for the one-shot gate
```

No private key, host key, fingerprint, credential path, phone identifier, or
private evidence path is recorded in this report.

## One authorized transition

GO remains valid only for this sequence:

1. Reconfirm clean synchronized Git and rerun the exact root, runner, package,
   NFS-window, credential, fallback, and inactive-service checks.
2. Create one fresh caller-owned mode-`0700` private evidence directory.
3. Start one 1,200-second exact-peer NFSv4.2 window with only the v7 opt-in.
4. Use the identity-pinned fallback `RESTART2("bootloader")` helper and require
   exactly one fastboot device with product `lahaina`.
5. Issue exactly one manifest-pinned temporary `fastboot boot`; never flash.
6. Run the accepted `confirm-gpucc` network-root staging sequence once and
   require the distinct pinned network-root SSH identity.
7. Invoke the v7 host runner exactly once.
8. Require the zero-action baseline, exact raw-size and compiler-aware logical
   rollback, equal post-settle GEM snapshot, nested watchdog handoff, and
   immediate normal reboot request.
9. Prove exact persistent fallback, zero pstore/project modules, and complete
   NFS/firewall/interface/sysctl/service cleanup.
10. Consume v7 and remove its server case regardless of pass or rejection.

Any failed or ambiguous prerequisite returns the decision to HOLD without
retrying the hardware gate. No v5 or v6 authorization can be reused.

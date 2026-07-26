# A660 ucode-allocation v6 — pre-live GO

Date: 2026-07-26

Decision: **GO for exactly one attended RAM-only v6 ucode-allocation cycle,
subject to every transition-time check below.**

This lifts the v6 control-plane HOLD. It does not accept ucode allocation on
hardware, GPU/GMU power, HFI, ZAP/SCM, a successful DRM open, rendering,
display, suspend, or persistent installation.

No phone state changed during this review. The phone was contacted only by
strict identity-pinned, read-only SSH checks. NFS was not started, no boot or
reboot command ran, and nothing was flashed.

## Fail-first bounded NFS window

Commit `32ad99084ad145044de02837e19c3ece57876e58` records the missing
v6 live-window case:

```text
FAIL bounded NFS server omits v6 live-window contract: /var/lib/rog5-network-root-a660-ucode-allocation-v6)
```

Commit `82bb90ba75adc0f0afcc321c20a0deac24e8978e` adds only one
explicit-opt-in v6 case. It requires:

```text
ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V6_NFS=1
```

and runs the complete protected v6 export verifier before the first
`etab`, NFS, firewall, mount, interface, or sysctl state line. Persistent v1
remains the only generic case. Every consumed A660/SMMU root, including v5,
remains absent.

Exact control identities are:

| Input | SHA-256 |
|---|---|
| bounded NFS server | `332eb0f9a332e08329d377c833ff650d58b45ff7d6d08d60cd198a0ea081a127` |
| v6 live-window test | `9c8705ce5c48c777a33fc1f8789fb54716c4994172cb8e77f68e0f1e1c62ef41` |
| one-invocation host runner | `57345cd2839f4c457d3e883dc4f2c55be4dfa98398e3de7060570a5580f4cbd3` |
| host-runner mock | `bfcda61e6f35e3ff277fc6f8970fb93abbe2ca29041d706eb000e10ba98083ba` |
| target compound gate | `5657ce39f7e3e8a81445662cda78e080e6b95df745c60d49a89acf716ec7e7a5` |
| temporary AVB boot image | `c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c` |

The server remains exact-peer, read-only, runtime-only, NFSv4.2-only, bound
to `169.254.77.1:2049`, firewalled to `169.254.77.2`, and bounded to
60–86,400 seconds. Cleanup removes every export, NFS thread, mount daemon,
bind mount, temporary firewall rule/interface assignment, and
`ip_nonlocal_bind` change.

An actual privileged invocation without the v6 opt-in returned:

```text
FAIL set ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V6_NFS=1 for the attended v6 window
```

It left zero NFS exports, mounts, port 111/2049 listeners, RPC processes, or
export mount, and `net.ipv4.ip_nonlocal_bind` remained zero.

## Revalidated immutable inputs

The report-aware v6 umbrella suite passes:

```text
PASS A660 ucode-allocation v6 is compiler-pinned, logical-vmap-balanced, snapshot-guarded, host-runner-tested, storage-isolated, explicit-window-only, and pre-live HOLD
```

The protected root verifier passes:

```text
PASS A660 ucode-allocation v6 export modules=7 firmware=2 zap=absent helper=exact compiler=relocations logical_vmap=4/4 gem_snapshot=equal credentials=preserved base=registration-v3 root-owned mode 0555
```

The accepted root remains mode `0555` and contains only the exact seven
modules, SQE/GMU firmware, no ZAP, generated baseline/probe, one-open helper,
accepted registration marker, and preserved SSH identities. The module
relocation contract still requires `kernel_new=3`, `kernel_put=2`, wrapper
`get=1, put=2`, logical `4/4`, exact rollback object sets, and an equal
post-settle GEM snapshot.

The unchanged temporary image is exactly 100,663,296 bytes. Its fourteen-file
manifest SHA-256 remains
`c4b9a2ec5afdd73a555031425a5eaedf5ab97a36a69eeefdcfede279ad7ffcd0`.

## Host, credential, and fallback preflight

At the GO checkpoint:

- branch `agent/linux-recovery-host` was clean and synchronized with GitHub
  at `82bb90ba75adc0f0afcc321c20a0deac24e8978e`;
- firewalld, NetworkManager, and ModemManager were active;
- `nfs-server.service`, `rpcbind.service`, and `rpcbind.socket` were inactive;
- there were zero NFS exports, mounts, listeners, RPC server processes, or
  export mount;
- `net.ipv4.ip_nonlocal_bind` was zero;
- the caller-owned private key and known-hosts file remained mode `0600`;
- the local key pair matched both protected v6 `authorized_keys` files;
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

No private key, host key, fingerprint, or device identifier is recorded in
this report.

## One authorized transition

GO remains valid only for this sequence:

1. Reconfirm clean synchronized Git and rerun the exact root, runner, package,
   NFS-window, credential, and inactive-service checks.
2. Create one fresh caller-owned mode-`0700` private evidence directory.
3. Start one 1,200-second exact-peer NFSv4.2 window with only the v6 opt-in.
4. Use the identity-pinned fallback `RESTART2("bootloader")` helper and require
   exactly one fastboot device with product `lahaina`.
5. Issue exactly one manifest-pinned temporary `fastboot boot`; never flash.
6. Run the accepted `confirm-gpucc` network-root staging sequence once and
   require the distinct pinned network-root SSH identity.
7. Invoke the v6 host runner exactly once.
8. Require the zero-action baseline, exact compiler-aware logical rollback,
   equal post-settle GEM snapshot, nested watchdog handoff, and immediate
   normal reboot request.
9. Prove exact persistent fallback, zero pstore/project modules, and complete
   NFS/firewall/interface/sysctl/service cleanup.
10. Consume v6 and remove its server case regardless of pass or rejection.

Any failed or ambiguous prerequisite returns the decision to HOLD without
retrying the hardware gate. The v5 cycle and authorization cannot be reused.

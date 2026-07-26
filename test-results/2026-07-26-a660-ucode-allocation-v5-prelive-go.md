# A660 ucode-allocation v5 — pre-live GO

Date: 2026-07-26

Decision: **GO for exactly one attended RAM-only ucode-allocation cycle,
subject to the transition-time checks below.**

This lifts the earlier control-plane HOLD. It does not accept ucode
allocation on hardware, GPU/GMU power, HFI, ZAP/SCM, a successful DRM open,
rendering, display, suspend, or persistent installation.

No phone state changed during this review. The phone was contacted only by
read-only ICMP and strict key-only SSH checks. NFS was not started, no boot
command ran, and nothing was flashed.

## Fail-first and implementation

Commit `7dfabd1` adds the missing live-window test. Before implementation it
failed with:

```text
FAIL bounded NFS server omits v5 live-window contract: /var/lib/rog5-network-root-a660-ucode-allocation-v5)
```

Commit `520a8613961efe44dbb25e9a08e14f194d4a202e` adds only one new
server case. The exact v5 path requires:

```text
ALLOW_MAINLINE_A660_UCODE_ALLOCATION_NFS=1
```

and reruns the complete root-owned export verifier before the first NFS,
firewall, mount, interface, or sysctl state line. Every consumed
A660/SMMU root remains rejected.

Exact control identities:

| Input | SHA-256 |
|---|---|
| bounded NFS server | `306474f71518ba1ff59373b9a13368b5a7f2a49753c6abba94feba3a05bbc3dc` |
| v5 live-window test | `0c5f1fb69ee377a42146be97a9c3f0a44338231fdc2c19b8383ccf170ad6f4c5` |
| one-invocation host runner | `c6df42496b2fa6920187773bc7a97a8dc8bc5a7afb518f98ff1265a585580225` |
| target gate | `5dfe2703934123d433c5cfb7b3e46b0d51e20333957b64940a429cb2b16dc779` |
| temporary AVB boot image | `c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c` |

An actual unarmed privileged invocation returned:

```text
FAIL set ALLOW_MAINLINE_A660_UCODE_ALLOCATION_NFS=1 for the attended v5 window
```

NFS/RPC services, mounts, listeners, and processes remained absent
afterward.

## Revalidated immutable inputs

The full v5 umbrella suite passes:

```text
PASS A660 ucode-allocation v5 contract is exact-root, trace-balanced, snapshot-clean, watchdog-guarded, storage-isolated, package-accepted, host-runner-tested, explicit-window-only, and non-flashing
```

The independent protected whole-tree verifier passes:

```text
PASS A660 ucode-allocation v5 export modules=7 firmware=2 zap=absent helper=exact trace=balanced gem_snapshot=equal credentials=preserved base=registration-v3 root-owned mode 0555
```

The root remains mode `0555`, contains only exact SQE/GMU firmware and seven
reviewed modules, has no ZAP image, preserves the accepted registration
marker and SSH identities, and requires exact balanced PID-filtered mapping,
GEM, CPU-vmap, firmware-reference, and equal pre/post snapshot evidence.

## Host and fallback preflight

At the decision checkpoint:

- Git branch `agent/linux-recovery-host` was clean and synchronized at
  `520a8613961efe44dbb25e9a08e14f194d4a202e`;
- firewalld, NetworkManager, and ModemManager were active;
- `nfs-server.service` and `rpcbind.service` were inactive;
- there were no NFS mounts or port 111/2049 listeners;
- `ip_nonlocal_bind=0`;
- the private SSH key and known-hosts file were caller-owned mode `0600`;
- both `rog5-fallback` and `rog5-network-root` had distinct pinned Ed25519
  identities; and
- the protected v5 authorization key matched the local public key.

The phone currently exposes the persistent fallback USB gadget. A deliberate
strict check under the network-root alias rejected its key; the presented
fingerprint exactly matched the separately pinned fallback alias. The
identity-pinned fallback verifier then passed the exact vendor kernel,
BusyBox init, `qcom,lahaina-mtp`, ext4 root, zero project modules, zero
pstore records, zero fatal signatures, safe thermals, and Python
availability:

```text
PASS exact persistent fallback ready for guarded bootloader reboot
```

## Remaining transition-time requirements

GO remains valid only for this sequence:

1. Create a fresh caller-owned mode-`0700` private evidence directory.
2. Start one 1,200-second exact-peer NFSv4.2 window with the v5 opt-in.
3. Use the identity-pinned `RESTART2("bootloader")` helper and require
   exactly one fastboot device with product `lahaina`.
4. Issue exactly one manifest-pinned temporary `fastboot boot`; never flash.
5. Run the fixed `confirm-gpucc` staging sequence once and require the exact
   network-root SSH identity.
6. Invoke the ucode-allocation host runner exactly once.
7. Require complete balanced rollback evidence and the guarded normal reboot.
8. Prove exact fallback health and complete NFS/firewall/service cleanup.
9. Consume v5 and remove this temporary serve case regardless of pass or
   rejection.

Any failed or ambiguous prerequisite changes the decision back to HOLD
without retrying the hardware gate.

# Headless SSH successor r2 — installed host preflight

Date: 2026-07-31

Result: **PASS; the exact signed r2 bundle is installed, the complete
lifecycle preflight passes against the connected fastboot device, and no
phone boot or payload transfer occurred.**

## Installed boundary

The reviewed fixed host components were already byte-identical to the pushed
repository sources. The consumed `headless-ssh-network-root-v3` bundle was
copied byte-for-byte to the private recoverable archive below before its five
known files were removed from the one-bundle store:

```text
/home/deck/.local/state/rog5-deployment-20260731-live1/consumed-bundles/
```

The production no-replace packager then atomically published only
`headless-ssh-network-root-v3-r2` below
`/var/lib/rog5-recovery-bundles`. The installed directory is caller-owned
mode `0500`; its files are mode `0400` and compare byte-for-byte with reviewed
build A. The admitted identities are:

```text
recovery_avb_sha256=11feb00b6a80e701e74c8538b6f80fb4956d9b21463d666806e0b5f14b52213c
trust_key_sha256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
manifest_sha256=9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630
host_verifier_sha256=9099f5f615144cf95655e6e169ac49b0cbe6f0a6d759441c59bc3130407ab78b
root_package_sha256=9eb60d6e4254986dc8e017fc1dd9d76d699e8d35cb3716d8fdef72ca6df1199d
```

## Aggregate preflight

From clean, origin-synchronized checkpoint `e635257`, the production
`preflight` action passed all of these gates as one invocation:

- local private-key/public-key admission without exposing key material;
- exact package, candidate, bundle, trust, recovery, wrapper, and host
  verifier admission;
- byte-current fixed host controller, export installer, and NFS server;
- privileged read-only NFS/export preflight;
- fallback SSH host prerequisites and retained host-key pin; and
- one connected fastboot device, serial `M5AIKN00F0353YH`, product `lahaina`.

The lifecycle reported that it started no phone boot, payload transfer, SSH
connection, or privileged serving session. A temporary local PolicyKit rule
authorized only `/usr/libexec/rog5-recovery-host/serve-network-root.sh` for
the active local `deck` user during this preflight. It was removed
immediately afterward.

## Cleanup proof

After the pass:

- the temporary source and installed PolicyKit rule were absent;
- the NFS readiness marker and root-owned server state record were absent;
- no ROG5 lifecycle, bundle-server, or network-root server process remained;
- no export mount or TCP/UDP listener on ports 2049 or 32767 remained;
- the repository remained clean and synchronized; and
- the phone remained in fastboot and was not booted or flashed.

## Remaining HOLD

The next action is one attended temporary `fastboot boot` lifecycle using the
exact r2 image. It remains a separate live-device step. Flashing and phone
storage writes remain prohibited.

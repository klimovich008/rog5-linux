# SteamOS deployment publication and connected preflight

Date: 2026-07-31

Result: **PASS host deployment; HOLD on fallback SSH authorization**

## Outcome

Pushed commit `fed5872133fae77348d3097b55a7f415b97d5709` passed both
GitHub Actions jobs. The reviewed fixed host controller was then reinstalled
byte-for-byte, SteamOS read-only protection was restored, and the admitted v3
root was atomically published at:

```text
/home/rog5-linux/exports/headless-ssh-network-root-v3
```

The fixed NFS preflight, stable-recovery artifact gate, and connected fastboot
gate all pass. No experimental image was booted, no partition was flashed,
and no phone filesystem was mounted. The separately authorized temporary boot
remains unused.

## Published host state

- `/home/rog5-linux`, `exports`, and the final export are root-owned mode
  `0700`;
- the extracted root is root-owned mode `0755`;
- the package manifest is root-owned mode `0444`;
- package SHA-256:
  `9eb60d6e4254986dc8e017fc1dd9d76d699e8d35cb3716d8fdef72ca6df1199d`;
- complete root:
  37,735 entries;
- tree SHA-256:
  `f4affd6d83f3af48259c7d7f650e91461465b59e045519310ac81bb5d71a0087`.

The installer rechecked the non-fixture SSH key, package, candidate, and
signed runtime-manifest chain before privilege. Publication used the
root-owned anonymous snapshot, full archive inspection, complete-tree
verification, durable sync, and `RENAME_NOREPLACE` path.

SteamOS had `nfs-utils` installed but had never initialized
`/var/lib/nfs/etab`. A root-owned mode-`0644` empty state file was created.
The fixed NFS preflight then reverified export ancestry, the full sealed root,
inactive system NFS service, empty exports/listeners, and unused drop zone. It
started no NFS service and created no mount, listener, export, firewall rule,
or interface address.

## Connected evidence

Exactly one USB fastboot device was present and the live gate accepted product
`lahaina`. The exact `headless-ssh-deployment-v3` wrapper, twin, trust root,
runtime manifest, host verifier, recovery components, AVB descriptor, and
boot-v3 layout passed again against the installed signed bundle.

The phone was normally rebooted from fastboot into the installed Alpine
fallback to investigate the remaining credential gate. This was not a
temporary experimental boot. The expected Alpine CDC-NCM and ACM gadgets
enumerated on the same physical USB port. A private fallback host pin was
captured outside Git.

The new deployment key was rejected by fallback SSH. Read-only USB serial
inspection then confirmed:

- kernel `5.4.134-qgki-perf-00001-g6c308144c23e`;
- BusyBox PID 1;
- `qcom,lahaina-mtp`;
- ext4 root;
- zero project modules;
- zero pstore files and zero fatal-signature matches;
- 70 readable thermal zones with a 38,800 m°C maximum;
- Python 3; and
- a root-owned mode-`0600` `authorized_keys` file containing two older keys,
  neither matching the new deployment key.

The temporary host address and serial client were removed after inspection.
SteamOS read-only protection remained enabled, and no NFS or recovery listener
was left running.

## Remaining decision gate

The lifecycle deliberately uses the same dedicated key for the new target and
the exact fallback. It must not consume the temporary boot until strict
fallback SSH succeeds.

The active tier keeps Alpine untouched and prohibits phone-storage writes.
The operator must therefore choose one of two paths before work continues:

1. supply a private key matching either existing authorized fallback key; or
2. explicitly revise the untouched-fallback safety tier, then separately
   authorize one bounded append of the already-built deployment public key to
   Alpine `/root/.ssh/authorized_keys` through local USB serial.

After strict fallback SSH is available:

1. prove strict key-only fallback SSH using the private host pin;
2. run the complete lifecycle preflight;
3. return Alpine to exactly one `lahaina` fastboot device; and
4. use at most the one authorized temporary boot.

This report does not revise the safety tier, grant a phone-storage write, or
authorize another live cycle.

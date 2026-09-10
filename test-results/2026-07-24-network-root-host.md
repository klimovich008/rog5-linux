# Network-root privileged host result

Status: **PASS host-only; phone boot not run**. The exact Arch export was
prepared and mounted by an isolated `/30` client. No image was transferred,
booted, flashed, or written to phone storage.

## Host preparation

- `nfs-utils` was installed through PolicyKit without enabling its system
  server.
- The manifest-pinned 2,007,208,337-byte archive reverified at SHA-256
  `e0de832fadc4005dc46aca17c3b9ecb4b4b5c107e1e35472e2971172d2a2861b`.
- Extraction to `/var/lib/rog5-network-root-v1` preserved ACLs/xattrs and
  passed the independent module, firmware, identity, SSH, and rootfs checks.

## Fedora compatibility fixes

The first privileged executions failed closed and removed their runtime
state. They exposed five host assumptions that the static harness could not
model:

- firewalld permits new zones only in permanent configuration, so the harness
  now requires the built-in `drop` zone to be unused and pristine, changes it
  only at runtime, and removes its exact allow rule on exit;
- procfs rejects chmod on `/proc/fs/nfsd`, so its mountpoint uses `mkdir -p`;
- a fresh `exportfs` can partially register an export while returning an
  error, so the standard state file is validated, cleanup is armed before the
  export call, and unexport uses the exact client/path; and
- Fedora formats `exportfs -v` across two lines, so path, peer, and options are
  validated independently; and
- new NFSv4 opens wait during server grace, so the private server sets the
  minimum supported 10-second grace/lease and reports ready only after
  `/proc/fs/nfsd/v4_end_grace` confirms completion.

Each case now has a static regression assertion.

## Passing runtime gate

- Listener: exactly one TCP socket at `169.254.77.1:2049`.
- Protocol: NFSv4.2; NFSv3, v4.0, v4.1, and UDP disabled.
- Export: exactly `169.254.77.2`, `ro`, `fsid=0`, and `no_root_squash`.
- Source: read-only bind mount with `nodev,nosuid`.
- Firewall: exact peer allow in the unused `drop` zone and negative-priority
  NFS/mountd drops in every pre-existing active zone.
- Persistence: no `/etc/exports` entry and no permanent firewalld rule.
- Services: `nfs-server`, rpcbind service/socket, and gssproxy remained
  inactive.

An isolated network namespace used `169.254.77.2/30`, mounted `/` over
NFSv4.2/TCP read-only, matched the staged `/etc/os-release`, and found
`/usr/lib/modules/7.1.4-g7a5cef0db479`.

## Cleanup proof

Attended termination left no export, port 111/2049/32767 listener, export
mount, `/proc/fs/nfsd` mount, nonlocal-bind sysctl change, runtime firewall
rule, test interface, or namespace. The pre-existing fallback USB profile was
restored and its peer remained reachable.

The subsequent temporary `fastboot boot` and separate attended kexec gate
passed in systemd diagnostic mode. See
`2026-07-24-network-root-v1-live.md`.

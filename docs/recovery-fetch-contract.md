# Fixed recovery bundle transport

Status: **device helper and responder integration pass offline**

Live authority: **none**

The device helper is
`tools/recovery_control/rog5-bundle-fetch.c`. Its native fault suite is
`scripts/host/test-recovery-fetch-native.py`; the pinned production builder,
root privilege-transition aggregate, and reproducible AArch64/QEMU aggregate
are:

```text
scripts/device/build-recovery-bundle-fetcher.sh
scripts/host/test-recovery-fetch-root.sh
scripts/host/test-recovery-fetch-aarch64.sh
```

The accepted helper and responder-integration evidence is
[fixed fetch offline result](../test-results/2026-07-28-recovery-fixed-fetch-offline.md).

The production build has no endpoint, path, identity, timeout, crash, write,
or seccomp override. The responder invokes it under the rollback watchdog,
but no initramfs contains either binary yet, and the fixed production
host-serving command still has to be integrated with the host controller.
The test server is a protocol oracle, not a deployment service. QEMU user
mode cannot safely install a
guest-architecture seccomp filter over the emulator's host syscall stream;
the native and
network-disabled root-container suites own the real seccomp, credential-drop,
chroot, capability, descriptor, and parent-death gates.

This transport moves one signed runtime bundle from the development host to
the RAM-only recovery. It is not an authorization mechanism. The independent
bundle verifier must still verify the production Ed25519 signature, policy,
Image, DTB, initramfs, generated command line, and sealed snapshots before
`PREPARE` may load anything.

## Fixed network boundary

Production has no URL, hostname, proxy, redirect, environment, interface, or
path input. The privileged acquisition parent opens one TCP connection with:

```text
interface: usb0
source:    169.254.77.2
peer:      169.254.77.1
port:      8080
```

It binds both `SO_BINDTODEVICE=usb0` and the fixed source address before
connecting. The host server listens only on the dedicated USB address and a
drop-by-default firewall admits only `169.254.77.2`.

## Privilege separation

The fixed acquisition helper has one privileged parent and one worker:

1. The parent opens and locks `/run/rog5-bundles`, validates its bounded
   inventory, cleans only recognized stale staging directories, enforces one
   finalized bundle plus one staging bundle, creates the connected socket and
   staging directory, then forks.
2. The worker receives only the connected socket as descriptor 3 and the
   staging directory as descriptor 4. It closes every other descriptor,
   requests `PR_SET_PDEATHSIG=SIGKILL`, rechecks its parent, enters a chroot
   rooted at the staging directory, drops supplementary groups, capability
   bounding/ambient state, GID and UID to 65534, enables `no_new_privs`, and
   installs a syscall allowlist before parsing network bytes.
3. The parent monitors the worker under its request deadline. On timeout or
   failure it sends `SIGKILL`, retains the root lock, and definitively reaps
   the child; the responder supplies the outer watchdog bound. A killed parent
   cannot leave an orphan worker.
4. Only the parent validates and normalizes final ownership/modes and performs
   atomic publication. The worker cannot access control state, the watchdog,
   verifier, kexec, the bundle root, or an unconnected network socket.
5. The recovery responder separately monitors the acquisition helper under
   the rollback watchdog. Fetch failure cannot invoke the verifier or loader.

The production state root remains session-scoped tmpfs. No fetched byte is
written to physical storage.

## Request frame

The worker sends one four-byte big-endian length followed by this canonical
ASCII record:

```text
format=rog5-fetch-request-v1
bundle=<bundle-id>
manifest_sha256=<64-lowercase-hex>
```

The record is newline-terminated and has no blank, duplicate, reordered, or
unknown field. The frame is at most 256 bytes.

## Response stream

The host replies on the same connection with one four-byte big-endian header
length and one canonical ASCII header:

```text
format=rog5-fetch-response-v1
bundle=<same-bundle-id>
manifest_sha256=<same-requested-hash>
manifest_size=<decimal>
signature_size=64
kernel_size=<decimal>
dtb_size=<decimal>
initramfs_size=<decimal>
```

The header is at most 1024 bytes. It is followed immediately by exactly five
bodies in this order:

```text
manifest
manifest.sig
Image
board.dtb
initramfs.cpio.gz
```

The server then closes the connection. Missing, reordered, duplicated,
truncated, oversized, or trailing data fails. There is no HTTP, DNS, TLS,
chunking, compression, redirect, generic URL parser, content negotiation, or
second request.

The worker first receives the bounded manifest, requires its SHA-256 to equal
the request, and parses the canonical manifest. Header lengths must equal the
manifest's kernel, DTB, and compressed-initramfs sizes. Every remaining body
is streamed once to an `O_EXCL|O_NOFOLLOW|O_CLOEXEC` file while its exact size
and SHA-256 are checked. The signature is exactly 64 bytes. The verifier later
reopens and independently verifies every finalized object.

Fixed limits are:

| Object | Minimum | Maximum |
|---|---:|---:|
| manifest | 1 byte | 4 KiB |
| signature | 64 bytes | 64 bytes |
| kernel | 64 bytes | 128 MiB |
| DTB | 40 bytes | 2 MiB |
| compressed initramfs | 2 bytes | 256 MiB |

The helper's 60-second absolute data-path deadline bounds connect, request,
response header, all five bodies, EOF, validation, and publication. A failed
worker is killed and definitively reaped while the helper retains the root
lock. Because Linux cannot guarantee a bounded reap for a task stuck in
uninterruptible kernel I/O, the responder independently imposes a 65-second
outer helper deadline and remains supervised by the rollback watchdog.
Individual network and file-processing waits are bounded by the helper's
remaining deadline.

## RAM and publication policy

The root admits at most one finalized bundle and one staging directory.
Therefore the maximum compressed fetch allocation is 386 MiB. During verifier
snapshotting, the maximum combined fetched-plus-sealed allocation is 772 MiB.
Unknown root entries, extra final bundles, unsafe metadata, links, and
unrecognized staging content fail closed.

Publication order is:

1. sync each complete worker-owned file;
2. parent verifies exact inventory, ownership, link count, mode, size, and
   content;
3. parent changes the staging directory to root:`0500`, closing the
   worker-UID namespace-mutation window;
4. parent changes each file to root ownership and mode `0400`;
5. sync every changed file and the staging directory;
6. parent reopens, rehashes, and revalidates the complete normalized tree;
7. `renameat2(RENAME_NOREPLACE)` to the final bundle ID; and
8. sync the bundle root.

There is no replacing-rename fallback. An existing final directory is reused
only after exact inventory/metadata validation and a matching manifest hash.
The same bundle ID with another hash, or another final bundle at the global
quota, returns a permanent conflict and is never overwritten.

## Required offline gates

- native host and real static AArch64/QEMU success;
- every request/header mutation, short body, extra byte, reset, timeout,
  slowloris, overflow, size/hash mismatch, and reordering;
- root, final, and stale-staging symlink/hardlink/mode/owner/extra-entry
  mutations;
- crash injection around every write, file sync, ownership/mode change,
  directory sync, rename, and root sync;
- stale-stage cleanup that deletes only the five known regular files;
- concurrent helper exclusion and parent-death orphan prevention;
- worker UID/GID/capability, descriptor, process-count, syscall-filter, and
  forbidden-syscall assertions;
- existing-final hash match/conflict and one-bundle RAM quota;
- ENOSPC/short-write handling and repeated failed request containment;
- watchdog death during connect, header, every body, worker reap, and
  publication;
- proof that incomplete/conflicting fetches never invoke verifier, kexec
  load, unload, or execute;
- responder `SIGKILL` propagates through the fetch helper to its
  `PDEATHSIG`-bound worker; and
- a new request ID cannot refetch after a recorded acquisition failure or
  bundle-ID conflict.

Host serving, image integration, production-key creation, live load, and live
execution remain separate later gates.

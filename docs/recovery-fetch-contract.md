# Fixed recovery bundle transport

Status: **device helper, responder integration, and fixed host serving pass
offline**

Artifact-local authority: **none**. Live use occurs only through the central
standing authorization and the recovery lifecycle's exact technical gates.

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
The host-side evidence is
[fixed host server result](../test-results/2026-07-28-recovery-host-server-offline.md).

The production build has no endpoint, path, identity, timeout, crash, write,
or seccomp override. The responder invokes it under the rollback watchdog,
but no initramfs contains either binary yet. The fixed one-shot host server,
root-owned controller, prompt-free operator-owned systemd socket, and
runtime-only firewall lifecycle pass offline. The earlier PolicyKit runtime
path reached a live signed recovery but timed out before bundle transfer;
automatic rollback and exact fallback passed. QEMU user mode cannot safely install a
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

## Fixed host server

The host implementation is
`tools/recovery_control/host_bundle_server.py`. Its protocol/descriptor test
is `scripts/host/test-recovery-bundle-server.py`. Production installation
copies that module and the controller to fixed root-owned, non-writable paths:

```text
/usr/libexec/rog5-recovery-host/host_bundle_server.py
/usr/libexec/rog5-recovery-bundle-controller
```

The unprivileged server accepts exactly these two forms:

```text
host_bundle_server.py --preflight BUNDLE MANIFEST_SHA256
host_bundle_server.py BUNDLE MANIFEST_SHA256
```

The first performs the complete descriptor/inventory/manifest preparation and
closes every descriptor without creating a socket. The second performs the
same preparation and then serves one fixed listener.

It has no path, address, port, URL, protocol, timeout, signing-key, or
environment override. It refuses UID 0 and opens only
`/var/lib/rog5-recovery-bundles`. The root must be owned by the configured
socket operator with mode `0700` and contain exactly the requested bundle
directory.
That directory must be mode `0500`; its exact five regular, single-link files
must be caller-owned mode `0400`. Symlinks, hard-link aliases, extras, unsafe
ownership/modes, and size/hash/manifest mismatches fail before `bind(2)`.

The server holds a shared root lock and opens the root, selected directory,
and all five files with `O_NOATIME`; file opens also use
`O_NOFOLLOW|O_CLOEXEC`. It verifies the canonical manifest against exact sizes
and SHA-256 values and serves only those already-open descriptors. Preflight
therefore leaves even access timestamps unchanged.
Path replacement after preparation cannot change the transmitted objects.
The host account remains inside the trust boundary for availability: another
process under the same UID could deliberately modify an already-open inode
in place. Such bytes still cannot become authorized because the recovery-side
verifier independently checks the requested manifest hash, Ed25519 signature,
and all artifact hashes before load.

The listener accepts only source `169.254.77.2`, rejects at most eight wrong
peers, serves one valid request, and requires both one canonical request frame
and TCP EOF in the request direction before sending any response byte. A
delayed trailing byte is therefore rejected rather than racing a one-time
peek. The server's 70-second monotonic deadline bounds all socket operations;
the controller independently terminates the complete server process 75
seconds after listener readiness, so a blocked host artifact read cannot
outlive the attended window. It does not support HTTP or a second request.

## Root controller and firewall lifecycle

`scripts/host/install-recovery-host-controller.sh` is a one-time PolicyKit
installer. It atomically installs the fixed root-owned code, creates the
operator-owned mode-`0700` bundle root, and enables
`/run/rog5-recovery-host.sock` as an operator-owned mode-`0600` systemd
socket. Normal operation uses `scripts/host/run-recovery-bundle-server.sh`,
which verifies that installed code is root-owned, non-writable, and
byte-identical to the reviewed repository sources. Its preflight invokes the
same descriptor-based server validator without creating a listener, requiring
the selected bundle to be the sole root entry and verifying its exact
inventory, metadata, hashes, and manifest bindings before any phone boot.
Serve then sends one bounded request through the socket. The root broker
validates `SO_PEERCRED`, a
root-owned operator/configuration record, and exact installed-controller
hashes before dispatch. It accepts no shell, arbitrary command, root path,
caller environment, repository executable, or installer operation. This
prevents a timed phone boot from depending on graphical authentication and
prevents a privileged invocation from importing code directly from an
editable Git checkout.

The controller:

1. requires a non-root `PKEXEC_UID`, exact bundle/hash arguments, safe
   installed metadata, active firewalld, and an unused TCP port 8080;
2. identifies exactly one NCM interface with USB IDs `1d6b:0104`, normalized
   product `ROG5_recovery`, and driver `cdc_ncm`;
3. adds a priority `-300` destination drop for `169.254.77.1:8080` to every
   firewall zone except an otherwise-empty, drop-by-default `drop` zone;
4. temporarily assigns only the exact gadget interface to that zone and
   permits only source `169.254.77.2/32` to destination
   `169.254.77.1/32` TCP port 8080;
5. refuses a conflicting host address or unexpected interface IPv4 state,
   then adds only `169.254.77.1/30`;
6. starts the server as the socket-authenticated operator with cleared
   supplementary groups, empty bounding/inheritable/ambient capability sets,
   `no_new_privs`, a parent-death signal, and a reset environment;
7. proves exactly one listener at the fixed address and PID;
8. arms a 75-second hard server watchdog that verifies its actual parent
   immediately after exec and again before signaling; and
9. after one transfer or any partial failure, stops the child and removes
   only the address, rules, zone assignment, and NetworkManager override
   created by that invocation.

No permanent firewall rule, new zone, forwarding, masquerade, route, DNS
setting, physical-storage write, or phone action is present. The offline
controller test mocks every host mutation and proves both the success cleanup
and failures before/after partial setup. Firewall exceptions and the added
IPv4 address also carry fixed 180-second kernel/firewalld lifetimes, limiting
residual exposure if an uncatchable controller death bypasses its traps.
Installation and live network setup remain separately visible host actions;
neither occurred at this checkpoint.

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
After sending it, the device calls `shutdown(SHUT_WR)`. The host requires EOF
in that direction before responding. The half-close leaves the response
direction available and gives trailing-request rejection an unambiguous
protocol boundary.

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

Image integration, production-key creation, live host installation, live
load, and live execution remain separate later gates.

The host-only gates are:

- nine server protocol, metadata, descriptor-pinning, peer, half-close, and
  malformed
  request tests;
- nine controller identity, pre-mutation refusal, partial-mutation,
  privilege policy,
  partial-failure rollback, hard-watchdog, abrupt-parent-death, success
  cleanup, and fixed-surface tests;
- Bash syntax, ShellCheck, Python compilation, and repository quick-suite
  integration.

# Fixed recovery host server offline result

Date: 2026-07-28

Result: **PASS OFFLINE; NOT INSTALLED; NO LIVE AUTHORITY**

The canonical recovery-bundle stream now has a fixed one-shot host server and
a privilege-separated host network controller. This checkpoint did not
install files under `/usr/libexec` or `/var/lib`, alter NetworkManager or
firewalld, configure an interface, connect to the phone, boot, reboot, flash,
load a kernel, or create/use a production signing key.

## Implemented boundary

The stdlib-only server:

- accepts only `BUNDLE` and the expected lowercase manifest SHA-256;
- refuses root and opens only `/var/lib/rog5-recovery-bundles`;
- requires one exact caller-owned bundle tree with root `0700`, bundle
  directory `0500`, five single-link files `0400`, and no extras or links;
- validates the canonical manifest plus artifact sizes/hashes before bind;
- pins and serves the same already-open descriptors even if pathnames are
  replaced;
- binds only `169.254.77.1:8080`, accepts only peer `169.254.77.2`, and
  requires the device's request half-close before serving exactly one
  canonical request; and
- contains no HTTP, URL, redirect, signing-key, shell, subprocess, or
  caller-selected endpoint surface.

The host controller is installed to a fixed root-owned path before normal
use. The unprivileged launcher checks that the installed controller and
server are non-writable and byte-identical to the reviewed repository source,
then invokes the controller through PolicyKit. The controller recognizes
exactly one `1d6b:0104` / `ROG5_recovery` / `cdc_ncm` interface, protects
TCP port 8080 in every firewalld zone, assigns only that interface to an
otherwise-empty drop zone, and admits only the exact USB peer and destination.
It refuses address/listener conflicts.

The server runs as the PolicyKit caller under `setpriv` with supplementary
groups cleared, all capability sets empty, `no_new_privs`, a parent-death
signal, and reset environment. The controller confirms a unique fixed-address
listener owned by that PID. Success, child failure, controller failure, and
signals all converge on scoped cleanup of only state created by the current
invocation. The added address and runtime firewall exceptions also expire
after 180 seconds if an uncatchable controller death bypasses its traps.
An independent 75-second controller watchdog starts after listener
verification and terminates the complete server even if a host artifact read
blocks outside Python's socket deadlines. It verifies its actual parent
immediately after exec and again before signaling, so an abrupt controller
death cannot turn a stale numeric PID into a later signal target.

The bundle-owner UID is trusted for host-side availability. Another process
under the same UID could deliberately change an opened inode in place.
Recovery-side manifest/signature/artifact verification remains the
authorization boundary, so such a race can cause rejection but cannot
authorize altered code.

## Offline tests

| Suite | Result |
|---|---:|
| server protocol and descriptor suite | 9 passed |
| mocked privileged controller lifecycle | 9 passed |
| Python bytecode compilation | passed |
| Bash syntax and ShellCheck | passed |
| `git diff --check` | passed |

Coverage includes exact response bytes; request fragmentation and canonical
field rejection; required request half-close and delayed trailing-byte
rejection; wrong-peer handling; root/bundle/file
owner/mode/inventory/link/hash mutation; pathname replacement after
preparation; invalid identity rejection before filesystem access; duplicate
or missing gadget refusal before mutation; pre-existing listener refusal;
fixed firewalld rule ordering; unprivileged capability-free launch; unique
listener/PID validation; a hard watchdog after listener creation; full
success cleanup; immediate controller-death watchdog exit; and cleanup after a
server startup failure.

## Remaining gates

1. Review and commit this checkpoint.
2. Integrate the responder, fetcher, verifier, fixed kexec-tools, device
   session minting, and a separately approved public key into the shell-free
   recovery initramfs.
3. Build twice and verify byte-identical images before any live staging
   action.
4. Install the host helpers and run a live interface preflight only as an
   explicit later host action.

## Commands

```text
python3 scripts/host/test-recovery-bundle-server.py
python3 scripts/host/test-recovery-host-controller.py
shellcheck packaging/host/rog5-recovery-bundle-controller \
  scripts/host/install-recovery-host-controller.sh \
  scripts/host/run-recovery-bundle-server.sh
scripts/host/test-repository-linux.sh quick
git diff --check
```

## Reproducible identities

| Item | SHA-256 |
|---|---|
| host server source | `35c5d023d685353559e7c131fae081e1a917d054953213f6aa376ea9567f78f5` |
| root controller source | `97cc5dc7106e348db13d846c7e2a00db857c63d373d87d359c88d1b9ae7446ad` |
| installer source | `441e446c277dd2bd0316881308747eb4eee3fe22c49e4fb5ef7607dafd36719e` |
| unprivileged launcher source | `49036c956e4c2b843d39f12b76fb4504ed82d0646ca7c08f2415a1958879b8df` |
| fetcher source with request half-close | `be892d0130831674f0ce380dbfc4c719a6090eb8d87994bb87cc6486dcb926f1` |
| reproducible AArch64 fetcher | `920c9bb3ccb4ab4b3fc3ad783532c5620ed31b3bd52377c8fe3e340fd865702f` |

The AArch64 fetcher was rebuilt twice in the pinned Alpine/GCC 15.2.0 image;
both outputs were byte-identical. Its QEMU suite passed 23 executable cases
with five architecture-emulation skips, and the network-disabled real-root
suite passed all 28 cases.

## Independent review

The first focused review returned `DO-NOT-COMMIT` because a one-time
nonblocking peek could miss a delayed trailing request byte and blocking host
artifact reads were outside Python's socket timeout. The revised protocol
half-closes the device request direction and requires host EOF; the revised
controller adds a hard post-listener watchdog.

The second pass found a fork-to-`PDEATHSIG` race in that watchdog. The final
watchdog verifies its real parent immediately after exec and again before
signaling, while the production launch retains `PDEATHSIG=KILL`. The offline
suite kills the controller immediately after watchdog launch and proves the
watchdog exits. The final focused reinspection found no remaining must-fix
issue and returned `COMMIT`.

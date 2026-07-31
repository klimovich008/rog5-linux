# Authenticated Alpine fallback ACM control — offline

Date: 2026-07-31

## Result

PASS hardware-free. The minimal-headless lifecycle no longer depends on the
new deployment client key being authorized in the installed Alpine fallback.
A fixed host controller now verifies Alpine through its existing pinned
Ed25519 SSH host key over the exact USB ACM interface.

No phone action, PolicyKit action, host-network mutation, fallback-storage
write, flash, erase, mount, or temporary boot occurred for this result. The
live cryptographic ACM preflight remains pending, and the previously
authorized temporary boot remains unused.

## Protocol

`scripts/host/fallback-acm-control.py`:

1. requires separate ACM-control, phone-credential-use, and action-scoped
   fallback-storage-write guards before pin or device access;
2. requires a canonical mode-`0600` one-key pin below a caller-owned
   mode-`0700` directory outside Git, snapshots it through one
   `O_NOFOLLOW` descriptor, and later gives `ssh-keygen` only a memfd copy;
3. requires exact inactive/dead ModemManager state, with load state either
   `loaded` or the safer `not-found`; one raw `1d6b:0104` Alpine product; one
   `cdc_acm` interface 02; a stable device number; exclusive tty ownership;
   and no other holder;
4. sends one launcher bounded to 2,000 bytes with a fresh 128-bit nonce, below
   Alpine's 2,048-byte BusyBox line-editor limit. The launcher starts a child
   in a clean environment with Python isolated, no-site, and
   bytecode-disabled modes, while preserving the supervised shell for later
   non-reboot actions;
5. waits for one nonce-bound loader-ready marker before sending one or more
   source chunks of at most 1,801 bytes each. The number of chunks is bounded
   by the fixed source payload rather than being part of the protocol
   contract. The loader verifies their count, length, base64 syntax, and
   SHA-256 before executing them, while echoed shell input contains no
   complete protocol marker. Missing or partial chunks expire under a
   phone-side receive deadline without executing the source;
6. reads only exact kernel/init/compatible/ext4 state, zero project modules,
   complete empty pstore, complete dmesg, the exact 70-zone thermal set across
   three samples, Python major version, and boot ID;
7. signs one canonical result with Alpine's existing Ed25519 SSH host key and
   returns exactly one nonce-correlated bounded frame;
8. verifies the signature with fixed `ssh-keygen -Y verify`, rechecks the
   open USB identity, and publishes only bounded private proof metadata to a
   caller-selected, no-replace mode-`0600` record outside Git.

The `host-preflight` action performs the deterministic host-only portion
before a temporary boot: fixed tool metadata, inactive ModemManager, exact
allowed-signers pin, loader bounds, the 600-900 second wait range, and the
contact-start/anchor-age relationship. It neither opens ACM nor requires the
phone-storage-effects guard. The lifecycle binds its 3,600-second maximum
contact-start age plus the maximum 900-second ACM wait below the controller's
7,200-second anchor-age limit. Wall-clock freshness and physical location are
checked again after ACM discovery and before payload transmission, covering a
host suspend or wall-clock jump during the wait.

`preflight` and `classify` return without a reboot path. `preflight` retains
the historical 60 C readiness ceiling. Return classification uses a separate
80 C hard-safety ceiling so a normal warm rollback is not mistaken for an
absent fallback.

The `reboot` action additionally requires:

- a third reboot-specific guard;
- fixed fastboot tooling and a canonical empty initial fastboot inventory;
- one verified signed PREPARED frame;
- one host ACK bound to nonce and boot ID;
- a same-boot health recheck;
- one COMMIT marker;
- typed AArch64 `RESTART2("bootloader")` marshalling; and
- one same-port, unique ASUS `0b05:4daf` device whose fastboot product is
  exactly `lahaina`.

The phone-side ACK wait expires after 30 seconds, exceeding the host's
signature-verification and USB-revalidation bounds. After ACK, the host allows
30 seconds for repeated health collection. The phone independently enforces a
25-second post-ACK deadline and checks it before and after COMMIT publication,
then again gates `RESTART2`; a stalled collection or COMMIT write cannot cause
a late reboot after host failure. An absent ACK cannot leave the probe
permanently holding ACM, and the host never retries an ambiguous reboot.

## Lifecycle integration

`run-minimal-headless-live-cycle.py` now calls
`fallback-acm-control.py host-preflight` before boot, then `wait-preflight`
after target departure and NFS cleanup. It passes the private fallback host
pin and the same-boot recovery USB anchor, but never passes the deployment
client key. The anchor schema and literal `ROG5 recovery` product are directly
checked against the real capture producer.

The controller publishes `rog5-fallback-identity-v2`, which contains:

- exact fallback kernel and boot ID;
- recovery-to-fallback physical USB location;
- challenge nonce and maximum sampled temperature;
- SHA-256 identities of the signed record, signature, and inspected host pin;
  and
- `result=PASS`.

The lifecycle revalidates exact field order, private file metadata, every
identity shape and bound, and a boot ID distinct from the temporary target
before resolving its durable intent.
The lifecycle records a fallback attempt before contacting ACM and never
contacts it again under the same authorization, including when final host
cleanup fails after fallback was already proved.

## Verification

The focused controller suite has 34 hardware-free cases. It includes real
disposable Ed25519 signing/verification; pin replacement; framing, echo,
truncation, duplication, nonce, record-order, and health mutations; exact and
additional thermal zones; pstore inspection errors; serial device-number,
holder, output, read, write, and ACK timeout paths; classify/reboot separation;
typed reboot marshalling; canonical initial and returned fastboot inventories;
wrong port/state/product; duplicate serial/port; a post-ACK deadline bound;
canonical remote failure frames; host-only prerequisite validation; the real
anchor-producer contract; wall-clock jump and final-read error cases; and
private evidence output.

The updated lifecycle suite has 17 process test methods covering admission,
ordering, cleanup, durable intent recovery, runtime rejection, fallback proof
failure, malformed successful control output, and non-retry behavior.

Commands:

```text
python3 scripts/host/test-fallback-acm-control.py
python3 scripts/host/test-run-minimal-headless-live-cycle.py
scripts/host/test-repository-linux.sh ci
```

Independent standards/security, lifecycle/specification, and Claude Opus
reviews found blocking issues in early drafts. A final source audit also found
that Alpine 3.24 enables BusyBox per-command history and that the parent
interactive shell chooses its history path before the launcher can change the
child environment. The same
[official Alpine configuration](https://gitlab.alpinelinux.org/alpine/aports/-/blob/3.24-stable/main/busybox/busyboxconfig)
sets the interactive editing maximum to 2,048 bytes. Reads of binaries,
libraries, and the host key may also update inode access times on writable
`relatime` ext4. The implementation now uses a sub-2,048-byte
ready-before-data loader and makes those action-scoped storage effects an
explicit, fail-first authorization boundary instead of claiming they are
absent. Other
incorporated fixes include typed unsigned
reboot arguments, bounded ACK, explicit credential authority, pin
snapshotting, no explicit sync/bytecode/storage-write path, exact
thermal/pstore state, exact service and tty ownership, pre-reboot fastboot
absence, same-port fastboot identity, schema versioning, and retained proof
metadata.

## Decision

Hardware-free result: PASS.

Live result: HOLD. Do not invoke host-key signing or reboot until the operator
provides fresh credential-use authorization and separately authorizes the
BusyBox-history and possible ext4-atime effects of the exact ACM action.
The live preflight also confirms that fallback `/usr/bin/ssh-keygen` supports
the required `-Y sign` operation; the historical serial observation did not
establish that prerequisite, so its absence is a prerequisite failure rather
than a kernel-health regression. A nonce-bound `host-key-sign` error preserves
that distinction on the live transport.
Passing this report does not authorize those writes, a temporary boot, flash,
retry, or persistent installation.

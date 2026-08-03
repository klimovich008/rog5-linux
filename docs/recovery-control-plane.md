# Stable recovery control plane

Status: **shell-free framed path passed one signed live transaction and exact
rollback; target rejected before SSH because its candidate selected historical
DTB v1; corrected isolated candidate is offline**

Artifact-local authority: **none**. Live use occurs only through the central
standing authorization and this document's exact technical gates.

Last reviewed: 2026-07-29

The executable stdlib-only reference model is in
`tools/recovery_control/reference.py`; its host test is
`scripts/host/test-recovery-control-reference.py`. It defines protocol and
crash semantics for the native responder.

The native C source is
`tools/recovery_control/rog5-recovery-control.c`; its pseudo-terminal suite is
`scripts/host/test-recovery-control-native.py`, and its pinned AArch64 builder
is `scripts/device/build-recovery-control.sh`. The reproducibility/QEMU
aggregate is `scripts/host/test-recovery-control-aarch64.sh`. Host and
QEMU-backed AArch64 tests exercise the same source. The production compile has
no test backend or path override. It now invokes the privilege-separated
fixed-host acquisition helper under the rollback watchdog, invokes the fixed
verifier, receives the exact verified file descriptors, and performs a
bounded legacy `kexec_load`. Those binaries are now integrated into the
shell-free stable-recovery initramfs and reproducible ASUS 5.4 wrapper using
only a disposable trust root. The exact verifier and acquisition
contracts are documented in
[recovery runtime bundle contract](recovery-bundle-contract.md) and
[fixed recovery bundle transport](recovery-fetch-contract.md). The resulting
image was used once through an exact guarded runner and remains outside the
durable temporary-boot allowlist. That action grants no repeat authority.

The host side now has a fixed one-shot stdlib server plus a root-owned
PolicyKit controller. It recognizes exactly one recovery NCM gadget, binds
only `169.254.77.1:8080`, applies runtime-only source/destination firewall
rules, drops to the caller with no capabilities, verifies the exact listener,
and removes every state item it created. The fixed controller was installed
root-owned through PolicyKit and used for the attended transaction. It
temporarily handed the exact UUID-pinned shared fallback/recovery `/30`
profile to recovery and restored that same profile afterward,
then restored the exact profile, firewall forwarding flag, interface, and
rules. A nonce-bound root-owned marker now attests the already-verified
NFSv4.2 listener to the unprivileged control client without requiring access
to root-only `/proc/fs/nfsd` files.

`scripts/host/prepare-recovery-candidate.py` is the first manifest-driven
offline adapter into the runtime-bundle packager. Its initial record maps the
consumed persistent-root P2 kernel, DTB, and initramfs to
`persistent-root-ro-v1`, verifies their tracked identities before packaging,
and refuses any record other than `status=consumed` and `authority=none`.
The adapter contains no server, transport, phone, or execution action. It
proves preparation parity only; integrating the fixed server/verifier/
executor remains an A0.4 task.

The former recovery control plane used an interactive shell on
`/dev/ttyGS0`; echo, cursor queries, serial-open races, stale output, and loss
of the USB connection during `kexec -e` made outcomes ambiguous. The
stable-recovery candidate replaces that shell with a fixed-function
responder, makes read-only retries safe, makes execution at-most-once per
recovery boot, and separates the stable recovery image from signed runtime
kernel/DTB/initramfs bundles. The first signed live execution returned to
fallback before SSH because the candidate selected historical DTB v1. The
corrected target remains non-runnable until a new trust root, complete
release-pin update, independent review, and one standing-authorized live
sequence admitted by the exact lifecycle gates are complete. See the
[live result](../test-results/2026-07-29-headless-stable-recovery-live.md).

## Invariants

The recovery platform must preserve all of these properties:

1. It is entered only with an attended, manifest-pinned `fastboot boot`.
   Nothing is flashed.
2. The Android/fallback slot remains untouched.
3. Root is RAM-backed. Physical block devices are made read-only before USB
   binds, the ASUS 5.4 wrapper must expose the measured 116-node topology,
   and no block-backed filesystem is mounted.
4. A rollback watchdog remains armed until an accepted target takes over.
5. The ACM endpoint accepts no shell syntax and exposes no arbitrary command
   execution.
6. Every request and response is framed and correlated by a request ID.
7. The device, not the host, mints a fresh session ID once per recovery boot.
8. Read-only and preparation requests are idempotent. Execution is claimed
   atomically on the device and is never automatically retried.
9. Runtime payloads are accepted only when a manifest verifies against a
   trust root embedded in the frozen recovery image.
10. Kernel command-line input is structured and allowlisted. An arbitrary
    command-line string is never accepted.

## Boundary

```mermaid
flowchart LR
    H["Host controller<br/>write-ahead ledger"] -->|"framed requests over ACM"| C["Fixed recovery responder"]
    C -->|"fixed NCM address<br/>manifest fetch"| S["Read-only host bundle server"]
    C --> V["Signature, size, hash,<br/>DTB and cmdline verifier"]
    V --> K["kexec load"]
    K -->|"atomic claim, then execute"| T["Target kernel"]
    T --> O["Out-of-band outcome<br/>target / fallback / recovery"]
    O --> H
```

ACM is the control channel. NCM carries larger files. The responder passes
only a strict bundle identifier and expected manifest hash to the fixed
acquisition helper; requests cannot provide a URL, host, interface, or port.
The helper binds `usb0` and source `169.254.77.2`, then connects only to
`169.254.77.1:8080`. It uses the canonical length-framed binary stream in
[fixed recovery bundle transport](recovery-fetch-contract.md), not HTTP:

```text
format=rog5-fetch-request-v1
bundle=<bundle-id>
manifest_sha256=<expected-hash>
```

`<bundle-id>` is limited to 1–64 lowercase ASCII letters, digits, `.`, `_`,
and `-`; it cannot begin with punctuation, contain `..`, or equal the reserved
unset value `none`.

## Framing

Use a bounded netstring carrying canonical ASCII `key=value` records:

```text
<decimal-byte-length>:<payload>,
```

The maximum payload is 4096 bytes. One parser feed is capped at 8192 bytes and
32 frames; callers perform additional bounded reads as needed. The parser must
tolerate a frame split across any number of reads and multiple frames in one
read. It must reject leading-zero lengths, non-decimal lengths, oversized
frames, missing commas, duplicate keys, unknown keys, embedded NUL, non-ASCII
input, and a truncated frame at end of stream.

A request has these common fields:

```text
version=1
kind=request
session=<32 lowercase hex characters>
request=<32 lowercase hex characters>
verb=<fixed verb>
body_sha256=<64 lowercase hex characters>
```

A response repeats `session`, `request`, and `verb`, adds a fixed result code,
and returns a body containing the exact state, prepared bundle, manifest hash,
prepare request, commit request, commit fingerprint, execution-started marker,
watchdog state, last fixed error, and immutable boot-time postmortem metadata.
The postmortem fields are state (`UNAVAILABLE`, `EMPTY`, or `PRESENT`), record
count, total record bytes, snapshot SHA-256, and up to 512 bytes of
hex-encoded snapshot tail. Its `body_sha256` covers all canonical fields.
`HELLO` is the only request allowed with an all-zero session. Its response
returns the device-minted session ID. USB already provides link integrity;
body hashes protect canonical request/response identity and replay matching
rather than replacing manifest signatures.

All-zero request IDs and manifest hashes are reserved unset values and are
rejected. Fixed result codes are bound to their valid verb and transaction
state. `EXEC_FAILED` is valid only with the persisted execution-started
marker. Successful target departure is classified out of band; the last
recoverable device state remains `CLAIMED` with `execution_started=YES`.

The responder opens `/dev/ttyGS0` itself, applies raw/no-echo termios, and
uses nonblocking I/O with fixed deadlines for a started frame, response
writes, and output drain. An idle poll continues to check the live watchdog.
An incomplete prefix or body and a stalled write or drain close the
connection without authorizing execution. The responder never starts a login
shell. The same interactive-shell removal applies to
`initramfs/recovery-init`, `initramfs/network-root-init`, and
`initramfs/persistent-root-init`.

The native parser reads one bounded frame at a time, so it never accumulates a
multi-frame input batch. Coalesced frames remain in the TTY queue and are
handled as separate bounded dispatches.

The stable initramfs build exports a fixed C locale and UTC timezone before
archive traversal. Its integration gate compares builds made under different
caller locales and time zones, locks the root account, removes login/password
and DHCP entry points, and rejects credential-like or set-ID content. The
fixed device address lives only in `/init`; the boot command line contains no
legacy `rog5.recovery_cidr` input.

## Fixed verbs and state

The first protocol needs only four verbs:

| Verb | Effect | Retry rule |
|---|---|---|
| `HELLO` | Return protocol version, capabilities, and current session ID | Safe |
| `STATUS` | Return session, prepared bundle, commit state, watchdog state, and last fixed error | Safe |
| `PREPARE` | Fetch and verify one signed bundle, then perform `kexec -l` with validated arguments | Safe only with the same request ID and body |
| `COMMIT_EXEC` | Atomically claim the prepared bundle, flush a `CLAIMED` response, then call `kexec -e` | Never retransmit after an unknown outcome |

`PREPARE` executes one fixed pipeline:

1. `/usr/libexec/rog5-bundle-fetch <bundle> <manifest-hash>`;
2. `/usr/libexec/rog5-bundle-verify --handoff-fd3 ...`; and
3. `/usr/sbin/kexec -c -l` using only the three sealed descriptors.

The responder gives the fetch helper a 65-second outer deadline and checks
the rollback-watchdog pidfd throughout. Fetcher exit 42 becomes the permanent
`BUNDLE_ID_CONFLICT` decision. Any other acquisition failure or timeout
becomes `FETCH_FAILED`. Both are written to the replay ledger, and neither
path can invoke the verifier, loader, unload, or executor.

One session may prepare only one bundle. For mutating verbs, a repeated
request ID with the same canonical body returns its immutable recorded
decision combined with the current monotonic state. After successful
preparation or a terminal `FETCH_FAILED`/`BUNDLE_ID_CONFLICT` acquisition
decision, another PREPARE request ID returns `PREPARE_ID_CONFLICT` without
refetching. A verifier rejection may be retried only under a new request ID;
the old ID always replays its original `VERIFY_FAILED` decision. The
authoritative successful prepare ID remains required by `COMMIT_EXEC`.
Reusing any mutation ID with a different body or verb returns
`REQUEST_CONFLICT`. Each decision records its original verb so cross-verb
replay cannot reinterpret or crash on the result. `HELLO` and `STATUS` are
read-only current-state queries and do not consume replay-ledger entries.

The device creates `/run/rog5-control/session` before USB binds using kernel
randomness and mode `0600`. It also keeps a bounded replay ledger in the same
RAM filesystem. Entries are not evicted during a recovery session. Three idle
slots are protected at the boundary: one lets a failed `PREPARE` decision be
recorded exactly once, while a successful `PREPARE` and its exact
`COMMIT_EXEC` need at most two entries. No verifier runs once fewer than three
idle slots remain, and only the matching commit may use the final transaction
capacity after preparation. Other new mutations return `LEDGER_FULL`.
`STATUS` remains available even at full capacity. Responder restarts reuse the
session and ledger; a full recovery reboot creates a new session and rejects
stale requests.

The responder does not trust a pathname-only watchdog marker. At startup it
opens an owner-private lease containing the watchdog PID and Linux process
start time, validates that identity through `/proc`, pins it with `pidfd_open`,
and polls the pidfd while ACM is absent, at idle, during framing, response,
drain, and both sides of the execution marker. The production executor checks
again before fork and child exec; its parent monitors and reaps the child
while waiting. PID reuse and a dead or replaced lease fail closed.

## Exact-object PREPARE boundary

After fixed-host acquisition publishes a finalized bundle, `PREPARE` forks
only `/usr/libexec/rog5-bundle-verify` with the requested bundle and manifest
hash. A private nonblocking Unix `SOCK_SEQPACKET` socket is the only
authorization channel. The verifier first copies each source into a
write-sealed `memfd`, then verifies and sends one bounded canonical plan plus
exactly three `SCM_RIGHTS` descriptors for those immutable kernel, DTB, and
initramfs snapshots. The responder rejects a wrong peer identity, truncation,
additional ancillary data, wrong descriptor count or type, missing seals,
aliases, unsafe metadata, nonzero offsets, verifier failure, timeout, and any
plan/request mismatch. Every descriptor installed by a malformed rights
packet is closed before rejection.

Received descriptors are close-on-exec in the responder. Only the loader child
clears that flag, immediately rechecks the watchdog, and directly executes:

```text
/usr/sbin/kexec -c -l /proc/self/fd/<kernel-fd>
    --initrd=/proc/self/fd/<initramfs-fd>
    --dtb=/proc/self/fd/<dtb-fd>
    --command-line=<verified-generated-command-line>
```

The fixed `-c` is required: the accepted ASUS staging kernel and custom DTB
use the legacy `kexec_load` path, matching the previously accepted device
loaders. The parent monitors and reaps both children under fixed deadlines,
closes all descriptors, and persists `PREPARED` only after the loader exits
zero. It never reopens an artifact through the bundle directory.

A crash after successful load but before durable `PREPARED` leaves the
transaction idle. On restart, the responder first runs fixed
`kexec -c -u`; only then may the same request safely load again. A rejected or
timed-out loader and a returned fixed executor also unload before the
responder continues. A crash after `PREPARED` is published is reconstructed
from durable RAM state and does not rerun the verifier or loader.
`COMMIT_EXEC` remains the sole non-retryable execution boundary.

Before image integration, a separately gated load-only cycle may proceed
under the central standing authorization and must use the real pinned AArch64
kexec-tools and these procfd arguments to prove
`/sys/kernel/kexec_loaded` changes from 0 to 1, that an exact repeat load is
safe, and that `kexec -c -u` returns it from 1 to 0 without target execution.
The image must mount `/proc`, expose `/proc/self/fd`, expose
`/sys/kernel/kexec_loaded`, include every kexec runtime library, and establish
the watchdog before starting the responder. The offline fake-kexec suite
proves that a loaded-then-timed-out image is unloaded and that restart
reconciles a crash after load; the staging-only live gate must prove those
same transitions against the real kernel.

Before `COMMIT_EXEC` calls `kexec -e`, it must:

1. verify that the referenced `PREPARE` transaction is still current;
2. create the commit claim with `O_CREAT|O_EXCL`, including the request
   fingerprint;
3. write and `fsync` the claim, then `fsync` its directory;
4. send and drain a `CLAIMED` response;
5. call `kexec -e` directly with `execve`, never through a shell.

Immediately before calling `kexec -e`, the responder persists an
execution-started marker. If `kexec -e` returns, the device records
`EXEC_FAILED` and remains fail-closed until rollback. A duplicate commit or a
responder restart after either marker never calls `kexec` again; it returns
the recorded transaction identity and state if the responder is still alive.
If USB disappears before the host receives a response, the result is
`UNKNOWN`, not success or failure.

## Host write-ahead ledger

The host cannot implement at-most-once semantics by itself. Its ledger becomes
meaningful only after `HELLO` supplies a device-minted session.

The live host client is `scripts/host/stable-recovery-control.py`. It discovers
only the exact recovery ACM identity, performs `HELLO`, permits one same-ID
`PREPARE` replay after a transport loss, writes the existing durable intent
before `COMMIT_EXEC`, and never retransmits that commit. A lost commit response
therefore remains `UNKNOWN` until an out-of-band target, fallback, or recovery
observation resolves it.
Ledger resolution is separately guarded by
`ALLOW_RECOVERY_INTENT_RESOLVE=1`; it is set only after the recorded target
identity or exact fallback observation has been captured.

`scripts/host/run-stable-recovery-live-gate.sh` is the separate boot boundary.
It requires two byte-identical ignored-directory wrapper builds, re-verifies
the embedded public key and fixed binaries, verifies the signed runtime bundle
and AVB footer, accepts only fastboot product `lahaina`, and contains only
`fastboot boot`. It does not add an ephemeral image to the durable boot
allowlist.

Before transmitting `COMMIT_EXEC`, the host writes a record containing the
device session, request ID, prepared-manifest hash, target identity, and
timestamp. It uses temporary-file + `fsync` + atomic rename + directory
`fsync` under an XDG state directory outside the repository. The durable
record is keyed by device session, with the request ID inside it, so choosing
a fresh request ID cannot bypass an unknown prior commit. It marks the record
`TRANSMITTED` before writing to ACM.

After transmission:

- a clear protocol rejection resolves the record as rejected;
- a target with the expected identity resolves it as executed;
- the exact fallback with a changed boot ID resolves it as target not
  accepted without inferring whether execution occurred unless that was
  independently observed;
- the same recovery session may resolve it through `STATUS`;
- transport loss without one of those observations remains `UNKNOWN`.

The host never sends a second `COMMIT_EXEC` in a device session that already
has a `TRANSMITTED` record, even if a caller supplies a new request ID. A new
device session is a new attended cycle, not permission to repeat a consumed
payload automatically.

## Runtime bundle trust

The exact first-version format, bounds, fixed paths, generated command line,
FDT policy, reproducible build, and remaining integration gates are in
[recovery runtime bundle contract](recovery-bundle-contract.md). The stable
image embeds only a public verification key and policy. A runtime bundle
contains:

- protocol and manifest version;
- bundle ID and purpose;
- kernel, DTB, and mandatory initramfs size and SHA-256;
- expected target kernel release and USB/SSH identity;
- a structured command-line policy;
- rollback timeout and target acceptance timeout within frozen bounds;
- a detached signature over canonical manifest bytes.

The first version does not accept command-line fields or text from the
manifest. It generates an exact command line from the fixed profile, validated
bundle ID, and bounded rollback timeout. That narrower rule rejects arbitrary
`init=`, `root=`, unknown keys, duplicates, writable-root flags, and unbounded
timeouts by construction.

No production signing key has been created. Disposable keys have been used
for offline tests and the consumed attended bundle; their private material was
not retained. The corrected target, bundle, shell-free initramfs, and wrapper
now pass a complete twin-build offline gate under one destroyed disposable
key. A live target still requires a newly generated single-use or admitted
production trust root and a rebuilt/allowlisted wrapper. The central standing
authorization covers one technically admitted cycle; the consumed live trust
root cannot authorize another bundle.
See the
[corrected offline result](../test-results/2026-07-29-corrected-headless-candidate-offline.md).

## PREPARE transport and replay evidence

`PREPARE` is retry-safe only inside the same recovery session and under one
absolute deadline. If the initial framed exchange loses ACM before returning a
correlated response, the host closes that descriptor and performs one stable
ACM discovery tagged `prepare-replay`. It replays the identical request only if
the recovered `HELLO` returns the same session. `COMMIT_EXEC` remains
non-retryable and is not part of this path.

The host must not let replay discovery overwrite the reason replay was needed.
A failed replay therefore reports one bounded terminal record containing:

- the fixed initial PREPARE transport-loss reason;
- the explicit `prepare-replay` phase; and
- saturated ACM state counts, bounded state transitions, fixed identity-field
  labels, and a truncation bit without device identity values.

This closes the Generation-9 host observability defect: a later Alpine product
mismatch can no longer masquerade as the initial recovery failure. It does not
yet identify whether recovery stalled after fetch, verification, kexec load,
or prepared-state publication. Those device-side phases require a separately
framed, bounded progress contract before another recovery image is issued.

## Postmortem outcome oracle

The installed fallback reserves 4 MiB for ramoops but cannot read it:

- the reservation has zero users and no bound driver;
- `ramoops_bound=0`;
- `/dev/mem` and BusyBox `devmem` are absent;
- `CONFIG_DEVMEM` is unset;
- no matching module build environment is available.

The stable recovery wrapper does not share that limitation: its pinned config
already has built-in `PSTORE`, `PSTORE_CONSOLE`, and `PSTORE_RAM`, and its
boot-v3 command line carries the exact reservation. Before starting the
framed responder, recovery now mounts pstore read-only in practice, copies
bounded regular records into a private RAM snapshot without unlinking them,
and publishes canonical metadata. The responder validates and pins that
owner-only status file at startup and includes it in every response.

Offline tests prove empty, present, unavailable, malformed, partial-I/O, and
restart behavior. They do **not** prove the Snapdragon DRAM region survives a
target → bootloader → recovery transition. That requires a controlled live
cycle. If it does not survive, the next oracle experiment is the possible
Qualcomm USB-C debug UART; no UART capability is currently claimed.

## Test suite before re-freeze

### Parser and protocol unit tests

- every possible split point for a valid frame;
- multiple frames in one read;
- truncated, oversized, malformed, duplicate-key, unknown-key, NUL, and
  non-ASCII input;
- request-ID replay with same and different bodies;
- stale and all-zero session rejection;
- fixed-verb, fixed-field, result/state, and reserved-sentinel enforcement;
- ledger-capacity exhaustion before processing, with no in-session eviction.

### State-model tests

- `HELLO -> PREPARE -> COMMIT_EXEC`;
- duplicate same-ID `PREPARE` returns its immutable decision with current
  state;
- same-bundle `PREPARE` with a new ID is rejected;
- second bundle in one session is rejected;
- duplicate commit never increments an execute counter;
- crash before claim, after claim, after reply, and after simulated execute;
- crash before/after immutable writes, file fsync, link, unlink, rename, and
  directory fsync;
- `kexec -e` return records a permanent session failure;
- fresh recovery session rejects every stale request;
- watchdog remains armed on all parser, fetch, verification, and execute
  failures.

### Pseudo-terminal integration tests

Run the real responder against `openpty(3)` with fault injection:

- delayed open and initial read race;
- partial writes and reads;
- incomplete-prefix/body timeouts, forced short writes, and drain timeout;
- disconnect before and after the atomic claim;
- watchdog death at startup, idle, before response, and after the execution
  marker;
- responder restart with `/run` state retained;
- dropped response followed by safe `STATUS`;
- `STATUS` correlates the exact prepare ID, commit ID/fingerprint, manifest,
  execution marker, watchdog, and last error;
- terminal echo and cursor queries are absent;
- arbitrary shell text is rejected and never reaches `execve`;
- sealed verified snapshots survive replacement and in-place overwrite of
  every bundle pathname;
- malformed plans, short or unsafe rights, nonzero verifier exit, and loader
  failure never create `PREPARED`;
- zero-byte and over-count rights packets never leak descriptors;
- rights packets up to Linux's 253-descriptor maximum are fully drained and
  rejected without leaks, while successful PREPARE also preserves the parent
  descriptor count;
- verifier and loader timeout or watchdog death kill and boundedly reap their
  child;
- watchdog death during verification is terminal;
- loaded-then-timeout, crash-after-load restart, and returned execution unload
  before another action; and
- the fixed execution child is boundedly killed and reaped on watchdog death.

### Bundle and security tests

- valid signature and all pinned hashes pass;
- changed manifest, payload, DTB, signature, or size fails;
- untrusted key and path traversal fail;
- oversized files and decompression bombs fail before allocation;
- invalid DTB compatibility, reserved-memory overlap, and command-line field
  fail;
- fetch is limited to the fixed NCM host and bundle path;
- no physical storage mount or write command exists in the image.

### Reproducibility and image tests

- two clean responder builds are byte-identical;
- two clean initramfs and wrapper builds are byte-identical;
- verifier proves storage gates run before responder start and UDC bind;
- verifier proves there is no `sh -i`, getty, authorized key, private key, or
  arbitrary command path in any of the three initramfs variants;
- the re-freeze updates the source/hash/verifier pins together;
- the temporary-boot allowlist admits only the newly accepted stable image.

### Live promotion sequence

1. Two attended staging-only cycles: exact image, RAM root, all physical
   devices read-only, ACM/NCM, no payload load, automatic rollback.
2. Two protocol-only cycles with malformed/replayed requests and no kexec.
3. One load-only cycle with a signed inert payload and automatic rollback.
4. One separately gated execute cycle under the central standing authorization,
   with host write-ahead intent and out-of-band target/fallback classification.

Each live cycle gets one invocation. A transport timeout never authorizes a
retry.

Recovery ACM enumeration failures are classified before any Generation-9
issuance. The host keeps only fixed state names, sample counts saturated at
999, at most 16 transitions, and the names—not values—of changed identity
fields. Any uninspectable ACM node fails closed. This diagnostic layer is
observational: it does not weaken exact product selection, read/write access,
the two-second stable-identity dwell, final revalidation, or the one-invocation
rule. See the
[offline classifier result](../test-results/2026-08-03-generation-9-recovery-acm-classifier-offline.md).

## Rollout order

1. Implement the parser/state reference model and fault-injection tests.
2. Implement the static responder and pseudo-terminal integration tests.
3. Add signed-manifest and fixed-command-line verification. **Complete
   offline.**
4. Add same-descriptor legacy `kexec_load` and integrate the verifier with
   `PREPARE`. **Complete offline and integrated into the shell-free
   initramfs.**
5. Connect the offline-tested fixed-host fetch helper to `PREPARE`.
   **Complete offline and integrated into the shell-free initramfs.**
6. Add the fixed read-only host-serving command and controller/firewall
   integration. **Complete and live-proven with exact cleanup.**
7. Remove all three interactive shells and update image verifiers.
   **Complete offline.**
8. Build the initramfs, wrapper, raw boot-v3 image, and AVB wrapper twice.
   **Complete reproducibly and used for one attended signed transaction;
   production trust root and release pins remain absent.**
9. Create the production-key candidate and update all release pins
   atomically.
10. Run the staging-only promotion sequence. **The shell-free wrapper,
    transport, signed PREPARE/COMMIT, target NCM, rollback, and host cleanup
    passed once; corrected-target SSH remains pending.**
11. Integrate the tested host-ledger semantics with the native responder and
    device-minted session. **Complete and live-proven for one commit resolved
    as `FALLBACK_RETURNED`.**
12. Investigate recovery-side retained-marker reading and USB-C debug UART
   independently.

The accepted v18 image remains a legacy staging transport while this work is
offline. Its payload helpers are evidence only; they are not an active live
gate.

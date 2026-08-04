# Recovery NCM progress channel

## Status

The device sender, bounded host collector core, and hardware-free regression
tests are implemented. They are **not yet wired into the privileged host
network broker**, no successor image has been issued, and the phone has not
been booted with this code. Generation 10 remains consumed and must never be
retried.

This channel addresses one exact failure: recovery can continue processing a
valid `PREPARE` after the ACM response transport disappears. Generation 10
proved `REQUEST_ACCEPTED` and a complete host-side bundle transfer, but ACM
loss hid the later fetch, verify, kexec-load, and prepared-state boundaries.

## Contract

The recovery responder opens at most one outbound TCP connection for a
`PREPARE` lifecycle:

- device interface: `usb0`;
- device address: `169.254.77.2`;
- host address: `169.254.77.1`;
- host port: `8081`; and
- transport: one receive-only host stream, with no host application bytes.

The stream carries the existing canonical, body-hashed, netstring-framed
`Progress` records in this exact contiguous order:

1. `REQUEST_ACCEPTED`
2. `FETCH_COMPLETE`
3. `VERIFY_COMPLETE`
4. `KEXEC_LOAD_COMPLETE`
5. `PREPARED_PERSISTED`

Every record binds the device-minted session, exact PREPARE request ID, bundle,
manifest SHA-256, sequence, phase, and armed-watchdog state. The responder
closes the stream when PREPARE reaches a terminal outcome. A prefix therefore
proves only that the device reached its last reported boundary; absence of a
later record does not prove which operation failed.

## Failure isolation

The NCM path is advisory by construction:

- the device reads no bytes from it;
- there are no acknowledgements, commands, retries, or reconnects;
- connection setup is nonblocking and bounded to 25 ms once per PREPARE;
- each record uses one nonblocking `send`; a short write, backpressure, peer
  closure, or other error permanently suppresses the channel;
- NCM emission happens before the corresponding possibly stalled ACM write;
- the armed-watchdog assertion is evaluated at every progress boundary even
  after ACM progress has been suppressed, so watchdog loss remains terminal;
- NCM failure never changes PREPARE state, result, ACM behavior, or rollback;
  and
- completing all five NCM records never creates a claim or calls kexec.

Only a correlated terminal ACM response with `result=PREPARED` can let the
host enter the pre-COMMIT gate. `COMMIT_EXEC` still requires its ACM request,
durable host intent, immutable device claim, drained ACM response, and direct
executor path. The collector record states `authority=NONE`; no COMMIT code
reads it.

## Host capture rules

The host collector core:

- accepts one exact device peer and closes the listener after that admission,
  so a second connection cannot influence the capture;
- shuts down the accepted socket's host-to-device direction before reading, so
  collector code cannot place application bytes in the device receive queue;
- supports an exact expected session/request or pins both from the first valid
  record;
- rejects identity changes, malformed records, body-hash failures, duplicate
  or noncontiguous phases, and trailing records;
- caps the complete wire capture at 8 KiB;
- hashes the captured wire bytes; and
- emits explicit `COMPLETE` or `PARTIAL`, reason, and `truncated=YES|NO`
  fields instead of promoting EOF, timeout, a torn record, or a cap hit.

The production listener helper binds the fixed host address and port with
`SO_BINDTODEVICE`. The remaining broker integration must open or securely
delegate that listener while retaining the exact NCM interface, address, and
firewall ownership through the post-fetch phases.

## Hardware-free evidence

`scripts/host/test-recovery-progress-collector.py` covers complete and
fragmented streams, every byte-level truncation point, explicit evidence-cap
truncation, timeout/stall, torn records, wrong pinned identities, identity
changes, noncontiguous prefixes, wrong peers, one-connection listener closure,
and exact mocked interface/endpoint binding call shape.

`scripts/host/test-recovery-control-native.py` additionally proves:

- the Generation-10 shape: ACM exposes only `REQUEST_ACCEPTED`, while NCM
  independently captures all five phases;
- a complete NCM trace leaves the device PREPARED but unclaimed until an exact
  ACM `COMMIT_EXEC` arrives;
- a torn NCM record does not change a healthy ACM PREPARE result; and
- a closed/dead collector peer does not delay or gate PREPARE.

The native x86_64 suite currently passes 62 tests. The AArch64 package
dependencies are restored on the host, but rootless Podman on this SteamOS
session still returns `Exec format error` for the pinned ARM64 container; that
host-runtime issue is not treated as AArch64 test evidence.

The native tests inject an already-connected descriptor and therefore do not
exercise the production `usb0` bind, source-address bind, nonblocking connect,
25 ms connect deadline, or `SO_ERROR` path. Those properties are implemented
and statically inspected, but they are not yet claimed as runtime evidence.
Likewise, the fixed host-listener test uses a mocked socket to prove exact
`SO_BINDTODEVICE`, bind, and listen call shape plus post-bind identity checks;
it is not a kernel-level `usb0` bind test. Gate 6 below covers both real paths.

## Remaining gate before a successor image

Do not issue Generation 11 until all of these are complete:

1. extend the fixed privileged broker and firewall policy for port `8081`;
2. keep the NCM interface/address alive after bundle EOF until progress capture
   reaches clean EOF or its bounded deadline;
3. run the collector unprivileged with a broker-opened exact-interface
   listener, or prove an equally strict privilege-drop design;
4. correlate its private mode-`0600` record with the ACM session/request and
   lifecycle timeline without feeding it into COMMIT;
5. add hostile broker/lifecycle tests for no collector, collector stall, wrong
   interface/peer, second connection, partial record, timeout, and cleanup;
6. exercise the exact production bind/connect path, including refusal and its
   25 ms bound, without substituting a pre-connected test descriptor;
7. restore and pass the exact AArch64 build/QEMU layer, complete local CI,
   constrained read-only review, and exact-head GitHub CI; and
8. only then twin-build and review a fresh offline-only recovery wrapper.

Pstore remains a complementary prior-boot oracle. It cannot replace this
same-lifecycle channel because the verified Alpine fallback cannot read the
ramoops reservation and survival across another recovery transition is not
proven.

# Recovery NCM progress channel

## Status

The device sender, bounded host collector, fixed privileged host boundary,
lifecycle correlation, and hardware-free regression tests are implemented.
The implementation passes the complete local Linux `ci` and provisioned
`quick` tiers and the hash-pinned host controller is installed and
host-preflighted. A distinct
[Generation-11 successor](../test-results/2026-08-04-generation-11-ncm-progress-wrapper-offline.md)
was clean-built twice and issued twice offline as AVB
`8472b206476e9a3143dec000b7f2369678c11248ad10203ef0646389e6bcf562`.
It remains ignored, unprofiled, unadmitted, unbooted, and `authority=none`;
the phone has not been booted with this code.
Generation 10 remains consumed and must never be retried.

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

The fixed root-owned controller discovers exactly one trusted recovery NCM
interface, owns `169.254.77.1/30`, port `8081`, and its source-restricted
firewall rule, and starts the collector before the port-`8080` bundle server.
The root-owned runtime helper opens the exact `SO_BINDTODEVICE` listener and
the caller's private output-directory descriptor, then clears groups,
capability bounding/ambient sets, and all root identities before creating one
mode-`0600` capture with `O_EXCL|O_NOFOLLOW`. It cannot regain root. Parent
death is armed before interpreter execution and re-armed after the UID/GID
change because Linux clears `PDEATHSIG` when credentials change.

Port `8081` remains advisory: an absent or exited collector is reported as
unavailable and does not block a successful port-`8080` transfer. A
pre-existing, duplicate, IPv6-conflicting, or mis-owned listener is a host
integrity conflict and still fails closed. Healthy startup gets a bounded
readiness window; after transfer, a two-second grace lets buffered evidence
drain before a stalled collector is terminated and demoted. After an accepted
stream, the lifecycle leaves a private stop record at correlated `PREPARED`;
the collector drains bytes and clean EOF already buffered before classifying
`STOP_REQUESTED`, without disabling its absolute deadline. Rejected streams
retain the observed byte count, hash, and valid phase prefix. Marker failure,
collector failure, missing capture, and an unsafe or internally impossible
capture remain `authority=NONE` and cannot change COMMIT.

The fixed broker, client, installer, and launch preflight hash-pin this helper
and its three Python modules. The current source hashes are:

- runtime helper: `8b15aaac28d54ac0acf93411dc2dbb77d9a9b7b5dfc8e2cc591609f7a23ed20a`;
- package `__init__.py`: `22364e5f8e8e18744fc9e1aabb069acf2e7020251f40c64202f4d30227b38175`;
- protocol reference: `82497ccf98ddf67fbaeccf6173c8ce5531029977d28c7015e191d940de84a4da`; and
- collector module: `5c5ee9480fa49448e204f30f97679dc8108c60687627a0f94ca3c812322ee5a8`.

## Hardware-free evidence

`scripts/host/test-recovery-progress-collector.py` has 21 tests covering
complete and fragmented streams, every byte-level truncation point, explicit
evidence-cap truncation, timeout/stall, torn records, wrong pinned identities,
identity changes, noncontiguous prefixes, wrong peers, one-connection listener
closure, exact mocked interface/endpoint binding, the PREPARED-stop versus
buffered-clean-EOF race, and the stop-drain absolute deadline.

`scripts/host/test-recovery-progress-runtime.py` has eight tests for the fixed
argument surface, descriptor-relative no-replace output, privilege-drop order
and irreversibility, parent-death re-arming, one private record, and
non-authoritative refusal classification. The controller and broker layers add
34 and 18 tests respectively, including no-listener continuation,
post-transfer EOF-marker failure, port conflicts before and after startup,
watchdog cleanup, exact output-directory forwarding, and signal propagation.

`scripts/host/test-recovery-control-native.py` additionally proves:

- the Generation-10 shape: ACM exposes only `REQUEST_ACCEPTED`, while NCM
  independently captures all five phases;
- a complete NCM trace leaves the device PREPARED but unclaimed until an exact
  ACM `COMMIT_EXEC` arrives;
- a torn NCM record does not change a healthy ACM PREPARE result; and
- a closed/dead collector peer does not delay or gate PREPARE; and
- an explicit test-only opt-in enters isolated user/network namespaces and
  exercises the production device path: source `169.254.77.2`, interface
  `usb0`, peer `169.254.77.1:8081`, wrong host interface, and unresolved peer.

The native responder suite passes 63 tests. The lifecycle suite passes 69 and
proves that missing, malformed, mismatched, partial, and complete progress
records are classified only after durable COMMIT; each assessment says
`authority=NONE`. Missing listener and capture do not gate target acceptance.
The complete repository Linux `ci` tier passes, including corrected-DTB,
source, generic QEMU/systemd, recovery, packaging, timeout, rollback, and
repository-policy gates. This remains hardware-free evidence.

## Remaining gate after offline issuance

The base NCM implementation publication, hash-pinned installed-host proof,
retained AArch64 gate, clean twin wrapper build, and Generation-11 issuer
publication are complete. The issuer/evidence checkpoint passed exact-head
GitHub Actions run `30899370666` at commit `5293e56`. Offline issuance did not
create boot authority. Continue in this order:

1. pin the exact Generation-11 wrapper and existing target tuple in one
   immutable offline-only lifecycle profile;
2. review and verify that profile together with the timeout lattice, rollback,
   fallback, one-shot consumption, and private-evidence paths;
3. publish the profile with green local and exact-head GitHub CI; and
4. only then consider one distinct central-policy admission and connected
   preflight before any temporary boot.

The current work creates no policy row, connected action, or phone state
change. Both retained Generation-11 trees state `authority=none` and cannot be
booted by the lifecycle controller.

Pstore remains a complementary prior-boot oracle. It cannot replace this
same-lifecycle channel because the verified Alpine fallback cannot read the
ramoops reservation and survival across another recovery transition is not
proven.

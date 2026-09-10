# Recovery postmortem-lineage checkpoint — offline

Date: 2026-08-09
Starting repository SHA: `f197d206c9bb1011cf0f71f94841a045a5b608ad`
Recommendation: **HOLD**

## Outcome

The stable-recovery pstore path is now internally verifiable and capable of
exact candidate/boot-ID correlation without exposing raw pstore through the
new operator action. This advances the independent-observability prerequisite,
but it does not prove that the Snapdragon ramoops reservation survives a real
target → bootloader → recovery transition. No candidate was issued, signed,
authorized, or booted.

The earlier network-root conclusion is unchanged: the host/target readiness
race was reproduced only in the hardware-free ordering model, not established
as the cause of Generation 12. Host transition timing, NFS timeout analysis,
watchdog conclusions, VCNL WIP isolation, and storage retention inventory
remain recorded in
[`2026-08-09-critical-network-root-readiness-review-offline.md`](2026-08-09-critical-network-root-readiness-review-offline.md).

## Concrete defects fixed

1. The native recovery responder trusted the bounded status file without
   validating the complete `/run/rog5-postmortem.snapshot`. A stale, malformed,
   substituted, or status-inconsistent snapshot could therefore not support a
   trustworthy later correlation. The responder now fails before session
   creation unless the fixed no-follow snapshot is a private, singly linked
   regular file with exact aggregate framing, record/payload bounds, metadata,
   aggregate hash, and tail.
2. The first marker scanner accepted only an unprefixed line. The accepted
   target has `CONFIG_PRINTK_TIME=y`; `console-ramoops` emits `[time] marker`,
   while panic `dmesg-ramoops` emits `<priority>[time] marker`. Both canonical
   forms are now accepted. Arbitrary text, malformed timestamps, leading-zero
   priorities, priorities above 191, malformed lookalikes, and distinct valid
   markers remain ambiguous.
3. A syntactically unique marker was not correlated to the expected execution.
   The read-only `stable-recovery-control.py postmortem-status CANDIDATE
   BOOT_ID` action now validates the expected identity before device discovery,
   recomputes the exact marker hash, and distinguishes `UNAVAILABLE`,
   `NO_RECORDS`, `NO_MARKER`, `AMBIGUOUS`, `DIFFERENT_MARKER`, `MATCH`, and
   `MATCH_REPEATED`.
4. The first host-action revision printed full protocol responses, including
   the pre-existing reversible `postmortem_tail_hex`. Independent review caught
   that disclosure. The correlation action now emits one redacted record with
   session/request identity, bounded snapshot metadata, expected identity,
   marker counts/hashes, and classification only.

The generic recovery `status` action remains the raw diagnostic action. The
three lineage fields extend the fixed `version=1` response schema, so the host
and recovery must be atomically re-frozen from the same reviewed checkpoint;
mixed old/new peers fail closed. `status` is not a current-cycle correlation
claim.

## Hostile coverage

The native tests cover:

- weak mode, symlink, hardlink, directory/non-regular type, and fixed production
  path. The native owner check is retained, but the unprivileged portable suite
  does not mutate file ownership;
- invalid record names, zero/noncanonical sizes, truncation, delimiter faults,
  more than 64 records, and more than 4 MiB of payload;
- record count, payload byte count, aggregate SHA-256, and final-tail mismatch;
- no marker, one marker, identical repeats, distinct markers, malformed
  lookalikes, arbitrary prefixes, exact console timestamps, exact panic syslog
  priority/timestamps, malformed timestamps, and invalid priorities;
- non-present snapshot consistency and rejection before session creation.

The host correlation tests cover invalid expected identities before device
discovery, stale-marker mismatch, all absence/ambiguity/match classes, exact
canonical hashing, and proof that neither the raw marker nor reversible tail is
emitted.

## Reproducible AArch64 evidence and timing

The pinned Alpine 15.2 ARM64 builder ran in the repository's private,
hash-pinned binfmt namespace. Two clean production builds were byte-identical:

- responder source: 104,279 bytes,
  `2da859afb4180b74b92bfb70c5c891aa8d365e26e13b6c2b77be1d1218186517`;
- production responder:
  `897a521c94557152a466f33c295f008100e3a183d84f94bf767c65bf49f91fea`;
- builder image ID:
  `a085070738e277a354bc22bb033f84c7c1568ae45a35ebf951ff27510fd7fd0e`;
- builder digest:
  `sha256:ab143fea42bd7780c2b69512397f9a33251ef9218c3258e5dd2995a905abddaa`.

The first direct ARM64 attempt failed in 0.65 seconds because the host-global
`qemu-aarch64` binfmt entry was absent. No host-global registration or
administrator credential was used; the private namespace restored the exact
gate. The clean-twin build plus full AArch64 QEMU PTY suite passed in 93.13
seconds.

Focused and full results before the exact-tree repository CI:

- fail-first snapshot/status mismatch: failed against the old responder in
  approximately 2.1 seconds;
- final six-test snapshot/lineage hostile subset: 6/6 pass in 2.222 seconds;
- final printk/correlation subsets: 2/2 pass in 2.345 seconds and 3/3 pass in
  0.003 seconds;
- native responder: 69/69 pass in 26.606 seconds (the prior 66-test baseline
  took 26.063 seconds);
- protocol reference: 52/52 pass in 0.340 seconds;
- stable recovery host controller: 41/41 pass in 0.139 seconds;
- minimal live-cycle parser/lifecycle: 81/81 pass in 77.706 seconds;
- production AArch64 responder/QEMU PTY gate: 69/69 pass with clean twins in
  93.13 seconds;
- first repository Linux `ci` attempt: failed after 363.10 seconds because the
  candidate-integration fixture still created only the old pstore status file;
  the production responder correctly refused the missing sealed snapshot;
- corrected candidate-integration regression: 2/2 pass in 3.120 seconds;
- added directory/non-regular snapshot regression: 1/1 pass in 2.362 seconds;
- second repository Linux `ci` attempt: failed after 437.60 seconds at the
  installed host-controller surface because the changed protocol reference
  retained its old exact SHA-256 pin;
- corrected installed reference pin regression: 1/1 pass in 0.009 seconds.

The exact-tree repository Linux `ci` rerun follows this report freeze; its
result and wall-clock timing are reported in the final checkpoint handoff so
the tested tree is not changed merely to describe its own test result.

## Review disposition

Independent standards review found no documented safety violation. Its native
marker-prefix duplication finding was fixed by sharing one constant;
duplicated host/reference validation remains intentional across the trust
boundary. Its final pass also caught overbroad protocol-compatibility wording
and overstated hostile path coverage. The documentation now requires an
atomic host/recovery re-freeze for the extended fixed schema, the portable
suite adds a non-regular directory case, and it no longer claims to mutate
file ownership. Independent specification review found and drove fixes for
console and panic printk formatting, stale-marker correlation, and raw-tail
redaction. Physical retention remains explicitly unproven rather than being
papered over by offline tests.

## Remaining uncertainty

- No offline test can prove the ramoops DRAM bytes survive the physical
  transition or that firmware does not clear/overwrite the reservation.
- `UNAVAILABLE`, `NO_RECORDS`, `NO_MARKER`, `AMBIGUOUS`, or even a matching
  marker with no fatal token is never proof that no crash occurred.
- The GENI route to GPIO18/19 remains a latent SoC route, not a proven
  connector or pad. Any future electrical probe remains receive-only because
  serial Magic SysRq is enabled.
- Stable recovery has not been rebuilt, signed, issued, or booted with this
  responder. Candidate creation and hardware execution remain separate safety
  decisions.

No phone, fastboot, ADB, ACM/NCM device, SSH credential, signing key,
administrator credential, reboot, storage access, flash, wipe, erase, slot
operation, or persistent installation was used.

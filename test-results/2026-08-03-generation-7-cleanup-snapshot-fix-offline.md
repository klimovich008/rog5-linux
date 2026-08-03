# Generation-7 cleanup snapshot correction — offline

Date: 2026-08-03

Result: **PASS offline**. The post-fallback cleanup deadline failure from the
consumed Generation-7 lifecycle is reproduced without phone access and fixed
without increasing its deadline or weakening any residue check.

## Root cause

One production `verify_host_clean(final=True)` observation took approximately
5.72 seconds. About 5.1 seconds came from launching roughly 23 sequential
`firewall-cmd` processes: one query for each drop-zone field followed by one
rich-rule query per host zone. The lifecycle allows 10 seconds for multiple
observations and requires one continuous clean second. Two otherwise-clean
observations therefore could not fit inside the deadline.

A hardware-free regression added 20 milliseconds to each mock firewalld call.
Before the correction it failed exactly as the live controller did:

```text
host cleanup deadline expired before the continuous clean dwell was proved
```

## Correction

The verifier now reads:

- one complete drop-zone snapshot;
- one canonical zone-name inventory; and
- one complete all-zone snapshot for forbidden lifecycle rich rules.

The consolidated parser still requires exact `DROP` target, empty lifecycle
fields, `masquerade: no`, canonical forwarding state, complete/unique zone
coverage, and absence of every exact temporary drop rule. It additionally
requires `icmp-block-inversion: no`. Unexpected, missing, duplicate, malformed,
unknown-zone, incomplete-zone, rich-rule, and active-interface states fail
closed. The installed firewalld must expose `forward:` and `masquerade:` in
`--list-all`; an older output format is rejected as incomplete.

The same read-only production observation now takes approximately 1.11
seconds. The 10-second deadline and one-second continuous dwell are unchanged.
The regression passes and still proves fallback intent resolution.

The deferred NetworkManager association error from the live run did not retain
its raw observation. The verifier therefore continues to accept only no UUID
or the one exact profile UUID after all address, ownership, interface, and
autoconnect checks pass. Future failures report only a non-sensitive shape:
`placeholder`, `duplicate-exact`, `mixed`, or `foreign`, plus line count.
Wrong values remain rejected and are never written to public evidence.

A subsequent source audit and byte-level host reproduction established that
NetworkManager 1.52.1 renders a NULL `GENERAL.CON-UUID` under `nmcli -g` as
one empty field plus newline. Python parses that as `[""]`, while the verifier
at this checkpoint accepted zero bytes (`[]`) or the exact UUID. The separate
[empty-field correction](2026-08-03-generation-7-nmcli-empty-field-fix-offline.md)
closes that exact mismatch without changing this snapshot correction's result.

## Verification

- red timing regression reproduced before the correction: pass;
- 59 complete lifecycle tests after the correction: pass;
- seven hostile consolidated-firewall snapshot cases: pass;
- empty, exact-stale, placeholder, duplicate-exact, mixed, and foreign UUID
  shapes: pass with only the first two accepted;
- consumed recovery inventory and retained twin-artifact gate: pass;
- 39 compatibility-oracle tests: pass;
- complete `scripts/host/test-repository-linux.sh ci` tier: pass;
- shell syntax, Python compilation, and `git diff --check`: pass; and
- read-only production cleanup observation: pass in approximately 1.11
  seconds.

The constrained Claude Opus review found no fail-open path. Its supported
hardening findings were applied: normalize active zone headers, require ICMP
block inversion off, test the rich-rule continuation path, test malformed and
incomplete snapshots, test unknown/missing zone snapshots, and cover all
privacy-preserving UUID classifications. Its compatibility observation is
recorded above; the behavior is deliberately fail-closed.

No credential, signing key, privileged host mutation, fastboot command, phone
interface, or phone storage was used. This correction does not issue or admit
a Generation-8 image.

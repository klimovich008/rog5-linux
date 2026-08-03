# Generation-7 NetworkManager empty-field correction — offline

Date: 2026-08-03

Result: **PASS offline**. The remaining Generation-7 deferred-profile
rejection is reproduced against the installed NetworkManager and corrected
without accepting a foreign connection, extending a timeout, or contacting
the phone.

## Root cause

The lifecycle asks `nmcli -g GENERAL.CON-UUID device show IFACE` after it has
already proved one exact recovery interface, no IPv4 address, NetworkManager
ownership disabled, the exact fallback profile bound to that interface, and
autoconnect disabled.

The installed host has NetworkManager `1.52.1-1.3`. Its exact upstream tag
`1.52.1`, commit `826e37b175368a9ce761a575adec520b83958742`, does the
following:

- `src/nmcli/devices.c` returns `NULL` for `GENERAL.CON-UUID` when the device
  has no active connection;
- `src/nmcli/nmcli.c` makes `-g` use terse output; and
- `src/nmcli/utils.c` renders an unset terse field as an empty string while
  still terminating the row with a newline.

A read-only probe of an existing disconnected host device confirmed the
installed behavior byte-for-byte:

```text
nmcli -g GENERAL.CON-UUID device show <disconnected-device> | od -An -tx1 -v
 0a
```

The same field in normal output renders as `--`. Python therefore parses the
actual `-g` output as `[""]`, not `[]` and not `["--"]`. The lifecycle mock
previously emitted zero bytes for the no-association case, so its successful
`[]` test did not represent production `nmcli` output. The unretained
Generation-7 value is not reconstructed, but this exact host/parser mismatch
reproduces the reported privacy-preserving `foreign count=1` shape.

## Correction

The deferred-profile verifier now accepts exactly three association shapes:

- `[]`, for a zero-byte compatible implementation;
- `[""]`, for NetworkManager 1.52.1's one empty `-g` field; or
- one exact fallback-profile UUID, as already permitted historical state.

The new empty-field allowance remains downstream of every existing physical
interface, product, firewall-zone, address, ownership, profile identity,
interface binding, and autoconnect check. `--`, duplicate empty or exact
values, foreign UUIDs, mixed values, addressed interfaces, managed
interfaces, and autoconnect-enabled profiles remain rejected.

## Verification

- installed NetworkManager byte-level read-only probe: pass;
- exact upstream source/tag/commit audit: pass;
- Python syntax and byte-to-line parser reproduction: pass;
- 61 lifecycle tests: pass;
- empty-field plus address residue: rejected;
- empty-field plus managed recovery interface: rejected;
- empty-field plus autoconnect enabled: rejected;
- `--`, duplicate empty, empty-plus-UUID, duplicate exact, mixed, and foreign
  shapes: rejected with non-sensitive classifications;
- central temporary-boot manifest: zero active `allow` rows;
- complete `scripts/host/test-repository-linux.sh ci` tier: pass; and
- `git diff --check`: pass.

The constrained Claude Opus review confirmed that the one-empty-field
allowance is sound and remains downstream of every strict state check. Its
supported findings added explicit duplicate-empty and mixed-empty
classifications and regression cases. One attempted follow-up emitted a fake
tool invocation despite the tool-free wrapper and was discarded; a smaller
self-contained retry returned `PASS`.

No credential, privileged host mutation, phone interface, fastboot command,
signing key, NFS service, or phone storage was used. This correction does not
issue, admit, or boot a Generation-8 artifact.

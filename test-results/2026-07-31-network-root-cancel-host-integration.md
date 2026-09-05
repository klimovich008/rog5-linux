# Network-root authenticated cancellation: host integration

Date: 2026-07-31

Result: **accepted on the real SteamOS host; no phone contact occurred**.

## Scope

The reviewed host controller was installed atomically during one bounded
SteamOS read-write window. Read-only protection was restored immediately.
The test used the exact deployment root and package identity, started the
fixed NFS server with the lifecycle's `start_new_session=True` process model,
waited for restricted NFSv4.2 readiness, and invoked the public launcher's
authenticated `cancel` action with the same ephemeral handoff token.

The token and complete logs remain in a mode-`0700` private evidence
directory outside Git.

## Defect found by integration

The first production-model cancellation stopped the root server and completed
its cleanup trap, but the server leader remained a zombie until its Python
parent called `wait()`. The cancel process required `/proc/PID` to disappear
before returning, while the parent waited for cancel to return. This produced
a bounded 30-second wait even though all NFS state was already clean.

The cancellation proof now accepts the exact leader's terminal `Z` or `X`
state only after the root-owned service record has disappeared. The PID,
start time, process group, session, root identity, PolicyKit caller, and token
checks still occur before signaling. A live or identity-changed process is
not accepted.

## Accepted rerun

The corrected rerun proved:

- the restricted server reached NFSv4.2 readiness;
- `cancel` succeeded through the exact public launcher even when
  `ROG5_NFS_TIMEOUT` was intentionally invalid, proving cancellation does not
  depend on serve-only configuration;
- the supervised parent reaped exit status 130;
- the server logged complete NFS and firewall cleanup;
- the service record, handoff marker, and export mount were absent;
- TCP 2049 and TCP/UDP 32767 had no listener;
- no export, NFS worker, or `rpc.mountd` process remained;
- the temporary PolicyKit rule was removed; and
- SteamOS read-only protection was enabled and installed/source server bytes
  matched.

This result validates only host process control and cleanup. It grants no
phone boot, flash, storage, or deployment acceptance.

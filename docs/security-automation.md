# Remote AI and personal-data boundary

The server can host Codex/Claude/OpenRouter clients and automation, but giving
an autonomous process unrestricted email and CV access is a much larger
security decision than enabling SSH.

## Staged account boundary

The Arch image now stages a locked `rog5-agent` system account. It has its own
group, `/usr/bin/nologin`, no password, no supplementary groups, no SSH
directory, and no access through the interactive `rog5` desktop account. Its
state root and reserved private-data directory are:

- `/var/lib/rog5-agent`, owned by `rog5-agent:rog5-agent`, mode `0700`;
- `/var/lib/rog5-agent/private`, with the same owner and mode; and
- `/var/lib/rog5-agent/chromium`, created by Chromium at runtime for the
  automation-only profile.

The headless Chromium service is disabled by default and must be started on
demand. It exposes CDP only on `127.0.0.1:9222`; has empty capability sets,
private devices and temporary files, no privilege escalation, and no access
to home directories; mounts the system read-only; and permits writes only
under `/var/lib/rog5-agent`. Its cgroup is limited to two CPUs, a 1.5 GiB
memory-high threshold, a 2 GiB hard memory cap, 512 MiB of swap, and 256
tasks. Low CPU/I/O weights yield to interactive and system work. Three starts
within five minutes trip systemd's start limiter, avoiding an unbounded crash
or OOM restart loop.

The verified image contains no API key, OAuth token, mailbox data, CV,
browser session, remote-desktop credential, or automation answer. The
`private` directory is an empty ownership boundary, not an encrypted secret
store. No model provider or personal account has been connected.

## Required runtime policy

- Use Tailscale/WireGuard or another authenticated private overlay; do not
  expose SSH, noVNC, ttyd, or browser-debug ports publicly.
- Keep key-only SSH on a dedicated key with a revocation plan.
- Add an encrypted runtime secret store before placing any credential or
  personal document on the device.
- Limit OAuth scopes to the smallest mailbox/folder and keep them read-only
  until a concrete write action is approved.
- Never store API keys, tokens, mailbox exports, CVs, application answers, or
  browser profiles in this repository or a build artifact.
- Require fresh user confirmation before connecting email, a model provider,
  or another external account.
- Require human approval before sending email, submitting an application,
  accepting legal terms, or disclosing personal data.
- Audit prompts, retrieved documents, proposed actions, approvals, and
  external results without recording secrets.
- Keep browser automation in the separate `rog5-agent` profile with no
  unrelated saved sessions.
- Measure the current cgroup limits on the phone before raising them; model
  clients need separate provider-rate, egress, thermal, and job-time limits.

The first runtime capability should be read, summarize, and draft. Automatic
submission remains a later, separately approved capability.

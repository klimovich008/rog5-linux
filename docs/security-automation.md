# Remote AI and personal-data boundary

The server can host Codex/Claude/OpenRouter clients and automation, but giving an autonomous process unrestricted email and CV access is a much larger security decision than enabling SSH.

Use these boundaries:

- Dedicated unprivileged `agent` user; no root shell and no raw device access.
- Tailscale/WireGuard or another authenticated private overlay; do not expose SSH, noVNC, ttyd, or browser-debug ports publicly.
- Key-only SSH with a dedicated key and a revocation plan.
- OAuth scopes limited to the smallest mailbox/folder and read-only until needed.
- Store CV/profile data in a dedicated directory readable only by the agent account.
- Never store API keys, tokens, mailbox exports, CVs, or application answers in this repository.
- Human approval before sending email, submitting an application, accepting legal terms, or disclosing personal data.
- Audit log of prompts, retrieved documents, proposed actions, approvals, and external results.
- Browser automation in a separate profile with no unrelated saved sessions.

The recommended first automation is read/summarize/draft. Automatic submission should be a later, explicitly approved capability.

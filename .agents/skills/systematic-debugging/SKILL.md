---
name: systematic-debugging
description: Investigate repeated, unexplained or cross-component ROG5 failures when explicitly invoked. Use focused reproduction and correction for a separately demonstrated defect.
---

# ROG5 systematic debugging

Project-local adaptation of obra/superpowers systematic-debugging; retained
upstream examples are reference material, not additional mandatory phases.
Invocation remains explicit-only in agents/openai.yaml. Do not invoke for
status, an already-proven one-line parser/identity/BusyBox fix, or routine tests.
Do not install companion skills.

## Choose the investigation size

- **Proven defect:** reproduce it at the actual failing boundary, add the
  smallest meaningful regression, correct it and run proportional checks.
  A separately unexplained incident does not block this fix.
- **Repeated, unexplained or cross-component failure:** use the investigation
  below. After two non-discriminating attempts at one boundary, stop issuing
  successors and reassess the evidence and hypotheses. Seek the bounded
  independent review specified by the active task if it can discriminate them.
- A count of failed fixes is not proof that the architecture is wrong.
  Change architecture only for demonstrated constraints and within task scope.

## Bounded investigation

1. State one question, the acceptance row it blocks, exact deployed inputs and
   the last proven boundary. Read current state and the relevant incident, not
   the entire project history. Separate observations, hypotheses and unknowns.
2. Reproduce with existing logs/fixtures and exact target runtime where possible.
   Inspect producer and consumer at the failing boundary. Do not infer deployed
   behavior from repository source, host GNU tools or a different kernel ABI.
3. Rank plausible explanations with supporting and contradicting evidence.
   Choose the smallest experiment with an expected discriminating result,
   deadline, permitted mutations, cleanup and evidence to retain.
4. Run that experiment under existing authority and safety gates. Record what
   actually happened, including absent data and ambiguous execution. Update
   the hypotheses; do not relabel an old failure as PASS.
5. Correct a demonstrated defect and cover it with a regression. For a necessary
   mitigation while the original cause is unknown, explicitly label the
   mitigation, its limits, verification and rollback. Do not claim root cause
   or qualification from symptom suppression.

These are reasoning aids, not a compulsory report template. Skip already-proven
steps and reuse unchanged evidence with its identity. Bounded diagnostics or
mitigations need not wait for proof of the original cause. Never alter an
active build or device coordinator's inputs.

## Stop conditions and scope

Preserve exact device/product/topology/slot, signed artifacts, battery/thermal,
storage-write scope and backups, independent watchdog/fallback, and permanent
non-retry of experimental post-COMMIT or ambiguous execution. Diagnostic
authority does not authorize another device, destructive storage, or a retry.

Use docs/release-acceptance.md as the definition of done and docs/development.md
for test tiers and experimental versus accepted-release operation. Fix a new
finding now only if it blocks qualification or materially threatens the
release; otherwise record it in the existing backlog. Reopen a completed
review only when new evidence materially changes its conclusion.

Collect only needed non-secret diagnostics; never dump whole environments,
credentials or private evidence into public logs. Do not add validation at
every layer automatically: retain checks at actual safety/trust boundaries
and add guards for demonstrated regressions.

## Optional reference techniques

Read only the applicable retained example: root-cause-tracing.md for tracing
a wrong input; condition-based-waiting.md for bounded readiness polling.
Their generic absolutes do not override the scope above. defense-in-depth.md,
pressure tests and creation notes remain historical material, not required
instructions. No universal phase count, four-layer validation mandate or
automatic architecture verdict applies.

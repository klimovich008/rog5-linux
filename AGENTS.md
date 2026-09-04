# ROG5 project guidance

Start with `docs/current-state.md`, `git status --short` and `git rev-parse HEAD`.
Read the latest relevant evidence and the matching sections of
`docs/development-lessons.md` only when the task needs them.
`docs/active-context.md` is a compatibility pointer, not another state ledger.

Use `scripts/host/rog5-dev` and `docs/development.md` for the development loop.
Prefer the smallest artifact and relevant tests. Freeze source before expensive
builds/CI; do not repeat completed checks on unchanged inputs. A hardware trial
must answer one specific question that offline tests cannot answer.

Preserve user changes, private evidence and the accepted server/rescue baseline.
Existing standing authorization applies to routine scoped work; destructive
storage remains separately reviewed. Keep exact identity, signing, storage,
power, fallback and post-COMMIT one-use guards.

Project skills supplement this guidance. `rog5-fast-loop` covers project changes;
`systematic-debugging` is explicit-only for repeated or cross-component unknown
failures. Do not install extra review/planning skills or edit global skills here.
Use bounded independent agents only when useful; one coordinator owns integration
and device access. Record results compactly in current state and one dated report.

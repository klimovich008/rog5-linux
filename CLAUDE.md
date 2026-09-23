@AGENTS.md

# Claude Code notes

Claude Code has coordinated this checkout since 2026-09-23. The Codex thread
`01a07ecb…` is idle; do not run a second coordinator against the phone.

## Orientation (cheap reads only)

- State: read only the generated block at the top of `docs/current-state.md`
  (`sed -n 1,8p`). The rest is a 300 KB historical log; grep it, never load it.
- Lessons: `grep -n` `docs/development-lessons.md` for the specific issue.
- Latest evidence: newest `test-results/2026-09-*.md`, plus `manifests/current-artifact.json`.
- Private state lives in `~/.local/state/rog5-*` (1000+ dirs). List it shallowly
  and never `grep -r` across it. Registered worktrees: `git worktree list`.
- Phone presence check (host-only, read-only): `lsusb | grep -i 0b05`.

## Fast offline testing

- Unit suites are standalone: `python3 scripts/device/test-<name>.py`. Most take under 10 s.
  The integrated tier is `scripts/host/rog5-dev test active` (about 750 s). Run it
  once on frozen source, not after each edit.
- Target shell code must run under the real ARM64 busybox. Extract `bin/busybox`
  and `lib/ld-musl-aarch64.so.1` from the target archive into a scratch dir, then
  `QEMU_LD_PREFIX=<dir> ROG5_TEST_QEMU=/usr/bin/qemu-aarch64-static ROG5_TEST_BUSYBOX=<dir>/bin/busybox python3 <test>`.
- Controller sources are hash-pinned in a chain. Before editing a pinned file,
  find its consumers with `git grep -l $(git show HEAD:<file> | sha256sum | cut -c1-64)`.
  Pins live in sources (`display-component.py` `SOURCE_PINS`), fixtures
  (`scripts/device/fixtures/*/source-pins.json`), controller patches
  (`patches/display-controller/*.patch`, which are themselves pinned downstream)
  and dated test-results. Never rewrite dated test-results. Re-pin forward and
  rerun every consumer suite, comparing against a clean `git worktree` of HEAD.

## Advisers

Oracle Pro (ChatGPT browser) is the standing adviser for hard architecture calls,
per AGENTS.md. The `oracle` CLI is installed. The Claude session has no Oracle MCP.
The ChatGPT quota ran out on 2026-09-22. A second opinion is also available
through the `codex:rescue` skill.

## Safety

`.claude/settings.json` denies direct fastboot/adb/dd-to-device commands. Physical
trials go through the reviewed controllers only, after fresh Ready (see AGENTS.md).

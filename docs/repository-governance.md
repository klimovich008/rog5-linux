# Repository governance prepared for maintainer review

These files prepare policy; this task does not change GitHub branch protection,
repository settings, production keys or publication permissions.

Protect `main`, prohibit force pushes and require pull requests. Require checks
on the actual proposed head and merge result: `head-exact`, `merge-compat`,
`board-production`, `panel-driver` and `qemu-system`. The board job must report an
explicit irrelevant-change selection on documentation/userspace edits; a selected
board build cannot succeed without source, compilation and its required tools.
Generic ARM64 QEMU proves userspace/initramfs behavior, not SM8350 hardware.
Historical candidate publication has no release or hardware-execution authority.

A small project may have one maintainer; CODEOWNERS routes review without
pretending independent review occurred. Seek a second technically qualified
reviewer for hardware-affecting changes, signing/admission boundaries, persistent
state and storage. Do not push those changes directly to protected main.
Repository policy cannot replace exact-device, one-use and signed fallback guards.
Never allow a failed required check to be bypassed merely to publish a checkpoint.

Review Actions dependency updates against upstream immutable commits. Record the
runner image and installed package/tool inventory with every CI build. A pinned
container digest is preferable once that environment has been qualified; a
mutable hosted runner plus recorded versions is traceability, not hermeticity.

Active mobile device configuration belongs in an ignored `*.local.json` file,
mode 0600, using [the redacted example](../configs/devices/example.json). Identity
is an input to existing exact-image/claim comparisons, never authorization.
Historical sealed claims, generated V27 fixtures and frozen private controllers
retain their original identity bytes and hashes. Migration of those legacy
consumers requires a newly qualified source closure; they must not silently
inherit a different unit from a default profile. No historical identities were
rewritten or made replayable in this task.

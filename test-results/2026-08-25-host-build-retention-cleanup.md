# Host build retention cleanup

- Trigger: `/home` had 3.0 GB free after the reproducible local-root milestone.
- Scope: eleven top-level `build/` trees with no tracked reference, artifact
  manifest row, active process, or mount dependency.
- Removed: one aborted power observer, five obsolete userdata-reset wrappers,
  one obsolete storage-preflight wrapper, one stale network-root kernel rebuild,
  one cache-integration fixture, and two superseded fast-attest outputs.
- Removal used individual KDE Trash entries and permanently removed only the
  exact newly-created entries. Pre-existing user Trash content was untouched.
- Reclaimed: 77,096,943,616 bytes. `/home` free space increased to 80,224,440,320
  bytes (about 75 GiB).
- Retained: current signed candidates, stable wrapper cache, source trees needed
  by current builds, phone backups, private evidence, and the VCNL worktree.

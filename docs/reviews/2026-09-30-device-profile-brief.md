# Review brief: per-phone device profile in the boot sources (2026-09-30)

Read-only review requested from GPT-6.1-Sol. Repository:
the development checkout (uncommitted working-tree
changes; `git diff` and `git status` show them). Nothing was installed or
booted; the reference phone still runs the old sources.

## Goal

The boot chain accepted exactly one phone: the reference ZS673KS (256 GB
UFS, 12 GB RAM). The UFS geometry, the filesystem UUIDs, the sealed root's
hashes and a 192 GiB overlay cap were literals spread through
`initramfs/persistent-root-init` (3.2k lines, the production init),
`initramfs/persistent-root-attest`, `initramfs/persistent-service-state`,
`initramfs/persistent-slotb-loader-init` and `initramfs/recovery-init` (both
in the flashed slot-B wrapper), and `scripts/device/stage-persistent-root-overlay.sh`.
Other ROG Phone 5 variants (128 GB, 512 GB; 8/16/18 GB RAM) differ in all of
the geometry values. The change moves every such value into one marked
block per file:

```
# BEGIN ROG5 DEVICE PROFILE
rog5_ufs_node_count=117
...
# END ROG5 DEVICE PROFILE
```

and makes the rest of each script use the `rog5_*` names. The block values
are the reference phone's; `scripts/host/rog5-device-profile render` rewrites
them from another profile (validated `KEY=VALUE` file:
`configs/device-profiles/reference.env` is the reference). The production
ramdisk builder renders the init, attestor and state helper when
`ROG5_DEVICE_PROFILE` is set. The rendered values end up inside the
Ed25519-signed bundle, as the literals did.

One behaviour change on the reference phone: the overlay image cap is no
longer a fixed 192 GiB (206158430208) but derived from the userdata size:
`userdata - 4 GiB (/persist image) - max(2 GiB, userdata/32)`, whole MiB,
rendered as `rog5_overlay_max_bytes` (198567788544 = 184.9 GiB on the
reference, whose overlay file is 182 GiB = 195421011968 bytes). The minimum
(16 GiB), whole-MiB rule, loop size == file size, owner/mode/link checks,
UUID and label checks are unchanged.

Other changes in the same diff:

- `scripts/device/stage-persistent-root-overlay.sh`: profile block;
  `fallocate` instead of `truncate` for the new image (fully allocated); a
  restartable partial may be empty or full-size; bundle-name check relaxed to
  the loader's `valid_bundle_name` regex (it required the historical
  `persistent-native-root-*`).
- `scripts/device/stage-persistent-service-state.sh`: restored from the
  archive tag, profile block, manifest identity checked after writing, no
  longer requires the legacy `rog5/images` directory.
- `scripts/host/install-default-kernel.py`: `--profile` (p24/p23 UUIDs and
  p24 size) and `--expected-trust-sha256` (default: the reference key).
- `scripts/host/package-production-ram-trial.py`: the signing key must match
  the raw key inside the recovery base (`etc/rog5/recovery-bundle-ed25519.pub`)
  instead of a pinned hash (same result for the reference: the recovery base
  holds that key).
- `scripts/host/production-ram-trial.py`: SSH key, known_hosts and USB
  interface can come from the environment or `~/.config/rog5/`.
- New: `scripts/host/rog5-device-profile` (collect/plan/make/check/render),
  `scripts/host/rog5-dtb-memory` (copy a phone's RAM map into board.dtb; refuse
  a no-map reservation outside RAM), `scripts/host/rog5-build-rootfs`,
  `scripts/device/rog5-install-userspace`, `configs/rootfs/*`, tests
  `scripts/host/test-rog5-device-profile.py`, `test-rog5-dtb-memory.py`,
  `scripts/device/test-rog5-install-userspace.py`; updated static-contract
  tests.

## Evidence so far

- Rendering every profiled source with the reference profile is the identity
  (test). No reference literal remains outside a block (test).
- `rog5-device-profile make` from a live read-only inventory of the reference
  phone plus the reference root identity reproduces `reference.env` exactly.
- `plan` on the stock layout reproduces the reference p23/p24 geometry.
- Existing suites pass after updating static-contract strings:
  test-persistent-root-{initramfs,overlay-runtime,storage-resolution},
  test-persistent-service-state-runtime, test-persistent-slotb-loader,
  test-persistent-slotb-recovery-loader, test-usb-storage-scope,
  test-recovery-init-policy, test-install-default-kernel, test-rog5-make-bundle,
  test-production-ram-trial and the rest of the boot-chain list.

## Questions

1. Did the refactor change any check's meaning for the reference phone
   (other than the overlay cap)? Look for a value moved into a variable that
   is now evaluated at a different time, under `set -u`, in a subshell, in a
   function extracted by tests, or in code run by a different shell (the
   wrapper's BusyBox ash, the root's bash for the attestor).
2. Is the derived overlay cap safe and sufficient? Is there a case where the
   new cap refuses a legitimately grown reference overlay, or accepts an image
   that cannot be backed by the filesystem? Should the boot instead compare
   with the ext4 size of userdata or require a non-sparse file?
3. Is rendering safe: can a malicious or mistaken profile inject shell code
   (values are restricted to `[0-9a-f-]`), or skip a check by leaving a key
   out (render refuses unknown keys; missing keys fail validation)?
4. Does anything still pin the reference phone that the profile does not
   cover (in the boot path: loader, recovery-init, init, attest, state
   helper, update tool, installer)?
5. `stage-persistent-root-overlay.sh` with `fallocate` and the relaxed partial
   rule: any safety regression?
6. `package-production-ram-trial.py` taking the trust key from the recovery
   base: any way to sign with a key the wrapper will not accept, or to accept
   a wrong base?
7. Anything a reviewer would block before this goes into a RAM trial?

Answer with findings ordered by severity, each with file:line and a
concrete fix.

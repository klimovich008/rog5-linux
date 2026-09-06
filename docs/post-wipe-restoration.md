# Post-wipe Linux restoration bundle

This private bundle preserves enough verified host material to rebuild the
ROG Phone 5 Linux environment after a stock-recovery factory reset. It does
not contain a full `userdata` snapshot and therefore cannot reproduce the
previous phone filesystem byte-for-byte.

## What the bundle restores

- The deployment-key-bound Arch root can be materialized again from the exact
  536,746,495-byte source archive.
- The pre-stock Alpine slot-B boot image is retained for provenance and for a
  later reviewed recovery installation.
- The exact stock WW `18.0840.2202.231` slot-B boot image is retained.
- All 107 previously captured small partitions, all 14 GPT ranges, the exact
  storage inventory, and their existing manifests are retained privately.
- The repository is included as a Git bundle at the exact recorded commit, so
  the image materializer, storage verifier, recovery builders, and history do
  not depend on GitHub availability.

The bundle deliberately contains no private SSH key, signing key, token, or
credential. Existing credentials remain in their separately protected host
locations.

## Verify before a wipe

Run from the host:

```sh
/home/deck/.local/state/rog5-post-wipe-restoration-20260817-r1/VERIFY.sh
```

The verifier checks the exact Arch, Alpine-boot, and stock-boot identities;
the bundle manifest; the exact Git head; all retained partition and GPT
backups; and seven sparse offline GPT restoration rehearsals. Do not wipe if
any check fails.

## Important limitation

A factory reset reformats `userdata`. That removes the installed Alpine root,
the current 16 GiB `/rog5/images/arch-local-a.ext4`, its controlled marker,
and all other phone-side service state. The retained Arch source archive can
recreate a functional Arch root, but it does not recreate every later mutable
file or the previous Alpine filesystem.

Do not flash the Alpine boot image by itself after a wipe. It expects an
Alpine root on `userdata`; without that root it is not a usable fallback.

The existing unissued Storage Stage-1 candidate is also invalid after a
factory reset because its filesystem and source-image identities describe the
pre-wipe state. Rebuild and re-review storage candidates from a fresh inventory.

## Functional restoration sequence

1. Verify this bundle and retain the existing stock slot-B recovery route.
2. Factory-reset only through the matched stock recovery; do not erase GPT,
   bootloader, firmware, calibration, modem/EFS, persist, or AVB partitions.
3. Boot stock Android and prove sustained positive charging, safe temperature,
   and `battery-soc-ok=yes` before further storage work.
4. Collect a fresh read-only UFS/GPT/filesystem inventory and compare every
   protected partition with `metadata/storage-inventory-v3.json`.
5. Check out the recorded source offline if needed:

   ```sh
   git clone source/rog5-linux.git.bundle rog5-linux-restored
   ```

6. Build a fresh RAM-only recovery and a new storage plan for the post-wipe
   geometry. Do not reuse a consumed candidate or the pre-wipe Stage-1 claim.
7. Materialize Arch from `inputs/arch-headless-root.tar.gz`, verify its tree
   seal, and install it only into the newly reviewed Linux image or partition.
8. Re-establish key-only SSH using the separately protected deployment key;
   the private key is intentionally absent from this bundle.
9. Preserve stock recovery until repeated standalone Arch boots and a separate
   recovery test pass.

This sequence restores a working Linux server. It is not a promise of an
exact rollback to the old `userdata` bytes.

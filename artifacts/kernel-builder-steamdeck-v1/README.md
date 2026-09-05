# Steam Deck kernel-builder rootfs manifest

`rootfs-manifest.tsv.gz` is the compressed normalized stream behind the
Steam Deck builder's rootfs identity. It contains regular-file SHA-256 values
and path/type/mode/owner/symlink metadata from the container image; it
contains no host files, credentials, phone data, or signing material.

```text
manifest lines:       24145
manifest sha256:      a82749a50365d864714594cc40ce27a28af4f132ef0e540946338b4681bf1fda
gzip sha256:          7680447aa94ed11de4313347face7b7b2168d73c92b243f733eeb656cf6bd94b
gzip bytes:           559326
```

Verify the tracked artifact:

```sh
gzip -t artifacts/kernel-builder-steamdeck-v1/rootfs-manifest.tsv.gz
gzip -dc artifacts/kernel-builder-steamdeck-v1/rootfs-manifest.tsv.gz |
  sha256sum
```

Generate a current image's uncompressed stream for comparison:

```sh
scripts/host/bootstrap-kernel-builder.sh manifest \
  localhost/rog5-kernel-builder:ubuntu-24.04
```

The manifest format deliberately remains byte-compatible with the rootfs
identity algorithm recorded on 2026-07-29.

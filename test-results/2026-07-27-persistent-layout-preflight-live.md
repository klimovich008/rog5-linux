# Persistent native-Linux layout — read-only preflight

Date: 2026-07-27

Result: **PASS read-only design preflight / HOLD all writes**

## Outcome

The installed Alpine fallback uses exact ext4 `userdata` at `/dev/sda23`.
The current boot slot is `_b`, and no boot-critical A/B partition is mounted.
The measured layout supports a non-repartitioning migration: preserve Alpine
at the filesystem root and add versioned Arch roots only below `/rog5`.

The live inspector returned:

```text
PASS persistent layout mode=live slot=_b protected_slot=_b root=/dev/sda23 filesystem=ext4 userdata_bytes=243766472704 free_kib=197263136 plan=no-repartition
```

This corresponds to about 228 GiB of partition capacity and 189 GiB currently
available in the ext4 filesystem.

## Test-first control

The missing-inspector contract failed first at commit `f9266d1`:

```text
FAIL missing persistent layout inspector
```

The completed fixture suite then accepted the exact measured map and rejected
eight independent mutations:

1. changed `userdata` size;
2. changed `userdata` GPT name;
3. a different fallback root device;
4. invalid slot suffix;
5. a mounted boot-critical partition;
6. less than 16 GiB free;
7. missing fallback root marker; and
8. changed `boot_b` GPT name.

ShellCheck and whitespace validation pass. The Linux-rootfs aggregate now
delegates this test.

| Control | SHA-256 |
|---|---|
| read-only inspector | `967e45b7797a68ddfd06b5e69f9fcb608b2202013b54d7e560d3a5e1b01534b3` |
| mutation suite | `7962a226949f4d3cbe80832fea0c7237a4a8f98e72e8fcea4cf5afc493189665` |
| Linux-rootfs aggregate | `9cb70bfc36789b46ae3ebe4bd46edeaa171c2aa3b9c292c9b0e4fd0dbe66107e` |

## Safety boundary

The inspector reads procfs, sysfs, one existing marker, and `df` metadata. It
does not open a block device, read partition contents, mount or unmount
anything, invoke a filesystem or partition tool, change the selected slot,
load kexec, reboot, use fastboot/ADB, or write to the phone.

Strict pinned SSH streamed the script to the existing shell; no executable or
evidence file was installed remotely. The phone remained on Alpine with its
screen off and remote tunnel active.

## Accepted design

The design is documented in
[`docs/persistent-storage.md`](../docs/persistent-storage.md):

- no repartitioning;
- preserve active fallback slot B;
- versioned Arch roots under `/rog5/roots`;
- hash-pinned boot candidates under `/rog5/boot`;
- one-shot kexec from Alpine into native Linux 7.x;
- read-only `ro,noload` UFS plus tmpfs-overlay acceptance before any mainline
  storage write;
- bounded directory-only write testing before a persistent Arch root; and
- atomic A/B root-generation promotion with no automatic retry.

The next gate is a host-side, deterministic root-staging package. Creating
`/rog5` or sending an archive to the phone remains HOLD pending a fresh
persistent-write instruction.

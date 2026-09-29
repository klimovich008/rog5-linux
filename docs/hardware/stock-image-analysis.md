# Stock-image analysis

Stock ASUS images are valuable compatibility evidence for the Linux port, but
they are not recoverable kernel source. The useful workflow is reproducible
unpacking, selective device-tree decompilation, and comparison against the
ASUS GPL release and upstream Linux.

This track is offline. It does not require a phone boot, partition read, or
flash.

## What it can answer

| Input | Evidence recovered | Port work it informs |
|---|---|---|
| `boot.img` | Android boot header, kernel identity/config, ramdisk, boot arguments | wrapper compatibility, kernel options, early init |
| `vendor_boot.img` | vendor ramdisk fragments, DTB placement, init and uevent rules | module loading, device permissions, firmware paths |
| `dtbo.img` | overlay table, board/revision selectors, overlay DTBs | board variants, display, touch, regulators, GPIO |
| `vbmeta*.img` | AVB descriptors, chained partitions, sizes and rollback metadata | reproducible non-flashing image verification |
| `vendor_dlkm` / module tree | module names, dependencies, aliases, vermagic, parameters | driver inventory and load order |
| `vendor`, `odm`, firmware trees | requested firmware names and userspace configuration | GPU, DSP, Wi-Fi, modem, panel and charging prerequisites |
| OTA `payload.bin` | a version-matched set of the preceding partition images | repeatable stock-version comparisons |

High-value comparisons for the ROG Phone 5 are:

1. reserved-memory ownership and `no-map` policy;
2. regulators, clocks, interconnects, power domains and reset lines;
3. GPU/GMU/SMMU firmware names and memory regions;
4. DSI panel modes, touch GPIO/IRQ wiring and the Pixelworks bridge boundary;
5. PCIe0/WCN6855 power sequencing and firmware paths;
6. USB role, UFS, PMIC GLINK, remoteproc and thermal dependencies; and
7. module aliases, parameters and userspace coldplug order.

## What it cannot do

Decompilation cannot reconstruct ASUS's original C source, commit history,
comments, build system, proprietary bridge drivers, or firmware. Decompiled
DTS also loses labels, includes, macros, comments and source organization.
Treat it as observed hardware data, not as code to copy wholesale.

The maintainable implementation remains:

- upstream Linux and upstream bindings;
- the corresponding ASUS GPL source where legally available;
- small reviewed board-specific DTS and driver changes; and
- behavior verified by isolated hardware tests.

## Private-input boundary

Keep all original images, extracted ramdisks, raw DTS, proprietary modules and
firmware outside Git. Also keep complete command lines, serials, partition
GUIDs, calibration data, Wi-Fi identifiers and panel command payloads out of
public reports.

The repository may contain only:

- extraction scripts and pinned tool identities;
- source image SHA-256 values when they do not identify private user data;
- normalized, redacted inventories;
- narrowly selected hardware facts needed by the port; and
- diffs against public ASUS GPL or upstream source.

Do not use a live partition dump when an official version-matched ASUS package
or OTA provides the same input.

## Reproducible workflow

1. Create a caller-owned private work directory outside the repository with
   mode `0700`.
2. Hash every original input before extraction.
3. Record the ASUS firmware/OTA version and extraction-tool versions.
4. Use AOSP `unpack_bootimg.py` for `boot` and `vendor_boot`, `avbtool
   info_image` for AVB metadata, and the matching AOSP DTBO tooling for the
   overlay table.
5. Hash every extracted kernel, ramdisk, DTB and DTBO.
6. Decompile DTBs with a pinned `dtc`, retaining warnings as evidence.
7. Normalize only the properties needed for the subsystem under study.
8. Compare each fact across stock runtime data, stock images, ASUS GPL source,
   upstream SM8350 DTS, and the current ROG5 candidate.
9. Repeat extraction into a second empty directory and require identical
   normalized output.
10. Commit only the redacted comparison and its tests.

Suggested private layout:

```text
rog5-stock-private/
  inputs/
  extraction-a/
  extraction-b/
  normalized/
  SHA256SUMS
  tool-versions.txt
```

## Acceptance gate

A stock-derived fact may enter the board port only when it:

- is reproduced from two clean extractions;
- is scoped to one subsystem;
- agrees with runtime evidence or has an explicit reason not to;
- is representable using upstream bindings;
- passes schema and mutation tests; and
- does not copy proprietary payloads into Git or a public build artifact.

The first concrete deliverable should be a redacted matrix for reserved memory,
GPU/GMU/SMMU, display/touch, and WCN6855. It should resolve open hardware
questions before any new live candidate is built.

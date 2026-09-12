# Licensing and provenance inventory

No project-wide license is selected by this repair. Existing license notices
are retained. Distribution review is incomplete; a hash proves identity, not
permission to redistribute. This is a source inventory, not a legal conclusion.

| Material | Available provenance | Unresolved work |
| --- | --- | --- |
| Linux patches | Exact v7.1.4 base and ordered patch series; file-level upstream notices | Review authorship and derivative-work notices for each added hunk before distribution |
| DTS and overlays | Existing file notices and qualified vendor/board source references | Establish missing file-level licensing; do not infer a license from directory placement |
| AMS678 generated driver | Generated-code notice, vendor-derived command sequences, existing GPL marker | Generated copyright FIXME remains unresolved; establish generator/version and correct attribution |
| AMS678 binding | Existing dual GPL-2.0-only/BSD-2-Clause SPDX declaration | Verify authorship history; no new blanket declaration added |
| GENI test extracts | Exact v7.1.4 I2C/GENI source excerpts retain their upstream file notices; source comparison is executable | Preserve those notices independently of the local boundary harness |
| Local touch binding | Newly authored disabled-prototype schema, with the existing kernel-binding dual SPDX convention; properties traced to the local driver and archived board mapping | Local validation contract, not an upstream submission or redistribution review of vendor binaries |
| Vendor panel commands | Retained ASUS msm-5.4 panel and Iris source paths; brightness derivation documented by the panel repair | Confirm redistribution provenance of extracted sequences separately from functional correctness |
| Firmware references | Exact firmware inventories and external source references | Inventory each firmware license and redistribution terms; reference does not grant permission |
| Tracked binaries and archives | Existing checksums plus artifact-set inventory | Missing source/toolchain/command records remain BLOCKED, even when binary identity is known |
| Third-party tools | Existing per-project notices, e.g. third_party/iw/COPYING | Preserve upstream notices and package metadata for each distributed tool |

See [artifact retention](artifact-retention.md) for the forward large-artifact
policy. Preserve sealed historical objects; do not rewrite Git history to change
notices or remove large objects. Add SPDX only after provenance establishes the
appropriate identifier. The new GENI excerpts preserve source notices; the local
touch schema has its own declaration. Neither selects a project-wide license.

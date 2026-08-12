# Generation 34 QMP-UFS no-bind module-load control

Status: **offline checkpoint passed; unbooted; one RAM-only use only; never flash**.

Generation 34 is the smallest discriminator after Generation 33. It reuses
the exact Image, QMP-UFS module, other packaged modules, and initramfs. A tested
one-property overlay changes only `&ufs_mem_phy` to `status = "disabled"`.
The UFS host stays enabled, but its module is absent, so the exact QMP-UFS
module may relocate and register its driver without binding or running
`qmp_ufs_probe`. No UFS controller can enumerate and no storage operation is
implemented in this cycle.

The hostile DT test proves that the overlay changes exactly one node status,
preserves all QMP-UFS resources and supplies, leaves the UFS host enabled, and
refuses an unexpected second node mutation. The live runner requires 12 seconds
of unchanged anchored NCM state and classifies a USB disappearance that races a
NetworkManager query.

| Artifact | SHA-256 |
|---|---|
| reused kernel Image | `53d42da77b65a37149bd269c5d71d7855a7edb51748cb2da478bff5cb5f95203` |
| one-property PHY-disabled DTB | `fff378b15088d752ffca8268c27e298fe97f593e89904b44f50501291e32db82` |
| reused initramfs | `e14253847f2acb7730a22e01cbad0f5f61147a9bc2b82365706fc5adf078f723` |
| signed manifest | `30fb6c355aa8e34097592cf4b33fe7ae4c4193a4c85ae36744c90778f1818cb7` |
| manifest signature | `022e1177cd4c1dcb1c7c26bf67f888ea8abdfc73143defe3390de5f65aa3a191` |
| Generation 34 AVB wrapper | `d314b940d8dbecf63334a8f425719200852d25af364838db24f9e8aebecffadd` |
| AVB generation record | `409ac124585987942a64ee0693687ce209691d9c3d8ec4e9f72578398efe9c58` |

Clean bundle twins and AVB generation twins are byte-identical. The cycle is
RAM-only, keeps the known-good fallback unchanged, and cannot access phone
storage.

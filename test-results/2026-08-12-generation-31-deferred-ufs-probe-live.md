# Generation 31 deferred Qualcomm UFS-host probe live result

Status: **consumed; target USB absent; exact fallback passed; never retry**.

The sole RAM-only cycle used the clean-twin Generation 31 Image, the retained
UFS-enabled DTB, and the USB-first persistent-root initramfs containing the
exact deferred three-module UFS host chain. The recovery controller accepted
one COMMIT and recorded its transmitted intent. No `ROG5 persistent root` USB
identity appeared before the known-good Alpine fallback returned.

Exact retained host timestamps (+0200):

- boot claim: 17:55:58.297;
- recovery boot request: 17:56:28.076;
- recovery USB anchor: 17:56:28.711;
- five-phase recovery progress capture complete: 17:56:47.898;
- bundle transfer and cleanup complete: 17:56:52.849;
- COMMIT/transmitted record: 17:56:53.634;
- exact Alpine USB appearance: 17:57:18;
- fallback profile restoration: 17:57:21.230;
- strict fallback identity: 17:57:23.498;
- intent resolution as `FALLBACK_RETURNED`: 17:57:26.259.

The fallback record proved the pinned Alpine identity at the anchored USB path
and a maximum reported thermal value of 42.1 °C. Pstore was empty, which
remains inconclusive. A read-only fallback `dmesg` showed the Haven watchdog
initialized and retained historical PMIC reset records, but no record uniquely
classifies this cycle's reset. Because target USB never appeared, the evidence
cannot identify the exact failing target instruction.

No target-side filesystem operation or phone-storage write was observed. The
cycle disproves the narrower hypothesis that deferring only UFS core, platform
glue, and the Qualcomm host is sufficient to reach initramfs USB. Compared
with Generation 29, the remaining UFS-specific built-in layer is the QMP-UFS
PHY. Generation 32 therefore changes only that layer from built-in to a fourth
explicit module loaded after stable target NCM.

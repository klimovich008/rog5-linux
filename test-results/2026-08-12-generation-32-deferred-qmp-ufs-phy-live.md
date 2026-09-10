# Generation 32 deferred QMP-UFS PHY live result

Status: **consumed; stable target NCM passed; later target loss; exact fallback passed; never retry**.

The sole RAM-only cycle used the clean-twin Generation 32 kernel, UFS-enabled
DTB, and explicit four-module QMP-UFS/UFS chain. Moving
`CONFIG_PHY_QCOM_QMP_UFS` from built-in to a sealed module allowed the mainline
initramfs to expose the exact `ROG5 persistent root` NCM product. This proves
that the previously built-in QMP-UFS PHY registration/probe was inside the
pre-init failure boundary seen in Generations 30 and 31.

Exact retained host events (+0200):

- boot claim: 19:26:11.485;
- recovery boot completed: 19:26:42.769;
- recovery USB anchor: 19:26:43.400;
- bundle transfer and recovery progress completed: 19:27:07.730;
- COMMIT/transmitted record: 19:27:08.639;
- target NCM enumeration: 19:27:09.120;
- stable target NCM lifecycle milestone: 19:27:12.057, 60.616 seconds from
  lifecycle start;
- target USB disconnect: 19:27:20.395, 11.276 seconds after enumeration;
- Alpine USB enumeration: 19:27:38.558;
- fallback profile restoration: 19:27:40.838;
- strict fallback identity: 19:27:43.077;
- intent resolution as `FALLBACK_RETURNED`: 19:27:46.160.

The retained transport does not identify which of the four explicit module
transitions was last reached. The target disconnected too early to prove that
the shell's 20-second `ufs-module` failure delay executed, so a blocked PHY
insertion, a later module transition, or the inherited reset boundary remains
possible. Generation 33 therefore reuses the exact kernel and modules, inserts
only `phy-qcom-qmp-ufs.ko`, and requires 12 seconds of exact post-insertion NCM
survival before its deliberate fallback.

The pinned Alpine identity returned on the anchored USB path with a maximum
reported thermal value of 41.8 °C. Pstore was empty and remains inconclusive;
the fallback exposed no cycle-specific PMIC reset-reason field. No filesystem,
block-device, or phone-storage operation occurred.

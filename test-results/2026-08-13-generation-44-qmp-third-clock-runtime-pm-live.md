# Generation 44 QMP-UFS three-clock runtime-PM live result

Status: **PASS; consumed; exact fallback passed; never retry or flash**.

Generation 44 temporarily booted the exact signed RAM-only candidate once.
The generated initramfs verified release `7.1.4-gc732b0b41d8d`, loaded only
`phy-qcom-qmp-ufs.ko`, confirmed `phy_qcom_qmp_ufs` in `/proc/modules`, and
sent the exact target-originated completion record from `169.254.77.2`.

The SM8350 diagnostic probe crossed `rx_symbol_0`, `rx_symbol_1`, and
`tx_symbol_0` fixed-rate clock registration with the generic CCF runtime-PM
correction. It returned before OF clock-provider publication, PHY creation,
or provider registration. UFS core, platform, and host modules remained
unloaded, so no UFS enumeration or phone-storage access was possible.

Target NCM became stable in 62.793 seconds and preserved the exact USB
identity, address, route, NetworkManager state, and non-drop firewall state
for a further 12.488 seconds after the module proof. Exact Alpine fallback
then returned with strict identity, profile restoration, host cleanup, and
durable intent resolution as `FALLBACK_RETURNED`. Maximum fallback
temperature was 40.5 degrees C.

Fallback pstore and the queried PMIC PON paths were empty. Those observations
are inconclusive and are not treated as proof that no crash or reset occurred.
The positive target record and stable control window establish the three-clock
boundary independently.

The next discriminator may publish the OF clock provider only if it also
registers the paired devm cleanup action before returning ahead of PHY
creation. Generation 44's exact claim is irreversibly consumed.

Retained private evidence:
`/home/deck/.local/state/rog5-generation44-live-20260813.x1FZOUXg`.

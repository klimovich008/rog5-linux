# Wi-Fi crypto availability probe

Test-only module: use under QEMU, not as part of the phone's runtime payload.
It allocates and frees SHA-256, CMAC, CCM, GCM and CTR transforms without keys,
packets or device access. It caught dependencies missing from the narrow module
package even though ath11k and cfg80211 themselves loaded successfully.

Copy this directory into temporary build output and compile it as an external
module against the exact retained kernel header/vmlinux/BTF kit. Boot that same
Image in QEMU with `-nic none`, no disk devices, the matching module package,
the canonical `configs/kernel/rog5-native-wifi-module-roots`, and `iw`.

Load the canonical module roots, then this probe. Require five
`ROG5_WIFI_CRYPTO_PASS` records and no failure. Separately load the signed
regulatory database and request a test-only country: it must succeed. Flip one
data byte while preserving its signature in a separate fixture; the database
must be rejected and the world domain retained. Never disable regulatory
signature checks to make this test pass.

# Generation 44 QMP-UFS third-clock runtime-PM offline checkpoint

Status: **unbooted RAM-only candidate; no phone-storage access; never flash**.

Generation 43's NCM-only success criterion was invalidated after exact-input
review proved that its initramfs still expected the Generation 42 kernel
release. Generation 44 fixes that concrete identity defect by substituting the
exact generated release into the initramfs. It also replaces the ambiguous
NCM-only completion signal with an exact target-originated record emitted only
after `insmod` returns and `/proc/modules` confirms `phy_qcom_qmp_ufs`.

The SM8350-only QMP-UFS diagnostic branch retains the generic CCF runtime-PM
correction, crosses the unresolved second and third fixed-rate symbol clocks,
and returns after `tx_symbol_0`. It still returns before OF clock-provider
publication, PHY creation, or provider registration. UFS core, platform, and
host modules remain outside the load path, so this candidate cannot enumerate
or access phone storage.

Exact clean-twin result:

- source commit: `c732b0b41d8d5fd2f4ccd76e1f4dbff8ff06c087`
- source tree: `be9d0f11638dc0ea300a31ab176955441dda1ca9`
- release: `7.1.4-gc732b0b41d8d`
- config SHA-256: `b959774825e2bca7c634e55cd00e838121fde8d95fd214ffeead732ce92e35e6`
- Image SHA-256: `a81f8c2be1178e7a61f1d55c8f3eda393eb1c15a9de300f506dd21625c32af46`
- Image.gz SHA-256: `17d13bea335b8b81bbdc9afb60127035af911fccedecd8853061afbec54ba5eb`
- QMP-UFS module SHA-256: `6da33a782ea8492f57db6ef55bbf744bdac8c8e04fb6d322bf125999a9349a6c`
- UFS core module SHA-256: `f0d63a1327277c87dc02664b5378bedd44a852f604ef9fd88f6c2be3e0aa7e02`
- UFS platform module SHA-256: `545513c63db5fd8e8286ce0562ee328c085fe7fdebe39adb6834098bddfdbfb5d`
- UFS Qualcomm module SHA-256: `c2825189ec8d575eed37f553a99eb288e727165158f3ba65d3f2c5128711489d`
- initramfs SHA-256: `998c2293298028763cd54c7976385efdf62861bf6102c4afacf3f52b2539f568`
- signed manifest SHA-256: `6d8195d2e384558b9ff79a42966fd6841837b38d4b41e83dd745bf554be14dc6`
- manifest signature SHA-256: `6a3a61e276e24d615e091bfa11f878c20139ad5faa9d943d3ebf2aabe8962eb2`
- Generation 44 recovery SHA-256: `2a8c210db1b846df4886c7803d337a4edf4fe1787537d1582529196a82734fd9`
- AVB salt: `e9bf9a3b3723ea6d70365379f63533359eb780b880312b139fcdb3ac13428e44`
- AVB digest: `039f3d74802391e894d2c6e24bd7e0eab40880e4abc26d3b834e75ab1a9ab713`
- AVB generation record SHA-256: `5bf1e8489b0fed50a091d950a2ec2d80b4684ff018e4a6d4a5ef36d2dd9fd55b`

The uncached clean kernel twin took 18 minutes 58.151 seconds. The independent
clean-output twin reused only the persistent compiler cache and took 2 minutes
2.766 seconds; the full twin verifier passed in 2.182 seconds. Initramfs twins
took 1.120 and 1.116 seconds. AVB issuance took 1.815 seconds. All released
twins are byte-identical. The raw recovery payload remains exact SHA-256
`90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6`.

The proof listener is fixed to `169.254.77.1:8079` and accepts exactly one
record from `169.254.77.2` containing the exact release, module name, and
`result=PASS`. Hostile tests reject a changed payload or wrong source address.
The target bounds proof delivery to 100 one-second connection attempts and
retains the 15-second local fallback path. No candidate has been booted as part
of this offline checkpoint.

# Generation 123 post-ConfigFS UDC inventory

Date: 2026-08-24

Result: **CONSUMED; ZERO/EXPECTED UDC CHURN.** Never retry or flash.

The target creates the same NCM-only ConfigFS function and link as production,
then binds nothing and classifies the first unexpected UDC basename or
zero/expected churn. It has no UDC bind, network, carrier, power/USB, UFS,
userdata, SSH, installer, or storage surface.

Clean-twin target initramfs SHA-256:
`96a2d2d60531e7337b73330051f89a1173f46e446cfe7f049ad151c7b2f817a9`.
Signed runtime manifest SHA-256:
`a9af841d12ecf27f28efed92562b2c5fd944a6db4f4f2e1594c26ad7b12a20dd`.
Generation-123 recovery SHA-256:
`14a4ae239fd5b3a2ac134300f6cd7afaef4d11743af7db130db5bf226989cf4d`.

Recovery USB departed at `12:40:08.816550`; exact fastboot appeared at
`12:41:56.072514`, 107.255964 seconds later. This exactly selects the 25-second
inventory window, 75-second `seen_zero` bucket, and restart overhead. No wrong
or additional UDC basename appeared. The class alternates between empty and
the exact `a600000.usb`, preventing 50 consecutive samples.

No UDC bind, target USB, network, power/USB, UFS, userdata, SSH, installer, or
storage path ran. The successor tolerates absence while polling, requires two
consecutive exact samples, rejects every wrong/multiple candidate, and
revalidates the exact UDC after binding.

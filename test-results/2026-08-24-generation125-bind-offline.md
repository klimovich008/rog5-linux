# Generation 125 immediate exact-UDC bind

Date: 2026-08-24

Result: **CONSUMED; SCAN-THEN-BIND TIMEOUT.** Never retry or flash.

The selector polls through temporary absence, rejects any wrong or multiple
candidate, attempts to bind immediately on one exact `a600000.usb` observation,
retries only if that expected UDC vanished, then verifies the bound UDC field
and class identity. All later staging behavior remains unchanged.

Clean-twin target initramfs SHA-256:
`d0eeb4c7ea54dc106349bcb5ae76814adea39ca77d1d60edb4d9aec76384083a`.
Signed runtime manifest SHA-256:
`e2c25b000269fe5b752ea505ce54855ee00f4babbc04836ff50e94252d67e6c1`.
Generation-125 recovery SHA-256:
`e8f6a22641b2520c3a129854cf890449552e08898a6098adcaad8743ad2b4b32`.

Recovery USB departed at `13:30:52.965499`; fastboot appeared at
`13:31:25.469511`, 32.504012 seconds later. This selects the 25-second bind
timeout plus restart overhead. No target USB, SSH, installer, or storage write
ran; fallback passed.

The full inventory scan and command substitution still introduce too much
latency before the write. The next selector polls the exact expected sysfs path
directly, attempts the exact bind immediately, retries only a vanished path,
then performs full wrong/multiple and bound-name validation after success.

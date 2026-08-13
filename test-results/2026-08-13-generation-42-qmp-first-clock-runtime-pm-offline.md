# Generation 42 QMP-UFS first-clock runtime-PM offline checkpoint

Status: **offline clean twins passed; unbooted; no phone-storage access**.

Generation 41 proved clock-data allocation and construction of the dynamic
`rx_symbol_0` name while preserving target NCM. Generation 42 addresses the
earliest remaining boundary: the first `devm_clk_hw_register_fixed_rate()`
call can walk all CCF orphans while unrelated clock providers are runtime
suspended.

The generic CCF correction takes balanced runtime-PM references for every
registered provider before acquiring `prepare_lock`, performs orphan
reparenting, releases the lock, and then drops the references. The same order
is used for both OF provider-publication paths. The SM8350 QMP-UFS diagnostic
branch crosses exactly the first fixed-rate clock registration and returns
before the second and third clocks, OF clock-provider publication, PHY
creation, or provider registration. UFS core, platform, and host modules are
absent, so this candidate cannot enumerate or access phone storage.

Fail-first source-contract tests reject the prior single-provider registration
path, missing all-provider references, references acquired under
`prepare_lock`, unbalanced error paths, and a QMP discriminator that returns
before or after the reviewed boundary. The exhaustive lock model verifies the
runtime-PM/CCF ordering independently of hardware.

Exact clean-twin result:

- source commit: `cdf38b1ddebb802d0659666a351f845e5897f557`
- source tree: `1965005b04872d031892b26332164ebfe40b7349`
- release: `7.1.4-gcdf38b1ddebb`
- config SHA-256: `b959774825e2bca7c634e55cd00e838121fde8d95fd214ffeead732ce92e35e6`
- Image SHA-256: `eeb1a0363485798c6b8a3027985d20d5d8d0afa213eb611418d0617b9d3743a3`
- QMP-UFS module SHA-256: `6d2462f43f323866fc3240bed187a7393debc2503330815184cffc6ae3e1b949`
- initramfs SHA-256: `7564d25c80f1ae278109e2a17b2051b927a49cb36241ea6dc561b28a0417f5fa`
- signed manifest SHA-256: `782756493f38d5ea9a634678043214926e9b49ef1ca01ce35e9e41e37169fd4b`
- Generation 42 recovery SHA-256: `1b0ec7c7c9b9abb1cbf71c252292203869e853717f4a41cfbc3a03936b5597a1`

The cold clean build took 1406.204 seconds. The independent clean twin reused
the exact compiler cache and took 114.476 seconds, a 12.3x reduction; outputs
remained byte-identical. Initramfs twins took 1.108 and 1.181 seconds. AVB
generation took 1.801 seconds and preserved the exact stable-recovery raw
payload SHA-256
`90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6`.

This checkpoint does not claim that CCF caused the Generation 39 loss. One
RAM-only physical cycle is required to test that hypothesis. Generation 42
remains single-use and must never be flashed.

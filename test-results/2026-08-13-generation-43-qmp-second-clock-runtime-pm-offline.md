# Generation 43 QMP-UFS second-clock runtime-PM offline checkpoint

Status: **historical offline checkpoint; live cycle consumed; never retry or flash**.

Generation 42 proved the first fixed-rate QMP-UFS symbol-clock registration
with the generic CCF runtime-PM correction. Generation 43 preserves that
correction and advances the SM8350 diagnostic branch through the second fixed
clock, `rx_symbol_1`. It returns before `tx_symbol_0`, OF clock-provider
publication, PHY creation, or provider registration. UFS core, platform, and
host modules remain absent, so this candidate cannot enumerate or access phone
storage.

The fail-first source contract rejects a return before or after the exact
second-clock boundary and requires the generic all-provider runtime-PM
correction. The focused contract test passes against the retained source.

Exact clean-twin result:

- source commit: `ad56d4021003b1f1c65ee92f583fda232013e301`
- source tree: `c66103679f9d5574758d0cd4595f41c632e4ed48`
- release: `7.1.4-gad56d4021003`
- config SHA-256: `b959774825e2bca7c634e55cd00e838121fde8d95fd214ffeead732ce92e35e6`
- Image SHA-256: `6730f8f35a66238709f138707c6de94101d064660a03109f129ceb03e3e25792`
- Image.gz SHA-256: `82fef240978b7be67c05160e54686a51c3597ffa2fda1b4adbd145598f9ec78d`
- QMP-UFS module SHA-256: `05712342e15f4195676f6646ac62c95c6c5d8651b53de418cc8d34129c057cac`
- UFS core module SHA-256: `f0619c3773f7324bc335fe9f6a0409eb88c84dfe0297b6cd080cf731947db173`
- UFS platform module SHA-256: `ccedf9ceb2117c36b46a72318681e092ee7ebefa24823b3209a9c3188f9b5131`
- UFS Qualcomm module SHA-256: `0f4e3439a1f941014f75ccae6c0a0eca1b2e0902015f1c21229503c830888189`
- initramfs SHA-256: `8fbecf724bab84145216bcfb63b40a076249d9b1bb1ad4a6d1a5040f2c7797c3`
- signed manifest SHA-256: `052d462cbd7820de331c446598f69224128eced8175665acd703428efb75b371`
- manifest signature SHA-256: `bad6fd783a41e203629c5ff67ab604af3dfdc8d0e82ecf448fbabb0857888fc5`
- Generation 43 recovery SHA-256: `505e2c0ec00f8b5582cb18e648674737667b7c8d7b9cc5638b6c89c34fad9ec0`
- AVB generation record SHA-256: `0b0832039db5d0fda9955fc99978b7fd197c2d481abaf09260eefef594060485`

The two clean kernel builds took 106.921 and 104.408 seconds. Initramfs twins
took 1.133 and 1.163 seconds. AVB issuance took 2.000 seconds. All released
twins are byte-identical. The raw recovery payload remains exact SHA-256
`90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6`.

Generation 43's exact clean-twin candidate was subsequently booted once. It
completed the second fixed-rate clock, preserved stable NCM, and returned to
exact Alpine without storage access. Its claim is irreversibly consumed; see
the [live result](2026-08-13-generation-43-qmp-second-clock-runtime-pm-live.md).

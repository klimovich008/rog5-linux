# Generation 49 read-only UFS enumeration offline checkpoint

Status: **unbooted RAM-only candidate; read-only enumeration only; never
flash**.

Generation 48 proved QMP-UFS OF PHY-provider registration. Generation 49
reuses that exact clean-twin kernel, module set, and DTB. Its sealed initramfs
now loads the fixed PHY, UFS core, platform, and Qualcomm host module chain,
waits for the previously measured 116-node topology, locks every physical disk
and partition read-only, resolves `userdata` by GPT identity and geometry,
and writes the inventory only to tmpfs. It refuses any block-backed mount,
blocked UFS command, wrong topology, wrong dynamic device identity, or lost
USB control state. An exact target proof is sent before an unconditional
rollback gate; the existing storage mount call is unreachable in this
generation.

Exact reproducible identities:

- source commit: `ae717d919f87b47ea9ed2173ea96660186b62a66`
- source tree: `939729426dcfa3bd72c75d81c0a675c6f0a193da`
- release: `7.1.4-gae717d919f87`
- config SHA-256: `b959774825e2bca7c634e55cd00e838121fde8d95fd214ffeead732ce92e35e6`
- Image SHA-256: `f9fbf172630187877451133bf3634df345703dd5610a01c328d1a50408381aad`
- target initramfs SHA-256: `24c0b7279964ea2de6f2dea87ec3a228885481fa2abe94cb4b3ea732a336b738`
- DTB SHA-256: `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`
- signed manifest SHA-256: `9ea343f70b9dfa3658a13d4b1e4dfd2cb841881ec21ce0444cd4422899434045`
- manifest signature SHA-256: `17ba19749ee675542b695e0b8b014e4592cfee5dab69ee7fe9dab29cf9e1e82d`
- Generation 49 AVB SHA-256: `7bd5cbae17f82d2496af0967534a53d8853f06d4eb6610a55641f7461e067399`
- AVB salt: `9901532ce6956506f5451b2f873873480f92d129fbf8b4f8d4867e8e73453c66`
- AVB digest: `8275db0d58696cf176bf8cfc27f08bd4cafa7d97cf4ff6c9eaba865a56028cf6`

The unchanged kernel clean twins remain byte-identical and mandatory release
evidence. The new initramfs twins took 2.237 seconds combined, signed bundle
twins took 0.539 seconds combined, and deterministic AVB generation took
3.236 seconds. Focused target, host proof, one-use claim, stable-gate, and
admission tests pass. This checkpoint authorizes neither a persistent write
nor a mount; publication and one exact RAM-only hardware cycle remain separate
gates.

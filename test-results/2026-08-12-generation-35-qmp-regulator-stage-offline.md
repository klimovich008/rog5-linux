# Generation 35 QMP-UFS clock/regulator-stage discriminator

Status: **offline checkpoint; unbooted; one RAM-only use only; never flash**.

Generation 35 uses the exact Generation 34 kernel Image and the UFS-enabled
DTB. Its patched QMP-UFS module binds only the exact SM8350 compatible,
acquires the driver's clock and regulator handles, applies the existing
reviewed 91,600 and 19,000 microamp regulator loads, emits one marker, and
returns before DT/MMIO parsing, clock-provider registration, PHY creation, or
provider registration. UFS core, platform, and host modules remain absent, so
the candidate cannot enumerate or access storage.

The source patch applies cleanly to commit
`cfd385a1c754684dd28b63a4559e04baa5e902b1`. The retained patched source is
commit `d6509d3ddc3db7654271b82f2f718fb671fdfbcf`, tree
`c72ed8ac89f74334584721a406471c86daff28f9`, and is clean. Two independent
module compilations and final links are byte-identical. Because the patch
changes no exported ABI and `CONFIG_MODVERSIONS` is disabled, finalization
reuses the exact unchanged Kbuild-generated module metadata and module-common
objects; every undefined symbol is present in the exact retained
`Module.symvers`.

| Artifact | SHA-256 |
|---|---|
| reused kernel Image | `53d42da77b65a37149bd269c5d71d7855a7edb51748cb2da478bff5cb5f95203` |
| UFS-enabled DTB | `72c0db7cb2f54055240c420bbcd4fece6f497e1e648ce7081141781bc78f48c2` |
| diagnostic QMP-UFS module | `82777c857be361e190ec0010bb3593251a8475cde6669ba1516ef859e0cddecf` |
| initramfs | `c1574c430e49fd05550fdcbef3300cbded51393e9ad7668d881f70133a8115bb` |
| signed manifest | `03e49b58a082826c1d88ab328c82d6c903c9130e56522fb645eaa3be31eb69a7` |
| manifest signature | `55a73dbc0414505a942115c6a264e20f974eac5c6c3602923bea937338da42fb` |
| Generation 35 AVB wrapper | `734a7d0a3632df5f5d04d6faa2ecca82e72e4945daf5bd46db100e062d4e9d6e` |
| AVB generation record | `e237fcbddcc7a9f35cf314b5d73c056107963244b54322e6e5a8828e272c53da` |

Bundle, initramfs, module, and issuance twins are byte-identical. Success means
clock/regulator acquisition and reviewed regulator loads do not reproduce the
loss; failure at the Generation 33 timing requires a clock-versus-regulator
split. The known-good Alpine fallback is unchanged.

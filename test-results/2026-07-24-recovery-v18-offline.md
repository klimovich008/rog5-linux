# Recovery v18 offline result

Status: **PASS offline; live temporary boot pending**. V18 is the current
credential-free ACM-only candidate and must never be flashed.

## Change from v16/v17

V16 reached exact recovery USB, working NCM, and automatic rollback, but ACM
returned no shell data. The authorized local v17 SSH diagnostic proved that
the RAM root, zero-block-mount gate, all 116 physical read-only checks, and
watchdog passed. It also showed that `/sys/class/tty/ttyGS0` existed while its
`/dev/ttyGS0` node did not.

V18 performs an explicit `mdev -s` after creating the ACM function, requires
`/dev/ttyGS0` to be a character device, then repeats the complete
block-backed-mount rejection and physical-device `BLKROSET` verification
before starting ACM or binding the UDC. A rescan, node, or second storage-gate
failure forces rollback while USB remains closed.

## Reproducibility

- Credential-free target and staging initramfs layers each reproduce
  byte-for-byte.
- Two fresh ASUS wrapper output volumes produce identical config, embedded
  initramfs, metadata, and Image.
- Two header-v3/AVB repacks are byte-identical.
- The strengthened verifier checks both storage gates and the ordering
  `mdev -> ttyGS0 -> storage -> ACM -> UDC`.
- The complete verifier passes in `acm-only` mode with networking disabled.
- Neither archive contains authorization or private-key material.

## Candidate products

| Product | Size | SHA-256 |
|---|---:|---|
| ASUS wrapper Image | 69,372,416 | `d48a349d37faae0a3737cce2c6d2c4ba24d0d2a0a13d3ec1c17120c8ca08cb4f` |
| ASUS wrapper config | 185,763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| embedded staging initramfs | 26,597,581 | `fae3ee19b2392e7f2ce46cf459e90b6bdfb2568364038e239a59b2a5d6ff0b1b` |
| Linux 7.1 Image | 38,406,656 | `4d6f3ecaa8d2af0b1e1fddd0655af469e867d596f8f3eae0a20583b058fbe697` |
| USB2 recovery DTB | 102,774 | `255c5ac199b0412c499aae39bb596507b934e71c003396040d4952f0c5ffabe6` |
| target initramfs | 5,838,973 | `852b02a2cbcb2dfd43598269ff1b2b10cb1542e90ab7a7aa32d1a26c7cc645fc` |
| staging initramfs | 26,597,581 | `fae3ee19b2392e7f2ce46cf459e90b6bdfb2568364038e239a59b2a5d6ff0b1b` |
| raw header-v3 image | 95,977,472 | `292a14e212826a250de501d4d502dda6973097ed172cd9324d82cf88d82fd657` |
| unsigned AVB image | 100,663,296 | `b06f016a5f9697a4e51b13159dede83990c30fc9bd36ff642214ac6715c05af7` |
| wrapper metadata | 442 | `f2ec55649b2951f3774ad2e26458506f4125ffff886f478f4ceb08a23a3851a0` |

## Live gate

Use only the explicit manifest-pinned `fastboot boot` workflow. Through ACM,
verify the wrapper release, RAM root, zero block-backed mounts, all 116
physical devices read-only, armed watchdog, live ACM supervisor, absence of
authorization and SSH, then allow automatic rollback to a changed fallback
boot identity. Repeat the complete cycle before kexec becomes eligible.

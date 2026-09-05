# NFS-gated diagnostic generation-2 AVB successor

Date: 2026-08-02

Result: **PASS offline — generation 2 is a distinct, twin-reproducible AVB
identity over the unchanged diagnostic recovery, and the complete artifact
preflight passes. No private key, phone interface, fastboot command, reboot, or
boot occurred.**

Generation 1 reached signed-bundle verification and one commit claim, then
exposed that the host control client did not classify the diagnostic bundle as
an NFS-root bundle. Exact fallback passed and generation 1 is consumed. Commit
`77336ed` adds `headless-netroot-early-diag-v1` to the exact v3 NFS rendezvous,
tests profile/package/marker/listener binding before `COMMIT_EXEC`, and rejects
unknown guarded bundles before device discovery. Local CI and GitHub Actions
run `30745676057` pass at that exact commit.

The deterministic issuer used the original generation-zero production wrapper
as its sealed source. It proved generation zero, preserved both raw A/B
payloads, kernel, initramfs, partition geometry, and normalized AVB descriptor
structure, then changed only the generation-derived salt and corresponding
hash digest. AVB remains algorithm `NONE`; the generation number is a one-shot
host-pinned identity, not new cryptographic trust.

## Exact identities

| Field | SHA-256/value |
|---|---|
| Generation | `2` |
| Source generation-zero AVB | `f710bbcd1f9602f0fdc3ce7023298f66cc5e7a014a0627c4f9123d7cc897b0ef` |
| Raw recovery A/B, unchanged | `2f460aa01ee1b97c495d0857b3207bf74920487c56f30c5e155e199967628a01` |
| Generation salt | `8f20854a98ee31fa889c5bfe2b7818ed42c5ed6186b671a55b3f57835c87e712` |
| Descriptor digest | `903826e0579863b0290004f5f415aecfcee1384f5b81a949ddd8845c880a7541` |
| Generation-2 AVB A/B | `70fd77f7f0225d1fe9cce54111d378002b1c8c8a0d1d59c581b4d4ef9bfc72b1` |
| Generation record | `4a1de575f2c428ae2625e38a37f31fa70850ce64895cf549509434d806e8d109` |
| AVB partition size | `100663296` bytes |
| Raw payload size | `58101760` bytes |
| Authority | `none` during issuance and artifact preflight |

The complete artifact preflight reverified the exact recovery control,
fetcher, native verifier, host verifier, production Ed25519 public root, signed
diagnostic manifest, target Image/DTB/initramfs, wrapper kernel/config/initramfs,
generation record, AVB footer, raw prefix, and A/B equality. Its terminal marker
was:

```text
PASS stable-recovery artifact preflight profile=headless-diagnostic-deployment-v1 image_sha256=70fd77f7f0225d1fe9cce54111d378002b1c8c8a0d1d59c581b4d4ef9bfc72b1
```

The wrapper is now the sole `allow` row in the deny-by-default temporary-boot
policy, for at most one RAM-only boot after review, local/GitHub CI, exact host
installation, fallback readiness, and connected preflight. It must be consumed
after any boot result, must never be retried after an ambiguous commit, and
must never be flashed.

# Early-target diagnostic candidate — offline acceptance

## Result

**PASS offline — the diagnostic initramfs, disposable-signed bundle, stable
recovery wrapper, raw boot image, and test-only AVB image reproduce from two
independent builds and pass the hardware-free admission gates.**

This run contacted no phone or external service, loaded no deployment
credential, used no host privilege, and performed no physical-storage action.
It grants no boot, flash, signing, or deployment authority. The disposable
Ed25519 private key was destroyed after packaging; only its public trust root
remains in the ignored build output.

## Candidate identity

| Field | Value |
|---|---|
| candidate / bundle | `headless-netroot-early-diag-v1` |
| profile | `diagnostic-initramfs-v1` |
| target | `headless-netroot-early-diag` |
| target release | `7.1.4-g7a5cef0db479` |
| manifest SHA-256 | `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76` |
| disposable public trust-root SHA-256 | `0734bf2074d7207b114edfa8bd6af4691f253f5592dd48f7e1c8ef7c427186a0` |
| rollback / target timeout | `600` / `480` seconds |
| authority | `none` |

The signed manifest binds the accepted 37,735-entry Arch lower through tree
SHA-256
`f4affd6d83f3af48259c7d7f650e91461465b59e045519310ac81bb5d71a0087`,
seal SHA-256
`42ef8388bb771fbd0dd8141939b042a89037ea1cf1bec9288f7a3ae51455210a`,
generation `arch-a`, and subtree `/`.

## Target and diagnostic artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Linux 7.1.4 `Image` | 40,049,152 | `349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf` |
| corrected board DTB | 102,870 | `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46` |
| diagnostic initramfs | 6,010,870 | `10cc407e2bb5a9c9b63fd7eb30c7fc785d78b587e0c7c0b32346f7b1a50ce35c` |
| static AArch64 reporter | 67,288 | `f0a9a52b42385a5c963230d5c48f152bed2e24e382c22de09acdba529082a1fd` |
| A660 command manifest | — | `99f194b32171c9c9f09d28636e351bba4cb34751997e1aa174e3466bd758a1d2` |

The two complete bundle directories and their prepared-candidate records are
byte-identical. The native bundle verifier accepted the diagnostic profile,
exact target/root tuple, executable sealed reporter, and signed manifest.

## Recovery wrapper

Two clean, network-disabled ASUS 5.4.210 wrapper builds used the same
7,594,703-byte stable-recovery initramfs and produced identical outputs:

| Artifact | SHA-256 |
|---|---|
| stable-recovery initramfs | `8f81ca46284c33dbb62a3b29149f279a459025a268c8f02d2ae2fa9c1f53dc78` |
| wrapper `.config` | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| wrapper `Image` | `886be3b0db40e0effac490e88fca0dc60bd080ce98e0387fd6c32c9a8cb6c85f` |
| header-v3 raw boot image | `5a0ee0cd4018680bb4d78539149ec020d7ecf934edc648c677b5710c9434671f` |
| test-only unsigned-AVB image | `d7fe565462c876aff32c73c44d3c3bd7436c57c8afd9b9210fc0308d788046e8` |

The raw and AVB twins compare byte-for-byte, unpack to the expected kernel and
initramfs, and pass the offline AVB/footer verifier. They are not present in
the temporary-boot allowlist.

## Builder and historical-byte repair

The live recovery-builder qualification passes with:

```text
private runner SHA-256:
4437422db78d196d6992fa53b006ebde68efb6d6dc8700ee91ccb46af2a3b621
builder profile SHA-256:
780d564013d30c278b709939db6402347243eb2866065c6cbbe1788a946b842f
```

The qualification profile had retained the runner identity from before later
runner hardening. The current runner, profile, verifier, and contract now
cross-check each other instead of accepting that stale pin.

The shared network-root init source has intentionally gained diagnostic
behavior, so rebuilding normal mode from current sources would not reproduce
the frozen historical archive. Normal reconstruction now extracts only its
five required source files from commit
`27a270f2955c57f61e2cb8aeae0be23b31223499`, tree
`56668d6b44907ffb3644c04d6d9ff3a7c1f49b95`, and twin-builds the exact
5,978,369-byte archive with SHA-256
`819bdf88c920057a5d8b511cb13e3adc0f7d8d9cf1a92a7fac087697889bb9b5`.
Diagnostic mode independently twin-builds the verifier, reporter, and archive
and reproduces the identities above.

## Verification

The acceptance run passed:

- 12 recovery-candidate adapter cases;
- two stable-recovery composition integration cases;
- exact candidate/profile and transport-isolation contracts;
- two complete signed bundle preparations;
- two clean stable-recovery initramfs builds;
- two clean ASUS wrapper kernel builds;
- two header-v3 raw and AVB repacks;
- an independent normal historical-initramfs reconstruction;
- an independent diagnostic reporter/initramfs reconstruction; and
- live rootless ARM64 builder/profile qualification.

The complete local repository `ci` tier passes against this checkpoint. It
includes the compatibility/profile hash chain, 39 core-profile cases, 74
source/DTB mutations with one optional retained-source skip, the real AArch64
systemd QEMU gate, recovery protocol, reporter/collector, packaging, rollback,
and repository policy. Independent final review reports zero standards/safety
and zero objective-fidelity findings after checking exact-manifest admission,
atomic no-replace publication, and its empty-destination race regression.
GitHub CI remains a separate gate.

## Limits and next step

This result proves reproducibility and hardware-free admission only. It does
not prove that the reporter enumerates on the phone, that any stage frame is
captured, that NCM or OpenSSH survives, or that the Linux target remains
running. It also does not create a production-signed external candidate.

The next engineering step is a diagnostic-only lifecycle supervisor that
starts the receive-only collector before the non-retryable commit boundary
and pins every identity above. Production-key use and one temporary phone boot
remain distinct guarded actions.

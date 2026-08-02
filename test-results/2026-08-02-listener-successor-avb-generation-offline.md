# Listener-corrected diagnostic AVB successor

Date: 2026-08-02

Result: **PASS offline — a distinct generation-1 AVB identity was issued over
the byte-identical, production-trust-root diagnostic recovery. No private key,
phone interface, fastboot command, or boot authority was used by issuance.**

The prior wrapper `f710bbcd…97b0ef` booted once and is permanently consumed.
Its recovery payload was not the failure: the installed host controller
rejected Steam's unrelated `127.0.0.1:8080` listener before bundle transfer or
target execution. The reviewed controller correction scopes conflicts to the
fixed recovery address and wildcard/mapped equivalents.

Recompiling the unchanged recovery kernel would add cost and unrelated bytes.
Instead, `issue-stable-recovery-avb-generation.sh` proves the source wrapper is
the canonical generation-zero encoding, copies both raw twins and required
wrapper evidence without modification, and changes only the AVB hash
descriptor's salt and corresponding digest. The AVB algorithm remains `NONE`;
this generation is an auditable one-shot identity, not additional cryptographic
trust. Trust remains the exact host-pinned wrapper SHA-256 and embedded Ed25519
public root.

## Identities

| Field | SHA-256/value |
|---|---|
| Generation | `1` |
| Raw recovery, unchanged | `2f460aa01ee1b97c495d0857b3207bf74920487c56f30c5e155e199967628a01` |
| Consumed generation-zero AVB | `f710bbcd1f9602f0fdc3ce7023298f66cc5e7a014a0627c4f9123d7cc897b0ef` |
| Generation salt | `334e66adbf188df2e746f674d2bd9577d76dab746e211fa84a38fc3d2ebeab5e` |
| Descriptor digest | `5a4025f5b1cbbd1aecaace6e7761643434043f2121e696a44b456dea524e1006` |
| New AVB wrapper | `332889a83f541ed0e17c94656836c512a35b5bfd6bbbaf735d2f5f6b94b51830` |
| Generation record | `68e42eec4875ba747dfe44dbcd086ba518049caeb80c7495953fc8b773f26f6c` |

Generation zero reproduces the consumed AVB image byte-for-byte. Two
generation-one issuances reproduce each other, generation two differs, the
complete normalized `avbtool info_image` structure is unchanged except for
salt and digest, the first 58,101,760 bytes exactly equal the raw image, and
`avbtool verify_image` passes against that raw `boot` payload. Publication is
atomic and failed validation leaves no output artifact.

The complete diagnostic artifact gate passes with the unchanged ASUS 5.4
wrapper kernel, initramfs, trust root, recovery components, signed target
manifest, corrected DTB, and host verifier. The new wrapper is listed once in
the deny-by-default temporary-boot policy for at most one RAM-only boot and
must be consumed after any boot result. It must never be flashed.

The corrected controller was then installed root-owned at exact source/install
SHA-256 `9f3be8e9…90894`; its fixed socket is enabled and active, and SteamOS
read-only mode is restored. Complete local repository CI passes. The target
remains unexecuted. Reviewed publication/GitHub CI, connected preflight, and
exact fallback readiness remain mandatory before the one-shot lifecycle.

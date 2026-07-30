# Headless SSH v2 recovery candidate

Date: 2026-07-30

Result: **PASS hardware-free; fixture-only; unbooted; authority=none**

## Outcome

The credential-clean `headless-ssh-v2` root and v3 package now have a distinct
recovery candidate: `headless-ssh-network-root-v3`. The candidate binds the
exact package tree, seal, entry count, command manifest, and root generation
to the accepted corrected recovery DTB. The package separately binds the
canonical Ed25519 authorized-key fingerprint. The signed runtime manifest
therefore binds the package's verified tree and tested SSH access policy
without changing the stable `network-root-v1` wire protocol.

No phone, fastboot, ADB, root password, private SSH key, production signing
key, host-global binfmt handler, mount, reboot, flash, or physical-storage
action occurred.

## Root and package identity

```text
build_profile=headless-ssh-v2
package_format=rog5-headless-network-root-package-v3
wire_profile=network-root-v1
authorized_key_fingerprint=SHA256:ylv66wbMSxVEAMiOFvMQOztcvtSB5wSbVe9FXePMLN0
source_archive_size=536750378
source_archive_sha256=2abe8c533179da598c37939ff8ebb4667a243bd8140c2d497237e41fbea72e6a
sealed_archive_size=536747283
sealed_archive_sha256=60fed48c8714a3f3b2082f95a04e913f32dfc74ed4c262e5b3d6e924a39a9c3b
root_tree_entries=37735
root_tree_sha256=6f8a8f11bfb581bb52ca7d590141ce465b8d48d8f9f4577a076b7a37604a2fd5
root_seal_sha256=f443a47c456b33d670e6efd4a2e20cff2bc72061e7661472694acfbba45c8d5a
```

The SSH fingerprint belongs to the public test fixture. Its private half was
destroyed previously and is not a deployment credential.

## Candidate identity

```text
candidate=headless-ssh-network-root-v3
profile=network-root-v1
target_id=headless-ssh-network-root
target_release=7.1.4-g7a5cef0db479
kernel_size=40049152
kernel_sha256=349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf
board_dtb_size=102870
board_dtb_sha256=86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46
target_initramfs_size=5978369
target_initramfs_sha256=819bdf88c920057a5d8b511cb13e3adc0f7d8d9cf1a92a7fac087697889bb9b5
runtime_manifest_size=819
runtime_manifest_sha256=a409f0ebad410edf8fb36e31d322029bf69d4c6621ddab84a660ff471da48e11
authority=none
```

The target initramfs is intentionally the same generic network-root loader
used by the other headless candidates. It does not contain the Arch lower
root. The signed manifest passes the package tree, seal, entry count, command
manifest, generation, and subtree to that loader, which verifies the
separately served read-only NFS root before handoff. The adapter test pins the
complete shared kernel and loader identities as well as each candidate's DTB;
sharing the loader is not a v1-root substitution.

The manifest is independent of the signing key. The offline gate generated
one mode-restricted disposable Ed25519 signing key, used it to create twin
test signatures, and destroyed the private key before returning success. Its
public trust-root SHA-256 was
`cc122e05f5c9acc1241978bc8504ef46c1f28d4df313d5ac3c71ab3b053ba827`.

## Reproducibility and verification

| Gate | Result |
|---|---:|
| candidate/package field binding | exact |
| malformed and co-varied candidate tuple refusal | passed |
| signed runtime bundles A/B | byte-identical |
| native verifier plans A/B | identical |
| shell-free recovery initramfs A/B | byte-identical |
| clean ASUS 5.4 wrapper kernels A/B | byte-identical |
| header-v3 raw wrappers A/B | byte-identical |
| test-only AVB wrappers A/B | byte-identical and verified |
| candidate adapter tests | 7 passed |
| recovery integration tests | 2 passed |
| disposable private-key cleanup | passed |
| complete repository Linux CI tier | passed |

Key wrapper identities:

```text
stable_recovery_initramfs_size=7593281
stable_recovery_initramfs_sha256=70e7ba4899aca28b3691917da7d35b0dea5b57f5e6cf3838cba6095a0152aee6
wrapper_config_sha256=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
wrapper_image_size=50498048
wrapper_image_sha256=c30788a3388fd007a400cb5b46877af8e78c03778a4974ebc55637c8a8af4298
raw_wrapper_size=58097664
raw_wrapper_sha256=8c5c643d2df544cea86506ec65c503f788b5a951552f61c92ebada7be3123ba5
test_avb_wrapper_size=100663296
test_avb_wrapper_sha256=63b4a25878edf3b90d71ab39086d00396353f6683062b0689507ae16f9eee1c7
```

## Remaining boundary

This result is fixture-only and cannot authenticate a deployment login. It
does not authorize credential use, host promotion, a connected preflight, or
a phone boot.

The next host-only feature must derive an Ed25519 public key from the caller's
private key, reject the fixture fingerprint, rebuild the root/package/candidate
chain, and verify the exact v3/profile pairing without contacting the phone.
Credential use and any later connected temporary boot require fresh explicit
authorization.

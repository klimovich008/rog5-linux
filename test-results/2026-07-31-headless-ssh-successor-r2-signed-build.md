# Headless SSH successor r2 — signed twin build

Date: 2026-07-31

Result: **PASS; the exact external r2 candidate was twin-signed, twin-built,
independently hashed, and accepted by the production artifact gate without
phone access.**

## Build boundary

The guarded production builder ran once from clean, pushed checkpoint
`81d2736811146df1a74f06b5dea28e75cee5383b`. It admitted the caller-owned
mode-`0444` candidate with SHA-256
`b26bc73ec6cd0053900044776270ed2c3a7f7bf6424140a59bb74d513b5dd51e`
and the existing external Ed25519 recovery signing key. The candidate remained
`headless-ssh-network-root-v3`; the one new signed transfer identity is bundle
`headless-ssh-network-root-v3-r2`.

The builder privately snapshotted the key, built two complete copies from
clean directories, and verified that no private snapshot survived. The
retained output contains only the raw public trust key. It did not inspect,
boot, or modify the phone and did not change host networking.

## Pinned identity tuple

```text
recovery_avb_sha256=11feb00b6a80e701e74c8538b6f80fb4956d9b21463d666806e0b5f14b52213c
recovery_raw_sha256=a937b03b54c01c6240cff45aa243632827d0c9d328e6f285ae489c973a6213a9
recovery_kernel_sha256=1a8bac7a2b016dc7d63d22f09d0872b9c3f251952b7627c68f7c387f386b0068
recovery_initramfs_sha256=f414d0ea26ee3aa6cca5c3aa12c1601934294c0207fc2709ebbae305bb3642e0
recovery_config_sha256=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
recovery_control_sha256=f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77
recovery_fetch_sha256=677fa731b1bd9fd11efc46aabeb32e7a725725483c86a2f58d417f482c27f392
recovery_verifier_sha256=374900be5769eee074820007ab2e335d4c033c500da7a480cc88f9a70137029b
host_verifier_sha256=9099f5f615144cf95655e6e169ac49b0cbe6f0a6d759441c59bc3130407ab78b
trust_key_sha256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
manifest_sha256=9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630
dtb_sha256=86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46
```

The trust key is unchanged because this successor deliberately reused the
existing recovery signing key. The manifest differs from the consumed v3
manifest because the signed bundle identity is now `…-r2`.

## Verification

- both candidate records, bundles, recovery initramfses, wrapper kernels,
  raw images, and AVB images are byte-identical across build A and build B;
- `SHA256SUMS` verifies every promoted identity;
- the recovery archive policy, native bundle verifier, composition tests,
  Android boot-v3 unpacking, and AVB descriptor verification pass;
- the production artifact gate accepts the exact profile, bundle, manifest,
  trust key, recovery components, wrapper configuration, and AVB image and
  exits before fastboot discovery; and
- 14 key-admission, 27 runtime-verifier, 14 recovery-control, and 19
  lifecycle tests pass, together with the live-gate and runtime-runner shell
  contracts; and
- the complete host-neutral repository CI tier passes after the reviewed
  candidate/bundle split and documentation update.

## Remaining HOLD

1. Review this pinning change, run full local CI, push it, and require green
   GitHub checks.
2. Install the signed r2 bundle and byte-current host components with the
   existing no-replace launchers.
3. Pass key, artifact, privileged host, and connected-fastboot preflights.
4. Only then perform one attended temporary `fastboot boot` lifecycle. Do not
   flash or write phone storage.

# Headless SSH deployment chain and live-gate admission

Date: 2026-07-31

Result: **PASS hardware-free; non-fixture chain built; no phone action**

## Outcome

One dedicated non-fixture Ed25519 SSH identity was bound into the minimal
Arch root. The root was sealed as a v3 package, threaded into the corrected
Linux 7.1.4 candidate, signed by a separate Ed25519 recovery key, and composed
twice with the shell-free recovery and vendor 5.4 wrapper. Both complete
builds matched byte-for-byte.

The resulting `headless-ssh-deployment-v3` profile passes the real
`artifact-preflight`, including:

- exact wrapper, trust-root, manifest, verifier, kernel, initramfs, and
  configuration hashes;
- twin equality for the recovery initramfs, kernel, raw wrapper, and AVB
  wrapper;
- native signed-bundle verification;
- recovery archive policy verification;
- Android boot-v3 unpacking and kernel/initramfs comparison; and
- AVB footer and embedded boot-descriptor verification.

No `fastboot`, ADB, SSH, host privilege, NFS export, or phone-storage action
occurred. The one authorized temporary boot was not consumed.

## Root and candidate identities

The retained private deployment products remain outside Git:

| Product | Size | SHA-256 |
|---|---:|---|
| source Arch root archive | 536,751,742 | `78888883ed48f1c6dcaa722da28c03cd6342ac56d796c429c3978aabee382724` |
| sealed v3 root archive | 536,746,495 | `4d120a4b3a10be098cea47ba8536969bbaa931b47b31cc37fc3474fea045b324` |
| v3 root manifest | 731 | `9eb60d6e4254986dc8e017fc1dd9d76d699e8d35cb3716d8fdef72ca6df1199d` |
| candidate record | 1,390 | `cda35b12db73966fd231ea6889978da5fbf9ab62375177a21084c2ec822f6bcd` |

The root manifest pins:

```text
root_tree_sha256=f4affd6d83f3af48259c7d7f650e91461465b59e045519310ac81bb5d71a0087
root_seal_sha256=42ef8388bb771fbd0dd8141939b042a89037ea1cf1bec9288f7a3ae51455210a
root_tree_entries=37735
ssh_fingerprint=SHA256:pfraAiWal9h1aErO6SCADKvG5Xai5PJL9HyQshUz7OM
authority=none
```

Clean extraction reproduced the complete root seal before candidate
composition. The candidate is constrained to the tracked corrected-DTB
template except for the six root identity fields.

## Signed target bundle

| Product | Size | SHA-256 |
|---|---:|---|
| Linux 7.1.4 Image | 40,049,152 | `349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf` |
| corrected board DTB | 102,870 | `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46` |
| target initramfs | 5,978,369 | `819bdf88c920057a5d8b511cb13e3adc0f7d8d9cf1a92a7fac087697889bb9b5` |
| signed-bundle manifest | 819 | `457273993a9ce3cb0a9c735ef29e96101c1303720cafefc774aed12972a6926e` |

The verified plan selects:

```text
bundle=headless-ssh-network-root-v3
profile=network-root-v1
target_id=headless-ssh-network-root
target_release=7.1.4-g7a5cef0db479
target_timeout=480
rollback_timeout=600
```

## Recovery and wrapper identities

| Product | Size | SHA-256 |
|---|---:|---|
| framed responder | 132,896 | `c1e1b7b58f36b9ff091bed3b5de463d6239031729a49e12c07064c410de43fd0` |
| fixed-host fetcher | 132,824 | `becc3fc1442823118fa75e79a9b756395df9f1b5b7df37440d4e2c8c5b4ef89c` |
| signed-bundle verifier | 4,467,272 | `374900be5769eee074820007ab2e335d4c033c500da7a480cc88f9a70137029b` |
| host bundle verifier | 48,144 | `9099f5f615144cf95655e6e169ac49b0cbe6f0a6d759441c59bc3130407ab78b` |
| raw Ed25519 trust root | 32 | `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b` |
| shell-free recovery initramfs | 7,593,278 | `4cfc5dfce5babc9ec76ba4a8a10accde6c0ec5f216f65f6e3f669641123a7cc2` |
| vendor 5.4 wrapper config | — | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| vendor 5.4 wrapper Image | 50,498,048 | `00168aafe5aaf4043b5252e116f6216f6d3b6ea03dc382dd630eec6991c3ff66` |
| raw header-v3 wrapper | 58,097,664 | `7227c5b7f10f4c89293dd53c3a060bd39a6aaadc044d23f6d5228f51e56b8380` |
| unsigned AVB wrapper | 100,663,296 | `f8488fe2e88f13b553127896fd1b1477b85bbe5c3aa36a15ab5d884ad87d1fed` |

AVB verification validates the unsigned `NONE` footer and its embedded boot
hash descriptor. It does not assert an AVB signing authority.

The external signing source remains mode `0600` outside the repository. The
builder's private snapshot was destroyed before success; retained build
outputs contain only the raw public trust root and detached signatures.
Private key material and private paths are not recorded here.

## Verification

The chain was built from clean pushed commit
`913a323aaae264daf29dfac7c40fdeefa5845f21`. The build completed:

- two credential-bound target bundles;
- two shell-free recovery initramfses;
- two clean vendor-wrapper kernel builds;
- two raw and unsigned-AVB boot images;
- all recovery candidate integration tests; and
- exact A/B byte comparison.

The new live-gate profile then passed its static guard test and the real
artifact preflight. This proves artifact admission only. It does not prove
USB enumeration, recovery execution, kexec, target SSH, runtime acceptance,
rollback, or fallback recovery on the phone.

## Next gate

Install and verify the reviewed fixed host components and no-replace
read-only NFS export. Then pass local key admission, artifact, cleanup,
fallback-SSH, and connected-fastboot preflights. Only after all of those
checks pass may the separately authorized one-time `fastboot boot` be used.

# Minimal-headless USB/NCM/SSH acceptance — offline

Date: 2026-07-30

Result: **PASS offline; no phone, user credential, signing, boot, reboot, live
network mutation, or storage action**

## Outcome

The corrected minimal-headless candidate's runtime record now binds both sides
of its only control transport. The independent host-key bootstrap already
requires the expected USB product, physical-port continuity, `cdc_ncm`, direct
host `/30` route, and one scanned Ed25519 server key. The target-side probe now
independently requires:

- the exact `1d6b:0104` `ROG5 network root` ConfigFS gadget descriptor,
  strings, and `NFS root over NCM` configuration;
- exactly one `ncm.usb0` function and its exact configuration link;
- a primary `a600000` UDC binding at `high-speed`;
- carrier-up, operational, 1500-MTU `usb0` with only
  `169.254.77.2/30`;
- one exact connected `169.254.77.0/30` route, only the three kernel-default
  IPv4 policy rules, and no IPv4 default route in any table;
- active SSH on port 22 with exactly one current server-side session from
  `169.254.77.1`, with effective policy evaluated for the exact remote address,
  local `169.254.77.2`, and local port 22;
- one valid 256-bit Ed25519 authorized key;
- a valid 256-bit Ed25519 host public key whose wire material is derived from
  and exactly matches the live private host key; and
- the existing locked-root and effective key-only SSH policy.

The canonical record grows from 68 to 88 ordered fields. The host verifier
accepts only the exact new values; fixture-mode output remains permanently
ineligible for live promotion.

## Hostile target fixtures

`scripts/device/test-collect-minimal-headless-runtime.sh` passes the golden
fixture and rejects 46 total core mutations. The 19 USB/NCM/SSH additions
reject:

1. a changed USB descriptor;
2. an additional ConfigFS gadget;
3. an additional gadget configuration;
4. an additional gadget function;
5. a changed NCM configuration link;
6. the secondary USB controller;
7. a deceptive UDC name that merely contains `a600000`;
8. non-high-speed negotiation;
9. a down NCM interface;
10. a changed MTU;
11. a changed connected route;
12. an alternate-table IPv4 default route;
13. an additional IPv4 policy-routing rule;
14. a different SSH peer;
15. a second SSH server session;
16. a non-Ed25519 authorized key;
17. a mismatched host private/public key pair;
18. a changed SSH port; and
19. a changed effective SSH host-key path.

The mismatched-pair case initially exposed an OpenSSH test trap:
`ssh-keygen -l -f PRIVATE_PATH` can use an adjacent `.pub` file. The final
probe derives public material directly from the private key with
`ssh-keygen -y` and compares its canonical key type/blob with the public file.
The hostile mismatch now fails closed.

## Verification

The following checks pass:

| Gate | Result |
|---|---|
| target runtime probe | golden 88-field record plus 46 rejected mutations |
| host runtime verifier | 21 test groups |
| strict-SSH capture runner | one hash-bound collection, private evidence, rollback armed |
| minimal Arch root contract | required `ip`, `ss`, and `sshd` runtime tools |
| retained source and corrected DTB | 53 cases, including the accepted positive case |
| ShellCheck, shell syntax, Python compile, diff whitespace | pass |
| complete repository CI | `PASS repository Linux ci tier` |

The retained source positive case uses clean Linux commit
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`; the corrected DTB remains
102,870 bytes with SHA-256
`86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46`.
No source, DTB, rootfs archive, bundle, or boot image changed.

## Bound identities

```text
13bd3df867027ac594c994a4131b9a7da643648db79cf993d139f3dc0855503e  scripts/device/collect-minimal-headless-runtime.sh
fbec5ddae1d6989e1c5d77175f7ec8b042632fd02f79dc0de6645579ac3246d8  scripts/device/test-collect-minimal-headless-runtime.sh
422470144725dd06df1febe7e456a9f91206be7932a3624ddce03c422a9fcab4  scripts/host/verify-minimal-headless-runtime.py
67ae400e6674249a35d58bc126ea8b8f72db55949de5b9d976765ea5973dae06  scripts/host/test-verify-minimal-headless-runtime.py
64c0b6ab4441035a53140888daca8f91433a1f91cfb48883573e7236eb22529d  scripts/host/run-minimal-headless-runtime-acceptance.sh
b4805ad063b5f543c6738ca28eb556c10c1318a93bb580309ba05c4f4525b1d9  scripts/host/test-run-minimal-headless-runtime-acceptance.sh
8c47b51db5b2c2af4ad0733396d4eebc023451fd091231ad72a34c99f5d02134  scripts/device/verify-staged-arch-headless-rootfs.sh
57d863c8a48d0fde984f86ac237f51872732a022bcb0ca04882b7cec44193700  scripts/host/test-arch-headless-rootfs-contract.sh
223436c93ff22f38efdf54dbb4829f48163de35da067a5306ac2b7132e82b11f  configs/compatibility/rog5-minimal-headless-v1.json
630cefe56a3cac3c76d4822a23bf0ef905d2afb8dccb67c65fd3c9c7af6a7c5  configs/compatibility/rog5-core-source-dtb-v1.json
```

## Safety result

- No command addressed the phone.
- No user/client SSH private key, target known-hosts file, production signing
  key, or external-service credential was opened. Tests used only disposable
  local fixture keys.
- No live host USB/NCM route, firewall, or phone network state changed.
- No retained Podman volume, cache, artifact, filesystem, or phone storage was
  removed or modified.
- No image was signed, flashed, booted, or made live-authorized.
- The rollback watchdog contract remains armed and unchanged.
- The corrected target remains `live-pending` with `authority=none`.

This result strengthens the next observation; it is not evidence that the
corrected target has passed live hardware.

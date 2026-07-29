# Core kernel-source and DTB contract — offline

Date: 2026-07-29

Result: **PASS hardware-free; accepted 7.1.4 baseline verified;
hardware acceptance unproven; authority=none**

## Outcome

The active minimal-headless compatibility suite now checks source and DT
integration in addition to artifact ancestry and Kconfig. The retained clean
Linux 7.1.4 tree passed at exact commit
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`, and the accepted corrected DTB
passed at exact SHA-256
`86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46`.

The verifier reported:

```text
profile=minimal-headless-v1
active_capabilities=6
source_checks=37
dt_checks=21
source_role=baseline
source_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
dtb_role=baseline
dtb_sha256=86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46
hardware_acceptance=unproven
authority=none
status=baseline-verified
```

This proves that the accepted baseline still carries the required Kconfig,
object wiring, OF match tables, SM8350 binding entries, source entry points,
and corrected DT topology for all six active capabilities. It does not prove
that a changed source tree builds, boots, or behaves correctly.

## Mutation coverage

Thirty-seven focused tests passed, including the retained-input positive case.
They reject:

- a non-exact baseline source commit;
- dirty, untracked, ignored-but-required, linked, or non-root source inputs;
- missing Kconfig declarations or Makefile object rules;
- missing OF compatible, match-table attachment/registration, binding
  compatible, or required source entry point, including comments continued by
  C backslash-newline splicing;
- narrowed active-source or DT capability coverage;
- duplicate JSON and source path escape;
- changed board identity or CPU/USB/thermal topology, disabled ancestors,
  missing `#phy-cells`, an alternate enabled UFS/QMP USB3 node, or a DWC3
  `phys` link to anything other than the accepted USB2 PHY;
- enabled UFS, disabled primary USB, missing USB isolation/property state, or
  a changed TSENS sensor count;
- changed DT string or u32 properties; and
- linked or truncated DTBs, or a non-identical baseline DTB.

The synthetic candidate case also passed and reported
`status=compatible-not-accepted`. That path is the regression gate for future
6.x/7.x source and DTB comparisons; it cannot promote hardware acceptance.

The existing 33-case core compatibility suite and corrected-DTB semantic
suite passed after integration. The new focused test is an exact CI entry for
all six active capability rows and runs in both repository test tiers.

## Source identities

```text
65682a641819988982fa44736c6d0c4312338069e205dcfd43d9eac259fc52f2  configs/compatibility/rog5-core-source-dtb-v1.json
ad35ae1fd9dfc0f7b2a5e8fc6a8d46b3e819719ce15bd1f7c9bf694f45b9e858  configs/compatibility/rog5-minimal-headless-v1.json
1028b8edf98d220faea3a396195c2cb24a95c2e3fd4e07f434524ff7fc31f760  scripts/host/verify-core-source-dtb-contract.py
a63f5fa91d05610370cc4c657d86ecf4a015299b5429524b25641f52c694b3a3  scripts/host/test-core-source-dtb-contract.py
283eac49a6eaeffe91c6e499a6677d47b79cc217b0bbbbeed9994be69932916c  scripts/device/verify-recovery-dtb-delta.py
```

## Shared DTB parser hardening

The existing semantic-delta parser now opens each DTB once with no-follow,
checks ordinary-file type and bounded size through `fstat`, verifies the file
did not change while being read, and then parses those exact bytes. Existing
recovery-overlay mutation tests remain green.

## Safety boundary

- No phone was contacted, booted, rebooted, or modified.
- No signing key, SSH key, known-hosts file, or other credential was used.
- No kernel source or retained DTB was modified.
- No host privilege, network, NFS, firewall, or PolicyKit action occurred.
- No storage, Podman volume, image, cache, or artifact was deleted.
- The corrected candidate remains `offline`, `live-pending`, and
  `authority=none`.

See the [contract documentation](../docs/core-source-dtb-contract.md).

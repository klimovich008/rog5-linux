# Current-host core baseline revalidation

Date: 2026-08-02  
Repository checkpoint: `92112b3511bb2d381b740d4f19952ab41071b64a`

## Purpose

Revalidate the real Linux 7.1.4 source and corrected DTB while the phone is in
Alpine fallback rather than fastboot. This is hardware-free evidence only; it
does not grant boot authority or claim phone compatibility.

## Inventory correction

The documented rootless Podman volume `rog5-mainline-v19-source` is absent
from the current host. Three ignored local worktrees remain at the exact
baseline commit and have no tracked or untracked changes:

- `build/linux-stable-v7.1.4-source` — canonical retained oracle;
- `build/linux-stable-v7.1.4-network-root-source`; and
- `build/qemu-linux-source`.

All three report commit
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`. Documentation now names the
canonical retained worktree instead of the absent volume.

## Verification

The focused suite ran with the real clean source enabled:

```sh
ROG5_ACCEPTED_KERNEL_SOURCE="$PWD/build/qemu-linux-source" \
  python3 scripts/host/test-core-source-dtb-contract.py
```

All 74 cases passed, including the exact real-source/real-DTB positive case
and hostile source, topology, thermal, USB, storage-isolation, and parser
mutations.

The canonical retained source then passed the direct baseline verifier with
the corrected DTB:

```text
active_capabilities=6
source_checks=43
dt_checks=23
thermal_cpu_zones=12
thermal_pmic_alarms=5
source_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
dtb_sha256=86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46
hardware_acceptance=unproven
authority=none
status=baseline-verified
```

## Boundary

No credential was read and no phone command was issued. The suite used only
disposable temporary trees; it did not change persistent host configuration,
project inputs, network state, or retained storage. The phone remains
live-pending until an exact generation-3 connected fastboot preflight and
temporary boot complete.

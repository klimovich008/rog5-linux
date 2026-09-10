# WCN6855 enumeration runtime package — offline acceptance and HOLD

Date: 2026-07-27

Result: **PASS offline; UNBOOTED_HOLD**

## Outcome

The exact Linux 7.1.4 WCN6855 kernel, merged board DTB, matching modules,
credential-free root overlay, nested kexec stage, ASUS 5.4.210 wrapper, and
Android boot-header-v3/AVB image now form one reproducible temporary-boot
package. Two complete clean production paths are byte-identical.

The layered verifier accepts the pristine package. Independent mutations to
the DTB, root overlay, and raw boot image are rejected even after each
mutated file's entry in `SHA256SUMS` is refreshed. The root-overlay suite also
rejects a changed QMP module, changed seal, changed probe mode, and injected
NetworkManager credential path.

This is package acceptance, not hardware acceptance. The phone was not
contacted, booted, rebooted, kexeced, flashed, or probed for this checkpoint.
No NFS/RPC service, module, firmware, PCIe controller, radio, scan,
association, hotspot, VPN, or credential was activated. Alpine remained
running and untouched.

## Accepted chain

The package derives from these immutable predecessors:

| Input | SHA-256 |
|---|---|
| accepted network-root v8 manifest | `014ad7322adddfa6f2a91a26d47fe0916e0110d628b934d96bfd8c998457a7a7` |
| accepted v8 kexec stage | `eba1c3b862a47f75fbbcca8baed064baa5ebad37f4f138094a143eef7d062863` |
| accepted v8 target initramfs | `4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac` |
| Arch successor-v3 root | `a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7` |
| Linux source | `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` |
| ASUS wrapper source | `3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8` |
| ASUS source marker | `54ea162415b31227ae50d98806d59179ac2b1acca53d71be1a3f036f9eb92069` |
| accepted wrapper config | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |

The Linux builds used Ubuntu clang 18.1.3, deterministic Kbuild identity and
timestamp, `PYTHONHASHSEED=0`, four compile jobs, one BTF job, rootless
Podman, read-only source/repository mounts, and disabled container networking.
The two wrapper builds used separate empty rootless Podman volumes, eight
jobs, dropped all capabilities, enabled `no-new-privileges`, mounted the
pinned source read-only, and disabled container networking.

## Runtime containment

The package preserves the accepted target initramfs byte-for-byte and changes
only the target `Image`, board DTB, and nested payload manifest in the kexec
stage. The wrapper embeds that exact stage once.

The target kernel has `CONFIG_SCSI_UFSHCD` disabled and contains no UFS
module. The target gate additionally requires:

- OverlayFS root over read-only NFS `169.254.77.1:/`;
- zero physical block devices and zero block-backed mounts;
- exact Linux `7.1.4-g7a5cef0db479`, healthy systemd, and exact USB network;
- an already armed rollback watchdog before any handoff;
- an independent 240-second SysRq fallback watchdog before disarming the old
  watchdog;
- exact root-owned seals and scripts;
- one probe invocation followed by one immediate normal reboot; and
- no retry path.

Wi-Fi modules are blacklisted by default and `wlan0` is held unmanaged.
There are no NetworkManager connection profiles or provider WireGuard
profiles. The attended probe creates a one-attempt marker in `/run`, loads
only power-sequencing, PCI power-control, QMP PCIe PHY, and ath11k modules,
and requires exact PCI `17cb:1103` with subsystem `17cb:0108`. It then
requires `wlan0` to remain down, unmanaged, unassociated, address-free, and
route-free. It does not scan, associate, activate Bluetooth, start an AP,
load credentials, or unload drivers. Fatal logs, RDDM, firmware crashes,
IOMMU faults, pstore changes, failed units, storage appearance, and unsafe
thermals all fail the gate.

## Reproducible artifacts

The complete non-secret record is
[`manifests/wifi-runtime-v1.tsv`](../manifests/wifi-runtime-v1.tsv).

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| ASUS wrapper `Image` | 69,372,416 | `8d299b4e106ff536db12d5a1cc87550c3c8a06accaa0fcdc204b9fbe01ad7241` |
| Linux 7.1.4 `Image` | 40,049,152 | `a4edaee34dca66534cf886fd0daa6068273d4fd722b63960d517ef17699af43e` |
| Linux module archive | 300,648,393 | `e7a2eed91e20742012cc0a1fb893545fc61870ec94ca0ca4add3ee6c41e5300d` |
| merged WCN6855 DTB | 107,038 | `15acdcd6fad910f105047ef53de08b47cafadbbf94827e123931408d92310d89` |
| target initramfs | 5,840,728 | `4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac` |
| kexec stage | 27,036,281 | `db7ea8d967366c67cd85a7ef864b1a9193de8ad1f7791eba5da20a40e9733206` |
| Wi-Fi root overlay | 300,650,470 | `4e2de54fad3476c950cfc1a97ad30d38a8d03810e66665747adc85762faa6025` |
| raw header-v3 image | 96,415,744 | `833e6d67a56bf876746d4391c27af0d6f9a244fb9cd566b3a25cd72912ba350a` |
| AVB image | 100,663,296 | `1a3358d5c3f90453505c37b4637527701bccbcf0761513636368cf25db0577c4` |
| complete manifest | 1,515 | `9bc99cf80a85388aff7732a0101771c7fcdd18479ba287c62a8dc9b22bd523cd` |

The AVB footer reports Algorithm `NONE` and exact partition size
100,663,296 bytes. This image is for a later temporary RAM-only boot and must
never be flashed.

## Verification

The following offline gates pass:

```text
PASS WCN6855 probe is explicit, enumeration-only, storage-free, unmanaged, unassociated, crash-checked, and watchdog-guarded
PASS Wi-Fi root overlay is predecessor-pinned, deterministic, module-complete, auto-probe-locked, credential-clean, mutation-tested, and offline-only
PASS Wi-Fi network-root package is input-pinned, deterministic, credential-free, storage-disabled, and offline-only
PASS Wi-Fi target gate is explicit, watchdog-handed-off, enumeration-only, one-probe, one-reboot, and no-retry
PASS two complete WCN6855 network-root bundles are byte-identical
PASS reproducible WCN6855 network-root bundle; PCIe/QMP/power/ath11k exact, storage disabled, credentials absent, offline validation only
PASS valid Wi-Fi bundle accepted; DTB, overlay, and raw-boot mutations rejected after manifest refresh
PASS Linux rootfs tools pin signed input, preserve metadata, and avoid phone writes
```

The mutation harness initially exposed an environment-isolation defect in
the test itself: exported fixture names activated nested optional test modes.
The harness now captures and unexports those names before invoking the
layered verifier. ShellCheck, syntax checks, the focused contracts, the full
mutation oracle, and the aggregate host-tool suite all pass after that fix.

## HOLD boundary and next steps

Promotion remains `UNBOOTED_HOLD`. The package is not yet present in a
recursively sealed, separately versioned NFS export, and there is no reviewed
host-side one-shot live-window runner for this tier. Offline acceptance does
not grant permission to contact or reboot the phone.

Before one live cycle:

1. derive a separate protected root from the exact successor-v3 archive plus
   this exact overlay;
2. recursively seal and mutation-test that root;
3. add verifier-first bounded NFS and a strict host runner with exact
   fallback and network-root SSH identities;
4. repeat connected fallback, USB, storage, watchdog, NFS, and cleanup
   preflight; and
5. request fresh authorization using the exact phrase:
   `GO WCN6855 enumeration-only one-cycle RAM boot with watchdog and immediate fallback`.

That future phrase would authorize at most one attended temporary boot and
enumeration-only probe. It would not authorize flashing, scanning,
association, AP/hotspot operation, Bluetooth, provider VPN credentials, or a
retry. Any failed or ambiguous prerequisite keeps the decision at HOLD.

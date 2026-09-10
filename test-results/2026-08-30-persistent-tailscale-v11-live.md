# Persistent V11 — firewall and normal reboot PASS

Executable source: `7f7621ce0a11a624d703200e5a65c03127802736`.
Full local CI passed in 697.88s; GitHub run `33299908148` passed exact-head,
merge, QEMU and publication. Active tier: 114.69s alongside kernel compilation;
focused module refresh: 0.08s. No recovery-wrapper rebuild or flash was needed.

## Exact correction and build

- The sole enabled kernel change is `NF_CONNTRACK_MARK=y`. Clean B took
  1171.26s. Image, vmlinux, all 19 power/USB/UFS modules and initramfs are
  byte-identical across clean twins. Final module/archive comparison: 11.40s.
- Image: `bdceaa516cafbe276179344c8d55d78f20319e7cb3f3375498536fca37879806`.
- Initramfs: `1daff38a2059b78d8376af01791fe4173fbe39dd9f1566f8c13f95ed76998b43`.
- Signed manifest: `a684bad14f84251ba342a87bde07da1f7b9aea412275ad124f7000716e94bbe2`.
- Exact old/new QEMU nft check: exit 1 → exit 0. All 19 rebuilt modules load
  without BTF/symbol errors. Their allocated code/data and relocations match
  the deployed modules; debug/BTF metadata is regenerated for the new kernel.
- The existing standalone packager preserves the reviewed normal shutdown
  helper and selects native nftables. Unrelated archive files are unchanged.

## Physical result

- Preflight: exact serial/product/USB path, battery gate yes at 8.675 V,
  unchanged p24 geometry, and clean stop relocking all 117 UFS nodes.
- Only `arch_root_a` transferred: six chunks in **72.816 seconds**. Slot A was
  selected during transfer; slot B was restored only after successful transfer.
  GPT, boot partitions, firmware and slot-A rescue were not flashed.
- First V11 boot: `35fe2a3a-8e9d-4f80-a15a-3ca3cf2a34cd`. Linux USB appeared
  about 30s after reboot; pinned SSH was observed by 68s. The running config
  proves NF_CONNTRACK_MARK=y and the installed exitramfs hash is exact.
- Tailscale retained its enrolled node and both addresses, reached Running
  after automatic NTP synchronization, and reported `Health: []`. Installed
  IPv4/IPv6 nft rules contain connection-mark save/restore. No firewall bypass.
- One normal `systemctl reboot`, without RAM helper replacement or fastboot
  intervention, returned V11 boot `9c752d3d-c7c0-490c-a074-ed73029358b3`.
  Host kernel events show recovery at +23s and Linux NCM at +33s. Pinned SSH
  and healthy enrolled Tailscale were observed by +100s; this is an observation
  bound, not a claim that SSH was unavailable until then.
- Both boots passed initial systemd running, stable key-only SSH, V49 UFS,
  zero UFS error events and exact two-node write scope (sda + sda23). P24 and
  the other protected nodes remain read-only. Battery Full/Good, 100%, 8.659 V,
  29.9°C; side USB online with +272 mA input in the first live sample.

## Retention and remaining work

V10/V9/V8 rollback images and slot A remain intact. Verified V11 sparse SHA-256
is `e6b3afac4369de31c33ba4500c3592d3bcaa8dd6e0c91f75ba393f0465f69996`;
its hash-checked compressed retention copy is 817,729,780 bytes. Disposable
build objects/source copies were removed only after retaining clean artifacts;
the exact source remains reachable and the module-build headers/tools are kept.

Independent peer SSH remains unproven: the separate userspace validation client
still needs account login. Self-connectivity is not peer proof. The preexisting
empty runtime package keyring also causes its background WKD refresh parser to
fail; the kernel change does not fix or hide that. Initial zero-failed-unit
observations are not a long-soak claim. No further kernel candidate is needed
to investigate either userspace/access issue.

# Tailscale enrollment and V10 reboot checkpoint

Enrollment and persisted node identity: PASS. Firewall and persistent shutdown:
correction in progress, not yet accepted for a new release.

- The phone enrolled as `rog5-server`; control connectivity, UDP discovery and
  DERP connectivity passed. No independent tailnet peer was available initially.
- Installed V10 lacks `CONFIG_NF_CONNTRACK_MARK`; its default iptables backend
  also lacks usable MARK compatibility. Native nftables installs the basic
  rules but reports EOPNOTSUPP for connection-mark save/restore.
- Exact deployed config inspection and a check-only nft transaction reproduce
  the gap. The exact deployed Image reproduces the same failure under QEMU,
  with no phone access or persistent firewall changes.
- Separate one-option fragment enables NF_CONNTRACK_MARK. Kconfig adds only
  two disabled options, NET_ACT_CONNMARK=n and NET_ACT_CTINFO=n. The builder
  checks this exact delta before compilation and after the clean build.
- R2 composition defect: V10 packaged the diagnostic bootloader exitramfs,
  not the already-reviewed standalone shutdown helper. The existing standalone
  builder now explicitly accepts V10 and preserves Tailscale runtime contents.
- The reviewed standalone helper was tested with the exact sealed BusyBox and
  substituted only in RAM. One normal systemd reboot returned through the
  slot-B loader without a fastboot command or user intervention.
- Reboot started 2026-08-30 07:06:23 UTC. Target USB returned at 07:06:56.888;
  pinned SSH returned at 07:07:22.964, about 60 seconds after the command.
- New boot ID `2ca47654-0f36-42bf-8f20-12be0d5b9e98`; enrolled node identity
  and both Tailscale addresses persisted with no re-login. WantRunning and
  RunSSH remain true. AutoUpdate.Apply is false for pinned deployment.
- Systemd was running, UFS errors zero, p24 read-only, only the p23 parent and
  partition writable. Battery Full/Good at 8.661 V and 30.0 C; USB online.
- The installed bundle remains V10, so its persistent shutdown and firewall
  defects are not claimed fixed by the RAM-only reboot test.
- Full local CI on `776921e`: PASS in 10m49.800s, alongside kernel compilation.
- Exact-head `8d81ac7` GitHub run `33299000074`: head 6m32s, merge 6m21s,
  QEMU 2m7s and candidate publication 1m6s, all PASS.
- Clean A Image `bdceaa516cafbe276179344c8d55d78f20319e7cb3f3375498536fca37879806`
  passes the same QEMU nft check (old Image exit 1; new Image exit 0).
  All 19 power/USB/UFS modules load successfully with no BTF/symbol errors.
- Rebuilt modules match the deployed allocated code/data sections and their
  relocations. Only debug/BTF/build-ID metadata and the external UFS build's
  `intree` marker are excluded from that equivalence comparison.
- The existing standalone packager can refresh the exact 4+15 module inventory
  for this rebuilt kernel. A fail-first regression covers missing/extra files,
  symlinks and wrong release. Untouched archive files remain byte-identical.
  The resulting A archive passes exact sealed-BusyBox syntax checks.
- Module-refresh focused regression: PASS (0.08s). Active tier after packaging
  correction: PASS (114.69s, concurrent with the six-job clean kernel build).
- A later soak snapshot has one failed background unit:
  `archlinux-keyring-wkd-sync.service`, `fpr_email[1]: unbound variable`.
  This is not a kernel or Tailscale failure and remains unresolved. Do not claim
  the long-running system has zero failed units based on its initial boot.

Next: finish the independent clean B build and exact twin comparisons, then
admit one corrected release. Keep
V10 and slot-A rescue intact. Test encrypted peer SSH only with another
authenticated tailnet peer; self-connectivity is not that proof.

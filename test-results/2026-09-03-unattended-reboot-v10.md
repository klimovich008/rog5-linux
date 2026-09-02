# Installed V10 unattended reboot

Result: **PASS**.

## Question

Does the installed slot-B recovery autonomously return the standalone V10 Arch
server to key-only SSH and healthd after an ordinary reboot, without host/NFS
boot services?

## Timing

- Source boot: `d1668631-bd7d-4cd7-90ca-f48f19590d4b`.
- Destination boot: `ded95724-7b0d-4959-988d-6ebb0ffde268`.
- Reboot request to new boot ID plus systemd `running`: **101.273 seconds**.
- USB disconnect was observed.
- Generation-20 comparison: approximately 380 seconds; current installed boot
  is about 3.75 times faster.

## Post-reboot acceptance

- kernel `7.1.4-g1eea8970e87f` and bundle
  `persistent-native-root-wifi-overlay-v10`;
- P2 `status=PASS`, 117 physical block nodes and zero failed systemd units;
- native Wi-Fi `192.168.1.193/24`, default route, Tailscale and healthd;
- pinned key-only SSH through active `rog5-early-sshd.service`;
- `sshd.service` intentionally inactive;
- exactly `sda` and `sda23` writable;
- `journal_recovery_events=0`, `ufs_error_events=0`;
- battery Good at approximately 8.52 V and 30.2 C;
- rollback timer inactive after acceptance.

No flash, GPT, slot, partition, protected-data or host/NFS boot operation was
performed. This was an ordinary installed reboot using the existing exitrd and
slot-B recovery path.

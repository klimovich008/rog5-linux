# Persistent root overlay V8 live result

Result: **PASS**, with one remaining pre-COMMIT recovery admission issue.

- Candidate: `persistent-native-root-wifi-overlay-v8`.
- Manifest: `3d4d2bfc5cfc54c44ff434503b5fbd8e6aced4f3f94c482b41d3d158cdf03133`.
- Initramfs: `75d56f649a0addf1e52ef34fd010bf7a5bcc803d96eaf33fa4265b7f78075819`.
- Selector-v2: `e86ca7a917d51761a6b6c57759096aa50b6044a5b4d0852b851798963a0887b3`.
- Kernel/DTB are byte-identical to accepted Wi-Fi V3.
- Accepted boots: `6e7281d7-a9ca-4d2d-8c42-387c277f3817` and current
  `ec8f1d5c-cea0-4f05-965c-8ff36d25f81c`.

The exact 16 GiB p23 overlay image booted with p24 read-only. V8 accepted one
successful journal replay belonging only to its sealed loop device:

- `journal_recovery_events=1`;
- `allowed_overlay_recovery_events=1`;
- blocked UFS query/SCSI counts zero;
- UFS error count zero.

It then reached systemd `running`, zero failed units, committed the healthy
trial and disarmed both rollback timers. The current boot reports recovery
counts `0/0` and the same healthy state.

Runtime acceptance:

- root and upper mode `0755`; non-root UID 81 execution passes;
- overlay loop `exec,nodev,nosuid`; p23 parent `noexec`;
- `/persist` service-state image active;
- native Wi-Fi, DHCP/default route, NCM, Tailscale and strict SSH active;
- exactly `sda` and `sda23` writable across 117 UFS nodes; p24 read-only;
- battery Full/Good, USB online and safe temperature;
- zero fatal ext4/UFS/panic/oops signatures.

Pacman keyring initialization populated persistent `/etc/pacman.d/gnupg`; WKD
sync returned success and the keyring survived reboot.

Failures V1–V6 were converted into fixtures and fixes: tmpfs-only attestation,
duplicated writable-UFS checks, mode-0700/non-executable upper, retained empty
`/persist`, and blanket rejection of the owned overlay's successful ext4 replay.

Full local CI passed at the coherent storage checkpoints, most recently in
490.458 seconds for the exact journal-replay policy. Focused/active tests passed
in approximately 3.2 seconds. V8 twin target composition reused the existing
kernel/wrapper cache; no kernel or ASUS wrapper rebuild was needed.

Remaining issue: recovery selector-v2 intermittently falls back to V11 before
the trial helper creates a record. The target is not executed in those cases;
a bounded pre-COMMIT retry selected V8. Keep selector-v2/V11 fallback until that
storage-readiness boundary is made observable and reliable.

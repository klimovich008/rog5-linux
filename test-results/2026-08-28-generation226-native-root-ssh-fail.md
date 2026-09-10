# Generation 226 native-root SSH failure

- Primary question: can clean p24 reach native systemd and strict key-only SSH under a RAM-only kernel?
- Passed stages: exact UFS/p24, read-only mount, root verification, tmpfs OverlayFS, runtime, final storage and switch-root.
- SSH evidence: final sshd exposed and the host pinned one Ed25519 host key; 128 authenticated attempts all exited 255.
- Root cause: p24 `/etc/shadow` retained the locked `root:!…` state; the earlier working initramfs used volatile `root:x`.
- Outcome: Generation 226 consumed; exact slot-A recovery fallback and host cleanup passed; no phone storage write.
- Regression/fix: Generation 227 modifies only OverlayFS `/etc/shadow`, proves the immutable lower remains locked, and keeps password and keyboard-interactive authentication disabled.

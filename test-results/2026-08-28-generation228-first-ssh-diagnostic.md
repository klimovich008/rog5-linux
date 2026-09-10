# Generation 228 first-SSH diagnostic

- Result: consumed successfully; `TARGET_ACCEPTED`; exact slot-A fastboot returned in 184.314 seconds; no phone-storage write.
- Passed: UFS/p24, read-only root verification, tmpfs OverlayFS, switch-root, stable NCM, final host-key pin, one bounded client transcript, one bounded target transcript, and direct restart2.
- Exact initial failure: the client completed KEX, offered the correct Ed25519 key, and timed out after 15.140 seconds. Target sshd accepted the root account lookup, started PAM, and stopped at `PAM: initializing for "root"` before processing the public-key offer.
- State: merged shadow `root:x`, immutable lower shadow locked, authorized-key metadata exact, no `/run/nologin` or `/etc/nologin`, `UsePAM yes`, password and keyboard authentication disabled.
- Root cause: the deliberately early sshd runs before the systemd/PAM dependencies are operational. Blind retries later accumulated OpenSSH source penalties but did not cause the first stall.
- Successor: Generation 229 adds `UsePAM no` only to the volatile strict key-only early-SSH policy, performs one authentication attempt, and restores full systemd/runtime/UFS acceptance.

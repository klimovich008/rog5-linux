# Generation 229 PAM fix pass / p24 content failure

- SSH result: first-attempt key authentication passed in 0.169 seconds with volatile `UsePAM no`; password and keyboard authentication remained disabled.
- Passed: exact UFS/p24, read-only root, tmpfs OverlayFS, switch-root, NCM, host-key pin, UFS link snapshot, and direct slot-A fastboot return.
- Runtime failure: `rog5-p2-ready` exited because `/usr/bin/stat` had an invalid zeroed header. `systemctl` and `tail` were likewise zeroed; systemd, bash, sshd, ssh-keygen, grep, journalctl, and dmesg retained AArch64 headers.
- Source comparison: the verified host ext4 image has correct AArch64 bytes for all sampled files. This is remaining p24 sparse materialization damage, not a kernel or package-architecture defect.
- Intent: `FALLBACK_RETURNED`; Generation 229 is consumed and non-retryable; no phone-storage write occurred.
- Next action: repair p24 with a sparse image that encodes every allocated ext4 block as RAW, including allocated zero bytes, and uses DONT_CARE only for free blocks.

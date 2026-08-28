# Generation 227 native-root SSH failure

- Primary question: does a volatile `root:x` account permit final key-only SSH on native p24?
- Passed: exact UFS/p24, read-only root verification, tmpfs OverlayFS, runtime preparation, `switch-root PASS`, stable NCM, and final Ed25519 host-key pinning.
- Failed: 127 authenticated SSH attempts returned 255. A later bounded verbose attempt received pre-KEX `Not allowed at this time`.
- Fallback: exact slot-A unauthorized recovery and host cleanup passed; durable intent resolved `FALLBACK_RETURNED`; no phone-storage write occurred.
- Corrected diagnosis: exact AArch64 OpenSSH 10.3/PAM controls accept the project key with both `root:x` and the original `root:!…`. The earlier locked-root explanation is disproven. Default source penalties explain the later pre-KEX refusal but not the first failure.
- Successor: Generation 228 performs one client attempt, captures one bounded target OpenSSH/PAM/config/namespace transcript over NCM, and invokes direct restart2. It does not apply a functional SSH-policy guess.

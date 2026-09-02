# Persistent-overlay package-update reboot debugging

Result: **root causes proven; source fixes pass; V9 not yet built**.

The package-updated V8 overlay remained cryptographically and structurally
intact, but its first fresh boots returned to recovery/fastboot before SSH.
Receive-only target stages localized the first boundary to `overlay FAIL`.

A one-use fixed-V11 diagnostic wrapper then mounted p23 and the 16 GiB overlay
image `ro,noload`. It proved:

- ext4 clean, `e2fsck -fn` status 0;
- exact UUID, label and manifest;
- exact shadow, ld cache, update markers and SSH policy;
- `upper` mode changed from `0755` to `0555`;
- stale internal OverlayFS whiteout `work/work/#b` remained.

The exact systemd 261 package contains `usr/lib/tmpfiles.d/root.conf` rule
`z / 555`; pacman's tmpfiles hook intentionally copied that stricter root mode
into the upper layer. The old initramfs accepted only `0755`. Linux 7.1.4
source independently proves OverlayFS cleans stale internal `work/work`
entries on mount, but this project rejects unexpected pre-mount work state.

A bounded repair changed only `upper` to `0755` for the existing V8 policy and
removed exact scratch whiteout `work/work/#b` plus its now-empty internal
directory. Post-repair e2fsck passed, work was empty, manifest unchanged, all
117 UFS nodes relocked, and V11 state/Tailscale restored. No GPT, p24, firmware,
slot or boot partition changed.

The next V8 execution passed every initramfs stage through `switch-root PASS`,
then P2 attestation initiated fallback. Persistent journal gave the exact
message `SSH password authentication is enabled`. Read-only reconstruction of
the merged root proved the actual OpenSSH 10.5 policy remained secure:

- `PasswordAuthentication no`;
- `KbdInteractiveAuthentication no`;
- `PermitRootLogin prohibit-password`;
- `PubkeyAuthentication yes`;
- `UsePAM no`.

OpenSSH 10.5 changed `sshd -T` option names from lowercase to mixed case. P2's
lowercase byte-exact grep therefore misclassified output format as insecure
policy. Failure class: R7.

Source corrections now:

- accept only upper-root modes `0755` or stricter `0555`;
- reject `0500`, `0777`, links and other metadata;
- capture `sshd -T` once as bounded root-only evidence;
- parse option names case-insensitively while requiring one exact two-field
  secure value;
- replay the observed OpenSSH 10.5 casing and hostile duplicates.

The bounded pre-COMMIT recovery successor selected the V8 primary first; after
the P2 parser fallback, installed recovery selected healthy V11. This proves
the retry recovery can reach the accepted primary, while the old installed
recovery still intermittently chooses V11. Both RAM wrapper identities are
consumed and will not be reused.

Focused initramfs/overlay tests and the active tier pass. Claude Opus review
was attempted after two non-discriminating boots but its OAuth session was
expired; systematic debugging continued from retained evidence. Current live
boot is V11 `86be83ad-92fd-467c-a879-46bbb875b871`; the repaired, package-updated
V8 overlay remains on p23. Next build/sign/stage a V9 target with unchanged
kernel/DTB and these initramfs-only fixes.

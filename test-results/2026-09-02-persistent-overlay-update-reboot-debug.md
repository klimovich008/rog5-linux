# Persistent-overlay package-update reboot debugging

Result: **V10 repeat and installed-recovery execution pass; transient fallback resolved**.

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

V9 changed only five initramfs members while reusing the exact V8 kernel and
DTB. Its first boot passed P2, systemd, native Wi-Fi, Tailscale, strict SSH,
the 163-package inventory, healthy-trial commit, rollback disarm, storage scope
and power gates. Bounded-retry recovery was subsequently installed to
`boot_b`; slot A and the old `f2a73030…` restore artifact remain available.

The first persistent repeat selected V9 and passed UFS plus OverlayFS, then
failed `runtime`. Read-only inspection proved systemd 261 had replaced the
empty `/etc/.updated` and `/var/.updated` sentinels with canonical four-line
`systemd-update-done` records sharing one `TIMESTAMP_NSEC`. All other runtime
inputs remained exact. New fail-first tests accept coherent empty or canonical
timestamped pairs and reject changed comments, malformed values and mismatched
timestamps. V10 remains initramfs-only.

Focused initramfs/overlay tests and the active tier pass. Claude Opus review
was attempted after two non-discriminating boots but its OAuth session was
expired; systematic debugging continued from retained evidence. Current live
boot is V10 `43c91566-b125-4da9-a933-af8f3601ea2a`; the healthy V10 trial and
package-updated overlay remain on p23.

V10 reused the exact V9 kernel and DTB and changed only the target initramfs.
Its first boot `2b9c86b0-4817-4891-b3f8-a5e151daf47d` passed all acceptance
gates with one exact allowed overlay journal replay. One subsequent recovery
cycle selected signed V11 despite exact V10 selector and healthy trial bytes.
The exact deployed AArch64 helper returns V10 against that same record through
a read-only bind and leaves its SHA unchanged. The following recovery cycle
selected V10; boot `43c91566-b125-4da9-a933-af8f3601ea2a` passed with clean
`0/0` journal evidence, the exact 163-package inventory, systemd, native Wi-Fi,
Tailscale, key-only SSH, p24 read-only, only `sda,sda23` writable, Full/Good
battery at 30.0 C and no precise fatal or UFS errors.

The recovery publishes exact trial-selection detail at S65 but immediately
overwrites it with S60, while its ACM reporter samples every 250 ms. Both live
logs therefore missed the only record that distinguishes primary, helper
fallback and preflight fallback. Failure class: R3/R8 observability at an
existing fallback boundary. Before claiming unattended reboot reliability,
make S65 observable without weakening healthy/pending semantics or retrying an
ambiguous helper execution, then require consecutive V10 boots.

A fail-first recovery regression now requires S65 to remain active longer than
the 250 ms reporter interval and before S60 replaces it. The source correction
adds one bounded 300 ms delay after publishing the already-existing exact
selection classification; trial semantics, retry policy, watchdogs, bundle
verification and kexec are unchanged. Focused loader/recovery tests and the
3.73-second active tier pass. One full local CI run also passed in about 5.9
minutes. The installed `boot_b` recovery remains unchanged until the correction
passes a separate RAM-only validation.

The RAM-only S65 observer then proved the transient fallback was not a selector
or helper defect. Failed cycles reported
`trial-fallback-prep-mount-recovery-orphan-incompat-a3`: p23 had ext4
`needs_recovery + orphan_present`, and the ASUS 5.4 wrapper lacks modern
`orphan_file` recovery support. V11 mainline recovered the same filesystem.

P23 was quiesced and backed up before modification. The retained sparse archive
is 812,180,590 bytes with SHA-256 `018d895f…6a644`; extraction and every project
file hash passed. Pre/post 16 MiB metadata snapshots and fsck/superblock logs
were retained. One bounded transaction removed only `orphan_file`, ran the
mandatory `e2fsck -fy`, relocked all 117 UFS nodes, and proved p23 clean with
unchanged UUID/label. The first manifest run correctly exposed a changed
Tailscale state image from intervening V11 boots; read-only fsck passed and a
current-state manifest then verified all 16 files.

Afterward, instrumented ASUS recovery selected `trial-primary-a1` immediately.
The same result passed after deliberately using the old exitrd shutdown shape,
and the unchanged installed `boot_b` recovery booted V10
`292e4435-cfa0-4db5-94a0-6c1015e938f2`. Final acceptance passed systemd,
native Wi-Fi, Tailscale, strict SSH, the exact 163-package inventory, p24
read-only, only `sda,sda23` writable, Full/Good battery and `0/0` journal
evidence. The recovery-selection blocker is resolved.

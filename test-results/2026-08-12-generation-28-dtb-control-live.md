# Generation 28 UFS-enabled DTB control: live result

Status: **PASS, consumed, never retry or flash**.

The sole RAM-only lifecycle transferred and committed the exact signed
`persistent-root-dtb-control-v7` bundle. The target used Generation 20's
live-proven UFS-disabled Image with Generation 25's UFS-enabled DTB and the
unchanged persistent initramfs. It enumerated as `ROG5 persistent root` on the
anchored USB port and reached stable NCM 59.723 seconds after lifecycle start.

The deliberate kernel-release mismatch then stopped target init before every
userspace UFS operation and returned exact Alpine. Fallback used a changed boot
ID, passed strict key-only SSH, restored the host profile, resolved the durable
intent as `FALLBACK_RETURNED`, and restored Steam's TCP/8081 socket. Maximum
fallback temperature was 40.8 C. Empty pstore remains inconclusive.

Exact target identities:

- Image: `349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf`;
- DTB: `72c0db7cb2f54055240c420bbcd4fece6f497e1e648ce7081141781bc78f48c2`;
- initramfs: `908f18f752962fae798249060aa8ee4c45673d8795571fbb8883ac4ed8d9e19e`;
- signed manifest: `c4cef9e256708d219c7c77f792dbff43336c5d446d0721048ff471b7c05969ee`;
- AVB wrapper: `5047cfae9fbbeb0b76b59175792fc7e671e5ac94625bb81304d5422dd85024ee`.

No UFS inventory, filesystem operation, or phone-storage access occurred. The
result exonerates the persistent DTB and its enabled nodes when no UFS driver
can bind. Combined with Generation 27, it isolates the remaining early failure
to the rebuilt UFS Image/config lineage or its interaction with active UFS
probing.

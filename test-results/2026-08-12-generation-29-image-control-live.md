# Generation 29 UFS Image control: live result

Status: **PASS, consumed, never retry or flash**.

The sole RAM-only lifecycle transferred and committed the exact signed
`persistent-root-image-control-v8` bundle. The target used the rebuilt UFS
Image from Generations 25/26 with Generation 20's live-proven UFS-disabled
DTB and the unchanged persistent initramfs. It enumerated as
`ROG5 persistent root` on the anchored USB port and reached stable NCM 58.780
seconds after lifecycle start.

The expected no-UFS rollback then returned exact Alpine. Fallback used a
changed boot ID, passed strict key-only SSH, restored the host profile,
resolved the durable intent as `FALLBACK_RETURNED`, and restored Steam's
TCP/8081 socket. Maximum fallback temperature was 40.8 C. Empty pstore remains
inconclusive.

Exact target identities:

- Image: `33366ffb30e453e191538799850ac38857c445c7f34f74d1a1c655f584c07cfb`;
- DTB: `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46`;
- initramfs: `908f18f752962fae798249060aa8ee4c45673d8795571fbb8883ac4ed8d9e19e`;
- signed manifest: `c3cab07c75012941b103a9100e69298ef69de7aa4d73893d6d02ea4602f66f56`;
- AVB wrapper: `0fa7d7511b0acce2427dccbc1c02dfdda6ee95b48040c6e66acb6ff77396f2ec`.

No UFS inventory, filesystem operation, or phone-storage access occurred.
Combined with Generations 27 and 28, this proves the persistent initramfs,
UFS-enabled DTB, and rebuilt Image each reach stable target NCM when active
UFS binding is absent. The Generations 25/26 pre-NCM loss therefore requires
interaction between that Image and enabled UFS hardware; it is not caused by
the rebuilt Image alone.

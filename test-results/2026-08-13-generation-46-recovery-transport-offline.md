# Generation 46 bounded recovery-transport checkpoint

Status: **consumed after successful target execution; no phone-storage access;
never retry or flash**.

Generation 46 retains Generation 45's exact target behavior:

- Image: `719f5ab2ec89ee01df9d3cd8a29a4e56b6e5cc0239a4266ba1b271fb66dd108d`
- DTB: `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`
- target initramfs: `6c06511dbfa69c634a4ce7fa7589176bc8ee8d9c89e2256e8ef2a92341f6d1a9`
- target release: `7.1.4-g07858678c59c`

Only the recovery transport changed. Its fetcher is
`c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3`,
and the deterministic recovery-initramfs twins are
`14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946`.
The unchanged ASUS wrapper Image is embedded in raw twin
`5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b`.
Generation-46 AVB identity is
`d7088753846b5190c18123cea07c81fac82372f03dd677ba8cb4a997ffcb631d`,
with salt `d8060f095f4f3534da9597429805c914b87c362c3f6e78f02e0b15555fc99598`
and digest `89bf56544cef22085beed51c94862d3141ca7bbbb4a72ceb3be33d8eb94e4064`.

Signed bundle twins reproduce manifest
`14f9b93e9951d664e036ef189526bef59a167572dd7a23c052ba56aed9fd44cf`.
Focused claim, lifecycle, stable-gate, admission, and exact artifact tests pass.
The predecessor transport correction passed full local CI in 430 seconds and
exact-head/merge-compat/QEMU CI at `1174e92`. The complete Generation 46
repository CI checkpoint passed in 426.34 seconds. The final role-only fix then
passed local CI in 425.54 seconds and exact-head/merge-compat/QEMU run
`31695782784` before the sole temporary boot.

The first connected preflight at `4383d75` refused before claim creation or
boot because the inventory role began `unissued`, while the generic live gate
accepts only an `unbooted` role. The corrected terminology preserves the same
artifact bytes and authority, adds a direct live-eligibility regression, and
passes the focused current-profile, stable-gate, retention-contract,
descriptor-boundary, and admission suites. No phone operation was consumed by
the refusal. The corrected complete repository CI checkpoint passed in 425.54
seconds.

The sole live cycle then transferred and verified the exact bundle, executed
the target, and proved OF clock-provider publication plus paired cleanup. See
the [live result](2026-08-13-generation-46-qmp-clock-provider-cleanup-live.md).

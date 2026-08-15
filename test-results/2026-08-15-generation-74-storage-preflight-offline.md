# Generation 74 read-only storage-preflight offline checkpoint

Generation 74 is admitted but unissued. It has not contacted or booted the
phone. The operation remains one temporary RAM-only boot with all discovered
phone block devices locked read-only and no mounts.

The changed recovery initramfs was built independently twice and is
byte-identical at SHA-256
`ae7ba9045045e1ac7048dc7061bf9f8c780fa53c43bfd43aebbecb29b03fa9f4`.
Both static contracts and the sealed AArch64 runtime test pass, including the
hostile journal-pending ext4 fixture. The candidate retains the exact
Generation 73 wrapper kernel `8dc38de4…02ae`; only the external initramfs is
new. Two independent header-v3 repacks took 1.735 seconds and produced exact
raw twins `cd9c3451…9d0` and exact 100,663,296-byte AVB twins
`4f7343b1…9d9ca`.

A separate clean wrapper experiment found a release-reproducibility defect
before candidate assembly. Builds A and B took 1079.117 and 1092.784 seconds,
used the same Clang 18.1.3, accepted config `df28224e…578f`, source, and
initramfs, but produced `caaf084c…835` and `84c5e3e7…f05`. The executable
layout was stable; Clang ThinLTO promotion suffixes differed because debug
metadata retained each output directory. A minimal Clang 18 reproduction
became byte-identical with `-fdebug-prefix-map`. The successor builder now
normalizes C and assembly debug paths and writes path-independent build
metadata. The mismatched experimental kernels are retained as non-candidate
evidence and are not present in the manifest.

Focused results after the correction:

- wrapper build contract: 0.045 seconds;
- candidate manifest, policy, claim, and local twin checks: 2.013 seconds;
- generic exact-record claim consumer: 0.269 seconds;
- retention admission: 3.318 seconds;
- executor contract: 0.092 seconds;
- storage initramfs source contract: 0.062 seconds;
- report collector hostile tests: 0.142 seconds;
- sealed AArch64 runtime: pass.

The next step is exact-head local and GitHub CI, followed by one connected
preflight and one claim-consuming RAM-only boot. Generation 73 remains
consumed and must never be retried. Final operator confirmation remains
mandatory before any filesystem resize, GPT change, format, or persistent
phone-storage write.

# Production module input closure — September 22

The retained source at `b5afca52` still has132 active suites PASS; the checkout
started this pass clean at documentation commit `d8b1d73f`. No production source,
accepted artifact pointer, signed fallback or historical result was changed.
[Machine-readable evidence](2026-09-22-production-module-closure.json) records
exact hashes and timings; full private file inventories and build logs remain in
the isolated preparation directory.

The archived historical target has69 module occurrences and54 unique modules.
A read-only comparison found37 nested production modules,8 other loose production
modules, one built-in I2C driver, one separate production touch fixture and three
missing custom helpers. The latter compiled twice against the retained Image/config
kit with clean W=1 and byte-identical outputs in4.225s/4.036s, as recorded in the
[prior preparation report](2026-09-21-display-trial-preparation.md). The UFS
production core contains the exact local-write marker once and the read-only
marker zero times; this extends the earlier BTF-first verifier counterexample.

A new source-level control ran the actual ath11k selector against the selected
production source: the recorded WCN6851 revision1:0x10 was rejected (`-95` rather
than the expected hw1.1 selector). The retained device patch applied cleanly to
an isolated source copy. The exact selector then passed twice, and four ath-family
modules built twice with W=1 in33.755s/33.465s. Output bytes matched across
builds. This is an offline software correction candidate, not phone Wi-Fi proof.

One isolated input tree now contains64 unique production-release modules spanning
historical storage/radio paths and the separate display closure. All staged bytes
were checked against selected hashes; all64 have the exact full vermagic,
0x4c0 module section, no BTF or version section, and a resolved `modinfo`
dependency within the selected set. The I2C GENI driver is recorded as built in
from both config and modules.builtin. Selection and ELF verification took
0.505s/0.369s. This is an ingredient set only; it has no archive, boot image,
claim, signature or admission authority. The Q6 kit's historical schema FAIL
remains open, as does physical qualification.

An isolated production-release module tree was then generated from those exact
64 inputs. The first scratch attempt exposed a missing `modules.order`; `depmod`
returned0 but warned, and the stage correctly refused PASS. The successful tree
preserves the selected board's order for60 modules and appends four separately
built modules. `depmod -ae -F` against the matching `System.map` returned0 with
no warnings in0.125s. An independent pass rehashed all78 tree files, checked64
`modules.dep` rows, and resolved nine key UFS, PAS, ath11k, MSM, panel, touch,
S12, Wi-Fi activator and LPG roots through `modprobe --show-depends` in0.039s.
The obsolete I2C `.ko` is absent; the matching kernel lists it as built in.

A deterministic private `module-root-complete.tar.gz` now contains the64 modules
and14 metadata files, with all78 extracted members byte-checked against the
tree. Its SHA-256 is `bed63b7b07aaf51af5547fc0e5acefe85ac2afd7ab4b127db9fce686306f8a6b`
(2,809,103 bytes, assembled and checked in0.212s). It is an unsigned ingredient
outside Git, not a boot archive or accepted candidate. No old loose `.ko`,
historical descriptor, init script or checksum catalog has been replaced.

The first same-conversation Pro review completed using verified gpt-6-pro/Pro.
Its attached six artifact links returned authenticated404; no proposed patch was
applied. It recommended a fixed production profile, MDT before PAS and an honest
unsigned ingredient stage, while explicitly leaving historical radio contents
and the shared MDT display-loader conflict unresolved. A follow-up with the new
full-module inventory reached the same conversation, but the browser returned
“You've hit your limit”; it produced no reviewed correction. No paid API or
weaker mode was used. The selected module input set therefore does not claim a
coherent target ramdisk or runnable display session.

An isolated archive rehearsal subsequently refreshed the historical newc archive
against the package above. It replaced31 loose modules, removed the historical
I2C `.ko` that is built into the selected kernel, replaced the nested package,
rewrote the 78-entry nested manifest and production `kernel-release`, and
regenerated the boot checksum catalog. The rehearsal deliberately removed
`init`, the consumed trial descriptor and the historical relay nonce, leaving
732 members and **no bootable output**. A full round-trip check passed in2.959s
under a512MiB/no-swap scope (254.4MiB peak); an independent streaming parser
then verified732 members,73 boot-catalog entries and78 nested-manifest entries
in0.372s. The disabled-init archive SHA-256 is
`e25306cb83c1cceb29b670a32788677544ce1228486f8d131cdf1b4b6f2c9ee3`.
This establishes the byte/catalog refresh path only. A runnable composition
still needs a reviewed shared MDT load contract, fresh private trial/health
identity, exact early-module policy and complete offline qualification. No
accepted image, fallback, claim or phone state changed.

The shared MDT conflict now has a direct source-level counterexample. The
production `modprobe --show-depends qcom_q6v5_pas` closure begins with
`mdt_loader`, while the actual display loader checks that every listed module
is absent before entry. Using its existing inert test fixture with only
`mdt_loader` preexisting produced `production module already present:
mdt_loader`, zero insertions and no durable display entry in0.136s. This is
not a phone observation. The loader must not simply skip a preloaded module
without an exact same-boot ownership and identity contract. The Pro follow-up
for this integration remains quota-limited.

The next source task is to review the shared MDT ownership contract with the
display loader and qualify an exact early-module policy before any bootable
composition. Actual private trial identity, health inputs, boot image and state
records remain unissued. The approved USB path was absent at the last exact
host check, so no phone command or physical test ran.

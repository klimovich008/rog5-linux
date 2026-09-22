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

The first same-conversation Pro review completed using verified gpt-6-pro/Pro.
Its attached six artifact links returned authenticated404; no proposed patch was
applied. It recommended a fixed production profile, MDT before PAS and an honest
unsigned ingredient stage, while explicitly leaving historical radio contents
and the shared MDT display-loader conflict unresolved. A follow-up with the new
full-module inventory reached the same conversation, but the browser returned
“You've hit your limit”; it produced no reviewed correction. No paid API or
weaker mode was used. The selected module input set therefore does not claim a
coherent target ramdisk or runnable display session.

The next source task is to refresh every loose/nested module occurrence, release
and checksum catalog in a bounded scratch archive, then review the MDT ownership
contract with the display loader. Actual private trial identity, health inputs,
boot image, and state records remain unissued. The approved USB path was absent
at the last exact host check, so no phone command or physical test ran.

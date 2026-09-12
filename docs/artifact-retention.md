# Retained artifact identities

Use [the current pointer](../manifests/current-artifact.json) to distinguish the
last observed runtime from the prepared signed candidate and new source work.
Neither a directory name nor `status: active` authorizes a boot or installation.
The existing signing, exact-byte admission and consumed-claim checks remain
authoritative. Current review fixes are **NOT INSTALLED**; an affected-driver
compile produces an unsigned test artifact, not a candidate.

[The set inventory](../manifests/artifact-sets.json) contains one manifest object
per retained directory set. It covers all 827 rows in `manifests/artifacts.tsv`,
all 177 tracked artifact files and the named private prepared IOMMU package:
442 sets total. Per-output status resolves mixed sets. `retired` means a retained
consumed/no-retry artifact; `superseded` has an identified replacement; `fixture`
is an offline input; `historical` is retained evidence without current admission;
`active` is a current preparation input, not physical acceptance.

Unknown provenance is explicitly **BLOCKED** (`null` under the inventory's
declared unknown-field convention). A repository commit that stores a blob is
not assumed to be its producing Linux/source commit. Old recorded SHA-256 values
retain their original provenance; this review checked only 68 small tracked
files and did not rehash large images. Unregistered private directories remain
outside this inventory and **BLOCKED pending inventory**. Nothing was deleted,
renamed, rebuilt, signed or re-admitted to fill missing fields.

The tracked `artifacts/buttons-indicator-v1/leds-qcom-lpg.ko` is the
`7.1.4-g7a5cef0db479` source-contract fixture, SHA-256
`5885a9db2a8821f7c0ee9b16d92092d6d44f5c5092561e8e312f6047bb1a246c`.
The separate f17 buttons trial composer requires SHA-256
`681440a4905d930b8b4e8e138020099700390a540ebb2b443941be7f09b914c6`,
vermagic `7.1.4-gf17befd4ef17 SMP preempt mod_unload aarch64`.
Both depend on `led-class-multicolor,qcom-pbs`; dependency names alone do not
make the modules interchangeable. The existing composer's size/hash checks
already reject the tracked old module, regardless of directory name. A new
regression supplies those actual old bytes to the production LPG identity check
and confirms refusal. This discrepancy is documented, not fixed by replacing
historical evidence. Neither module establishes the newer 136f kernel's ABI.

Run `python3 scripts/host/check-artifact-inventory.py` after changing retained
inventory. Record exact source/Linux commits, production patch-series/config
and toolchain hashes, command, ABI/dependencies, inputs/outputs and qualification
in each new set before using it. Missing historical facts remain unknown.

Going forward, put large immutable build outputs in release assets or a
content-addressed artifact store with exact sizes/hashes and retrieval checks.
Keep the minimum fixtures needed for clean offline CI in Git. Migrate existing
large files only after verifying a durable identical copy and their consumers;
do not rewrite history or delete evidence as part of this review. An artifact
store is a storage location, not a substitute for provenance or admission.

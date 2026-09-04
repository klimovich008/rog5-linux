---
name: rog5-fast-loop
description: Change or diagnose this ROG5 project's kernel, modules, DTB, initramfs, recovery, live candidates, charging, UFS, storage or boot chain. Excludes simple status questions.
---

# ROG5 fast loop

Start with `docs/current-state.md`, Git status and HEAD. Then read the latest
relevant result and applicable R1–R10 sections of `docs/development-lessons.md`.
Active context is a pointer, not another required history load. Read the full
pre-build/live checklists before issuing a successor.

State one question and classify the changed layer. Use the smallest artifact:

| Layer | Artifact and checks |
|---|---|
| Observer/userspace | Script only; focused behavior plus active tier |
| Shell/BusyBox or initramfs | Target archive only; exact applets/filesystem and composition |
| Module | Exact .ko plus ABI-dependent modules; vermagic/BTF/closure and active tier |
| DT | DTB only; composition and active tier |
| Built-in kernel/ABI | Locked incremental cached build; focused then full CI |
| Stable recovery/wrapper | Rebuild only for changed kernel/recovery/repack inputs; full CI |
| Shared lifecycle/trust/storage | Focused regression then one full CI at integration |

Documentation, policy, host-only and target-bundle changes must not invalidate
the ASUS wrapper kernel cache. Freeze source before expensive builds/CI and
never edit an active build's inputs. Preserve already verified work.

Use `scripts/host/rog5-dev` and `docs/development.md`. Run target commands
against the exact sealed BusyBox and filesystem, not host GNU utilities.
Relevant prior failures include find -printf, modprobe --first-time, od duplicate
compression, quoting, stat modes, short/full USB paths and missing modules.dep.
The isolated applet runner cannot prove hardware or systemd sandbox behavior.

Optional observations report present/absent/unsupported/error. Abort for wrong
device/slot/topology, unsafe battery/temperature, storage-scope violation,
signature/integrity failure, transport ambiguity or loss of fallback.

Keep exact identity/boot-chain, power/thermal, signatures, storage/backup,
independent watchdog/fallback and permanent non-retry after COMMIT or ambiguous
execution. Existing task authorization remains valid; destructive storage
review stays separate. Packaging never grants boot authority.

Historical QMP-UFS/GPU matrices are nightly unless changed. Do not repeat full
local CI on unchanged source, or full remote CI for admission-only data when
isolated artifact/trust checks suffice. Publication/release gates remain.

One live boot answers one question while collecting adjacent evidence; do not
consume a candidate to discover an optional field. After two non-discriminating
failures at one boundary, stop successors, invoke explicit systematic debugging
or a bounded independent review, verify findings, and reconsider the approach.

Record edit-to-test, build/cache, CI and boot-to-evidence timings, plus whether
the failure was infrastructure or kernel. Update current state and one dated
result only. Recommend global skill changes separately; never edit them here.

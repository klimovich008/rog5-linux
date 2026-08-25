---
name: rog5-fast-loop
description: Change or diagnose this repository's ASUS ROG Phone 5 kernel, modules, DTB, initramfs, recovery, live candidates, charging, UFS, storage, or boot chain. Do not use for simple status or progress questions.
---

# ROG5 Fast Loop

Optimize each iteration for one useful hardware or software answer while keeping
the standalone Arch Linux server objective intact.

## Start

Read only:

- `docs/current-state.md`
- `docs/active-context.md`
- `docs/development-lessons.md`
- the latest test result relevant to the changed track
- `git status` and the current `HEAD`

State one primary question for the iteration. Do not expand into unrelated
subsystems.

## Classify the changed layer

Choose one highest affected layer:

- observer or userspace only
- shell or sealed BusyBox runtime
- kernel module
- initramfs
- DTB
- built-in kernel or ABI
- stable recovery or wrapper
- trust or admission
- destructive storage

Use the cheapest valid artifact:

- Observer/userspace: copy only the script.
- BusyBox target: rebuild only the target initramfs.
- Module: rebuild only the exact `.ko` and ABI-dependent modules.
- DT: rebuild only the DTB.
- Initramfs: rebuild only the target archive.
- Built-in or ABI change: use the exact-state incremental cached kernel build.
- Wrapper: rebuild only when wrapper kernel, recovery initramfs, or repack inputs
  changed.
- Documentation, policy, host tooling, and target-bundle changes must not
  invalidate the ASUS wrapper cache.

Freeze source before an expensive build or CI run. Never edit inputs used by an
active build.

## Prove target compatibility first

Before live hardware, execute every target command against the exact sealed
BusyBox/applets and target filesystem. Prove option and output compatibility;
never infer GNU behavior. Include the established failure shapes when relevant:
`find -printf`, `modprobe --first-time`, `od` duplicate compression, quoting,
`stat` modes, and short versus canonical USB paths.

Observation fields are non-fatal and must report `present`, `absent`,
`unsupported`, or `error`. Abort only for wrong device, slot, or topology;
unsafe battery or temperature; storage-scope violation; signature or integrity
failure; transport ambiguity; or loss of fallback.

## Select one test tier

- Observer, probe, or target-only: focused test plus active tier.
- Module-only: active tier plus exact ABI, vermagic, BTF, and closure checks.
- DT or initramfs composition: focused composition checks plus active tier.
- Kernel, recovery, shared lifecycle, trust, or storage code: one full CI run.
- Historical QMP-UFS and GPU matrices: nightly unless directly changed.

Do not rerun full local CI on unchanged code. Do not run a second full GitHub
suite for admission-only generated data when isolated artifact and trust checks
prove it.

## Live iteration

One live boot answers one primary question and collects all adjacent evidence.
Do not consume a successor for an optional missing observation. Measure:

- edit-to-focused-test time
- build/cache result
- CI tier and duration
- boot-to-evidence time
- whether the cycle found a target defect or infrastructure defect

After two non-discriminating failures at the same boundary, stop issuing
successors. Use systematic debugging or a bounded Opus review, independently
verify its result, and reconsider the architecture.

## Invariants

Preserve:

- exact device, product, topology, slot, and boot-chain checks
- battery and temperature gates
- signed artifact verification
- exact storage-write scope
- independent watchdog and fallback
- permanent non-retry after COMMIT or ambiguous target execution

Keep current documentation compact: update current state and one incident or
result record only. Do not append full lifecycle transcripts to active docs.

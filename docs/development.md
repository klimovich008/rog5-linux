# Development loop

Start at [current state](current-state.md). Work on one question and choose the
cheapest artifact that changes its answer. Historical profile names are not
the active server. In particular, `power-usb-active.json` and its generated
lock still describe the older NFS observer track; they are kept for its
regression/publication contract, not the installed V10 selector.

## Commands and tests

Run these from the repository; `scripts/host/rog5-dev` also works from another
directory. Each command delegates to an existing implementation.

```sh
scripts/host/rog5-dev test active
scripts/host/rog5-dev select --event push BASE HEAD
scripts/host/rog5-dev build-initramfs --help
scripts/host/rog5-dev package --help
scripts/host/rog5-dev check-target --help
```

- Documentation: link/context checks and active tier.
- Observer/userspace: focused behavior tests and active tier; copy only the
  admitted script if no reboot is needed.
- Module: exact `.ko`, ABI/vermagic/BTF and dependency closure; no full kernel
  build unless built-in code or ABI changes. Unsafe unload requires a short boot.
- DT/initramfs: compose only the affected DTB/archive, then test that composition.
- Kernel/recovery/shared lifecycle/trust/storage: focused checks first, one full
  `test ci` on the frozen tree. Historical matrices run `test nightly`.

Do not rerun full local tests without changed code or a new failure. The runner
prints per-suite duration. It parallelizes only explicitly isolated suites;
shared-state tests remain sequential. CI uses this same runner. PR head and
merge validation remain separate; main pushes now select from before/head.
Unknown or unavailable diffs broaden validation. Scheduled/manual validation
runs nightly and QEMU. Required job names are retained, with explicit skipped
merge handling for non-PR runs.

## Packaging without identity-copy scripts

The runtime packager accepts one JSON `--config` containing its non-credential
Configuration fields. Run `package --help` for field names (JSON uses underscores).
All values are strings. Artifact paths resolve relative to the JSON file.
The recipe cannot contain signing-key/output paths, admission authority or
unknown fields; CLI recipe overrides are rejected. Supply the key and a fresh
private output directory separately. The original CLI remains supported.

The packager computes sizes, hashes and the signed manifest from the actual
input bytes and publishes atomically. Do not copy derived hashes into a second
manual signing script. Keep per-cycle private recipes and receipts outside Git.
`build-initramfs` delegates to the qualified base/radio composer; later layer
builders retain their own explicit input contracts.

For a packaging rehearsal, use an ephemeral test key and the retained accepted
Image/DTB/archive. Compare twin outputs and run the native bundle verifier with
that test public key. Such an output is **not trusted by the phone**. Testing
with a test key must never replace production signature verification.

## Exact target filesystem checks

Host QEMU without filesystem isolation previously exposed host `modules.dep`
and hid a real BusyBox failure. The following command extracts the archive into
a disposable root and runs its own BusyBox, using bubblewrap plus static
`qemu-aarch64-static`. No host `/lib`, network or physical device is exposed.

```sh
scripts/host/rog5-dev check-target --release TARGET_RELEASE INITRAMFS -- \
  sh -n /rog5-native-wifi/runtime
scripts/host/rog5-dev check-target --release TARGET_RELEASE \
  --empty-module-index INITRAMFS -- \
  modinfo -F vermagic /rog5-native-wifi/qcom-pon.ko
```

`--empty-module-index` explicitly simulates the trusted pre-switch runtime's
empty mode-0444 index **inside the disposable extraction**. Omit it to test the
original archive. Check expected output as well as status: BusyBox `modinfo`
can exit zero for a missing module. Archive paths precede runtime relocation;
`/rog5-native-wifi` becomes `/run/rog5-native-wifi` during boot. This runner
does not execute init, load modules, emulate hardware or prove systemd behavior.

## Builds, trials and publication

Reuse the retained kernel/DT/modules for host, documentation and userspace
changes. `kernel-build-contract.sh` already enforces locked exact-state
incremental reuse through `INCREMENTAL_BUILD=1`, optional `KBUILD_CCACHE=1`
and bounded `JOBS`. A changed kernel input must invalidate reuse. The existing
ASUS wrapper cache binds actual source, toolchain, config, initramfs and repack
inputs; host docs and target bundle names are not wrapper-kernel inputs.
Keep clean twins when changed recovery/kernel inputs need release reproduction.

Local development path: freeze source; run the appropriate local tests;
compose/package without remote access; validate exact archive, signature,
payload identity and output inventory; retain source SHA and timings. This
path now uses the shared recipe CLI instead of copied scripts requiring a
fresh remote run merely to package unchanged payloads.

Live admission is separate. Existing reviewed device/topology/slot, power,
fallback, artifact and one-use claim checks still apply. This consolidation
does not add a local-CI waiver to a live gate that requires remote evidence.
Publication/release still requires successful CI for the exact commit plus
merge validation where applicable. A shared trust/runtime change receives full
validation. Admission-only generated data need isolated artifact/claim checks,
not another complete run when the already verified source is unchanged.

Do not invoke historical Alpine/NFS live gates for the installed native server.
The native RAM loader and transaction are
`scripts/device/load-native-ram-bundle.sh` and
`scripts/device/execute-native-ram-bundle-transaction.sh`; host admission must
precede them. Neither this command front door nor packaging consumes a claim.
Never retry an ambiguous or post-COMMIT target. The deferred screen test needs
one operator-attended cycle; it is not part of repository consolidation.

## Retention and context

Current state owns accepted identities and links to evidence. Active context
is a pointer; lessons contain failure patterns, not another chronological log.
Use [the archive index](archive/README.md) for superseded instructions. Global
skills/configuration are unchanged; the project debugging skill remains
explicit-only and does not require installing its upstream companion skills.

Before reclaiming a build, check references, mounts/processes, cache twins and
recovery dependencies. Archive the exact tree without dereferencing symlinks,
compare archive members with originals, test restoration, and retain the
archive digest and original path privately. Remove only that verified obsolete
tree; preserve source, cache, unique evidence and recovery inputs.

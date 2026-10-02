# k120 Iris host preparation

Scope: host-only work on `agent/video-iris-k118`, starting from `63117d4b`.
No phone access, boot, flash, install, push, rebase or other branch/ref change.
The phone PIN file was not read. The existing r118 build was not used.

Already completed by the predecessor: k117 patches 0169-0171, firmware-check
and staged encoder tooling, four k117 wrappers. Supplied phone results: F1
H.264/HEVC 300/300 identical, compliance 48/48, clean power-off, five-minute
idle PASS; reload hard-hangs after `mark: remove`. F2r rejects stock-sized
VP9 DPBs with 0x1003; stock counts unchanged, third failure contained. F3 not run.

This round adds 0172-0178, default-off remove/VP9 experiments, built-in cleanup
markers, never-powered probe control and complete configuration capture and a separated remove/init lifecycle guard;
registered actual-C-function and staged-shell fault tests; hardened encoder
stage evidence. Analysis and self-review: [review](../docs/reviews/2026-10-02-video-iris-k120.md).

## Passing host checks

- `python3 scripts/host/check-repository-static.py`: PASS.
- `test-video-iris-k120.py`: 6/6 PASS, including byte equality with the
  fresh full-series source (`ROG5_LINUX_SOURCE=~/.local/state/rog5-iris-k120-prepare-r3/source`).
- `test-video-encoder-trial.py`: 5/5 PASS on host sh and 5/5 PASS with the
  exact target ARM64 BusyBox extracted from the pinned ramdisk base under QEMU.
- `test-production-kernel-build.py`: 13/13 PASS.
- `test-production-build-diagnostics.py`: 17/17 PASS.
- `test-rog5-make-bundle.py`: 15/15 PASS.
- `test-render-current-state.py`: 4/4 PASS.
- `test-rebase-kernel-series.py`: 2/2 PASS (disposable test repositories only).
- Production builder `--prepare-only`: PREPARED on the exact v7.2.7 base,
  all production patches through 0178 apply, config policy passes. This used
  the dirty development tree in `rog5-iris-k120-prepare-r3`, label k0; it is
  **not** a clean committed k120 build. The first preparation caught missing
  new-file mode headers in 0172; corrected and verified on the fresh extract.
- Affected built-in objects and `qcom-iris.o`: ARM64 `W=1` compile PASS, no
  warnings/errors. This used an independent copy of k117 objects and the
  development source, with no Image/modules install/modpost qualification.
  Old build trees were not edited. Log:
  `~/.local/state/rog5-iris-k120-compile/compile-r2.log`; the final 0178
  core guard and combined Iris object also passed in `compile-r3.log`.

## Environment blocks and incomplete release work

`git add` failed with `Read-only file system` at
`~/.local/state/rog5-haven-clean-ci-20260810/.git/worktrees/rog5-video-wt/index.lock`.
The tool sandbox mounts this worktree metadata read-only despite the writable
common Git root, and this session disallows escalation. No bypass, alternate
index/ref update or scratch publication was attempted. No commit was created;
HEAD remains `63117d4b`. All task changes remain in this working tree, including
new untracked patch/test/review files. A commit message ending with the required
coauthor is prepared outside Git under `rog5-iris-k120-work/commit-message.txt`.

Active tier: **BLOCKED**, zero suites reached, 76 blocked. Initial startup
attempts could not write the default HOME scratch parent. After selecting the
writable cache parent, its Unix-socket preflight failed. A separate 49-byte
AF_UNIX socket path produced `PermissionError(1, 'Operation not permitted')`;
this is a sandbox restriction, not a path-length or test assertion failure.
Retained summary:
`~/.local/state/rog5-iris-k120-active-tests-r3/summary.json`.
Full CI has the same mandatory preflight and was not redundantly attempted.
The passing focused suites do not constitute an active/CI tier pass.

The required clean source commit is therefore unavailable. The official
`~/.local/state/rog5-kernel-7.2.7-build-r120` has **not** been created. None of
`main-k120-d15-261002a..d` was packaged or registered, no one-use descriptors
were consumed, and there are no wrapper SHA-256 values to report. DTB d15 stays
unchanged with SHA-256 `16cbb3848624c2b2037821e9a3c9d0374891a9f3e44d41a98d3ebdef4c71b639`.
Recheck this value against the registry before resuming packaging.

## Resume once Git metadata and local test sockets are writable

1. Review `git diff` and the new files, rerun static/focused checks, then
   commit all task changes on **this** branch with the prepared message.
   Require `git status --porcelain` empty. Never amend or rebase prior history.
2. Run the clean production build:

   ```sh
   PATH="$HOME/.local/state/rog5-host-tools/dtschema-2026.6/bin:$PATH" \
     "$HOME/.local/state/rog5-host-tools/dtschema-2026.6/bin/python3" \
     scripts/host/build-rog5-production-kernel.py \
     --linux-git "$HOME/.local/state/rog5-linux-stable-git" \
     --output "$HOME/.local/state/rog5-kernel-7.2.7-build-r120" --label k120 \
     --jobs 4 --ccache "$HOME/.local/state/rog5-host-tools/ccache-4.14/ccache"
   ```

   Require build PASS, `repository.dirty=false`, release `7.2.7-rog5-k120`,
   full-series/config/schema/module/DT checks and exact source identity.
   Run the Iris suite with `ROG5_LINUX_SOURCE` pointing to that build's source.
   Run the active/CI tiers with the documented environment, a short writable
   `ROG5_TEST_TMP_PARENT` and new report directories.
3. From a clean HEAD, run `scripts/host/rog5-make-bundle.py --role main
   --kernel k120 --dtb d15 --date 261002 --name-letter a` (and b/c/d), committing
   each generated registry/docs change on this branch **before the next**
   package. Use the required coauthor line on every commit. If continuing on
   another day, use its YYMMDD consistently for all four names; do not reuse
   burned names. Packaging snapshots HEAD and does not authorize a phone boot.
4. Record each real wrapper digest from `make-bundle.json` and verify against
   `sha256sum package-<bundle>/boot-ram-128m.img`; record the signed bundle,
   descriptor and source SHA. Replace the pending table in video.md with the
   real hashes and commit that report. No push.

On-phone verification remains G1 removal with externally streamed logs,
G2 opt-in VP9 extradata with frame hashes, and G3 staged encoder on a fresh
boot. The [exact G1/G2/G3 steps](../docs/hardware/video.md#k120-trials) explain
the last-marker attribution and how wrapper d is selected. No live
qualification or hardware fix is asserted by these development checks.

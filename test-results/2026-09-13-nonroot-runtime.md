# Non-root runtime permission prerequisite — 2026-09-13

Starting source `a39dfe947a176f9029ff264b4605cedf8e27dc5a`, tree `0417b32feb7f6d0dac8ba0ce9eafdbd607f6b51d`.
Frozen implementation `808b9c0c4d4b6794c097e1ad79fab1bf95d292e8`, tree `0bcde52c9b1cc5b004599bb7dcf64c1cf997081e`.
The final publication commit changes evidence and status metadata only.

The retained extractor forces umask077. Its root-only VM success could not
establish non-owner access: public package executables/directories became0700.
The new explicit `--permission-policy package-read` preserves package group/other
read/execute bits while removing group/other writes and privileged bits. Private
files/directories remain private; the host output directory is0700. The default
owner-only behavior, authentication and fresh-output guards remain intact.

| Personally executed check | Result | Duration |
| --- | --- | --- |
| New profile tests with old extraction behavior | Expected FAIL: six subcases,16 tests run | 0.573s |
| Final focused extraction suite, Python -O | 19 PASS | 0.876s |
| Rootless container, owner-only control | Expected denial, exit126 | 0.294s |
| Rootless container, package-read treatment | Public execute/read; private read denied | 0.294s |
| Frozen-source active tier | 93 PASS;0 FAIL/BLOCKED/SKIPPED;255 NOT_SELECTED | 139.288s |

The real container checks UID/GID1000 against root-owned fixture files, all five
capability sets empty and NoNewPrivs=1. Its account name is the container's
ordinary test account, not the proposed mobile identity. No ARM64 compositor,
bus or seat session is established by this permission test.

Changed source files: `scripts/host/materialize-mobile-runtime.py`,
`scripts/host/test-mobile-runtime-materialization.py`, `docs/development.md`,
`docs/development-lessons.md`. Publication adds this report and its qualification
JSON and updates the existing artifact inventory, pointer, project status and
generated current-state header. Exact commands, logs, hashes, deadlines, limits
and raw expected failures are in [qualification](2026-09-13-nonroot-runtime-qualification.json).
These are locally executed results, not imported GitHub CI results.

The1.61GB retained326-package tree and its manifest are unchanged. No full
replacement was attempted: currently available disk cannot fit a separate copy
while preserving the3GiB reserve. No archive, prior evidence or artifact was
deleted. A bounded separate view with authenticated permission metadata is the
next storage-efficient preparation step; its safety and guest permission
semantics still need testing before use. Existing Denial/engine/AOT bytes can
then be reused; no new build is needed for this session question.

Non-root Denial/native applications, normal-user bus/seat authorization and the
mobile security contract remain **NOT RUN**. This is not logind, lock-screen or
authentication proof. The next physical question remains A660 XR24/fence/readback
on the exact frozen trial, under separate authorization. **No phone operation,
signing, admission/claim, candidate creation or protected-storage mutation occurred.**
Headless S06/R01 FAIL and every historical physical result remain unchanged.

Publication checks also PASS: five optimized metadata regressions, eight mobile
status regressions, artifact inventory, generated-status validation and
`git diff --check`. They took 1.154s combined; the active tier used285.2MiB and no swap.

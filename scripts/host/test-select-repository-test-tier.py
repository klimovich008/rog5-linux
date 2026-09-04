#!/usr/bin/env python3

import importlib.util
import contextlib
import io
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).with_name("select-repository-test-tier.py")
SPEC = importlib.util.spec_from_file_location("tier_selector", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class TierSelectorTest(unittest.TestCase):
    def test_probe_only_changes_use_fast_tier(self) -> None:
        self.assertEqual(
            MODULE.classify(
                [
                    "scripts/device/observe-early-mainline-power.sh",
                    "scripts/host/early-target-diagnostics.py",
                ]
            ),
            ("probe", "no"),
        )

    def test_docs_only_use_active_tier(self) -> None:
        self.assertEqual(
            MODULE.classify(["docs/current-state.md", "README.md"]),
            ("active", "no"),
        )

    def test_agent_guidance_markdown_uses_active_tier(self) -> None:
        for path in ("AGENTS.md", ".agents/skills/rog5-fast-loop/SKILL.md",
                     ".agents/skills/example/references/notes.md"):
            with self.subTest(path=path):
                self.assertEqual(MODULE.classify([path]), ("active", "no"))
                self.assertEqual(MODULE.classify([
                    path, "scripts/host/early-target-diagnostics.py",
                ]), ("probe", "no"))

    def test_agent_runtime_files_and_consumed_evidence_stay_broad(self) -> None:
        # These reports are consumed by runtime builders/compatibility oracles;
        # test-results is not a documentation-only namespace.
        for path in (".agents/skills/example/scripts/check.py",
                     ".agents/skills/example/template.json", ".agents/config.md",
                     "tools/AGENTS.md", "test-results/runtime.json",
                     "test-results/2026-07-26-a660-gmu-resume-entry-v8-live-rejected.md",
                     "test-results/2026-07-22-kernel-20.md"):
            with self.subTest(path=path):
                self.assertEqual(MODULE.classify([path]), ("ci", "yes"))

    def test_shared_lifecycle_uses_full_ci(self) -> None:
        self.assertEqual(
            MODULE.classify(
                ["scripts/host/run-minimal-headless-live-cycle.py"]
            ),
            ("ci", "yes"),
        )

    def test_kernel_dtb_recovery_or_storage_changes_require_qemu(self) -> None:
        for path in (
            "initramfs/network-root-init",
            "dts/qcom/sm8350-asus.dts",
            "patches/linux/ufs.patch",
            "tools/early_target_diag/rog5-early-target-diag.c",
        ):
            with self.subTest(path=path):
                self.assertEqual(MODULE.classify([path])[1], "yes")

    def test_empty_or_unknown_change_fails_to_full_ci(self) -> None:
        self.assertEqual(MODULE.classify([]), ("ci", "yes"))
        self.assertEqual(
            MODULE.classify(["scripts/host/unknown.py"]), ("ci", "yes")
        )


    def test_markdown_outside_documentation_is_not_docs_only(self) -> None:
        for path in (
            "artifacts/qemu-systemd-arm64-v1/README.md",
            "artifacts/kernel-builder-steamdeck-v1/README.md",
            "initramfs/policy.md",
            "tests/fixtures/runtime.md",
            "new-runtime.md",
            "docs/runtime.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(MODULE.classify([path]), ("ci", "yes"))

    def test_documentation_does_not_escalate_known_probe_changes(self) -> None:
        self.assertEqual(MODULE.classify([
            "docs/current-state.md", "scripts/host/early-target-diagnostics.py",
        ]), ("probe", "no"))
        self.assertEqual(MODULE.classify([
            "README.md", "tools/early_target_diag/rog5-early-target-diag.c",
        ]), ("probe", "yes"))

    def test_unknown_paths_always_escalate(self) -> None:
        for path in (".github/workflows/offline-smoke.yml", "manifests/new.json",
                     "scripts/device/kernel-build-contract.sh", "new/input"):
            with self.subTest(path=path):
                self.assertEqual(MODULE.classify(["README.md", path]), ("ci", "yes"))


class GitSelectionTest(unittest.TestCase):
    """Real isolated Git DAGs; no checkout, config changes or repository commits."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="rog5-ci-selection-")
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.git("init", "--quiet")
        repo_patch = patch.object(MODULE, "REPO", self.repo)
        repo_patch.start()
        self.addCleanup(repo_patch.stop)
        self.root = self.commit({"README.md": "initial docs\n"})

    def git(self, *arguments: str, data: bytes | None = None) -> str:
        environment = dict(os.environ, GIT_AUTHOR_NAME="CI test",
                           GIT_AUTHOR_EMAIL="ci@example.invalid",
                           GIT_COMMITTER_NAME="CI test",
                           GIT_COMMITTER_EMAIL="ci@example.invalid")
        return subprocess.run(["git", "-C", str(self.repo), *arguments],
                              input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              env=environment, check=True).stdout.decode().strip()

    def commit(self, files: dict[str, str], *parents: str) -> str:
        # Populate only a private index and object database, never shared refs.
        self.git("read-tree", "--empty")
        for path, content in files.items():
            blob = self.git("hash-object", "-w", "--stdin", data=content.encode())
            self.git("update-index", "--add", "--cacheinfo", "100644", blob, path)
        tree = self.git("write-tree")
        parent_args = [item for parent in parents for item in ("-p", parent)]
        return self.git("commit-tree", tree, *parent_args, data=b"CI fixture\n")

    def select(self, base: str, head: str, event: str) -> tuple[str, str]:
        with contextlib.redirect_stderr(io.StringIO()):
            return MODULE.select(base, head, event)

    def test_push_docs_uses_before_head(self) -> None:
        head = self.commit({"README.md": "updated docs\n"}, self.root)
        self.assertEqual(self.select(self.root, head, "push"), ("active", "no"))

    def test_pr_excludes_base_branch_advancement(self) -> None:
        base = self.commit({"README.md": "initial docs\n", "runtime": "new"}, self.root)
        head = self.commit({"README.md": "updated docs\n"}, self.root)
        self.assertEqual(self.select(base, head, "pull_request"), ("active", "no"))
        # A force push removing runtime MUST use two-dot, not the PR merge base.
        self.assertEqual(self.select(base, head, "push"), ("ci", "yes"))

    def test_merge_selects_actual_merge_resolution(self) -> None:
        head = self.commit({"README.md": "updated docs\n"}, self.root)
        merge = self.commit({"README.md": "updated docs\n", "runtime": "resolution"},
                            self.root, head)
        self.assertEqual(self.select(self.root, head, "pull_request"), ("active", "no"))
        self.assertEqual(self.select(self.root, merge, "merge"), ("ci", "yes"))

    def test_merge_excludes_unchanged_base_runtime(self) -> None:
        base = self.commit({"README.md": "initial docs\n", "runtime": "base"}, self.root)
        head = self.commit({"README.md": "updated docs\n"}, self.root)
        merge = self.commit({"README.md": "updated docs\n", "runtime": "base"}, base, head)
        self.assertEqual(self.select(base, merge, "merge"), ("active", "no"))

    def test_missing_zero_and_invalid_revisions_fail_broad(self) -> None:
        for event in ("pull_request", "push", "merge"):
            for revision in ("", "0" * 40, "f" * 40, "missing-ref", "--all"):
                with self.subTest(event=event, revision=revision):
                    self.assertEqual(self.select(revision, self.root, event), ("ci", "yes"))
                    self.assertEqual(self.select(self.root, revision, event), ("ci", "yes"))

    def test_unrelated_histories_fail_broad_for_pr(self) -> None:
        unrelated = self.commit({"README.md": "unrelated\n"})
        self.assertEqual(self.select(self.root, unrelated, "pull_request"), ("ci", "yes"))

    def test_multiple_merge_bases_fail_broad(self) -> None:
        first = self.commit({"README.md": "first\n"}, self.root)
        second = self.commit({"README.md": "second\n"}, self.root)
        left = self.commit({"README.md": "left\n"}, first, second)
        right = self.commit({"README.md": "right\n"}, second, first)
        self.assertEqual(self.select(left, right, "pull_request"), ("ci", "yes"))

    def test_empty_diff_fails_broad(self) -> None:
        self.assertEqual(self.select(self.root, self.root, "push"), ("ci", "yes"))

    def test_runtime_to_docs_rename_and_deletion_fail_broad(self) -> None:
        base = self.commit({"runtime.md": "identical\n"}, self.root)
        renamed = self.commit({"docs/runtime.md": "identical\n"}, base)
        deleted = self.commit({}, base)
        self.assertEqual(set(MODULE.changed_paths(base, renamed)),
                         {"runtime.md", "docs/runtime.md"})
        for head in (renamed, deleted):
            self.assertEqual(self.select(base, head, "push"), ("ci", "yes"))

    def test_paths_with_newlines_remain_single_paths(self) -> None:
        head = self.commit({"README.md": "initial docs\n", "runtime\nREADME.md": "x"}, self.root)
        self.assertEqual(MODULE.changed_paths(self.root, head), ["runtime\nREADME.md"])
        self.assertEqual(self.select(self.root, head, "push"), ("ci", "yes"))

    def test_manual_and_scheduled_validation_ignore_diff(self) -> None:
        for event in ("schedule", "workflow_dispatch"):
            self.assertEqual(self.select("", "", event), ("nightly", "yes"))

    def test_unknown_event_fails_broad(self) -> None:
        self.assertEqual(self.select(self.root, self.root, "unexpected"), ("ci", "yes"))

    def test_cli_fallback_is_successful_and_machine_readable(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(MODULE.main(["--event", "push", "0" * 40, self.root]), 0)
        self.assertEqual(output.getvalue(), "tier=ci\nqemu=yes\n")


class WorkflowSelectionTest(unittest.TestCase):
    def setUp(self) -> None:
        workflow = SOURCE.parents[2] / ".github/workflows/offline-smoke.yml"
        self.workflow = workflow.read_text()
        self.jobs = dict(re.findall(
            r"^  ([\w-]+):\n(.*?)(?=^  [\w-]+:\n|\Z)",
            self.workflow.split("\njobs:\n", 1)[1], re.M | re.S))

    def test_stable_checks_and_head_identity(self) -> None:
        self.assertEqual(set(self.jobs),
                         {"head-exact", "merge-compat", "candidate-publication", "qemu-system"})
        self.assertNotRegex(self.jobs["head-exact"], r"(?m)^    if:")
        self.assertIn("ref: ${{ github.event.pull_request.head.sha || github.sha }}",
                      self.jobs["head-exact"])
        self.assertIn('test "$actual" = "$expected"', self.jobs["head-exact"])
        self.assertNotIn("paths-ignore:", self.workflow)
        self.assertNotIn("continue-on-error:", self.workflow)

    def test_event_and_revision_wiring(self) -> None:
        self.assertIn("--event '${{ github.event_name }}'", self.jobs["head-exact"])
        self.assertIn("github.event.pull_request.base.sha || github.event.before",
                      self.jobs["head-exact"])
        merge = self.jobs["merge-compat"]
        self.assertIn("--event merge", merge)
        self.assertIn("'${{ github.event.pull_request.base.sha }}' \\\n            HEAD)", merge)
        self.assertNotIn("github.event.pull_request.head.sha", merge)
        self.assertIn("qemu: ${{ steps.select-tier.outputs.qemu }}", merge)

    def test_only_active_skips_bootstrap_after_selection(self) -> None:
        for job_name in ("head-exact", "merge-compat"):
            job = self.jobs[job_name]
            steps = dict(re.findall(
                r"      - name: ([^\n]+)\n(.*?)(?=      - |\Z)", job, re.S))
            for name in ("Bootstrap pinned Android boot tools", "Build canonical boot-v3 template"):
                with self.subTest(job=job_name, step=name):
                    match = re.search(r"^        if: (.+)$", steps[name], re.M)
                    self.assertIsNotNone(match, "bootstrap must be gated by the selected tier")
                    condition = match.group(1)
                    self.assertEqual(condition, "steps.select-tier.outputs.test_tier != 'active'")
                    self.assertLess(job.index("id: select-tier"), job.index("- name: " + name))
                    for tier in ("active", "probe", "ci", "nightly"):
                        translated = condition.replace("steps.select-tier.outputs.test_tier", repr(tier))
                        self.assertEqual(eval(translated, {"__builtins__": {}}), tier != "active")
            self.assertNotIn("        if:", steps["Install native test dependencies"])

    def test_qemu_dependency_and_skipped_semantics(self) -> None:
        job = self.jobs["qemu-system"]
        self.assertIn("needs: [head-exact, merge-compat]", job)
        expression = re.search(r"    if: >-\n(.*?)\n    runs-on:", job, re.S).group(1)
        self.assertIn("!cancelled()", expression)  # Override implicit success() on skipped needs.
        for head_status, merge_status, head_qemu, merge_qemu, cancelled, expected in (
            ("success", "skipped", "yes", "", False, True),  # main/manual/schedule
            ("success", "skipped", "no", "", False, False),  # main docs
            ("success", "success", "no", "no", False, False),  # PR docs
            ("success", "success", "yes", "no", False, True),
            ("success", "success", "no", "yes", False, True),  # merge-only runtime
            ("failure", "success", "yes", "yes", False, False),
            ("success", "failure", "yes", "yes", False, False),
            ("cancelled", "success", "yes", "yes", False, False),
            ("success", "cancelled", "yes", "yes", False, False),
            ("success", "success", "yes", "yes", True, False),
        ):
            with self.subTest(head=head_status, merge=merge_status, qemu=(head_qemu, merge_qemu)):
                translated = " ".join(expression.split())
                for token, value in {
                    "!cancelled()": not cancelled,
                    "needs.head-exact.result": head_status,
                    "needs.merge-compat.result": merge_status,
                    "needs.head-exact.outputs.qemu": head_qemu,
                    "needs.merge-compat.outputs.qemu": merge_qemu,
                }.items():
                    translated = translated.replace(token, repr(value))
                translated = translated.replace("&&", " and ").replace("||", " or ")
                self.assertEqual(eval(translated, {"__builtins__": {}}), expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)

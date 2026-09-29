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
# Stand-ins for a probe-only tool and its QEMU-backed source (the real
# early-target diagnostics were archived on 2026-09-29).
EXAMPLE_PROBE = "scripts/host/example-probe.py"
EXAMPLE_QEMU = "tools/example_probe/example-probe.c"


class TierSelectorTest(unittest.TestCase):
    def tier_tests(self, tier):
        # The runner lists each tier straight from configs/repository-tests.json.
        runner=SOURCE.with_name('test-repository-linux.sh')
        return subprocess.check_output(['bash',str(runner),'--list',tier],text=True).splitlines()

    def test_broad_tiers_retain_all_narrow_tests_once(self):
        narrow=set(self.tier_tests('active'))|set(self.tier_tests('probe'))
        for tier in ('ci','nightly'):
            tests=self.tier_tests(tier)
            self.assertLessEqual(narrow,set(tests))
            self.assertEqual(len(tests),len(set(tests)))

    def test_explicit_development_impact_and_dependencies(self):
        observer='scripts/host/source-teardown-observation.py'
        service='scripts/device/rog5-healthd.py'
        for paths,impact in ((['docs/current-state.md'],'documentation'),
                            ([observer,'README.md','test-results/2026-09-05-headless-acceptance.md'],'read-only-observer'),
                            ([service],'isolated-userspace')):
            d=MODULE.development_decision(paths)
            self.assertTrue(d['eligible'])
            self.assertEqual(d['impact'],impact)
            self.assertFalse(d['remote_ci_before_experiment'])
            self.assertFalse(d['release_qualified'])
            self.assertEqual(d['status'],'NOT RUN')
        for dependency in ('scripts/host/production-ram-trial.py',
                           'packaging/arch/rog5-healthd.service',
                           'initramfs/persistent-root-shutdown-standalone',
                           'scripts/host/new-claim-consumer.py',
                           'new/unknown.py'):
            with self.subTest(dependency=dependency):
                d=MODULE.development_decision([observer,service,dependency])
                self.assertFalse(d['eligible'])
                self.assertTrue(d['remote_ci_before_experiment'])
                self.assertEqual(d['tier'],'ci')
        self.assertFalse(MODULE.development_decision([observer,'test-results/runtime.md'])['eligible'])

    def test_development_mixed_checks_are_unioned(self):
        d=MODULE.development_decision(['scripts/host/source-teardown-observation.py',
                                     'scripts/device/rog5-healthd.py'])
        self.assertIn('scripts/host/test-source-teardown-observation.py',d['focused_tests'])
        self.assertIn('scripts/device/test-rog5-healthd.py',d['focused_tests'])
        self.assertTrue(d['exact_target_required'])
        self.assertTrue(d['service_experiment_required'])
        self.assertFalse(MODULE.development_decision([])['eligible'])

    def test_critical_one_line_paths_cannot_use_development_fast_path(self):
        for path in ('patches/linux/module.patch','dts/qcom/phone.dts',
                     'configs/boot-admission-policy.tsv','initramfs/power',
                     'scripts/device/build-watchdog-module.sh','manifests/power-usb-active.json'):
            d=MODULE.development_decision([path])
            self.assertFalse(d['eligible'])
            self.assertTrue(d['final_composition_required'])

    def test_module_and_registration_checks_are_explicit(self):
        d=MODULE.development_decision(['tools/module_once/module-once.c'])
        self.assertTrue(d['module_ABI_BTF_closure_required'])
        self.assertFalse(d['eligible'])
        d=MODULE.development_decision(['scripts/host/new-claim-consumer.py'])
        self.assertTrue(d['all_admission_consumers_required'])
        self.assertIn('scripts/host/test-install-default-kernel.py',d['optimized_tests'])
        self.assertFalse(d['eligible'])

    def test_cpu_power_cap_is_critical_even_when_mixed_with_observer(self):
        for path in ('scripts/device/cpu-frequency-cap.py','scripts/device/new-power-profile.sh',
                     'scripts/device/headless-cpu-policy.py','packaging/arch/rog5-headless-cpu-policy.service'):
            d=MODULE.development_decision([path,'scripts/host/source-teardown-observation.py'])
            self.assertIn('critical-runtime',d['impact_categories'])
            self.assertEqual(d['tier'],'ci')
            self.assertFalse(d['eligible'])
            self.assertTrue(d['remote_ci_before_experiment'])
            self.assertIn('scripts/host/test-source-teardown-observation.py',d['focused_tests'])

    def test_every_probe_change_runs_its_own_regression_suite(self) -> None:
        selected = set(self.tier_tests("probe"))
        for changed in MODULE.PROBE_ONLY:
            path = Path(changed)
            required = str(path if path.name.startswith("test-")
                           else path.with_name("test-" + path.name))
            with self.subTest(changed=changed):
                self.assertIn(required, selected)
        self.assertIn("scripts/host/test-select-repository-test-tier.py", selected)

    def test_former_probe_only_paths_now_need_ci(self) -> None:
        self.assertEqual(MODULE.PROBE_ONLY, frozenset())
        self.assertEqual(MODULE.classify(["scripts/host/new-probe-tool.py"]), ("ci", "yes"))

    def test_docs_only_use_active_tier(self) -> None:
        self.assertEqual(
            MODULE.classify(["docs/current-state.md", "README.md"]),
            ("active", "no"),
        )

    @patch.object(MODULE, "PROBE_ONLY", frozenset({EXAMPLE_PROBE, EXAMPLE_QEMU}))
    @patch.object(MODULE, "PROBE_QEMU", EXAMPLE_QEMU)
    def test_agent_guidance_markdown_uses_active_tier(self) -> None:
        for path in ("AGENTS.md", "CLAUDE.md", ".claude/skills/rog5-fast-loop/SKILL.md",
                     ".agents/skills/rog5-fast-loop/SKILL.md",
                     ".agents/skills/example/references/notes.md"):
            with self.subTest(path=path):
                self.assertEqual(MODULE.classify([path]), ("active", "no"))
                self.assertEqual(MODULE.classify([
                    path, EXAMPLE_PROBE,
                ]), ("probe", "no"))

    def test_agent_runtime_files_and_consumed_evidence_stay_broad(self) -> None:
        # These reports are consumed by runtime builders/compatibility oracles;
        # test-results is not a documentation-only namespace.
        for path in (".agents/skills/example/scripts/check.py",
                     ".agents/skills/example/template.json", ".agents/config.md",
                     "tools/AGENTS.md", "tools/CLAUDE.md", ".claude/settings.json",
                     "test-results/runtime.json",
                     "test-results/2026-07-26-a660-gmu-resume-entry-v8-live-rejected.md",
                     "test-results/2026-07-22-kernel-20.md"):
            with self.subTest(path=path):
                self.assertEqual(MODULE.classify([path]), ("ci", "yes"))

    def test_shared_lifecycle_uses_full_ci(self) -> None:
        self.assertEqual(
            MODULE.classify(
                ["scripts/host/production-ram-trial.py"]
            ),
            ("ci", "yes"),
        )

    @patch.object(MODULE, "PROBE_ONLY", frozenset({EXAMPLE_PROBE, EXAMPLE_QEMU}))
    @patch.object(MODULE, "PROBE_QEMU", EXAMPLE_QEMU)
    def test_reviewed_narrative_uses_same_ci_and_development_scope(self):
        report = MODULE.NARRATIVE_REPORT
        for paths in ([report], [report, 'docs/current-state.md', 'README.md']):
            self.assertTrue(MODULE.development_decision(paths)['eligible'])
            self.assertEqual(MODULE.classify(paths), ('active', 'no'))
        self.assertEqual(MODULE.classify([
            report, EXAMPLE_PROBE]), ('probe', 'no'))
        for dependency in ('initramfs/native-wifi/runtime',
                           'scripts/host/new-claim-consumer.py',
                           'test-results/runtime.md', 'new/unknown.py'):
            with self.subTest(dependency=dependency):
                self.assertEqual(MODULE.classify([report, dependency]), ('ci', 'yes'))

    def test_kernel_dtb_recovery_or_storage_changes_require_qemu(self) -> None:
        for path in (
            "initramfs/network-root-init",
            "dts/qcom/sm8350-asus.dts",
            "patches/linux/ufs.patch",
            EXAMPLE_QEMU,
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

    @patch.object(MODULE, "PROBE_ONLY", frozenset({EXAMPLE_PROBE, EXAMPLE_QEMU}))
    @patch.object(MODULE, "PROBE_QEMU", EXAMPLE_QEMU)
    def test_documentation_does_not_escalate_known_probe_changes(self) -> None:
        self.assertEqual(MODULE.classify([
            "docs/current-state.md", EXAMPLE_PROBE,
        ]), ("probe", "no"))
        self.assertEqual(MODULE.classify([
            "README.md", EXAMPLE_QEMU,
        ]), ("probe", "yes"))

    def test_unknown_paths_always_escalate(self) -> None:
        for path in (".github/workflows/offline-smoke.yml", "manifests/new.json",
                     "scripts/device/new-kernel-contract.sh", "new/input"):
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

    def test_development_cli_records_exact_objects_without_claiming_tests(self):
        import json
        head=self.commit({'README.md':'changed\n'},self.root)
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(MODULE.main(['--development',self.root,head]),0)
        value=json.loads(output.getvalue())
        self.assertEqual(value['head_revision'],head)
        self.assertEqual(value['head_tree'],self.git('rev-parse',head+'^{tree}'))
        self.assertEqual(value['status'],'NOT RUN')
        self.assertTrue(value['eligible'])
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            MODULE.main(['--development','bad-ref',head])
        self.assertFalse(json.loads(output.getvalue())['eligible'])


class WorkflowSelectionTest(unittest.TestCase):
    def setUp(self) -> None:
        workflow = SOURCE.parents[2] / ".github/workflows/offline-smoke.yml"
        self.workflow = workflow.read_text()
        self.jobs = dict(re.findall(
            r"^  ([\w-]+):\n(.*?)(?=^  [\w-]+:\n|\Z)",
            self.workflow.split("\njobs:\n", 1)[1], re.M | re.S))

    def test_stable_checks_and_head_identity(self) -> None:
        self.assertEqual(set(self.jobs),
                         {"head-exact", "merge-compat", "panel-driver", "board-production"})
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
        self.assertNotIn("ref: ${{ github.event.pull_request.head.sha", merge)

    def test_merge_checkout_survives_ref_regeneration_after_event(self) -> None:
        # Observed CI: same merge parents, different merge SHA by checkout time.
        with tempfile.TemporaryDirectory() as directory:
            def git(*args, data=None):
                return subprocess.check_output(['git','-C',directory,*args],input=data,
                    env=dict(os.environ,GIT_AUTHOR_NAME='Fixture',GIT_AUTHOR_EMAIL='fixture@example.invalid',
                        GIT_COMMITTER_NAME='Fixture',GIT_COMMITTER_EMAIL='fixture@example.invalid'),
                    stderr=subprocess.DEVNULL).decode().strip()
            git('init','-q');tree=git('mktree',data=b'')
            base=git('commit-tree',tree,'-m','base')
            head=git('commit-tree',tree,'-p',base,'-m','head')
            event=git('commit-tree',tree,'-p',base,'-p',head,'-m','event merge')
            regenerated=git('commit-tree',tree,'-p',base,'-p',head,'-m','regenerated merge')
            git('update-ref','refs/pull/1/merge',regenerated)
            merge=self.jobs['merge-compat']
            selected=re.search(r'^          ref: (.+)$',merge,re.M).group(1)
            selected=selected.replace('${{ github.sha }}',event).replace('${{ github.event.pull_request.number }}','1')
            git('checkout','--detach',selected)
            self.assertEqual(git('rev-parse','HEAD'),event,
                'mutable merge ref does not prove the event merge SHA')

    def test_active_has_unpacker_but_skips_unused_boot_template(self) -> None:
        for job_name in ("head-exact", "merge-compat"):
            job = self.jobs[job_name]
            steps = dict(re.findall(
                r"      - name: ([^\n]+)\n(.*?)(?=      - |\Z)", job, re.S))
            # The active composition suite invokes the hash-pinned unpacker.
            # A clean checkout must supply it even without a boot template.
            # Restored from the cache or fetched on a miss, then always verified
            # against the fetcher's pinned hashes, in every tier.
            self.assertIn("path: artifacts/android-boot-tools-v1",
                          steps["Restore pinned Android boot tools"])
            self.assertNotIn("        if:", steps["Restore pinned Android boot tools"])
            self.assertEqual(re.findall(r"^        if: (.+)$", steps["Bootstrap pinned Android boot tools"], re.M),
                             ["steps.boot-tools-cache.outputs.cache-hit != 'true'"])
            self.assertIn("scripts/host/fetch-android-boot-tools.sh",
                          steps["Bootstrap pinned Android boot tools"])
            self.assertNotIn("        if:", steps["Verify pinned Android boot tools"])
            self.assertIn("sha256sum -c -", steps["Verify pinned Android boot tools"])
            for name in ("Build canonical boot-v3 template",):
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

if __name__ == "__main__":
    unittest.main(verbosity=2)

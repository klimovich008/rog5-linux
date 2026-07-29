#!/usr/bin/env python3
"""Mutation tests for the ROG5 core kernel-source and DTB contract."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/host/verify-core-source-dtb-contract.py"
PROFILE = (
    REPO / "configs/compatibility/rog5-core-source-dtb-v1.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "verify_core_source_dtb_contract",
        SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source/DTB verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(
    arguments: list[str],
    *,
    cwd: Path = REPO,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def profile() -> dict[str, object]:
    return json.loads(PROFILE.read_text(encoding="utf-8"))


def render_source_tree(root: Path, contract: dict[str, object]) -> None:
    checks = contract["source_checks"]
    if not isinstance(checks, list):
        raise AssertionError("source checks are not a list")
    for raw in checks:
        if not isinstance(raw, dict):
            raise AssertionError("source check is not an object")
        path = root / str(raw["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        required = raw["required"]
        if not isinstance(required, list):
            raise AssertionError("required source values are not a list")
        kind = raw["kind"]
        lines: list[str] = []
        if kind == "kconfig":
            lines.extend(f"config {value}" for value in required)
        elif kind == "makefile":
            for value in required:
                symbol, object_name = str(value).split(":", 1)
                lines.append(f"obj-$({symbol}) += {object_name}")
        elif kind == "of-match":
            lines.append("static const struct of_device_id fixture[] = {")
            lines.extend(
                f'\t{{ .compatible = "{value}" }},' for value in required
            )
            lines.extend(
                [
                    "\t{}",
                    "};",
                    "MODULE_DEVICE_TABLE(of, fixture);",
                    "static struct platform_driver fixture_driver = {",
                    "\t.driver = {",
                    "\t\t.of_match_table = fixture,",
                    "\t},",
                    "};",
                    "module_platform_driver(fixture_driver);",
                ]
            )
        elif kind == "binding":
            lines.extend(f'  - "{value}"' for value in required)
        elif kind == "source":
            lines.extend(str(value) for value in required)
        else:
            raise AssertionError(f"unknown fixture source kind: {kind}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_NAME": "ROG5 fixture",
            "GIT_AUTHOR_EMAIL": "fixture.invalid@example.invalid",
            "GIT_AUTHOR_DATE": "2026-07-29T00:00:00+00:00",
            "GIT_COMMITTER_NAME": "ROG5 fixture",
            "GIT_COMMITTER_EMAIL": "fixture.invalid@example.invalid",
            "GIT_COMMITTER_DATE": "2026-07-29T00:00:00+00:00",
        }
    )
    subprocess.run(
        ["git", "-C", str(root), "commit", "-q", "-m", "fixture"],
        check=True,
        env=environment,
    )


def dts_text() -> str:
    cpus = "\n".join(
        f'\t\tcpu@{address} {{ compatible = "{compatible}"; }};'
        for address, compatible in (
            ("0", "arm,cortex-a55"),
            ("100", "arm,cortex-a55"),
            ("200", "arm,cortex-a55"),
            ("300", "arm,cortex-a55"),
            ("400", "arm,cortex-a78"),
            ("500", "arm,cortex-a78"),
            ("600", "arm,cortex-a78"),
            ("700", "arm,cortex-x1"),
        )
    )
    return f"""/dts-v1/;

/ {{
\tcompatible = "asus,rog-phone5", "qcom,sm8350";

\tcpus {{
{cpus}
\t}};

\tpsci {{
\t\tcompatible = "arm,psci-1.0";
\t\tmethod = "smc";
\t}};

\tsoc@0 {{
\t\tcpufreq@18591000 {{
\t\t\tcompatible = "qcom,sm8350-cpufreq-epss",
\t\t\t\t     "qcom,cpufreq-epss";
\t\t}};

\t\tufshc@1d84000 {{
\t\t\tcompatible = "qcom,sm8350-ufshc", "qcom,ufshc",
\t\t\t\t     "jedec,ufs-2.0";
\t\t\tstatus = "disabled";
\t\t}};

\t\tphy@1d87000 {{
\t\t\tcompatible = "qcom,sm8350-qmp-ufs-phy";
\t\t\tstatus = "disabled";
\t\t}};

\t\tphy@88e3000 {{
\t\t\tcompatible = "qcom,sm8350-usb-hs-phy",
\t\t\t\t     "qcom,usb-snps-hs-7nm-phy";
\t\t\tstatus = "okay";
\t\t\t#phy-cells = <0>;
\t\t\tphandle = <1>;
\t\t}};

\t\tphy@88e8000 {{
\t\t\tcompatible = "qcom,sm8350-qmp-usb3-dp-phy";
\t\t\tstatus = "disabled";
\t\t}};

\t\tphy@88eb000 {{
\t\t\tcompatible = "qcom,sm8350-qmp-usb3-uni-phy";
\t\t\tstatus = "disabled";
\t\t}};

\t\tusb@a6f8800 {{
\t\t\tcompatible = "qcom,sm8350-dwc3", "qcom,dwc3";
\t\t\tstatus = "okay";
\t\t\tqcom,select-utmi-as-pipe-clk;
\t\t\tusb@a600000 {{
\t\t\t\tcompatible = "snps,dwc3";
\t\t\t\tdr_mode = "peripheral";
\t\t\t\tmaximum-speed = "high-speed";
\t\t\t\tphys = <1>;
\t\t\t\tphy-names = "usb2-phy";
\t\t\t}};
\t\t}};

\t\tusb@a8f8800 {{
\t\t\tcompatible = "qcom,sm8350-dwc3", "qcom,dwc3";
\t\t\tstatus = "disabled";
\t\t}};

\t\tthermal-sensor@c263000 {{
\t\t\tcompatible = "qcom,sm8350-tsens", "qcom,tsens-v2";
\t\t\t#qcom,sensors = <15>;
\t\t}};

\t\tthermal-sensor@c265000 {{
\t\t\tcompatible = "qcom,sm8350-tsens", "qcom,tsens-v2";
\t\t\t#qcom,sensors = <14>;
\t\t}};
\t}};
}};
"""


def build_dtb(path: Path, text: str | None = None) -> None:
    source = path.with_suffix(".dts")
    source.write_text(text if text is not None else dts_text(), encoding="utf-8")
    subprocess.run(
        ["dtc", "-q", "-I", "dts", "-O", "dtb", "-o", str(path), str(source)],
        check=True,
    )


class CoreSourceDtbContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-core-source-dtb-test-"
        )
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "linux"
        self.dtb = self.root / "candidate.dtb"
        self.contract = profile()
        render_source_tree(self.source, self.contract)
        build_dtb(self.dtb)

    def candidate_arguments(self) -> list[str]:
        return [
            "--kernel-source",
            str(self.source),
            "--source-role",
            "candidate",
            "--dtb",
            str(self.dtb),
            "--dtb-role",
            "candidate",
        ]

    def test_metadata_only_passes(self) -> None:
        result = run(["--metadata-only"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("active_capabilities=6", result.stdout)
        self.assertIn("source_checks=37", result.stdout)
        self.assertIn("dt_checks=21", result.stdout)
        self.assertIn("status=metadata-only", result.stdout)
        self.assertIn("authority=none", result.stdout)

    def test_candidate_source_and_dtb_pass(self) -> None:
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("source_role=candidate", result.stdout)
        self.assertIn("dtb_role=candidate", result.stdout)
        self.assertIn("status=compatible-not-accepted", result.stdout)
        self.assertIn("authority=none", result.stdout)

    def test_cli_requires_complete_explicit_mode(self) -> None:
        result = run([])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("one of the arguments", result.stderr)
        result = run(
            [
                "--kernel-source",
                str(self.source),
                "--source-role",
                "candidate",
            ]
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--dtb", result.stderr)

    def test_baseline_source_requires_exact_commit(self) -> None:
        arguments = self.candidate_arguments()
        arguments[3] = "baseline"
        result = run(arguments)
        self.assertEqual(result.returncode, 1)
        self.assertIn("baseline source commit changed", result.stderr)

    def test_dirty_source_fails(self) -> None:
        check = self.contract["source_checks"][0]
        path = self.source / str(check["path"])
        path.write_text(path.read_text() + "# dirty\n", encoding="utf-8")
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn("kernel source tree is dirty", result.stderr)

    def test_untracked_source_file_fails(self) -> None:
        (self.source / "untracked").write_text("x\n", encoding="utf-8")
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn("kernel source tree is dirty", result.stderr)

    def test_linked_source_file_fails(self) -> None:
        check = self.contract["source_checks"][0]
        path = self.source / str(check["path"])
        replacement = path.with_suffix(".real")
        path.rename(replacement)
        path.symlink_to(replacement.name)
        subprocess.run(
            ["git", "-C", str(self.source), "add", "-A"],
            check=True,
        )
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_AUTHOR_NAME": "ROG5 fixture",
                "GIT_AUTHOR_EMAIL": "fixture.invalid@example.invalid",
                "GIT_COMMITTER_NAME": "ROG5 fixture",
                "GIT_COMMITTER_EMAIL": "fixture.invalid@example.invalid",
            }
        )
        subprocess.run(
            ["git", "-C", str(self.source), "commit", "-q", "-m", "link"],
            check=True,
            env=environment,
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "source input is not an ordinary stage-zero tracked blob",
            result.stderr,
        )

    def test_required_source_file_must_remain_tracked(self) -> None:
        check = self.contract["source_checks"][0]
        relative = str(check["path"])
        subprocess.run(
            ["git", "-C", str(self.source), "rm", "-q", "--cached", relative],
            check=True,
        )
        exclude = self.source / ".git/info/exclude"
        exclude.write_text(
            exclude.read_text(encoding="utf-8") + f"\n/{relative}\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.source),
                "-c",
                "user.name=fixture",
                "-c",
                "user.email=fixture.invalid@example.invalid",
                "commit",
                "-q",
                "-m",
                "untrack",
            ],
            check=True,
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "source input is not an ordinary tracked blob",
            result.stderr,
        )

    def mutate_source_check(self, kind: str) -> subprocess.CompletedProcess[str]:
        check = next(
            row
            for row in self.contract["source_checks"]
            if row["kind"] == kind
        )
        path = self.source / str(check["path"])
        required = str(check["required"][0])
        if kind == "makefile":
            symbol, object_name = required.split(":", 1)
            needle = f"obj-$({symbol}) += {object_name}"
        elif kind == "kconfig":
            needle = f"config {required}"
        elif kind == "of-match":
            needle = f'.compatible = "{required}"'
        elif kind == "binding":
            needle = required
        else:
            needle = required
        text = path.read_text(encoding="utf-8")
        self.assertIn(needle, text)
        path.write_text(text.replace(needle, "removed", 1), encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(self.source), "add", str(path)],
            check=True,
        )
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_AUTHOR_NAME": "ROG5 fixture",
                "GIT_AUTHOR_EMAIL": "fixture.invalid@example.invalid",
                "GIT_COMMITTER_NAME": "ROG5 fixture",
                "GIT_COMMITTER_EMAIL": "fixture.invalid@example.invalid",
            }
        )
        subprocess.run(
            ["git", "-C", str(self.source), "commit", "-q", "-m", "mutate"],
            check=True,
            env=environment,
        )
        return run(self.candidate_arguments())

    def test_missing_kconfig_symbol_fails(self) -> None:
        result = self.mutate_source_check("kconfig")
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing Kconfig symbol", result.stderr)

    def test_missing_makefile_rule_fails(self) -> None:
        result = self.mutate_source_check("makefile")
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing Makefile object rule", result.stderr)

    def test_missing_of_compatible_fails(self) -> None:
        result = self.mutate_source_check("of-match")
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing registered OF compatible", result.stderr)

    def test_missing_binding_compatible_fails(self) -> None:
        result = self.mutate_source_check("binding")
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing binding compatible", result.stderr)

    def test_missing_source_literal_fails(self) -> None:
        result = self.mutate_source_check("source")
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing source contract literal", result.stderr)

    def test_of_match_without_registration_fails(self) -> None:
        check = next(
            row
            for row in self.contract["source_checks"]
            if row["kind"] == "of-match"
        )
        path = self.source / str(check["path"])
        text = path.read_text(encoding="utf-8")
        text = text.replace("MODULE_DEVICE_TABLE(of, fixture);", "removed;")
        text = text.replace(
            "module_platform_driver(fixture_driver);",
            "removed_again;",
        )
        path.write_text(text, encoding="utf-8")
        subprocess.run(["git", "-C", str(self.source), "add", str(path)], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(self.source),
                "-c",
                "user.name=fixture",
                "-c",
                "user.email=fixture.invalid@example.invalid",
                "commit",
                "-q",
                "-m",
                "registration",
            ],
            check=True,
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing registered OF compatible", result.stderr)

    def test_of_match_not_attached_to_driver_fails(self) -> None:
        check = next(
            row
            for row in self.contract["source_checks"]
            if row["kind"] == "of-match"
        )
        path = self.source / str(check["path"])
        text = path.read_text(encoding="utf-8").replace(
            ".of_match_table = fixture,",
            ".of_match_table = disconnected,",
        )
        path.write_text(text, encoding="utf-8")
        subprocess.run(["git", "-C", str(self.source), "add", str(path)], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(self.source),
                "-c",
                "user.name=fixture",
                "-c",
                "user.email=fixture.invalid@example.invalid",
                "commit",
                "-q",
                "-m",
                "disconnected-of-match",
            ],
            check=True,
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing registered OF compatible", result.stderr)

    def test_spliced_line_comment_registration_fails(self) -> None:
        check = next(
            row
            for row in self.contract["source_checks"]
            if row["kind"] == "of-match"
        )
        path = self.source / str(check["path"])
        text = path.read_text(encoding="utf-8")
        text = text.replace(
            "module_platform_driver(fixture_driver);",
            "// registration disabled \\\n"
            "module_platform_driver(fixture_driver);",
            1,
        )
        path.write_text(text, encoding="utf-8")
        subprocess.run(["git", "-C", str(self.source), "add", str(path)], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(self.source),
                "-c",
                "user.name=fixture",
                "-c",
                "user.email=fixture.invalid@example.invalid",
                "commit",
                "-q",
                "-m",
                "commented-registration",
            ],
            check=True,
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing registered OF compatible", result.stderr)

    def test_changed_board_compatible_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace("asus,rog-phone5", "asus,mutant", 1),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn("DT check board-identity compatible changed", result.stderr)

    def test_enabled_ufs_fails(self) -> None:
        text = dts_text().replace(
            'compatible = "qcom,sm8350-ufshc", "qcom,ufshc",\n'
            '\t\t\t\t     "jedec,ufs-2.0";\n'
            '\t\t\tstatus = "disabled";',
            'compatible = "qcom,sm8350-ufshc", "qcom,ufshc",\n'
            '\t\t\t\t     "jedec,ufs-2.0";\n'
            '\t\t\tstatus = "okay";',
            1,
        )
        build_dtb(self.dtb, text)
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "forbidden compatible is effectively enabled",
            result.stderr,
        )

    def test_alternate_enabled_ufs_node_fails(self) -> None:
        alternate = """
\t\tufshc@1d85000 {
\t\t\tcompatible = "qcom,sm8350-ufshc", "qcom,ufshc",
\t\t\t\t     "jedec,ufs-2.0";
\t\t\tstatus = "okay";
\t\t};

"""
        build_dtb(
            self.dtb,
            dts_text().replace(
                "\t\tufshc@1d84000 {\n",
                alternate + "\t\tufshc@1d84000 {\n",
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "forbidden compatible is effectively enabled",
            result.stderr,
        )

    def test_alternate_enabled_driver_aliases_fail(self) -> None:
        for compatible in (
            "qcom,ufshc",
            "jedec,ufs-2.0",
            "qcom,sm8350-qmp-usb3-phy",
        ):
            with self.subTest(compatible=compatible):
                alternate = f"""
\t\talternate@9900000 {{
\t\t\tcompatible = "{compatible}";
\t\t\tstatus = "okay";
\t\t}};

"""
                build_dtb(
                    self.dtb,
                    dts_text().replace(
                        "\t\tufshc@1d84000 {\n",
                        alternate + "\t\tufshc@1d84000 {\n",
                        1,
                    ),
                )
                result = run(self.candidate_arguments())
                self.assertEqual(result.returncode, 1)
                self.assertIn(
                    "forbidden compatible is effectively enabled",
                    result.stderr,
                )

    def test_disabled_primary_usb_fails(self) -> None:
        text = dts_text().replace(
            'status = "okay";\n\t\t\tqcom,select-utmi-as-pipe-clk;',
            'status = "disabled";\n\t\t\tqcom,select-utmi-as-pipe-clk;',
            1,
        )
        build_dtb(self.dtb, text)
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn("DT check usb-primary status changed", result.stderr)

    def test_disabled_soc_ancestor_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                "\tsoc@0 {\n",
                '\tsoc@0 {\n\t\tstatus = "disabled";\n',
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn("ancestor is not enabled: /soc@0", result.stderr)

    def test_changed_thermal_sensor_count_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace("#qcom,sensors = <15>;", "#qcom,sensors = <13>;", 1),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn("DT check tsens0 u32 property changed", result.stderr)

    def test_missing_boolean_property_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace("\t\t\tqcom,select-utmi-as-pipe-clk;\n", "", 1),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn("DT check usb-primary property is absent", result.stderr)

    def test_changed_usb_string_property_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                'maximum-speed = "high-speed";',
                'maximum-speed = "super-speed";',
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "DT check usb-primary-dwc3 string property changed",
            result.stderr,
        )

    def test_wrong_usb_phy_reference_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace("phys = <1>;", "phys = <99>;", 1),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "DT check usb-primary-dwc3 phandle property changed",
            result.stderr,
        )

    def test_missing_usb_phy_cells_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace("\t\t\t#phy-cells = <0>;\n", "", 1),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "DT check usb2-phy u32 property is absent: #phy-cells",
            result.stderr,
        )

    def test_truncated_dtb_fails(self) -> None:
        data = self.dtb.read_bytes()
        self.dtb.write_bytes(data[:128])
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn("DTB total size does not equal its file size", result.stderr)

    def test_linked_dtb_fails(self) -> None:
        target = self.root / "real.dtb"
        self.dtb.rename(target)
        self.dtb.symlink_to(target.name)
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn("DTB is not an ordinary file", result.stderr)

    def test_baseline_dtb_requires_exact_identity(self) -> None:
        module = load_module()
        with self.assertRaisesRegex(ValueError, "baseline DTB size changed"):
            module.validate_dtb(
                self.dtb,
                deepcopy(self.contract),
                "baseline",
            )

    def test_profile_cannot_narrow_active_capabilities(self) -> None:
        module = load_module()
        contract = deepcopy(self.contract)
        contract["active_capabilities"].pop()
        with self.assertRaisesRegex(
            ValueError,
            "active capability set differs from compatibility profile",
        ):
            module.validate_contract(REPO, contract)

    def test_every_active_capability_needs_source_coverage(self) -> None:
        module = load_module()
        contract = deepcopy(self.contract)
        contract["source_checks"] = [
            row
            for row in contract["source_checks"]
            if "thermal-readonly" not in row["capabilities"]
        ]
        with self.assertRaisesRegex(
            ValueError,
            "active capability lacks source coverage: thermal-readonly",
        ):
            module.validate_contract(REPO, contract)

    def test_forbidden_inventory_cannot_be_narrowed(self) -> None:
        module = load_module()
        contract = deepcopy(self.contract)
        contract["forbidden_enabled_compatibles"].pop()
        with self.assertRaisesRegex(
            ValueError,
            "forbidden enabled compatible inventory changed",
        ):
            module.validate_contract(REPO, contract)

    def test_every_declared_dtb_capability_needs_dtb_coverage(self) -> None:
        module = load_module()
        contract = deepcopy(self.contract)
        contract["dt_checks"] = [
            row
            for row in contract["dt_checks"]
            if "watchdog-rollback-reboot" not in row["capabilities"]
        ]
        with self.assertRaisesRegex(
            ValueError,
            "active capability lacks DT coverage: watchdog-rollback-reboot",
        ):
            module.validate_contract(REPO, contract)

    def test_duplicate_json_fails(self) -> None:
        duplicate = self.root / "duplicate.json"
        text = PROFILE.read_text(encoding="utf-8")
        duplicate.write_text(
            text.replace(
                '"format": "rog5-core-source-dtb-contract-v1",',
                '"format": "rog5-core-source-dtb-contract-v1",\n'
                '  "format": "rog5-core-source-dtb-contract-v1",',
                1,
            ),
            encoding="utf-8",
        )
        result = run(["--profile", str(duplicate), "--metadata-only"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate JSON field", result.stderr)

    def test_source_check_path_escape_fails(self) -> None:
        module = load_module()
        contract = deepcopy(self.contract)
        contract["source_checks"][0]["path"] = "../escape"
        with self.assertRaisesRegex(ValueError, "source path is unsafe"):
            module.validate_contract(REPO, contract)

    def test_accepted_source_and_dtb_pass_when_explicitly_available(self) -> None:
        source_raw = os.environ.get("ROG5_ACCEPTED_KERNEL_SOURCE", "")
        accepted_dtb = REPO / str(self.contract["accepted_dtb"]["path"])
        if not source_raw or not accepted_dtb.exists():
            self.skipTest("retained accepted source/DTB are optional in CI")
        result = run(
            [
                "--kernel-source",
                source_raw,
                "--source-role",
                "baseline",
                "--dtb",
                str(accepted_dtb),
                "--dtb-role",
                "baseline",
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("status=baseline-verified", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)

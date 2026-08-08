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
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/host/verify-core-source-dtb-contract.py"
PROFILE = (
    REPO / "configs/compatibility/rog5-core-source-dtb-v1.json"
)
DEFAULT_ACCEPTED_KERNEL_SOURCE = (
    REPO / "build/linux-stable-v7.1.4-source"
)


def accepted_kernel_source(
    default: Path = DEFAULT_ACCEPTED_KERNEL_SOURCE,
) -> Path | None:
    override = os.environ.get("ROG5_ACCEPTED_KERNEL_SOURCE", "")
    if override:
        return Path(override)
    if os.path.lexists(default):
        return default
    return None


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
    rendered: dict[Path, list[str]] = {}
    for raw in checks:
        if not isinstance(raw, dict):
            raise AssertionError("source check is not an object")
        path = root / str(raw["path"])
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
        rendered.setdefault(path, []).extend(lines)
    for path, lines in rendered.items():
        path.parent.mkdir(parents=True, exist_ok=True)
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
    cpu_rows = (
        ("cpu0", "0", "arm,cortex-a55", 0),
        ("cpu1", "100", "arm,cortex-a55", 0),
        ("cpu2", "200", "arm,cortex-a55", 0),
        ("cpu3", "300", "arm,cortex-a55", 0),
        ("cpu4", "400", "arm,cortex-a78", 1),
        ("cpu5", "500", "arm,cortex-a78", 1),
        ("cpu6", "600", "arm,cortex-a78", 1),
        ("cpu7", "700", "arm,cortex-x1", 2),
    )
    cpus = "\n".join(
        f"""\t\t{label}: cpu@{address} {{
\t\t\tcompatible = "{compatible}";
\t\t\tdevice_type = "cpu";
\t\t\tenable-method = "psci";
\t\t\t#cooling-cells = <2>;
\t\t\treg = <0 0x{address}>;
\t\t\tclocks = <2 {domain}>;
\t\t\tqcom,freq-domain = <2 {domain}>;
\t\t}};"""
        for label, address, compatible, domain in cpu_rows
    )
    cpu_zone_rows = (
        ("cpu0-thermal", 1, ("cpu0", "cpu1", "cpu2", "cpu3")),
        ("cpu1-thermal", 2, ("cpu0", "cpu1", "cpu2", "cpu3")),
        ("cpu2-thermal", 3, ("cpu0", "cpu1", "cpu2", "cpu3")),
        ("cpu3-thermal", 4, ("cpu0", "cpu1", "cpu2", "cpu3")),
        ("cpu4-top-thermal", 7, ("cpu4", "cpu5", "cpu6", "cpu7")),
        ("cpu5-top-thermal", 8, ("cpu4", "cpu5", "cpu6", "cpu7")),
        ("cpu6-top-thermal", 9, ("cpu4", "cpu5", "cpu6", "cpu7")),
        ("cpu7-top-thermal", 10, ("cpu4", "cpu5", "cpu6", "cpu7")),
        ("cpu4-bottom-thermal", 11, ("cpu4", "cpu5", "cpu6", "cpu7")),
        ("cpu5-bottom-thermal", 12, ("cpu4", "cpu5", "cpu6", "cpu7")),
        ("cpu6-bottom-thermal", 13, ("cpu4", "cpu5", "cpu6", "cpu7")),
        ("cpu7-bottom-thermal", 14, ("cpu4", "cpu5", "cpu6", "cpu7")),
    )
    cpu_zones: list[str] = []
    for zone_number, (
        zone_name,
        sensor_index,
        cooling_cpus,
    ) in enumerate(cpu_zone_rows):
        label = zone_name.replace("-", "_")
        cooling = ", ".join(
            f"<&{cpu} 0xffffffff 0xffffffff>"
            for cpu in cooling_cpus
        )
        trip0_phandle = 0x100 + zone_number * 2
        trip1_phandle = trip0_phandle + 1
        cpu_zones.append(
            f"""\t\t{zone_name} {{
\t\t\tpolling-delay-passive = <250>;
\t\t\tthermal-sensors = <&tsens0 {sensor_index}>;
\t\t\ttrips {{
\t\t\t\t{label}_trip0: trip-point0 {{
\t\t\t\t\ttemperature = <90000>;
\t\t\t\t\thysteresis = <2000>;
\t\t\t\t\ttype = "passive";
\t\t\t\t\tphandle = <0x{trip0_phandle:x}>;
\t\t\t\t}};
\t\t\t\t{label}_trip1: trip-point1 {{
\t\t\t\t\ttemperature = <95000>;
\t\t\t\t\thysteresis = <2000>;
\t\t\t\t\ttype = "passive";
\t\t\t\t\tphandle = <0x{trip1_phandle:x}>;
\t\t\t\t}};
\t\t\t\t{label}_crit: cpu-crit {{
\t\t\t\t\ttemperature = <110000>;
\t\t\t\t\thysteresis = <1000>;
\t\t\t\t\ttype = "critical";
\t\t\t\t}};
\t\t\t}};
\t\t\tcooling-maps {{
\t\t\t\tmap0 {{
\t\t\t\t\ttrip = <&{label}_trip0>;
\t\t\t\t\tcooling-device = {cooling};
\t\t\t\t}};
\t\t\t\tmap1 {{
\t\t\t\t\ttrip = <&{label}_trip1>;
\t\t\t\t\tcooling-device = {cooling};
\t\t\t\t}};
\t\t\t}};
\t\t}};"""
        )
    pmic_rows = (
        ("pm8350", 1, "pm8350-thermal", "pm8350c-crit"),
        ("pm8350c", 2, "pm8350c-thermal", "pm8350c-crit"),
        ("pm8350b", 3, "pm8350b-thermal", "pm8350c-crit"),
        ("pmr735a", 4, "pmr735a-thermal", "pmr735a-crit"),
        ("pmr735b", 5, "pmr735b-thermal", "pmr735a-crit"),
    )
    pmic_alarm_nodes = "\n".join(
        f"""\t\t\tpmic@{sid} {{
\t\t\t\t{label}_alarm: temp-alarm@a00 {{
\t\t\t\t\tcompatible = "qcom,spmi-temp-alarm";
\t\t\t\t\treg = <0xa00>;
\t\t\t\t\tinterrupts = <{sid} 10 0 3>;
\t\t\t\t\t#thermal-sensor-cells = <0>;
\t\t\t\t}};
\t\t\t}};"""
        for label, sid, _zone_name, _critical_name in pmic_rows
    )
    pmic_zones = "\n".join(
        f"""\t\t{zone_name} {{
\t\t\tpolling-delay-passive = <100>;
\t\t\tthermal-sensors = <&{label}_alarm>;
\t\t\ttrips {{
\t\t\t\t{label}_trip0: trip0 {{
\t\t\t\t\ttemperature = <95000>;
\t\t\t\t\thysteresis = <0>;
\t\t\t\t\ttype = "passive";
\t\t\t\t}};
\t\t\t\t{label}_crit: {critical_name} {{
\t\t\t\t\ttemperature = <115000>;
\t\t\t\t\thysteresis = <0>;
\t\t\t\t\ttype = "critical";
\t\t\t\t}};
\t\t\t}};
\t\t}};"""
        for label, _sid, zone_name, critical_name in pmic_rows
    )
    return f"""/dts-v1/;

/ {{
\t#address-cells = <2>;
\t#size-cells = <2>;
\tcompatible = "asus,rog-phone5", "qcom,sm8350";

\tmemory@80000000 {{
\t\tdevice_type = "memory";
\t\treg = <0 0x80000000 0 0x37100000>,
\t\t      <2 0 1 0x80000000>,
\t\t      <0 0xc0000000 1 0x40000000>,
\t\t      <0 0xb9500000 0 0>;
\t}};

\tcpus {{
\t\t#address-cells = <2>;
\t\t#size-cells = <0>;
{cpus}
\t}};

\tpsci {{
\t\tcompatible = "arm,psci-1.0";
\t\tmethod = "smc";
\t}};

\tthermal-zones {{
{chr(10).join(cpu_zones)}
{pmic_zones}
\t}};

\tsoc@0 {{
\t\tgic: interrupt-controller@17a00000 {{
\t\t\tcompatible = "arm,gic-v3";
\t\t\t#interrupt-cells = <3>;
\t\t\tinterrupt-controller;
\t\t\tphandle = <3>;
\t\t}};

\t\tpdc: interrupt-controller@b220000 {{
\t\t\tcompatible = "qcom,sm8350-pdc";
\t\t\t#interrupt-cells = <2>;
\t\t\tinterrupt-controller;
\t\t\tinterrupt-parent = <&gic>;
\t\t}};

\t\tcpufreq@18591000 {{
\t\t\tcompatible = "qcom,sm8350-cpufreq-epss",
\t\t\t\t     "qcom,cpufreq-epss";
\t\t\t#clock-cells = <1>;
\t\t\t#freq-domain-cells = <1>;
\t\t\tphandle = <2>;
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

\t\ttsens0: thermal-sensor@c263000 {{
\t\t\tcompatible = "qcom,sm8350-tsens", "qcom,tsens-v2";
\t\t\t#qcom,sensors = <15>;
\t\t\t#thermal-sensor-cells = <1>;
\t\t\tinterrupt-names = "uplow", "critical";
\t\t\tinterrupts-extended = <&pdc 26 4>, <&pdc 28 4>;
\t\t}};

\t\ttsens1: thermal-sensor@c265000 {{
\t\t\tcompatible = "qcom,sm8350-tsens", "qcom,tsens-v2";
\t\t\t#qcom,sensors = <14>;
\t\t\t#thermal-sensor-cells = <1>;
\t\t\tinterrupt-names = "uplow", "critical";
\t\t\tinterrupts-extended = <&pdc 27 4>, <&pdc 29 4>;
\t\t}};

\t\tspmi@c440000 {{
{pmic_alarm_nodes}
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
        self.assertIn("source_checks=43", result.stdout)
        self.assertIn("dt_checks=23", result.stdout)
        self.assertIn("thermal_cpu_zones=12", result.stdout)
        self.assertIn("thermal_pmic_alarms=5", result.stdout)
        self.assertIn("thermal_forced_fallback=pending", result.stdout)
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
        return self.mutate_source_check_id(str(check["id"]))

    def mutate_source_check_id(
        self,
        identity: str,
        requirement_index: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        check = next(
            row
            for row in self.contract["source_checks"]
            if row["id"] == identity
        )
        path = self.source / str(check["path"])
        required = str(check["required"][requirement_index])
        kind = str(check["kind"])
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
        self.commit_source_change(path)
        return run(self.candidate_arguments())

    def commit_source_change(
        self,
        path: Path,
        message: str = "mutate",
    ) -> None:
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
            ["git", "-C", str(self.source), "commit", "-q", "-m", message],
            check=True,
            env=environment,
        )

    def reset_source(self) -> None:
        shutil.rmtree(self.source)
        render_source_tree(self.source, self.contract)

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

    def test_each_thermal_safety_source_contract_is_enforced(self) -> None:
        identities = (
            "thermal-tsens-critical-source",
            "thermal-tsens-v2-feature-source",
            "thermal-critical-core-source",
            "thermal-hw-protection-source",
            "thermal-pmic-alarm-source",
        )
        for identity in identities:
            check = next(
                row
                for row in self.contract["source_checks"]
                if row["id"] == identity
            )
            for requirement_index in range(len(check["required"])):
                with self.subTest(
                    source_check=identity,
                    requirement=requirement_index,
                ):
                    self.reset_source()
                    result = self.mutate_source_check_id(
                        identity,
                        requirement_index,
                    )
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(
                        f"source check {identity} "
                        "missing source contract literal",
                        result.stderr,
                    )

    def test_thermal_driver_registration_contracts_are_enforced(self) -> None:
        for identity in (
            "thermal-tsens-of-match",
            "thermal-pmic-of-match",
        ):
            with self.subTest(source_check=identity):
                self.reset_source()
                result = self.mutate_source_check_id(identity)
                self.assertEqual(result.returncode, 1)
                self.assertIn(
                    f"source check {identity} "
                    "missing registered OF compatible",
                    result.stderr,
                )

    def test_source_whitespace_normalization_is_scoped(self) -> None:
        check = next(
            row
            for row in self.contract["source_checks"]
            if row["id"] == "thermal-critical-core-source"
        )
        path = self.source / str(check["path"])
        text = path.read_text(encoding="utf-8")
        needle = "static void thermal_zone_device_halt("
        self.assertIn(needle, text)
        path.write_text(
            text.replace(
                needle,
                "static\nvoid thermal_zone_device_halt(",
                1,
            ),
            encoding="utf-8",
        )
        self.commit_source_change(path, "split-unapproved-literal")
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "source check thermal-critical-core-source "
            "missing source contract literal",
            result.stderr,
        )

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

    def test_changed_memory_bank_geometry_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace("0x37100000", "0x37000000", 1),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "DT check memory-banks u32 property changed: reg",
            result.stderr,
        )

    def test_changed_root_cell_widths_fail(self) -> None:
        mutations = (
            (
                "\t#address-cells = <2>;",
                "\t#address-cells = <1>;",
                "#address-cells",
            ),
            (
                "\t#size-cells = <2>;",
                "\t#size-cells = <1>;",
                "#size-cells",
            ),
        )
        for original, replacement, prop in mutations:
            with self.subTest(property=prop):
                build_dtb(
                    self.dtb,
                    dts_text().replace(original, replacement, 1),
                )
                result = run(self.candidate_arguments())
                self.assertEqual(result.returncode, 1)
                self.assertIn(
                    f"DT check board-identity u32 property changed: {prop}",
                    result.stderr,
                )

    def test_changed_cpu_container_cell_widths_fail(self) -> None:
        mutations = (
            (
                "\t\t#address-cells = <2>;",
                "\t\t#address-cells = <1>;",
                "#address-cells",
            ),
            (
                "\t\t#size-cells = <0>;",
                "\t\t#size-cells = <1>;",
                "#size-cells",
            ),
        )
        for original, replacement, prop in mutations:
            with self.subTest(property=prop):
                build_dtb(
                    self.dtb,
                    dts_text().replace(original, replacement, 1),
                )
                result = run(self.candidate_arguments())
                self.assertEqual(result.returncode, 1)
                self.assertIn(
                    f"DT check cpu-container u32 property changed: {prop}",
                    result.stderr,
                )

    def test_changed_cpu_reg_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                "\t\t\treg = <0 0x100>;",
                "\t\t\treg = <0 0x101>;",
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "DT check cpu100 u32 property changed: reg",
            result.stderr,
        )

    def test_additional_cpu_node_fails(self) -> None:
        extra_cpu = """
\t\tcpu@800 {
\t\t\tcompatible = "arm,cortex-a55";
\t\t\tdevice_type = "cpu";
\t\t\tenable-method = "psci";
\t\t\treg = <0 0x800>;
\t\t};"""
        build_dtb(
            self.dtb,
            dts_text().replace(
                "\n\t};\n\n\tpsci {",
                f"{extra_cpu}\n\t}};\n\n\tpsci {{",
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn("DT CPU node inventory changed", result.stderr)

    def test_additional_system_memory_node_fails(self) -> None:
        extra_memory = """
\tmemory@400000000 {
\t\tdevice_type = "memory";
\t\treg = <4 0 0 0x1000>;
\t};
"""
        build_dtb(
            self.dtb,
            dts_text().replace(
                "\n\tcpus {",
                f"{extra_memory}\n\tcpus {{",
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn("DT system-memory node inventory changed", result.stderr)

    def test_memory_node_must_not_gain_compatible(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                '\tmemory@80000000 {\n\t\tdevice_type = "memory";',
                '\tmemory@80000000 {\n'
                '\t\tcompatible = "example,memory";\n'
                '\t\tdevice_type = "memory";',
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "DT check memory-banks has an unexpected compatible",
            result.stderr,
        )

    def test_changed_cpu_frequency_domain_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                "\t\t\tqcom,freq-domain = <2 0>;",
                "\t\t\tqcom,freq-domain = <2 1>;",
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "DT check cpu0 phandle-array property changed: qcom,freq-domain",
            result.stderr,
        )

    def test_changed_cpu_clock_domain_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                "\t\t\tclocks = <2 0>;",
                "\t\t\tclocks = <2 1>;",
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "DT check cpu0 phandle-array property changed: clocks",
            result.stderr,
        )

    def test_missing_cpu_cooling_cells_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace("\t\t\t#cooling-cells = <2>;\n", "", 1),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "thermal cooling target lacks cell count: /cpus/cpu@0",
            result.stderr,
        )

    def test_cpufreq_clock_cell_count_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                "\t\t\t#clock-cells = <1>;",
                "\t\t\t#clock-cells = <2>;",
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "DT check cpu0 phandle-array target cell count changed",
            result.stderr,
        )

    def test_cpufreq_provider_cell_count_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                "\t\t\t#freq-domain-cells = <1>;",
                "\t\t\t#freq-domain-cells = <2>;",
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "DT check cpu0 phandle-array target cell count changed",
            result.stderr,
        )

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
        self.assertIn(
            "thermal sensor controller "
            "/soc@0/thermal-sensor@c263000 property changed: #qcom,sensors",
            result.stderr,
        )

    def test_thermal_policy_metadata_cannot_change(self) -> None:
        module = load_module()
        contract = deepcopy(self.contract)
        contract["thermal_policy"]["polling_delay_passive_ms"] = 251
        with self.assertRaisesRegex(
            ValueError,
            "thermal policy differs from the accepted static topology",
        ):
            module.validate_contract(REPO, contract)
        contract = deepcopy(self.contract)
        contract["thermal_policy"]["passive_trip_millicelsius"] = [
            95000,
            90000,
        ]
        with self.assertRaisesRegex(
            ValueError,
            "thermal trip ordering or hysteresis is unsafe",
        ):
            module.validate_contract(REPO, contract)
        contract = deepcopy(self.contract)
        contract["thermal_policy"][
            "critical_hysteresis_millicelsius"
        ] = 0
        with self.assertRaisesRegex(
            ValueError,
            "thermal trip ordering or hysteresis is unsafe",
        ):
            module.validate_contract(REPO, contract)
        contract = deepcopy(self.contract)
        contract["thermal_policy"]["cpu_zone_groups"] = "invalid"
        with self.assertRaisesRegex(ValueError, "thermal policy is malformed"):
            module.validate_contract(REPO, contract)

    def test_tsens_critical_interrupt_name_change_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                'interrupt-names = "uplow", "critical";',
                'interrupt-names = "uplow", "fatal";',
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "thermal sensor controller "
            "/soc@0/thermal-sensor@c263000 property changed: "
            "interrupt-names",
            result.stderr,
        )

    def test_tsens_critical_interrupt_route_change_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                "interrupts-extended = <&pdc 26 4>, <&pdc 28 4>;",
                "interrupts-extended = <&pdc 26 4>, <&pdc 30 4>;",
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "thermal sensor controller "
            "/soc@0/thermal-sensor@c263000 property changed: "
            "interrupts-extended",
            result.stderr,
        )

    def test_tsens_pdc_parent_change_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                "interrupt-parent = <&gic>;",
                "interrupt-parent = <&tsens1>;",
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "thermal PDC /soc@0/interrupt-controller@b220000 "
            "property changed: interrupt-parent",
            result.stderr,
        )

    def test_disabled_cpu_thermal_zone_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                "\t\tcpu0-thermal {\n",
                '\t\tcpu0-thermal {\n\t\t\tstatus = "disabled";\n',
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "DT check thermal zone cpu0-thermal is not enabled",
            result.stderr,
        )

    def test_cpu_sensor_index_out_of_range_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                "thermal-sensors = <&tsens0 1>;",
                "thermal-sensors = <&tsens0 15>;",
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "thermal CPU zone sensor index is out of range: "
            "/thermal-zones/cpu0-thermal",
            result.stderr,
        )

    def test_duplicate_unrelated_thermal_sensor_binding_fails(self) -> None:
        extra_zone = """
\t\tboard-skin-thermal {
\t\t\tthermal-sensors = <&tsens0 1>;
\t\t};
"""
        build_dtb(
            self.dtb,
            dts_text().replace(
                "\n\t};\n\n\tsoc@0 {",
                f"{extra_zone}\n\t}};\n\n\tsoc@0 {{",
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "thermal zone sensor binding is duplicated",
            result.stderr,
        )

    def test_cpu_thermal_trip_mutations_fail(self) -> None:
        mutations = (
            (
                "temperature = <90000>;",
                "temperature = <91000>;",
                "trip-point0",
                "temperature",
            ),
            (
                "hysteresis = <2000>;",
                "hysteresis = <3000>;",
                "trip-point0",
                "hysteresis",
            ),
            (
                'type = "passive";',
                'type = "hot";',
                "trip-point0",
                "type",
            ),
            (
                "temperature = <110000>;",
                "temperature = <120000>;",
                "cpu-crit",
                "temperature",
            ),
        )
        for original, replacement, trip_name, property_name in mutations:
            with self.subTest(property=property_name, original=original):
                build_dtb(
                    self.dtb,
                    dts_text().replace(original, replacement, 1),
                )
                result = run(self.candidate_arguments())
                self.assertEqual(result.returncode, 1)
                self.assertIn(
                    f"thermal trip /thermal-zones/cpu0-thermal/trips/"
                    f"{trip_name} "
                    f"property changed: {property_name}",
                    result.stderr,
                )

    def test_cpu_passive_polling_delay_change_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                "polling-delay-passive = <250>;",
                "polling-delay-passive = <500>;",
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "thermal CPU zone /thermal-zones/cpu0-thermal "
            "property changed: polling-delay-passive",
            result.stderr,
        )

    def test_cpu_cooling_map_trip_change_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                "trip = <&cpu0_thermal_trip0>;",
                "trip = <&cpu0_thermal_trip1>;",
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "thermal CPU cooling map "
            "/thermal-zones/cpu0-thermal/cooling-maps/map0 "
            "property changed: trip",
            result.stderr,
        )

    def test_cpu_cooling_device_limit_change_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                "<&cpu0 0xffffffff 0xffffffff>",
                "<&cpu0 0 0xffffffff>",
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "thermal CPU cooling map "
            "/thermal-zones/cpu0-thermal/cooling-maps/map0 "
            "property changed: cooling-device",
            result.stderr,
        )

    def test_additional_cpu_thermal_zone_fails(self) -> None:
        extra_zone = """
\t\tcpu8-thermal {
\t\t\tthermal-sensors = <&tsens0 0>;
\t\t};
"""
        build_dtb(
            self.dtb,
            dts_text().replace(
                "\n\t};\n\n\tsoc@0 {",
                f"{extra_zone}\n\t}};\n\n\tsoc@0 {{",
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn("thermal CPU zone inventory changed", result.stderr)

    def test_renamed_zone_cannot_gain_cpu_cooling_fails(self) -> None:
        extra_zone = """
\t\tbig-cluster-thermal {
\t\t\tthermal-sensors = <&tsens0 5>;
\t\t\ttrips {
\t\t\t\tbig_cluster_trip: trip0 {
\t\t\t\t\ttemperature = <90000>;
\t\t\t\t\thysteresis = <2000>;
\t\t\t\t\ttype = "passive";
\t\t\t\t};
\t\t\t};
\t\t\tcooling-maps {
\t\t\t\tmap0 {
\t\t\t\t\ttrip = <&big_cluster_trip>;
\t\t\t\t\tcooling-device = <&cpu0 0xffffffff 0xffffffff>;
\t\t\t\t};
\t\t\t};
\t\t};
"""
        build_dtb(
            self.dtb,
            dts_text().replace(
                "\n\t};\n\n\tsoc@0 {",
                f"{extra_zone}\n\t}};\n\n\tsoc@0 {{",
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn("thermal CPU zone inventory changed", result.stderr)

    def test_missing_pmic_alarm_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                'compatible = "qcom,spmi-temp-alarm";',
                'compatible = "qcom,mutant-temp-alarm";',
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn("thermal PMIC alarm inventory changed", result.stderr)

    def test_disabled_pmic_alarm_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                "\t\t\t\tpm8350_alarm: temp-alarm@a00 {\n",
                "\t\t\t\tpm8350_alarm: temp-alarm@a00 {\n"
                '\t\t\t\t\tstatus = "disabled";\n',
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "DT check thermal PMIC alarm "
            "/soc@0/spmi@c440000/pmic@1/temp-alarm@a00 "
            "is not enabled",
            result.stderr,
        )

    def test_disabled_pmic_thermal_zone_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                "\t\tpm8350-thermal {\n",
                '\t\tpm8350-thermal {\n\t\t\tstatus = "disabled";\n',
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "DT check thermal PMIC zone "
            "/thermal-zones/pm8350-thermal is not enabled",
            result.stderr,
        )

    def test_pmic_alarm_interrupt_change_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                "interrupts = <1 10 0 3>;",
                "interrupts = <1 11 0 3>;",
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "thermal PMIC alarm "
            "/soc@0/spmi@c440000/pmic@1/temp-alarm@a00 "
            "property changed: interrupts",
            result.stderr,
        )

    def test_pmic_critical_trip_change_fails(self) -> None:
        build_dtb(
            self.dtb,
            dts_text().replace(
                "temperature = <115000>;",
                "temperature = <116000>;",
                1,
            ),
        )
        result = run(self.candidate_arguments())
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "thermal trip "
            "/thermal-zones/pm8350-thermal/trips/pm8350c-crit "
            "property changed: temperature",
            result.stderr,
        )

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

    def test_compatible_absence_policy_cannot_be_narrowed(self) -> None:
        module = load_module()
        contract = deepcopy(self.contract)
        memory = next(
            row
            for row in contract["dt_checks"]
            if row["id"] == "memory-banks"
        )
        memory["compatible"] = ["example,memory"]
        with self.assertRaisesRegex(
            ValueError,
            "DT compatible-absence inventory changed",
        ):
            module.validate_contract(REPO, contract)

    def test_compatible_absence_policy_cannot_be_expanded(self) -> None:
        module = load_module()
        contract = deepcopy(self.contract)
        cpu = next(
            row for row in contract["dt_checks"] if row["id"] == "cpu0"
        )
        cpu["compatible"] = []
        with self.assertRaisesRegex(
            ValueError,
            "DT compatible-absence inventory changed",
        ):
            module.validate_contract(REPO, contract)

    def test_phandle_array_requires_arguments(self) -> None:
        module = load_module()
        contract = deepcopy(self.contract)
        cpu = next(
            row for row in contract["dt_checks"] if row["id"] == "cpu0"
        )
        cpu["phandle_args_properties"]["clocks"][0]["args"] = []
        with self.assertRaisesRegex(
            ValueError,
            "has no phandle arguments",
        ):
            module.validate_contract(REPO, contract)

    def test_phandle_array_target_must_be_checked(self) -> None:
        module = load_module()
        contract = deepcopy(self.contract)
        cpu = next(
            row for row in contract["dt_checks"] if row["id"] == "cpu0"
        )
        cpu["phandle_args_properties"]["clocks"][0][
            "target"
        ] = "/unchecked@0"
        with self.assertRaisesRegex(
            ValueError,
            "has unchecked phandle-array targets",
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

    def test_accepted_source_and_dtb_pass_when_retained_input_available(self) -> None:
        source = accepted_kernel_source()
        accepted_dtb = REPO / str(self.contract["accepted_dtb"]["path"])
        if source is None or not accepted_dtb.exists():
            self.skipTest("retained accepted source/DTB are optional in CI")
        result = run(
            [
                "--kernel-source",
                str(source),
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


class AcceptedSourceDiscoveryTest(unittest.TestCase):
    def test_explicit_source_overrides_retained_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            explicit = root / "explicit"
            default = root / "default"
            default.mkdir()
            with mock.patch.dict(
                os.environ,
                {"ROG5_ACCEPTED_KERNEL_SOURCE": str(explicit)},
            ):
                self.assertEqual(
                    accepted_kernel_source(default),
                    explicit,
                )

    def test_retained_default_is_automatic_and_absence_skips(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            default = root / "accepted"
            with mock.patch.dict(
                os.environ,
                {"ROG5_ACCEPTED_KERNEL_SOURCE": ""},
            ):
                self.assertIsNone(accepted_kernel_source(default))
                default.mkdir()
                self.assertEqual(accepted_kernel_source(default), default)

    def test_unsafe_retained_path_is_not_silently_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            missing = root / "missing"
            default = root / "accepted"
            default.symlink_to(missing, target_is_directory=True)
            with mock.patch.dict(
                os.environ,
                {"ROG5_ACCEPTED_KERNEL_SOURCE": ""},
            ):
                self.assertEqual(accepted_kernel_source(default), default)


if __name__ == "__main__":
    unittest.main(verbosity=2)

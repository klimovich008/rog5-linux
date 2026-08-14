#!/usr/bin/env python3
"""Hostile tests for the offline retention-cycle executor contract."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "scripts/host/retention-cycle-executor-contract.py"
ADAPTER_SOURCE = REPO / "scripts/host/retention-cycle-adapter.py"
PROFILE = (
    REPO
    / "configs/retention-cycles/host-rendezvous-v3-observer-v1.json"
)
POLICY = REPO / "manifests/temporary-boot-images.tsv"
CONSUMER = REPO / "scripts/host/consume-exact-boot-claim.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CONTRACT = load_module("rog5_retention_executor_contract", SOURCE)
ADAPTER = load_module("rog5_retention_adapter_for_contract", ADAPTER_SOURCE)

TARGET_BOOT_ID = "01234567-89ab-cdef-0123-456789abcdef"
FALLBACK_BOOT_ID = "fedcba98-7654-3210-fedc-ba9876543210"
USB_LOCATION = "pci0000:00/0000:00:14.0/usb1/1-3"
FASTBOOT_SERIAL = "M1AIB760D093XYZ"
FALLBACK_KNOWN_HOSTS = "/private/rog5/fallback-known-hosts"


class RetentionCycleExecutorContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.inputs = CONTRACT.ExecutorInputs(
            target_boot_id=TARGET_BOOT_ID,
            fallback_boot_id=FALLBACK_BOOT_ID,
            usb_location=USB_LOCATION,
            fastboot_serial=FASTBOOT_SERIAL,
            fallback_known_hosts=FALLBACK_KNOWN_HOSTS,
        )

    def specs(self):
        return CONTRACT.process_specs(self.inputs)

    def test_exact_six_process_specs_match_the_adapter(self) -> None:
        specs = self.specs()
        self.assertEqual(
            tuple(item.name for item in specs),
            (
                "execution-claim",
                "execution-boot",
                "fallback-reboot",
                "observer-claim",
                "observer-boot",
                "postmortem-read",
            ),
        )
        expected_programs = (
            "scripts/host/consume-exact-boot-claim.py",
            "scripts/host/run-stable-recovery-live-gate.sh",
            "scripts/host/fallback-acm-control.py",
            "scripts/host/consume-exact-boot-claim.py",
            "scripts/host/run-observation-recovery-live-gate.sh",
            "scripts/host/stable-recovery-control.py",
        )
        self.assertEqual(
            tuple(item.program for item in specs), expected_programs
        )
        self.assertEqual(
            tuple(item.program for item in ADAPTER.INVOCATIONS),
            expected_programs,
        )
        self.assertEqual(
            ADAPTER.INVOCATIONS[2].arguments,
            ("reboot", ADAPTER.FALLBACK_PIN_TOKEN),
        )
        self.assertEqual(
            ADAPTER.INVOCATIONS[2].resolve_arguments(
                TARGET_BOOT_ID, FALLBACK_KNOWN_HOSTS
            ),
            ("reboot", FALLBACK_KNOWN_HOSTS),
        )
        for spec in specs:
            invocation = next(
                item for item in ADAPTER.INVOCATIONS
                if item.name == spec.name
            )
            self.assertEqual(spec.program, invocation.program)
            self.assertEqual(spec.cwd, str(REPO))
            self.assertTrue(spec.argv[0].startswith("/usr/bin/"))
            self.assertEqual(
                spec.argv[-len(invocation.arguments) :],
                invocation.resolve_arguments(
                    TARGET_BOOT_ID, FALLBACK_KNOWN_HOSTS
                ),
            )

    def test_environment_is_closed_and_parent_independent(self) -> None:
        baseline = self.specs()
        hostile_parent = {
            "PATH": "/hostile",
            "HOME": "/home/attacker",
            "XDG_STATE_HOME": "/tmp/intent-confusion",
            "SSH_AUTH_SOCK": "/tmp/agent",
            "GITHUB_TOKEN": "secret",
            "ALLOW_STABLE_RECOVERY_CONTROL": "1",
            "ALLOW_ATTENDED_KEXEC": "1",
            "PYTHONPATH": "/tmp/inject",
        }
        saved = dict(os.environ)
        try:
            os.environ.clear()
            os.environ.update(hostile_parent)
            observed = self.specs()
        finally:
            os.environ.clear()
            os.environ.update(saved)
        self.assertEqual(observed, baseline)
        expected_base = {
            "HOME": "/nonexistent",
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "TZ": "UTC",
        }
        forbidden = {
            "SSH_KEY",
            "SSH_AUTH_SOCK",
            "GITHUB_TOKEN",
            "GH_TOKEN",
            "XDG_STATE_HOME",
            "PYTHONPATH",
            "ALLOW_STABLE_RECOVERY_CONTROL",
            "ALLOW_ATTENDED_KEXEC",
            "ALLOW_RECOVERY_INTENT_RESOLVE",
            "ALLOW_NETWORK_ROOT_NFS_HANDOFF",
        }
        for spec in baseline:
            environment = dict(spec.environment)
            self.assertEqual(len(environment), len(spec.environment))
            self.assertLessEqual(expected_base.items(), environment.items())
            self.assertFalse(forbidden & set(environment))
            for name, value in spec.environment:
                self.assertRegex(name, r"^[A-Z][A-Z0-9_]*$")
                self.assertNotIn("\x00", value)
                self.assertNotIn("\n", value)

    def test_each_action_has_only_its_reviewed_environment(self) -> None:
        specs = {item.name: item for item in self.specs()}
        execution = dict(specs["execution-boot"].environment)
        self.assertEqual(
            {
                name: execution[name]
                for name in CONTRACT.EXECUTION_ENVIRONMENT_NAMES
            },
            CONTRACT.execution_environment(FASTBOOT_SERIAL, USB_LOCATION),
        )
        fallback = dict(specs["fallback-reboot"].environment)
        self.assertEqual(
            {
                name: fallback[name]
                for name in CONTRACT.FALLBACK_ENVIRONMENT_NAMES
            },
            {
                "ALLOW_FALLBACK_ACM_CONTROL": "1",
                "ALLOW_FALLBACK_ACM_STORAGE_WRITE": "1",
                "ALLOW_FALLBACK_BOOTLOADER_REBOOT": "1",
                "ALLOW_PHONE_CREDENTIAL_USE": "1",
                "ROG5_EXPECTED_FASTBOOT_SERIAL": FASTBOOT_SERIAL,
                "ROG5_EXPECTED_USB_LOCATION": USB_LOCATION,
                "ROG5_RETENTION_BOOT_RESULT": "1",
            },
        )
        self.assertNotIn("FALLBACK_KNOWN_HOSTS", fallback)
        self.assertNotIn("SSH_KEY", fallback)
        self.assertEqual(
            specs["fallback-reboot"].argv[-1], FALLBACK_KNOWN_HOSTS
        )
        observer = dict(specs["observer-boot"].environment)
        self.assertEqual(
            {
                name: observer[name]
                for name in CONTRACT.OBSERVER_ENVIRONMENT_NAMES
            },
            CONTRACT.observer_environment(FASTBOOT_SERIAL, USB_LOCATION),
        )
        for name in (
            "execution-claim",
            "observer-claim",
            "postmortem-read",
        ):
            self.assertEqual(
                dict(specs[name].environment),
                dict(CONTRACT.BASE_ENVIRONMENT),
            )

    def test_dynamic_inputs_fail_before_any_spec_is_returned(self) -> None:
        hostile = (
            {"target_boot_id": "bad"},
            {"target_boot_id": Path("/tmp/not-a-string")},
            {"fallback_boot_id": TARGET_BOOT_ID},
            {"fallback_boot_id": "f" * 36},
            {"usb_location": "/sys/devices/1-3"},
            {"usb_location": "pci/../usb1/1-3"},
            {"fastboot_serial": "bad serial"},
            {"fastboot_serial": ""},
            {"fallback_known_hosts": "relative/pin"},
            {"fallback_known_hosts": str(REPO / "private-pin")},
            {"fallback_known_hosts": "/private/with space/pin"},
            {"fallback_known_hosts": "/private/%h/pin"},
            {"fallback_known_hosts": "/private/./pin"},
            {"fallback_known_hosts": "/private/pin\x00other"},
            {"fallback_known_hosts": "/private/pin\nother"},
        )
        for mutation in hostile:
            with self.subTest(mutation=mutation):
                with self.assertRaises(CONTRACT.ContractError):
                    CONTRACT.process_specs(replace(self.inputs, **mutation))

    def test_helper_sources_are_exact_repository_owned_inputs(self) -> None:
        by_program = {item.program: item for item in self.specs()}
        expected = {
            "scripts/host/consume-exact-boot-claim.py": (
                45778,
                "d249f4d6a07e592bbade8c7fc2dfe740487275fd09f32a13cb94c5719b0da8a1",
            ),
            "scripts/host/run-stable-recovery-live-gate.sh": (
                191549,
                "812e71c1c2e829623ba57f3df885058168b675c412a444f598e353c529f23f44",
            ),
            "scripts/host/fallback-acm-control.py": (
                110389,
                "4eff0818d6a9b4efc050d24ec5aa856fa1cea251495c6bdb67b23bea953a8534",
            ),
            "scripts/host/run-observation-recovery-live-gate.sh": (
                21083,
                "0b950c1f5456f88599835fe13349667974e8ddf6b1457baa668eb8338e59b929",
            ),
            "scripts/host/stable-recovery-control.py": (
                38326,
                "5da3033e23422e566f951f35632592f916bdd544a7baf5b7b797c4a3375edf66",
            ),
        }
        self.assertEqual(set(by_program), set(expected))
        for program, (size, digest) in expected.items():
            path = REPO / program
            metadata = path.lstat()
            self.assertTrue(stat.S_ISREG(metadata.st_mode))
            self.assertFalse(path.is_symlink())
            self.assertEqual(stat.S_IMODE(metadata.st_mode), 0o755)
            self.assertEqual(metadata.st_size, size)
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), digest
            )
            spec = by_program[program]
            self.assertEqual(spec.program_size, size)
            self.assertEqual(spec.program_sha256, digest)
            self.assertEqual(spec.program_mode, "0755")

    def test_stream_deadline_and_process_cleanup_contract_is_exact(self) -> None:
        expected = {
            "execution-claim": (15, 4096, "exact-claim-pass-v1"),
            "execution-boot": (300, 131072, "retention-boot-result-v1"),
            "fallback-reboot": (240, 131072, "retention-boot-result-v1"),
            "observer-claim": (15, 4096, "exact-claim-pass-v1"),
            "observer-boot": (
                300,
                131072,
                "retention-boot-result-v1",
            ),
            "postmortem-read": (
                90,
                16384,
                "postmortem-lineage-json-v1",
            ),
        }
        for spec in self.specs():
            timeout, output_limit, protocol = expected[spec.name]
            self.assertEqual(spec.timeout_seconds, timeout)
            self.assertEqual(spec.output_limit_bytes, output_limit)
            self.assertEqual(spec.success_protocol, protocol)
            self.assertEqual(spec.stdin, "devnull")
            self.assertEqual(spec.stdout, "bounded-pipe")
            self.assertEqual(spec.stderr, "bounded-pipe")
            self.assertTrue(spec.start_new_session)
            self.assertTrue(spec.kill_process_group_on_timeout)
            self.assertTrue(spec.close_fds)
            self.assertEqual(spec.umask, "0077")
            self.assertEqual(spec.accepted_exit_codes, (0,))

    def test_contract_has_no_executor_cli_or_inherited_credential_surface(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for token in (
            "subprocess",
            "socket",
            "Popen",
            "os.system",
            "os.environ",
            "SSH_KEY",
            "SSH_AUTH_SOCK",
            "GITHUB_TOKEN",
            "ALLOW_STABLE_RECOVERY_CONTROL",
            "ALLOW_ATTENDED_KEXEC",
        ):
            self.assertNotIn(token, source)
        self.assertNotIn("if __name__ ==", source)
        self.assertEqual(CONTRACT.BUILTIN_EXECUTOR, "none")
        self.assertEqual(CONTRACT.LIVE_ENTRYPOINT, "none")
        self.assertEqual(CONTRACT.CONNECTED_ADMISSION, "none")
        self.assertEqual(CONTRACT.CREDENTIAL_USE, "none")

    def test_hold_claim_and_policy_state_remains_closed(self) -> None:
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        self.assertEqual(profile["state"], "hold")
        self.assertEqual(profile["authority"], "none")
        self.assertEqual(profile["boot_authority"], "none")
        self.assertEqual(profile["claims"]["execution"], "not-defined")
        self.assertEqual(profile["claims"]["observer"], "not-defined")
        rows = [
            line.split("\t")
            for line in POLICY.read_text(encoding="utf-8").splitlines()[1:]
            if line
        ]
        self.assertEqual(
            sum(
                row[0]
                == "build/observation-recovery-mainline-udc-v11-generation10-20260811-r1/repack/stable-recovery-a.avb.img"
                and row[1] == "allow"
                for row in rows
            ),
            1,
        )
        consumer = CONSUMER.read_text(encoding="utf-8")
        self.assertIn(
            "retention-host-rendezvous-v3-execution-v1", consumer
        )
        self.assertIn(
            "retention-host-rendezvous-v3-observer-v1", consumer
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Verify the attended GPUCC load-to-kexec sequence is fixed and atomic."""

from __future__ import annotations

import ast
import importlib.util
import inspect
from pathlib import Path
import re
import sys


def fail(message: str) -> None:
    raise SystemExit(f"FAIL {message}")


if len(sys.argv) != 3:
    fail("usage: verify-network-root-gpucc-atomic-confirmation.py ACM TESTS")

sys.dont_write_bytecode = True
acm_path = Path(sys.argv[1])
test_path = Path(sys.argv[2])
acm_source = acm_path.read_text()
test_source = test_path.read_text()
ast.parse(acm_source)
ast.parse(test_source)

spec = importlib.util.spec_from_file_location("rog5_network_root_acm", acm_path)
if spec is None or spec.loader is None:
    fail("cannot import ACM helper")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

expected_sequence = {
    "confirm-gpucc": ("load-gpucc-confirmation", "execute"),
}
if module.SEQUENCES != expected_sequence:
    fail("GPUCC confirmation sequence is not exact")
if module.ACTIONS["load-gpucc-confirmation"] != (
    "ROG5_SYSTEMD_DIAGNOSTIC=1 ROG5_RECOVERY_TIMEOUT=900 "
    "/usr/local/sbin/rog5-load-mainline-recovery",
    module.LOAD_MARKER,
    False,
    60,
):
    fail("trace-free load action is not exact")
if module.ACTIONS["execute"] != ("kexec -e", None, True, 20):
    fail("execute action is not exact")

sequence_source = inspect.getsource(module.run_fixed_sequence)
for forbidden in ("sleep(", "time.sleep", "while ", "try:", "except "):
    if forbidden in sequence_source:
        fail(f"atomic sequence contains forbidden control: {forbidden}")
if sequence_source.count("run_fixed_action(action)") != 1:
    fail("atomic sequence does not have one fixed-action call site")
for contract in (
    "for action in SEQUENCES[sequence]:",
    'return "".join(output)',
):
    if contract not in sequence_source:
        fail(f"atomic sequence omits: {contract}")

calls: list[str] = []
original_fixed_action = module.run_fixed_action


def passing_action(action: str) -> str:
    calls.append(action)
    if action == "load-gpucc-confirmation":
        return module.LOAD_MARKER.decode() + "\n"
    return ""


module.run_fixed_action = passing_action
result = module.run_fixed_sequence("confirm-gpucc")
if calls != ["load-gpucc-confirmation", "execute"]:
    fail("atomic sequence call order is not exact")
if result != module.LOAD_MARKER.decode() + "\n":
    fail("atomic sequence did not retain load evidence")

calls.clear()


def failing_load(action: str) -> str:
    calls.append(action)
    raise module.MissingLoadMarkerError("synthetic load failure")


module.run_fixed_action = failing_load
try:
    module.run_fixed_sequence("confirm-gpucc")
except module.MissingLoadMarkerError:
    pass
else:
    fail("atomic sequence swallowed a load failure")
if calls != ["load-gpucc-confirmation"]:
    fail("execute remained reachable after a load failure")

action_source = inspect.getsource(original_fixed_action)
if (
    "except MissingLoadMarkerError:" not in action_source
    or 'if action == "execute":' not in action_source
    or action_source.count("return run_serial(") != 2
):
    fail("fixed-action retry boundary is not exact")

for contract in (
    'needs_kexec = action in SEQUENCES',
    'if action == "execute":',
    "needs_kexec = True",
    'if needs_kexec and os.environ.get("ALLOW_ATTENDED_KEXEC") != "1":',
    "output = run_fixed_sequence(action)",
):
    if contract not in acm_source:
        fail(f"ACM source omits: {contract}")
network_guard = acm_source.index('os.environ.get("ALLOW_NETWORK_ROOT_ACM")')
kexec_guard = acm_source.index(
    'if needs_kexec and os.environ.get("ALLOW_ATTENDED_KEXEC") != "1":'
)
host_check = acm_source.index("if os.uname().sysname")
sequence_call = acm_source.index("output = run_fixed_sequence(action)")
if not network_guard < kexec_guard < host_check < sequence_call:
    fail("guards do not precede host and device work")

if re.search(r"fastboot\s+flash|dd\s+.*of=/dev/|mount\s+.*/dev/", acm_source):
    fail("ACM helper contains a persistent-write path")

for test_name in (
    "test_atomic_confirmation_requires_kexec_guard_before_discovery",
    "test_atomic_confirmation_loads_then_executes_without_gap",
    "test_atomic_confirmation_never_executes_after_load_failure",
    "test_execute_is_never_retried",
):
    if f"def {test_name}(" not in test_source:
        fail(f"ACM tests omit: {test_name}")

print(
    "PASS atomic GPUCC confirmation is guard-first, load-before-execute, "
    "delay-free, and non-retryable after execute"
)

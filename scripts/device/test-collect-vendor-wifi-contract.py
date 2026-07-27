#!/usr/bin/python3
"""Offline tests for the read-only vendor Wi-Fi device-tree collector."""

import struct
import subprocess
import sys
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
TARGET = REPO / "scripts/device/collect-vendor-wifi-contract.py"


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def write_property(node: Path, name: str, value: bytes) -> None:
    node.mkdir(parents=True, exist_ok=True)
    (node / name).write_bytes(value)


def cells(*values: int) -> bytes:
    return struct.pack(f">{len(values)}I", *values)


def strings(*values: str) -> bytes:
    return b"\0".join(value.encode("ascii") for value in values) + b"\0"


def add_phandle(root: Path, relative: str, handle: int) -> Path:
    node = root / relative
    write_property(node, "phandle", cells(handle))
    return node


def add_regulator(
    root: Path,
    relative: str,
    handle: int,
    name: str,
    minimum: int,
    maximum: int,
) -> None:
    node = add_phandle(root, relative, handle)
    write_property(node, "regulator-name", strings(name))
    write_property(node, "regulator-min-microvolt", cells(minimum))
    write_property(node, "regulator-max-microvolt", cells(maximum))


def build_fixture(root: Path, *, resolve_io: bool = False) -> None:
    tlmm = add_phandle(root, "soc/pinctrl@f000000", 144)
    write_property(tlmm, "compatible", strings("qcom,sm8350-tlmm"))

    pinctrl = {
        210: "soc/pinctrl@f000000/cnss_pins/cnss_wlan_en_active",
        211: "soc/pinctrl@f000000/cnss_pins/cnss_wlan_en_sleep",
        1578: "soc/pinctrl@f000000/cnss_pins/wifi_ant_switch",
        652: "soc/pinctrl@f000000/pcie0_default",
        653: "soc/pinctrl@f000000/pcie0_clkreq_default",
        654: "soc/pinctrl@f000000/pcie0_wake_default",
        655: "soc/pinctrl@f000000/pcie0_clkreq_sleep",
    }
    for handle, relative in pinctrl.items():
        add_phandle(root, relative, handle)

    add_regulator(
        root,
        "soc/rsc@18200000/rpmh-regulator-smpe2/regulator-pmr735a-s2",
        212,
        "pmr735a_s2",
        976000,
        976000,
    )
    add_regulator(
        root,
        "soc/rsc@18200000/rpmh-regulator-smpb11/regulator-pm8350-s11",
        213,
        "pm8350_s11",
        752000,
        1012000,
    )
    if resolve_io:
        add_regulator(
            root,
            "soc/rsc@18200000/rpmh-regulator-ldob7/regulator-pm8350-l7",
            214,
            "fixture_io",
            1800000,
            1800000,
        )
    add_regulator(
        root,
        "soc/rsc@18200000/rpmh-regulator-smpc1/regulator-pm8350c-s1",
        215,
        "pm8350c_s1",
        1800000,
        1952000,
    )
    add_regulator(
        root,
        "soc/rsc@18200000/rpmh-regulator-smpb12/regulator-pm8350-s12",
        216,
        "pm8350_s12",
        1224000,
        1360000,
    )
    add_regulator(
        root,
        "soc/rsc@18200000/rpmh-regulator-ldoe7/regulator-pmr735a-l7",
        219,
        "pmr735a_l7",
        2800000,
        2800000,
    )

    cnss = root / "soc/qcom,cnss-qca6490@b0000000"
    write_property(cnss, "compatible", strings("qcom,cnss-qca6490"))
    write_property(cnss, "qcom,wlan-rc-num", cells(0))
    write_property(
        cnss,
        "pinctrl-names",
        strings("wlan_en_active", "wlan_en_sleep", "wifi_ant_gpio"),
    )
    write_property(cnss, "pinctrl-0", cells(210))
    write_property(cnss, "pinctrl-1", cells(211))
    write_property(cnss, "pinctrl-2", cells(1578))
    write_property(cnss, "wlan-en-gpio", cells(144, 64, 0))
    write_property(cnss, "qcom,bt-en-gpio", cells(144, 65, 0))
    write_property(cnss, "qcom,sw-ctrl-gpio", cells(144, 153, 0))

    cnss_supplies = {
        "vdd-wlan-aon": (212, (976000, 976000, 0, 0, 1)),
        "vdd-wlan-dig": (213, (950000, 952000, 0, 0, 1)),
        "vdd-wlan-io": (214, (1800000, 1800000, 0, 0, 1)),
        "vdd-wlan-rfa1": (215, (1880000, 1880000, 0, 0, 1)),
        "vdd-wlan-rfa2": (216, (1350000, 1350000, 0, 0, 1)),
        "wlan-ant-switch": (219, (2800000, 2800000, 0, 0, 0)),
    }
    for name, (handle, requested) in cnss_supplies.items():
        write_property(cnss, f"{name}-supply", cells(handle))
        write_property(cnss, f"qcom,{name}-config", cells(*requested))

    add_regulator(
        root,
        "soc/qcom,gdsc@16b004",
        656,
        "gcc_pcie_0_gdsc",
        0,
        0,
    )
    add_regulator(
        root,
        "soc/rsc@18200000/rpmh-regulator-ldob5/regulator-pm8350-l5",
        30,
        "pm8350_l5",
        880000,
        888000,
    )
    add_regulator(
        root,
        "soc/rsc@18200000/rpmh-regulator-ldob6/regulator-pm8350-l6",
        31,
        "pm8350_l6",
        1200000,
        1208000,
    )
    add_regulator(
        root,
        "soc/rsc@18200000/rpmh-regulator-cxlvl/regulator-pm8350c-s6-level",
        32,
        "pm8350c_s6_level",
        16,
        65535,
    )

    pcie = root / "soc/qcom,pcie@1c00000"
    write_property(pcie, "compatible", strings("qcom,pci-msm"))
    write_property(pcie, "cell-index", cells(0))
    write_property(pcie, "linux,pci-domain", cells(0))
    write_property(pcie, "pinctrl-names", strings("default", "sleep"))
    write_property(pcie, "pinctrl-0", cells(652, 653, 654))
    write_property(pcie, "pinctrl-1", cells(652, 655, 654))
    write_property(pcie, "perst-gpio", cells(144, 94, 0))
    write_property(pcie, "wake-gpio", cells(144, 96, 0))
    pcie_supplies = {
        "gdsc-vdd": (656, ()),
        "vreg-0p9": (30, (880000, 880000, 47900)),
        "vreg-1p8": (31, (1200000, 1200000, 15000)),
        "vreg-cx": (32, (65535, 256, 0)),
    }
    for name, (handle, requested) in pcie_supplies.items():
        write_property(pcie, f"{name}-supply", cells(handle))
        if requested:
            write_property(
                pcie, f"qcom,{name}-voltage-level", cells(*requested)
            )


def run_collector(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [TARGET, "--root", root],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )


def require_line(output: str, expected: str) -> None:
    if expected not in output.splitlines():
        fail(f"collector output omits: {expected}")


def main() -> int:
    if not TARGET.is_file() or TARGET.is_symlink() or not TARGET.stat().st_mode & 0o111:
        fail(f"missing executable collector: {TARGET}")

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "device-tree"
        build_fixture(root)
        result = run_collector(root)
        if result.returncode != 2:
            fail(
                "unresolved vendor supply did not produce HOLD status "
                f"(status={result.returncode}, stderr={result.stderr.strip()})"
            )
        for expected in (
            "ROG5_VENDOR_WIFI_CONTRACT_V1",
            "cnss_node=/soc/qcom,cnss-qca6490@b0000000",
            "wlan_root_complex=0",
            "pcie_node=/soc/qcom,pcie@1c00000",
            "pcie_domain=0",
            "cnss_supply=vdd-wlan-aon|phandle=212|provider=/soc/rsc@18200000/rpmh-regulator-smpe2/regulator-pmr735a-s2|regulator=pmr735a_s2|provider_min=976000|provider_max=976000|requested_cells=976000,976000,0,0,1",
            "unresolved_supply=vdd-wlan-io|phandle=214",
            "cnss_gpio=wlan-enable|controller=/soc/pinctrl@f000000|number=64|flags=0",
            "cnss_gpio=bt-enable|controller=/soc/pinctrl@f000000|number=65|flags=0",
            "cnss_gpio=switch-control|controller=/soc/pinctrl@f000000|number=153|flags=0",
            "cnss_pinctrl=wifi_ant_gpio|node=/soc/pinctrl@f000000/cnss_pins/wifi_ant_switch",
            "pcie_gpio=perst|controller=/soc/pinctrl@f000000|number=94|flags=0",
            "pcie_gpio=wake|controller=/soc/pinctrl@f000000|number=96|flags=0",
            "pcie_supply=vreg-cx|phandle=32|provider=/soc/rsc@18200000/rpmh-regulator-cxlvl/regulator-pm8350c-s6-level|regulator=pm8350c_s6_level|provider_min=16|provider_max=65535|requested_cells=65535,256,0",
            "unresolved_supply_count=1",
            "contract_status=HOLD",
        ):
            require_line(result.stdout, expected)
        if "provider=fixture_io" in result.stdout:
            fail("collector guessed a provider for the unresolved I/O rail")

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "device-tree"
        build_fixture(root, resolve_io=True)
        result = run_collector(root)
        if result.returncode:
            fail(
                "complete fixture was rejected "
                f"(status={result.returncode}, stderr={result.stderr.strip()})"
            )
        require_line(
            result.stdout,
            "cnss_supply=vdd-wlan-io|phandle=214|provider=/soc/rsc@18200000/rpmh-regulator-ldob7/regulator-pm8350-l7|regulator=fixture_io|provider_min=1800000|provider_max=1800000|requested_cells=1800000,1800000,0,0,1",
        )
        require_line(result.stdout, "unresolved_supply_count=0")
        require_line(result.stdout, "contract_status=COMPLETE")

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "device-tree"
        build_fixture(root, resolve_io=True)
        duplicate = root / "soc/duplicate-cnss"
        write_property(
            duplicate, "compatible", strings("qcom,cnss-qca6490")
        )
        result = run_collector(root)
        if result.returncode != 1:
            fail("ambiguous CNSS nodes were not rejected")
        if "expected exactly one qcom,cnss-qca6490" not in result.stderr:
            fail("ambiguous CNSS rejection was not explicit")

    result = subprocess.run(
        [TARGET, "--root", "relative/device-tree"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 1 or "absolute directory" not in result.stderr:
        fail("relative device-tree root was not rejected")

    source = TARGET.read_text(encoding="utf-8")
    for forbidden in ("subprocess", "os.system", "fastboot", "reboot", "modprobe"):
        if forbidden in source:
            fail(f"collector contains forbidden mutation surface: {forbidden}")

    print(
        "PASS vendor Wi-Fi contract collector is deterministic, read-only, "
        "and holds on unresolved supplies"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

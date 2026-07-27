#!/usr/bin/python3
"""Read the vendor QCA6490 and matching PCIe device-tree contract."""

import argparse
import struct
import sys
from pathlib import Path


CNSS_COMPATIBLE = "qcom,cnss-qca6490"
PCIE_COMPATIBLE = "qcom,pci-msm"

CNSS_SUPPLIES = (
    ("vdd-wlan-aon", "vdd-wlan-aon-supply", "qcom,vdd-wlan-aon-config"),
    ("vdd-wlan-dig", "vdd-wlan-dig-supply", "qcom,vdd-wlan-dig-config"),
    ("vdd-wlan-io", "vdd-wlan-io-supply", "qcom,vdd-wlan-io-config"),
    ("vdd-wlan-rfa1", "vdd-wlan-rfa1-supply", "qcom,vdd-wlan-rfa1-config"),
    ("vdd-wlan-rfa2", "vdd-wlan-rfa2-supply", "qcom,vdd-wlan-rfa2-config"),
    (
        "wlan-ant-switch",
        "wlan-ant-switch-supply",
        "qcom,wlan-ant-switch-config",
    ),
)
PCIE_SUPPLIES = (
    ("gdsc-vdd", "gdsc-vdd-supply", None),
    (
        "vreg-0p9",
        "vreg-0p9-supply",
        "qcom,vreg-0p9-voltage-level",
    ),
    (
        "vreg-1p8",
        "vreg-1p8-supply",
        "qcom,vreg-1p8-voltage-level",
    ),
    ("vreg-cx", "vreg-cx-supply", "qcom,vreg-cx-voltage-level"),
)
CNSS_GPIOS = (
    ("wlan-enable", "wlan-en-gpio"),
    ("bt-enable", "qcom,bt-en-gpio"),
    ("switch-control", "qcom,sw-ctrl-gpio"),
)
PCIE_GPIOS = (("perst", "perst-gpio"), ("wake", "wake-gpio"))


class ContractError(Exception):
    """The vendor tree does not have one unambiguous contract."""


def property_bytes(node: Path, name: str) -> bytes:
    try:
        return (node / name).read_bytes()
    except OSError as error:
        raise ContractError(f"missing property {relative(node)}/{name}") from error


def cells(data: bytes, source: str) -> tuple[int, ...]:
    if not data or len(data) % 4:
        raise ContractError(f"{source} is not a non-empty u32 cell array")
    return struct.unpack(f">{len(data) // 4}I", data)


def property_cells(node: Path, name: str) -> tuple[int, ...]:
    return cells(property_bytes(node, name), f"{relative(node)}/{name}")


def optional_cell(node: Path, name: str) -> str:
    path = node / name
    if not path.exists():
        return "-"
    values = cells(path.read_bytes(), f"{relative(node)}/{name}")
    if len(values) != 1:
        raise ContractError(f"{relative(node)}/{name} is not one u32 cell")
    return str(values[0])


def one_cell(node: Path, name: str) -> int:
    values = property_cells(node, name)
    if len(values) != 1:
        raise ContractError(f"{relative(node)}/{name} is not one u32 cell")
    return values[0]


def string_list(data: bytes, source: str) -> tuple[str, ...]:
    if not data or not data.endswith(b"\0"):
        raise ContractError(f"{source} is not a terminated string list")
    try:
        values = tuple(
            part.decode("ascii") for part in data.rstrip(b"\0").split(b"\0")
        )
    except UnicodeDecodeError as error:
        raise ContractError(f"{source} is not ASCII") from error
    if not values or any(not value for value in values):
        raise ContractError(f"{source} has an empty string")
    return values


def property_strings(node: Path, name: str) -> tuple[str, ...]:
    return string_list(property_bytes(node, name), f"{relative(node)}/{name}")


def optional_string(node: Path, name: str) -> str:
    path = node / name
    if not path.exists():
        return "-"
    values = string_list(path.read_bytes(), f"{relative(node)}/{name}")
    if len(values) != 1:
        raise ContractError(f"{relative(node)}/{name} is not one string")
    return values[0]


def status(node: Path) -> str:
    path = node / "status"
    if not path.exists():
        return "okay"
    values = string_list(path.read_bytes(), f"{relative(node)}/status")
    if len(values) != 1:
        raise ContractError(f"{relative(node)}/status is not one string")
    return values[0]


def relative(node: Path) -> str:
    return "/" + node.relative_to(ROOT).as_posix()


def compatible_nodes(root: Path, compatible: str) -> list[Path]:
    matches = []
    for path in root.rglob("compatible"):
        try:
            values = string_list(path.read_bytes(), relative(path))
        except (ContractError, OSError):
            continue
        if compatible in values:
            matches.append(path.parent)
    return sorted(matches)


def phandle_map(root: Path) -> dict[int, tuple[Path, ...]]:
    found: dict[int, set[Path]] = {}
    for name in ("phandle", "linux,phandle"):
        for path in root.rglob(name):
            try:
                values = cells(path.read_bytes(), relative(path))
            except (ContractError, OSError):
                continue
            if len(values) == 1:
                found.setdefault(values[0], set()).add(path.parent)
    return {
        handle: tuple(sorted(nodes))
        for handle, nodes in found.items()
    }


def resolve_unique(
    handles: dict[int, tuple[Path, ...]], handle: int
) -> Path | None:
    matches = handles.get(handle, ())
    return matches[0] if len(matches) == 1 else None


def requested_cells(node: Path, name: str | None) -> str:
    if name is None:
        return "-"
    return ",".join(str(value) for value in property_cells(node, name))


def collect_supply(
    output: list[str],
    unresolved: list[tuple[str, int]],
    prefix: str,
    node: Path,
    handles: dict[int, tuple[Path, ...]],
    label: str,
    supply_property: str,
    request_property: str | None,
) -> None:
    handle = one_cell(node, supply_property)
    provider = resolve_unique(handles, handle)
    request = requested_cells(node, request_property)
    if provider is None:
        unresolved.append((label, handle))
        output.append(f"unresolved_supply={label}|phandle={handle}")
        return
    output.append(
        f"{prefix}_supply={label}|phandle={handle}"
        f"|provider={relative(provider)}"
        f"|regulator={optional_string(provider, 'regulator-name')}"
        f"|provider_min={optional_cell(provider, 'regulator-min-microvolt')}"
        f"|provider_max={optional_cell(provider, 'regulator-max-microvolt')}"
        f"|requested_cells={request}"
    )


def collect_gpio(
    output: list[str],
    unresolved: list[str],
    prefix: str,
    node: Path,
    handles: dict[int, tuple[Path, ...]],
    label: str,
    property_name: str,
) -> None:
    values = property_cells(node, property_name)
    if len(values) != 3:
        raise ContractError(
            f"{relative(node)}/{property_name} is not three GPIO cells"
        )
    controller = resolve_unique(handles, values[0])
    if controller is None:
        unresolved.append(f"{prefix}_gpio:{label}:{values[0]}")
        output.append(
            f"unresolved_reference={prefix}_gpio:{label}|phandle={values[0]}"
        )
        return
    output.append(
        f"{prefix}_gpio={label}|controller={relative(controller)}"
        f"|number={values[1]}|flags={values[2]}"
    )


def collect_pinctrl(
    output: list[str],
    unresolved: list[str],
    prefix: str,
    node: Path,
    handles: dict[int, tuple[Path, ...]],
) -> None:
    names = property_strings(node, "pinctrl-names")
    for index, name in enumerate(names):
        for handle in property_cells(node, f"pinctrl-{index}"):
            target = resolve_unique(handles, handle)
            if target is None:
                unresolved.append(f"{prefix}_pinctrl:{name}:{handle}")
                output.append(
                    f"unresolved_reference={prefix}_pinctrl:{name}"
                    f"|phandle={handle}"
                )
                continue
            output.append(
                f"{prefix}_pinctrl={name}|node={relative(target)}"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/proc/device-tree"))
    return parser.parse_args()


def main() -> int:
    global ROOT
    root = parse_args().root
    if not root.is_absolute() or not root.is_dir():
        print("ERROR device-tree root must be an absolute directory", file=sys.stderr)
        return 1
    ROOT = root.resolve()

    try:
        cnss_nodes = compatible_nodes(ROOT, CNSS_COMPATIBLE)
        if len(cnss_nodes) != 1:
            raise ContractError(
                f"expected exactly one {CNSS_COMPATIBLE}, "
                f"found {len(cnss_nodes)}"
            )
        cnss = cnss_nodes[0]
        root_complex = one_cell(cnss, "qcom,wlan-rc-num")

        pcie_nodes = [
            node
            for node in compatible_nodes(ROOT, PCIE_COMPATIBLE)
            if one_cell(node, "cell-index") == root_complex
        ]
        if len(pcie_nodes) != 1:
            raise ContractError(
                f"expected exactly one {PCIE_COMPATIBLE} root complex "
                f"{root_complex}, found {len(pcie_nodes)}"
            )
        pcie = pcie_nodes[0]
        handles = phandle_map(ROOT)
        output = [
            "ROG5_VENDOR_WIFI_CONTRACT_V1",
            f"cnss_node={relative(cnss)}",
            f"cnss_status={status(cnss)}",
            f"wlan_root_complex={root_complex}",
            f"pcie_node={relative(pcie)}",
            f"pcie_status={status(pcie)}",
            f"pcie_domain={one_cell(pcie, 'linux,pci-domain')}",
        ]
        unresolved_supplies: list[tuple[str, int]] = []
        unresolved_references: list[str] = []

        for supply in CNSS_SUPPLIES:
            collect_supply(
                output,
                unresolved_supplies,
                "cnss",
                cnss,
                handles,
                *supply,
            )
        for gpio in CNSS_GPIOS:
            collect_gpio(
                output,
                unresolved_references,
                "cnss",
                cnss,
                handles,
                *gpio,
            )
        collect_pinctrl(
            output, unresolved_references, "cnss", cnss, handles
        )

        for supply in PCIE_SUPPLIES:
            collect_supply(
                output,
                unresolved_supplies,
                "pcie",
                pcie,
                handles,
                *supply,
            )
        for gpio in PCIE_GPIOS:
            collect_gpio(
                output,
                unresolved_references,
                "pcie",
                pcie,
                handles,
                *gpio,
            )
        collect_pinctrl(
            output, unresolved_references, "pcie", pcie, handles
        )

        output.append(
            f"unresolved_supply_count={len(unresolved_supplies)}"
        )
        output.append(
            f"unresolved_reference_count={len(unresolved_references)}"
        )
        hold = (
            bool(unresolved_supplies)
            or bool(unresolved_references)
            or status(cnss) != "okay"
            or status(pcie) != "okay"
        )
        output.append(f"contract_status={'HOLD' if hold else 'COMPLETE'}")
        print("\n".join(output))
        return 2 if hold else 0
    except (ContractError, OSError) as error:
        print(f"ERROR {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

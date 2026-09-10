#!/usr/bin/env python3
"""Verify the accepted kernel/config/modules contract for ROG5 buttons and LED."""

from __future__ import annotations

import argparse
from hashlib import sha256
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tarfile
from typing import NoReturn


ACCEPTED_SOURCE_COMMIT = "7a5cef0db4795d9d453a12e0f61b5b7634fc4d40"
ACCEPTED_CONFIG_SHA256 = (
    "68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f"
)
ACCEPTED_CONFIG_SIZE = 239677
ACCEPTED_MODULES_SHA256 = (
    "5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9"
)
ACCEPTED_MODULE_FIXTURE_SHA256 = (
    "5885a9db2a8821f7c0ee9b16d92092d6d44f5c5092561e8e312f6047bb1a246c"
)
ACCEPTED_MODULE_FIXTURE_SIZE = 368320
MAX_TEXT_SIZE = 2 * 1024 * 1024
MAX_MODULES_SIZE = 512 * 1024 * 1024
EXPECTED_MODULE = (
    "lib/modules/7.1.4-g7a5cef0db479/kernel/"
    "drivers/leds/rgb/leds-qcom-lpg.ko"
)
EXPECTED_MODULE_MARKERS = (
    b"description=Qualcomm LPG LED driver",
    b"license=GPL v2",
    b"alias=of:N*T*Cqcom,pm8350c-pwm",
    b"vermagic=7.1.4-g7a5cef0db479 SMP preempt mod_unload aarch64",
)

REQUIRED_CONFIG = {
    "CONFIG_OF": "y",
    "CONFIG_INPUT": "y",
    "CONFIG_INPUT_EVDEV": "y",
    "CONFIG_KEYBOARD_GPIO": "y",
    "CONFIG_INPUT_PM8941_PWRKEY": "y",
    "CONFIG_GPIOLIB": "y",
    "CONFIG_REGMAP_SPMI": "y",
    "CONFIG_SPMI": "y",
    "CONFIG_SPMI_MSM_PMIC_ARB": "y",
    "CONFIG_PINCTRL_QCOM_SPMI_PMIC": "y",
    "CONFIG_MFD_SPMI_PMIC": "y",
    "CONFIG_NEW_LEDS": "y",
    "CONFIG_LEDS_CLASS": "y",
    "CONFIG_LEDS_QCOM_LPG": "m",
    "CONFIG_PWM": "y",
}

SOURCE_FRAGMENTS = {
    "Makefile": (
        "VERSION = 7",
        "PATCHLEVEL = 1",
        "SUBLEVEL = 4",
    ),
    "drivers/input/misc/pm8941-pwrkey.c": (
        'input_set_capability(pwrkey->input, EV_KEY, pwrkey->code);',
        ".wakeup_source_default = true,",
        ".wakeup_source_default = false,",
        '.compatible = "qcom,pmk8350-pwrkey"',
        " .data = &pon_gen3_pwrkey_data",
        '.compatible = "qcom,pmk8350-resin"',
        " .data = &pon_gen3_resin_data",
        "device_init_wakeup(&pdev->dev, wakeup);",
        "static int pm8941_pwrkey_suspend(struct device *dev)",
        "if (device_may_wakeup(dev)) enable_irq_wake(pwrkey->irq);",
        "if (device_may_wakeup(dev)) disable_irq_wake(pwrkey->irq);",
        ".pm = pm_sleep_ptr(&pm8941_pwr_key_pm_ops),",
        "module_platform_driver(pm8941_pwrkey_driver);",
    ),
    "drivers/input/misc/Kconfig": (
        "config INPUT_PM8941_PWRKEY",
        'tristate "Qualcomm PM8941 power key support"',
        "depends on MFD_SPMI_PMIC",
    ),
    "drivers/input/misc/Makefile": (
        "obj-$(CONFIG_INPUT_PM8941_PWRKEY) += pm8941-pwrkey.o",
    ),
    "drivers/input/keyboard/gpio_keys.c": (
        "static struct platform_driver gpio_keys_device_driver",
        '.name = "gpio-keys"',
        "platform_driver_register(&gpio_keys_device_driver);",
        "late_initcall(gpio_keys_init);",
        'button->wakeup = fwnode_property_read_bool(child, "wakeup-source")',
        "device_init_wakeup(dev, wakeup);",
        "error = enable_irq_wake(bdata->irq);",
        "error = disable_irq_wake(bdata->irq);",
        "error = gpio_keys_enable_wakeup(ddata);",
        ".pm = pm_sleep_ptr(&gpio_keys_pm_ops),",
    ),
    "drivers/input/keyboard/Kconfig": (
        "config KEYBOARD_GPIO",
        'tristate "GPIO Buttons"',
        "depends on GPIOLIB || COMPILE_TEST",
    ),
    "drivers/input/keyboard/Makefile": (
        "obj-$(CONFIG_KEYBOARD_GPIO) += gpio_keys.o",
    ),
    "drivers/spmi/Kconfig": (
        "config SPMI_MSM_PMIC_ARB",
        'tristate "Qualcomm MSM SPMI Controller (PMIC Arbiter)"',
        "depends on ARCH_QCOM || COMPILE_TEST",
    ),
    "drivers/spmi/Makefile": (
        "obj-$(CONFIG_SPMI_MSM_PMIC_ARB) += spmi-pmic-arb.o",
    ),
    "drivers/spmi/spmi-pmic-arb.c": (
        'of_device_is_compatible(node, "qcom,spmi-pmic-arb")',
        '.compatible = "qcom,spmi-pmic-arb"',
        ".of_match_table = spmi_pmic_arb_match_table",
        "module_platform_driver(spmi_pmic_arb_driver);",
    ),
    "drivers/leds/rgb/leds-qcom-lpg.c": (
        "static const struct lpg_data pm8350c_pwm_data",
        ".triled_base = 0xef00,",
        "{ .base = 0xe800, .triled_mask = BIT(7), .sdam_offset = 0x48 }",
        "{ .base = 0xe900, .triled_mask = BIT(6), .sdam_offset = 0x56 }",
        "{ .base = 0xea00, .triled_mask = BIT(5), .sdam_offset = 0x64 }",
        '.compatible = "qcom,pm8350c-pwm"',
        " .data = &pm8350c_pwm_data",
        'of_property_count_strings(lpg->dev->of_node, "nvmem-names")',
        "if (sdam_count <= 0) return 0;",
        'of_property_read_string(np, "default-state", &state)',
        '!strcmp(state, "on")',
        "cdev->brightness = LED_OFF;",
        "cdev->brightness_set_blocking(cdev, cdev->brightness);",
        "regmap_write(lpg->map, lpg->triled_base + TRI_LED_EN_CTL, 0);",
        "module_platform_driver(lpg_driver);",
    ),
    "drivers/leds/rgb/Kconfig": (
        "config LEDS_QCOM_LPG",
        'tristate "LED support for Qualcomm LPG"',
        "depends on PWM",
        "depends on SPMI",
    ),
    "drivers/leds/rgb/Makefile": (
        "obj-$(CONFIG_LEDS_QCOM_LPG) += leds-qcom-lpg.o",
    ),
    "Documentation/devicetree/bindings/input/qcom,pm8941-pwrkey.yaml": (
        "- qcom,pmk8350-pwrkey",
        "- qcom,pmk8350-resin",
        "wakeup-source:",
        "'pwrkey' always wakes the system by default",
        "linux,code:",
    ),
    "Documentation/devicetree/bindings/input/gpio-keys.yaml": (
        "- gpio-keys",
        "debounce-interval:",
        "wakeup-source:",
        "linux,can-disable:",
        "linux,code",
    ),
    "Documentation/devicetree/bindings/leds/leds-qcom-lpg.yaml": (
        "- qcom,pm8350c-pwm",
        '"#address-cells":',
        '"#size-cells":',
        '"^led@[0-9a-f]$":',
        "default-state",
    ),
    "arch/arm64/boot/dts/qcom/pmk8350.dtsi": (
        "pon_pwrkey: pwrkey",
        'compatible = "qcom,pmk8350-pwrkey";',
        "linux,code = <KEY_POWER>;",
        "pon_resin: resin",
        'compatible = "qcom,pmk8350-resin";',
    ),
    "arch/arm64/boot/dts/qcom/pm8350c.dtsi": (
        "pm8350c_pwm: pwm",
        'compatible = "qcom,pm8350c-pwm";',
        "#pwm-cells = <2>;",
        'status = "disabled";',
    ),
}


def fail(message: str) -> NoReturn:
    raise ValueError(message)


def lexical_path(path: Path) -> Path:
    return Path(path.expanduser().absolute())


def require_ordinary_directory(path: Path) -> Path:
    lexical = lexical_path(path)
    if lexical.is_symlink():
        fail(f"source is not an ordinary directory: {path}")
    resolved = lexical.resolve(strict=True)
    if lexical != resolved or not resolved.is_dir():
        fail(f"source contains a linked component or is not a directory: {path}")
    return resolved


def read_ordinary(path: Path, limit: int = MAX_TEXT_SIZE) -> bytes:
    lexical = lexical_path(path)
    if lexical.is_symlink():
        fail(f"input is not an ordinary file: {path}")
    resolved = lexical.resolve(strict=True)
    if lexical != resolved:
        fail(f"input contains a linked path component: {path}")
    descriptor = os.open(
        resolved,
        os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            fail(f"input has an invalid type or size: {path}")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        len(data) != before.st_size
        or before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ctime_ns != after.st_ctime_ns
    ):
        fail(f"input changed while it was read: {path}")
    return data


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def check_source_fragments(texts: dict[str, str]) -> None:
    if set(texts) != set(SOURCE_FRAGMENTS):
        fail("source text set does not equal the critical-file contract")
    for relative, fragments in SOURCE_FRAGMENTS.items():
        normalized = normalize(texts[relative])
        for fragment in fragments:
            if normalize(fragment) not in normalized:
                fail(f"source contract marker is missing: {relative}: {fragment}")


def load_source_texts(source: Path) -> dict[str, str]:
    texts: dict[str, str] = {}
    for relative in SOURCE_FRAGMENTS:
        data = read_ordinary(source / relative)
        try:
            texts[relative] = data.decode("utf-8")
        except UnicodeDecodeError as error:
            fail(f"source file is not UTF-8: {relative}: {error}")
    return texts


def git_output(source: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(source), *arguments],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode:
        fail(
            f"git {' '.join(arguments)} failed for source: "
            f"{completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def verify_source(source_path: Path) -> tuple[Path, str]:
    source = require_ordinary_directory(source_path)
    commit = git_output(source, "rev-parse", "HEAD")
    if commit != ACCEPTED_SOURCE_COMMIT:
        fail(f"source commit is not accepted: {commit}")
    if git_output(source, "status", "--porcelain=v1", "--untracked-files=no"):
        fail("accepted source has tracked or staged modifications")
    check_source_fragments(load_source_texts(source))
    return source, commit


def parse_config(data: bytes) -> dict[str, str]:
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as error:
        fail(f"kernel config is not ASCII: {error}")
    values: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("CONFIG_") and "=" in line:
            name, value = line.split("=", 1)
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            name = line[2 : -len(" is not set")]
            value = "n"
        else:
            continue
        if name in values:
            fail(f"kernel config contains a duplicate symbol: {name}")
        values[name] = value
    return values


def check_required_config(values: dict[str, str]) -> None:
    for name, expected in REQUIRED_CONFIG.items():
        actual = values.get(name)
        if actual != expected:
            fail(
                f"kernel config value is wrong: {name}="
                f"{actual!r}, expected {expected!r}"
            )


def verify_config(path: Path) -> str:
    data = read_ordinary(path)
    digest = sha256(data).hexdigest()
    if digest != ACCEPTED_CONFIG_SHA256:
        fail(f"kernel config hash is not accepted: {digest}")
    check_required_config(parse_config(data))
    return digest


def check_module_members(members: list[tarfile.TarInfo]) -> None:
    names: set[str] = set()
    found = 0
    for member in members:
        if member.name in names:
            fail(f"modules archive contains a duplicate member: {member.name}")
        names.add(member.name)
        if member.name == EXPECTED_MODULE:
            if not member.isfile():
                fail("accepted LPG module archive member is not a regular file")
            found += 1
    if found != 1:
        fail(f"modules archive has {found} accepted LPG module members")


def verify_module_bytes(data: bytes) -> str:
    digest = sha256(data).hexdigest()
    if len(data) != ACCEPTED_MODULE_FIXTURE_SIZE:
        fail(f"accepted LPG module size is wrong: {len(data)}")
    if digest != ACCEPTED_MODULE_FIXTURE_SHA256:
        fail(f"accepted LPG module hash is wrong: {digest}")
    if (
        len(data) < 20
        or data[:6] != b"\x7fELF\x02\x01"
        or int.from_bytes(data[16:18], "little") != 1
        or int.from_bytes(data[18:20], "little") != 183
    ):
        fail("accepted LPG module is not an AArch64 relocatable ELF")
    for marker in EXPECTED_MODULE_MARKERS:
        if marker not in data:
            fail(f"accepted LPG module marker is missing: {marker!r}")
    return digest


def verify_module_fixture(path: Path) -> str:
    return verify_module_bytes(read_ordinary(path))


def verify_modules(path: Path) -> tuple[str, int]:
    lexical = lexical_path(path)
    if lexical.is_symlink():
        fail(f"input is not an ordinary file: {path}")
    resolved = lexical.resolve(strict=True)
    if lexical != resolved:
        fail(f"input contains a linked path component: {path}")
    descriptor = os.open(
        resolved,
        os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_size <= 0
            or before.st_size > MAX_MODULES_SIZE
        ):
            fail(f"input has an invalid type or size: {path}")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            digest_builder = sha256()
            size = 0
            while chunk := stream.read(1024 * 1024):
                size += len(chunk)
                digest_builder.update(chunk)
            digest = digest_builder.hexdigest()
            if digest != ACCEPTED_MODULES_SHA256:
                fail(f"modules archive hash is not accepted: {digest}")
            stream.seek(0)
            with tarfile.open(fileobj=stream, mode="r:gz") as archive:
                members = archive.getmembers()
                check_module_members(members)
                member = archive.getmember(EXPECTED_MODULE)
                projected = archive.extractfile(member)
                if projected is None:
                    fail("accepted LPG module archive member is not readable")
                with projected:
                    module_data = projected.read(
                        ACCEPTED_MODULE_FIXTURE_SIZE + 1
                    )
                verify_module_bytes(module_data)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        size != before.st_size
        or before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ctime_ns != after.st_ctime_ns
    ):
        fail(f"input changed while it was verified: {path}")
    return digest, size


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("modules", type=Path)
    return parser.parse_args(arguments)


def main(arguments: list[str]) -> int:
    options = parse_arguments(arguments)
    source, commit = verify_source(options.source)
    config_digest = verify_config(options.config)
    modules_digest, modules_size = verify_modules(options.modules)
    print(f"source={source}")
    print(f"source_commit={commit}")
    print(f"config_sha256={config_digest}")
    print(f"modules_sha256={modules_digest}")
    print(f"modules_size={modules_size}")
    print("buttons=power,volume-down,volume-up")
    print("indicator=pm8350c-lpg-channel-2-green-default-off")
    print("PASS accepted kernel source, config, and module capability contract")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, subprocess.SubprocessError, tarfile.TarError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)

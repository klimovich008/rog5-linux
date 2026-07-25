#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-}
[ -n "$source_dir" ] || {
	echo 'FAIL set SOURCE_DIR to the pinned v14 Linux source' >&2
	exit 1
}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0011-clk-guard-orphan-reparent-with-runtime-PM.patch
verifier=$repo/scripts/device/verify-clk-orphan-runtime-pm-patch.sh
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

[ -r "$patch" ] && [ -x "$verifier" ]
"$verifier" "$patch" "$source_dir" >/dev/null
tree=$stage/mutation-source
git -c advice.detachedHead=false clone -q --shared --no-checkout \
	"$source_dir" "$tree"
git -C "$tree" sparse-checkout set --no-cone /drivers/clk/clk.c
git -C "$tree" checkout -q 6e40861cc51c067f9989c4513003e8fbd046c22f
git -C "$tree" apply "$patch"
canonical=$stage/canonical-clk.c
cp "$tree/drivers/clk/clk.c" "$canonical"

reject_mutation() {
	label=$1
	mutant=$2
	if ALLOW_UNPINNED_PATCH=1 "$verifier" "$mutant" "$source_dir" \
		>"$stage/$label.output" 2>&1
	then
		echo "FAIL runtime-PM verifier accepted $label mutation" >&2
		exit 1
	fi
}

make_mutation() {
	label=$1
	mutation=$2
	mutant=$stage/$label.patch
	cp "$canonical" "$tree/drivers/clk/clk.c"
	python3 - "$tree/drivers/clk/clk.c" "$mutation" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
mutation = sys.argv[2]
text = path.read_text()

def function_text(signature):
    start = text.index(signature)
    end = text.index("\n}\n", start) + 3
    return start, end, text[start:end]

def replace_function(start, end, function):
    global text
    text = text[:start] + function + text[end:]

if mutation == "get-under-lock":
    start, end, function = function_text(
        "static int __clk_core_init(struct clk_core *core)"
    )
    function = function.replace(
        "\tret = clk_pm_runtime_get_all();", "\tret = 0;", 1
    )
    function = function.replace(
        "\tclk_prepare_lock();\n",
        "\tclk_prepare_lock();\n\tret = clk_pm_runtime_get_all();\n",
        1,
    )
    replace_function(start, end, function)
elif mutation == "put-before-unlock":
    start, end, function = function_text(
        "static int __clk_core_init(struct clk_core *core)"
    )
    function = function.replace("\tclk_pm_runtime_put_all();\n", "", 1)
    function = function.replace(
        "\tclk_prepare_unlock();\n",
        "\tclk_pm_runtime_put_all();\n\tclk_prepare_unlock();\n",
        1,
    )
    replace_function(start, end, function)
elif mutation == "missing-put":
    start, end, function = function_text(
        "static int __clk_core_init(struct clk_core *core)"
    )
    function = function.replace("\tclk_pm_runtime_put_all();\n", "", 1)
    replace_function(start, end, function)
elif mutation == "missing-hw-provider-guard":
    start = text.index("int of_clk_add_hw_provider(")
    end = text.index("EXPORT_SYMBOL_GPL(of_clk_add_hw_provider);", start)
    function = text[start:end]
    function = function.replace("\tret = clk_pm_runtime_get_all();\n", "", 1)
    function = function.replace("\tclk_pm_runtime_put_all();\n", "", 1)
    text = text[:start] + function + text[end:]
elif mutation == "missing-provider-cleanup":
    start = text.index("int of_clk_add_provider(")
    end = text.index("EXPORT_SYMBOL_GPL(of_clk_add_provider);", start)
    function = text[start:end]
    function = function.replace("\t\tof_clk_del_provider(np);\n", "", 1)
    text = text[:start] + function + text[end:]
elif mutation == "skip-orphan-scan":
    start, end, function = function_text(
        "static int __clk_core_init(struct clk_core *core)"
    )
    function = function.replace(
        "\tclk_core_reparent_orphans_nolock(core);\n",
        "\t/* orphan scan skipped */\n",
        1,
    )
    replace_function(start, end, function)
elif mutation == "direct-runtime-pm":
    start, end, function = function_text(
        "static int __clk_core_init(struct clk_core *core)"
    )
    function = function.replace(
        "ret = clk_pm_runtime_get_all();",
        "ret = pm_runtime_resume_and_get(core->dev);",
        1,
    )
    replace_function(start, end, function)
elif mutation == "qcom-specific":
    start, end, function = function_text(
        "static int __clk_core_init(struct clk_core *core)"
    )
    function = function.replace(
        "\tclk_prepare_lock();\n",
        '\tif (of_device_is_compatible(core->of_node, "qcom,sm8350"))\n'
        "\t\treturn 0;\n\tclk_prepare_lock();\n",
        1,
    )
    replace_function(start, end, function)
elif mutation == "extra-regmap-read":
    start, end, function = function_text(
        "static int __clk_core_init(struct clk_core *core)"
    )
    function = function.replace(
        "\tclk_prepare_lock();\n",
        "\tregmap_read(NULL, 0, NULL);\n\tclk_prepare_lock();\n",
        1,
    )
    replace_function(start, end, function)
else:
    raise SystemExit(f"unknown mutation: {mutation}")

path.write_text(text)
PY
	git -C "$tree" diff -- drivers/clk/clk.c >"$mutant"
	reject_mutation "$label" "$mutant"
}

make_mutation get-under-lock get-under-lock
make_mutation put-before-unlock put-before-unlock
make_mutation missing-put missing-put
make_mutation missing-hw-provider-guard missing-hw-provider-guard
make_mutation missing-provider-cleanup missing-provider-cleanup
make_mutation skip-orphan-scan skip-orphan-scan
make_mutation direct-runtime-pm direct-runtime-pm
make_mutation qcom-specific qcom-specific
make_mutation extra-regmap-read extra-regmap-read

echo 'PASS CCF verifier rejects lock inversion, imbalance, incomplete paths, skipped scans, and device-specific control'

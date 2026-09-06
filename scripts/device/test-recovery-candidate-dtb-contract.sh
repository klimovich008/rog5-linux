#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-recovery.dtso
builder=$repo/scripts/device/build-recovery-candidate-dtb.sh
delta_verifier=$repo/scripts/device/verify-recovery-dtb-delta.py
bundle_verifier=$repo/scripts/device/verify-network-root-bundle.sh
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

[ -r "$overlay" ] && [ -x "$builder" ] && [ -x "$delta_verifier" ] &&
	[ -x "$bundle_verifier" ]
for command in dtc fdtget fdtoverlay fdtput python3; do
	command -v "$command" >/dev/null
done
[ "$(grep -c 'status = "okay";' "$overlay")" -eq 2 ]
[ "$(grep -c 'status = "disabled";' "$overlay")" -eq 5 ]
[ "$(grep -c '^&' "$overlay")" -eq 8 ]

for label in rmtfs_mem gpu gmu gpucc adreno_smmu; do
	grep -q "^&$label {" "$overlay"
	grep -Eq "^[[:space:]]*$label([[:space:]]|$)" "$builder"
done

for node in \
	/reserved-memory/memory@9b800000 \
	/soc@0/gpu@3d00000 \
	/soc@0/gmu@3d6a000 \
	/soc@0/clock-controller@3d90000 \
	/soc@0/iommu@3da0000
do
	grep -Fq "$node" "$builder"
	grep -Fq "$node" "$bundle_verifier"
done

# Every missing isolation status must fail for the exact source-policy reason.
printf 'dummy\n' >"$stage/dummy-base.dtb"
for label in rmtfs_mem gpu gmu gpucc adreno_smmu; do
	awk -v label="$label" '
		$0 == "&" label " {" { target = 1 }
		target && /status = "disabled";/ { target = 0; next }
		{ print }
	' "$overlay" >"$stage/mutant.dtso"
	if "$builder" "$stage/dummy-base.dtb" "$stage/mutant.dtso" \
		"$stage/output.dtb" >"$stage/source-policy.log" 2>&1; then
		echo "FAIL builder accepted recovery overlay without $label isolation" >&2
		exit 1
	fi
	grep -Fxq \
		'FAIL recovery overlay must contain exactly five disabled statuses' \
		"$stage/source-policy.log" || {
		echo "FAIL builder rejected missing $label isolation incorrectly" >&2
		cat "$stage/source-policy.log" >&2
		exit 1
	}
done

cat >"$stage/base.dts" <<'EOF'
/dts-v1/;

/ {
	compatible = "asus,rog-phone5", "qcom,sm8350";
	#address-cells = <2>;
	#size-cells = <2>;

	memory@80000000 {
		device_type = "memory";
		reg = <0x0 0x80000000 0x0 0x37100000
		       0x2 0x0 0x1 0x80000000
		       0x0 0xc0000000 0x1 0x40000000
		       0x0 0xb9500000 0x0 0x0>;
	};

	reserved-memory {
		#address-cells = <2>;
		#size-cells = <2>;
		ranges;

		rmtfs_mem: memory@9b800000 {
			reg = <0x0 0x9b800000 0x0 0x400000>;
			status = "okay";
		};
	};

	soc@0 {
		compatible = "simple-bus";
		#address-cells = <2>;
		#size-cells = <2>;
		ranges;

		ufs_mem_hc: ufshc@1d84000 {
			status = "disabled";
		};

		ufs_mem_phy: phy@1d87000 {
			status = "disabled";
		};

		gpu: gpu@3d00000 {
			status = "okay";
		};

		gmu: gmu@3d6a000 {
			status = "okay";
		};

		gpucc: clock-controller@3d90000 {
			status = "okay";
		};

		adreno_smmu: iommu@3da0000 {
			status = "okay";
		};

		usb_1: usb@a6f8800 {
			status = "disabled";

			usb_1_dwc3: usb@a600000 {
				dr_mode = "peripheral";
				maximum-speed = "super-speed";
				phys = <&usb_1_hsphy &usb_1_qmpphy>;
				phy-names = "usb2-phy", "usb3-phy";
			};
		};

		usb_1_hsphy: phy@88e3000 {
			#phy-cells = <0>;
			status = "disabled";
		};

		usb_1_qmpphy: phy@88e8000 {
			#phy-cells = <0>;
			status = "disabled";
		};

		usb_2: usb@a8f8800 {
			status = "disabled";
		};
	};
};
EOF

dtc -q -@ -I dts -O dtb -o "$stage/base.dtb" "$stage/base.dts"
"$builder" "$stage/base.dtb" "$overlay" "$stage/recovery.dtb" >/dev/null
"$delta_verifier" "$stage/base.dtb" "$stage/recovery.dtb" >/dev/null

mkdir "$stage/mock-bin"
cat >"$stage/mock-bin/fdtoverlay" <<'EOF'
#!/bin/sh
kill -TERM "$PPID"
exit 0
EOF
chmod 0755 "$stage/mock-bin/fdtoverlay"
set +e
PATH=$stage/mock-bin:$PATH \
	"$builder" "$stage/base.dtb" "$overlay" \
	"$stage/signal-output/recovery.dtb" \
	>"$stage/signal.log" 2>&1
signal_status=$?
set -e
[ "$signal_status" -eq 143 ] || {
	echo "FAIL TERM returned unexpected builder status: $signal_status" >&2
	cat "$stage/signal.log" >&2
	exit 1
}
[ ! -e "$stage/signal-output/recovery.dtb" ]
[ -z "$(find "$stage/signal-output" -maxdepth 1 -type d \
	-name '.rog5-recovery-dtb.*' -print -quit)" ]

reject_delta() {
	mutant=$1
	expected=$2
	log=$mutant.log
	if "$delta_verifier" "$stage/base.dtb" "$mutant" >"$log" 2>&1; then
		echo "FAIL delta verifier accepted $(basename "$mutant")" >&2
		exit 1
	fi
	grep -Fq "$expected" "$log" || {
		echo "FAIL delta verifier rejected $(basename "$mutant") incorrectly" >&2
		cat "$log" >&2
		exit 1
	}
}

cp "$stage/recovery.dtb" "$stage/unapproved-property.dtb"
fdtput -t s "$stage/unapproved-property.dtb" / model rog5-mutant
reject_delta "$stage/unapproved-property.dtb" \
	'FAIL recovery overlay changed an unapproved property: /:model'

cp "$stage/recovery.dtb" "$stage/wrong-isolation.dtb"
fdtput -t s "$stage/wrong-isolation.dtb" \
	/soc@0/clock-controller@3d90000 status okay
reject_delta "$stage/wrong-isolation.dtb" \
	'FAIL candidate recovery property is wrong:'

cp "$stage/recovery.dtb" "$stage/extra-node.dtb"
fdtput -c "$stage/extra-node.dtb" /soc@0/rog5-mutant
reject_delta "$stage/extra-node.dtb" \
	'FAIL recovery overlay changed DTB nodes:'

cp "$stage/recovery.dtb" "$stage/wrong-phy.dtb"
qmp_phandle=$(fdtget -t x "$stage/base.dtb" /soc@0/phy@88e8000 phandle)
fdtput -t x "$stage/wrong-phy.dtb" \
	/soc@0/usb@a6f8800/usb@a600000 phys "$qmp_phandle"
reject_delta "$stage/wrong-phy.dtb" \
	'FAIL candidate recovery property is wrong:'

dd if="$stage/recovery.dtb" of="$stage/truncated.dtb" \
	bs=1 count=128 status=none
reject_delta "$stage/truncated.dtb" \
	'FAIL DTB total size does not equal its file size:'

awk '
	$0 == "&gpu {" {
		print
		print "\tcompatible = \"rog5,unapproved\";"
		next
	}
	{ print }
' "$overlay" >"$stage/unapproved-overlay.dtso"
if "$builder" "$stage/base.dtb" "$stage/unapproved-overlay.dtso" \
	"$stage/unapproved-output.dtb" >"$stage/unapproved-builder.log" 2>&1; then
	echo 'FAIL builder accepted an unrelated recovery DTB property change' >&2
	exit 1
fi
grep -Fq \
	'FAIL recovery overlay changed an unapproved property:' \
	"$stage/unapproved-builder.log" || {
	echo 'FAIL builder rejected unrelated DTB change for the wrong reason' >&2
	cat "$stage/unapproved-builder.log" >&2
	exit 1
}
[ -z "$(find "$stage" -maxdepth 1 -type d \
	-name '.rog5-recovery-dtb.*' -print -quit)" ] || {
	echo 'FAIL builder left a DTB publication staging directory' >&2
	exit 1
}

echo 'PASS recovery DT contract preserves the board and limits the exact semantic delta'

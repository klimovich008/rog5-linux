#!/bin/sh
set -eu

source_dir=${1:?usage: verify-a660-full-dependency-contract.sh PINNED_SOURCE FIRMWARE_ROOT KERNEL_CONFIG}
firmware_root=${2:?missing firmware root}
kernel_config=${3:?missing kernel config}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
expected_commit=d9ac316489f4258d389d6298659d5e9c22183400
expected_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92

dtsi=$source_dir/arch/arm64/boot/dts/qcom/sm8350.dtsi
hdk=$source_dir/arch/arm64/boot/dts/qcom/sm8350-hdk.dts
gpu_binding=$source_dir/Documentation/devicetree/bindings/display/msm/gpu.yaml
gmu_binding=$source_dir/Documentation/devicetree/bindings/display/msm/gmu.yaml
msm_makefile=$source_dir/drivers/gpu/drm/msm/Makefile
msm_drv=$source_dir/drivers/gpu/drm/msm/msm_drv.c
msm_gpu=$source_dir/drivers/gpu/drm/msm/msm_gpu.c
msm_iommu=$source_dir/drivers/gpu/drm/msm/msm_iommu.c
adreno_device=$source_dir/drivers/gpu/drm/msm/adreno/adreno_device.c
adreno_gpu=$source_dir/drivers/gpu/drm/msm/adreno/adreno_gpu.c
a6xx_catalog=$source_dir/drivers/gpu/drm/msm/adreno/a6xx_catalog.c
a6xx_gpu=$source_dir/drivers/gpu/drm/msm/adreno/a6xx_gpu.c
a6xx_gmu=$source_dir/drivers/gpu/drm/msm/adreno/a6xx_gmu.c
qcom_smmu=$source_dir/drivers/iommu/arm/arm-smmu/arm-smmu-qcom.c
mdt_loader=$source_dir/drivers/soc/qcom/mdt_loader.c
mdt_header=$source_dir/include/linux/soc/qcom/mdt_loader.h
qcom_scm=$source_dir/drivers/firmware/qcom/qcom_scm.c
qcom_scm_header=$source_dir/include/linux/firmware/qcom/qcom_scm.h
smmu_verifier=$repo/scripts/device/verify-adreno-smmu-dependency-contract.sh
firmware_verifier=$repo/scripts/device/verify-a660-firmware.sh

[ -d "$source_dir/.git" ]
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ]
[ "$(git -C "$source_dir" rev-parse 'HEAD^{tree}')" = "$expected_tree" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]

check_hash() {
	file=$1
	expected=$2
	[ -f "$file" ] && [ ! -L "$file" ]
	[ "$(sha256sum "$file" | cut -d ' ' -f 1)" = "$expected" ]
}

check_hash "$dtsi" \
	58d28a520a21e21f55703ae968d6e45c6b7750e6a2d3138dcb6cafe2bc6d0a3c
check_hash "$hdk" \
	23a033cf675cb898cfaf2f660ce3fc60a5728d85d5a6fe35e35ce169657dfd9f
check_hash "$gpu_binding" \
	e24e7d2ef531f4cf55cc482fcfdf33cbf66bbc6f220db9b2f9c55742ab21edeb
check_hash "$gmu_binding" \
	8b27958c17c544b3ed9fb87763834a5de68091c52fe5e119731c42a7f7e06256
check_hash "$msm_makefile" \
	cfe132cb04b1f630bd85b589fe27e43b45adf759c761e532d58fb0151bb72195
check_hash "$msm_drv" \
	7f928abf51301516c63c834946e3b264b53416c016f4800729c2a9b1025f9c1e
check_hash "$msm_gpu" \
	5a20c0a5151a8da2646380cddf14f6cdfa34a8f953b5330fe613774ae695daa6
check_hash "$msm_iommu" \
	d196c1c9efb4af66729bf8eaeb26510f707b7acc1bc4edb43530315602785e29
check_hash "$adreno_device" \
	e7d3de968a744c61394e708cfc416a1aead514c09e71e2a68342260000479599
check_hash "$adreno_gpu" \
	3bd1c6a4d15f1f31ecfbda2ea1d1a07d6b122eb2864adfaf6178e8942bc9fbe0
check_hash "$a6xx_catalog" \
	f1089d825f7b52029520509a39de23c6c05c4ef432e6dff0b084dbdb4bf547b8
check_hash "$a6xx_gpu" \
	29733589c6375930852cb26cfee674f83008084e6bdb792fd86164ea487bf85d
check_hash "$a6xx_gmu" \
	97b2fc130862f00445b509855b16121b2eba6e5a5228f92457c2923297fd4999
check_hash "$qcom_smmu" \
	a8ba34c18e75740495d64a15ad6ff94fec4265814f96d7068b9f4c5e45eb3663
check_hash "$mdt_loader" \
	aaea94b2a992efc459f5fdd7a0e50d22ec505dd244a9ad564cacd0541764d8a8
check_hash "$mdt_header" \
	48979d5ce45033d31c02260e60a1c57dda22ebcee6a7e6bf75119b52d8744969
check_hash "$qcom_scm" \
	9937c99567878507e03e213a0b89b2f2c1b31dec1ac89c0342deb387de467c33
check_hash "$qcom_scm_header" \
	7c946d7e6509af94b9902f17e572153db88956a815d5897f3730a3abbe647d04
check_hash "$smmu_verifier" \
	d02d84c6c7f1d7569c76ea4d366feda3b5c1f73c66b0166080dbcb3e92cccdea
check_hash "$firmware_verifier" \
	958cb7a3a6d228ff83e3e2722e9bc8792540fa7304aa7633c5699d4d9b47af00

sh "$smmu_verifier" "$source_dir" >/dev/null
sh "$firmware_verifier" "$firmware_root" >/dev/null

gpu_block=$(sed -n \
	'/^[[:space:]]*gpu: gpu@3d00000 {/,/^[[:space:]]*gmu: gmu@3d6a000 {/p' \
	"$dtsi" | sed '$d')
gmu_block=$(sed -n \
	'/^[[:space:]]*gmu: gmu@3d6a000 {/,/^[[:space:]]*gpucc: clock-controller@3d90000 {/p' \
	"$dtsi" | sed '$d')
gpu_mem_block=$(sed -n \
	'/^[[:space:]]*pil_gpu_mem: memory@8b51a000 {/,/^[[:space:]]*};/p' \
	"$dtsi")

[ -n "$gpu_block" ]
[ -n "$gmu_block" ]
[ -n "$gpu_mem_block" ]

for property in \
	'compatible = "qcom,adreno-660.1", "qcom,adreno";' \
	'reg = <0 0x03d00000 0 0x40000>,' \
	'<0 0x03d9e000 0 0x1000>,' \
	'<0 0x03d61000 0 0x800>;' \
	'reg-names = "kgsl_3d0_reg_memory",' \
	'"cx_mem",' \
	'"cx_dbgc";' \
	'interrupts = <GIC_SPI 300 IRQ_TYPE_LEVEL_HIGH>;' \
	'iommus = <&adreno_smmu 0 0x400>, <&adreno_smmu 1 0x400>;' \
	'operating-points-v2 = <&gpu_opp_table>;' \
	'qcom,gmu = <&gmu>;' \
	'#cooling-cells = <2>;' \
	'status = "disabled";' \
	'memory-region = <&pil_gpu_mem>;'
do
	printf '%s\n' "$gpu_block" | grep -Fq "$property"
done

[ "$(printf '%s\n' "$gpu_block" | grep -c 'opp-hz = ')" -eq 10 ]
gpu_frequencies=$(printf '%s\n' "$gpu_block" |
	sed -n 's/.*opp-hz = .*<\([0-9][0-9]*\)>.*/\1/p' |
	tr '\n' ' ' | sed 's/ $//')
[ "$gpu_frequencies" = \
	'840000000 778000000 738000000 676000000 608000000 540000000 491000000 443000000 379000000 315000000' ]
if printf '%s\n' "$gpu_block" |
	grep -Eq '^[[:space:]]*(clocks|clock-names|power-domains|interconnects|.*-supply)[[:space:]]*='
then
	echo 'FAIL upstream A660 GPU node gained an unreviewed direct dependency' >&2
	exit 1
fi

for property in \
	'compatible = "qcom,adreno-gmu-660.1", "qcom,adreno-gmu";' \
	'reg = <0 0x03d6a000 0 0x34000>,' \
	'<0 0x03de0000 0 0x10000>,' \
	'<0 0x0b290000 0 0x10000>;' \
	'reg-names = "gmu", "rscc", "gmu_pdc";' \
	'interrupts = <GIC_SPI 304 IRQ_TYPE_LEVEL_HIGH>,' \
	'<GIC_SPI 305 IRQ_TYPE_LEVEL_HIGH>;' \
	'interrupt-names = "hfi", "gmu";' \
	'power-domains = <&gpucc GPU_CX_GDSC>,' \
	'<&gpucc GPU_GX_GDSC>;' \
	'power-domain-names = "cx",' \
	'"gx";' \
	'iommus = <&adreno_smmu 5 0x400>;' \
	'opp-hz = /bits/ 64 <200000000>;' \
	'opp-level = <RPMH_REGULATOR_LEVEL_MIN_SVS>;'
do
	printf '%s\n' "$gmu_block" | grep -Fq "$property"
done

[ "$(printf '%s\n' "$gmu_block" |
	sed -n '/^[[:space:]]*clocks = /,/;$/p' |
	grep -o '<&' | wc -l)" -eq 7 ]
gmu_clock_names=$(printf '%s\n' "$gmu_block" |
	sed -n '/^[[:space:]]*clock-names = /,/;$/p' |
	sed 's/.*= //' | tr -d '";,' | tr '\n\t' '  ' |
	tr -s ' ' | sed 's/^ //; s/ $//')
[ "$gmu_clock_names" = 'gmu cxo axi memnoc ahb hub smmu_vote' ]
[ "$(printf '%s\n' "$gmu_block" | grep -c 'opp-hz = ')" -eq 1 ]
if printf '%s\n' "$gmu_block" |
	grep -Eq '^[[:space:]]*(status|firmware-name|memory-region|interconnects|.*-supply)[[:space:]]*='
then
	echo 'FAIL upstream A660 GMU node gained an unreviewed property' >&2
	exit 1
fi

printf '%s\n' "$gpu_mem_block" |
	grep -Fq 'reg = <0x0 0x8b51a000 0x0 0x2000>;'
printf '%s\n' "$gpu_mem_block" | grep -Fq 'no-map;'
if printf '%s\n' "$gpu_mem_block" | grep -Eq 'status[[:space:]]*='; then
	echo 'FAIL GPU PIL reservation status assumption changed' >&2
	exit 1
fi

hdk_gpu=$(sed -n '/^&gpu {/,/^};/p' "$hdk")
hdk_zap=$(sed -n '/^&gpu_zap_shader {/,/^};/p' "$hdk")
printf '%s\n' "$hdk_gpu" | grep -Fq 'status = "okay";'
printf '%s\n' "$hdk_zap" |
	grep -Fq 'firmware-name = "qcom/sm8350/a660_zap.mbn";'

for binding in \
	"pattern: '^qcom,adreno-[3-7][0-9][0-9]\\.[0-9]+$'" \
	'qcom,gmu:' \
	'zap-shader:' \
	'memory-region:' \
	'firmware-name:'
do
	grep -Fq "$binding" "$gpu_binding"
done
for binding in \
	'qcom,adreno-gmu-660.1' \
	'- const: rscc' \
	'- const: gmu_pdc' \
	'- const: smmu_vote' \
	'- const: cx' \
	'- const: gx'
do
	grep -Fq -- "$binding" "$gmu_binding"
done

a660_catalog=$(sed -n \
	'/[.]chip_ids = ADRENO_CHIP_IDS(0x06060001)/,/^[[:space:]]*}, {/p' \
	"$a6xx_catalog")
for catalog_entry in \
	'.family = ADRENO_6XX_GEN4,' \
	'.revn = 660,' \
	'[ADRENO_FW_SQE] = "a660_sqe.fw",' \
	'[ADRENO_FW_GMU] = "a660_gmu.bin",' \
	'.gmem = SZ_1M + SZ_512K,' \
	'ADRENO_QUIRK_HAS_CACHED_COHERENT' \
	'ADRENO_QUIRK_HAS_HW_APRIV' \
	'.funcs = &a6xx_gpu_funcs,' \
	'.zapfw = "a660_zap.mdt",' \
	'.hwcg = a660_hwcg,' \
	'.protect = &a660_protect,' \
	'.gbif_cx = a640_gbif,' \
	'.gmu_cgc_mode = 0x00020000,' \
	'.prim_fifo_threshold = 0x00300200,'
do
	printf '%s\n' "$a660_catalog" | grep -Fq "$catalog_entry"
done

grep -Fq "obj-\$(CONFIG_DRM_MSM)" "$msm_makefile"
grep -Fq 'module_param(separate_gpu_kms, bool, 0400);' "$msm_drv"
grep -Fq 'return separate_gpu_kms;' "$msm_drv"
grep -Fq 'msm.separate_gpu_kms=1' "$0"
grep -Fq 'msm_gpu_no_components()' "$adreno_device"
grep -Fq 'return msm_gpu_probe(pdev, &a3xx_ops);' "$adreno_device"
grep -Fq 'DRIVER_RENDER' "$msm_drv"

msm_open_block=$(sed -n '/^static int msm_open(/,/^}/p' "$msm_drv")
load_gpu_block=$(sed -n '/^static void load_gpu(/,/^}/p' "$msm_drv")
adreno_load_block=$(sed -n '/^struct msm_gpu \*adreno_load_gpu(/,/^}/p' \
	"$adreno_device")
a6xx_init_block=$(sed -n '/^static struct msm_gpu \*a6xx_gpu_init(/,/^}/p' \
	"$a6xx_gpu")
msm_gpu_init_block=$(sed -n '/^int msm_gpu_init(/,/^}/p' "$msm_gpu")
gmu_init_block=$(sed -n '/^int a6xx_gmu_init(/,/^}/p' "$a6xx_gmu")
rpmh_init_block=$(sed -n '/^static void a6xx_gmu_rpmh_init(/,/^}/p' "$a6xx_gmu")
iommu_new_block=$(sed -n '/^struct msm_mmu \*msm_iommu_new(/,/^}/p' "$msm_iommu")
gmu_resume_block=$(sed -n '/^int a6xx_gmu_resume(/,/^}/p' "$a6xx_gmu")

printf '%s\n' "$msm_open_block" | grep -Fq 'load_gpu(dev);'
printf '%s\n' "$load_gpu_block" |
	grep -Fq 'priv->gpu = adreno_load_gpu(dev);'

for registration_step in \
	'of_parse_phandle(pdev->dev.of_node, "qcom,gmu", 0);' \
	'BUG_ON(!node);' \
	'adreno_gpu_init(dev, pdev, adreno_gpu, info->funcs, nr_rings);' \
	'a6xx_gmu_init(a6xx_gpu, node);' \
	'msm_mmu_set_fault_handler'
do
	printf '%s\n' "$a6xx_init_block" | grep -Fq "$registration_step"
done
if printf '%s\n' "$a6xx_init_block" |
	grep -Eq 'request_firmware|adreno_load_fw|clk_bulk_prepare_enable'
then
	echo 'FAIL A660 registration now starts firmware or clocks directly' >&2
	exit 1
fi

for registration_step in \
	'gpu->mmio = msm_ioremap(pdev, config->ioname);' \
	'devm_request_irq(&pdev->dev, gpu->irq, irq_handler,' \
	'ret = get_clocks(pdev, gpu);' \
	'devm_regulator_get(&pdev->dev, "vdd");' \
	'devm_regulator_get(&pdev->dev, "vddcx");' \
	'platform_set_drvdata(pdev, &gpu->adreno_smmu);' \
	'gpu->vm = gpu->funcs->create_vm(gpu, pdev);'
do
	printf '%s\n' "$msm_gpu_init_block" | grep -Fq "$registration_step"
done
grep -Fq 'devm_clk_bulk_get_all(&pdev->dev, &gpu->grp_clks);' "$msm_gpu"
if printf '%s\n' "$msm_gpu_init_block" |
	grep -Eq 'request_firmware|adreno_load_fw|clk_bulk_prepare_enable'
then
	echo 'FAIL generic MSM GPU registration now starts firmware or clocks' >&2
	exit 1
fi

for registration_step in \
	'pm_runtime_enable(gmu->dev);' \
	'a6xx_gmu_clocks_probe(gmu);' \
	'a6xx_gmu_memory_probe(adreno_gpu->base.dev, gmu);' \
	'a6xx_gmu_memory_alloc(gmu, &gmu->debug, SZ_4K * 7,' \
	'a6xx_gmu_memory_alloc(gmu, &gmu->dummy, gmu->dummy.size,' \
	'a6xx_gmu_memory_alloc(gmu, &gmu->icache,' \
	'a6xx_gmu_memory_alloc(gmu, &gmu->log, SZ_16K, 0, "log");' \
	'a6xx_gmu_memory_alloc(gmu, &gmu->hfi, SZ_16K, 0, "hfi");' \
	'a6xx_gmu_get_irq(gmu, pdev, "hfi", a6xx_hfi_irq);' \
	'a6xx_gmu_get_irq(gmu, pdev, "gmu", a6xx_gmu_irq);' \
	'dev_pm_domain_attach_by_name(gmu->dev, "cx");' \
	'dev_pm_domain_attach_by_name(gmu->dev, "gx");' \
	'a6xx_gmu_pwrlevels_probe(gmu);' \
	'a6xx_hfi_init(gmu);' \
	'a6xx_gmu_rpmh_init(gmu);'
do
	printf '%s\n' "$gmu_init_block" | grep -Fq "$registration_step"
done
if printf '%s\n' "$gmu_init_block" |
	grep -Eq 'request_firmware|adreno_load_fw|clk_bulk_prepare_enable'
then
	echo 'FAIL GMU registration now starts firmware or clocks' >&2
	exit 1
fi

for write_path in \
	'devm_platform_ioremap_resource_byname(pdev, "gmu_pdc");' \
	'gmu_write_rscc(gmu, REG_A6XX_GPU_RSCC_RSC_STATUS0_DRV0, BIT(24));' \
	'gmu_write_rscc(gmu, REG_A6XX_RSCC_PDC_SLAVE_ID_DRV0, 1);' \
	'gmu_write_rscc(gmu, seqmem0_drv0_reg, 0xeaaae5a0);' \
	'pdc_write(pdcptr, REG_A6XX_PDC_GPU_SEQ_START_ADDR, 0);' \
	'pdc_write(pdcptr, REG_A6XX_PDC_GPU_ENABLE_PDC, 0x80000001);'
do
	printf '%s\n' "$rpmh_init_block" | grep -Fq "$write_path"
done

printf '%s\n' "$iommu_new_block" |
	grep -Fq 'iommu_attach_device(iommu->domain, dev);'
grep -Fq 'mmu = msm_iommu_gpu_new(&pdev->dev, gpu, quirks);' "$adreno_gpu"
grep -Fq 'mmu = msm_iommu_new(gmu->dev, 0);' "$a6xx_gmu"
for smmu_callback in \
	'priv->get_ttbr1_cfg = qcom_adreno_smmu_get_ttbr1_cfg;' \
	'priv->set_ttbr0_cfg = qcom_adreno_smmu_set_ttbr0_cfg;' \
	'priv->get_fault_info = qcom_adreno_smmu_get_fault_info;' \
	'priv->set_stall = qcom_adreno_smmu_set_stall;'
do
	grep -Fq "$smmu_callback" "$qcom_smmu"
done

for deferred_step in \
	'ret = adreno_load_fw(adreno_gpu);' \
	'pm_runtime_enable(&pdev->dev);' \
	'ret = pm_runtime_get_sync(&pdev->dev);' \
	'ret = msm_gpu_hw_init(gpu);'
do
	printf '%s\n' "$adreno_load_block" | grep -Fq "$deferred_step"
done
load_order=$(printf '%s\n' "$adreno_load_block" | nl -ba)
firmware_line=$(printf '%s\n' "$load_order" |
	awk '/ret = adreno_load_fw/ { print $1; exit }')
runtime_line=$(printf '%s\n' "$load_order" |
	awk '/pm_runtime_get_sync/ { print $1; exit }')
hardware_line=$(printf '%s\n' "$load_order" |
	awk '/ret = msm_gpu_hw_init/ { print $1; exit }')
[ "$firmware_line" -lt "$runtime_line" ]
[ "$runtime_line" -lt "$hardware_line" ]

for resume_step in \
	'pm_runtime_get_sync(gmu->dev);' \
	'clk_set_rate(gmu->core_clk, 200000000);' \
	'clk_bulk_prepare_enable(gmu->nr_clocks, gmu->clocks);' \
	'ret = a6xx_gmu_fw_start(gmu, status);' \
	'ret = a6xx_hfi_start(gmu, status);' \
	'clk_bulk_disable_unprepare(gmu->nr_clocks, gmu->clocks);'
do
	printf '%s\n' "$gmu_resume_block" | grep -Fq "$resume_step"
done
grep -Fq 'ret = a6xx_gmu_resume(a6xx_gpu);' "$a6xx_gpu"
grep -Fq 'ret = adreno_zap_shader_load(gpu, GPU_PAS_ID);' "$a6xx_gpu"
grep -Fq 'request_firmware_direct(&fw, fwname, gpu->dev->dev);' "$adreno_gpu"
grep -Fq 'mem_size = qcom_mdt_get_size(fw);' "$adreno_gpu"
grep -Fq 'if (mem_size > resource_size(&r))' "$adreno_gpu"
grep -Fq 'ret = qcom_mdt_load(dev, fw, fwname, pasid,' "$adreno_gpu"
grep -Fq 'ret = qcom_scm_pas_auth_and_reset(pasid);' "$adreno_gpu"
grep -Fq 'ret = qcom_scm_set_gpu_smmu_aperture(0);' "$adreno_gpu"
grep -Fq 'ssize_t qcom_mdt_get_size(const struct firmware *fw)' "$mdt_loader"
grep -Fq 'max_addr = ALIGN(phdr->p_paddr + phdr->p_memsz, SZ_4K);' \
	"$mdt_loader"
grep -Fq 'int qcom_scm_pas_auth_and_reset(u32 pas_id)' "$qcom_scm_header"

sqe=$firmware_root/qcom/a660_sqe.fw
gmu_fw=$firmware_root/qcom/a660_gmu.bin
zap=$firmware_root/qcom/sm8350/a660_zap.mbn
check_hash "$sqe" \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76
check_hash "$gmu_fw" \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7
check_hash "$zap" \
	5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d
[ "$(wc -c < "$sqe")" -eq 43292 ]
[ "$(wc -c < "$gmu_fw")" -eq 55252 ]
[ "$(wc -c < "$zap")" -eq 1054648 ]

phdr_words=$(od -An -tx4 -N96 -j52 "$zap" | tr -d ' \n')
[ "$phdr_words" = \
	'00000000000000000000000000000000000000940000000007000000000000000000000000001000000000000000000000000f9000000f90020000000000100000000001001010000000100000001000000007b8000007b80800000700100000' ]
zap_memory_size=4096
gpu_reserved_size=8192
[ "$zap_memory_size" -le "$gpu_reserved_size" ]

check_hash "$kernel_config" \
	68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f
for symbol in \
	CONFIG_ARCH_QCOM=y \
	CONFIG_DRM=y \
	CONFIG_DRM_MSM=y \
	CONFIG_DRM_MSM_KMS=y \
	CONFIG_QCOM_SCM=y \
	CONFIG_QCOM_MDT_LOADER=y \
	CONFIG_QCOM_RPMH=y \
	CONFIG_QCOM_RPMHPD=y \
	CONFIG_QCOM_RPMPD=y \
	CONFIG_QCOM_COMMAND_DB=y \
	CONFIG_QCOM_AOSS_QMP=y \
	CONFIG_QCOM_LLCC=y \
	CONFIG_REGULATOR_QCOM_RPMH=y \
	CONFIG_ARM_SMMU=y \
	CONFIG_ARM_SMMU_QCOM=y \
	CONFIG_IOMMU_SUPPORT=y \
	CONFIG_FW_LOADER=y \
	CONFIG_INTERCONNECT=y \
	CONFIG_INTERCONNECT_QCOM=y \
	CONFIG_INTERCONNECT_QCOM_SM8350=y \
	CONFIG_COMMON_CLK_QCOM=y \
	CONFIG_QCOM_GDSC=y \
	CONFIG_SM_GPUCC_8350=m \
	CONFIG_PM_GENERIC_DOMAINS=y \
	CONFIG_PM_GENERIC_DOMAINS_OF=y \
	CONFIG_QCOM_CLK_RPMH=y
do
	grep -qx "$symbol" "$kernel_config"
done

echo 'PASS pinned Linux 7.1.4 A660 graph: probe-time GPU/GMU IOMMU plus RSCC/PDC setup, deferred first-open firmware/power/SCM, exact 4 KiB zap payload in 8 KiB no-map memory, and complete built-in dependencies'

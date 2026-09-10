#!/bin/sh
set -eu

source_dir=${1:?usage: verify-a660-ucode-allocation-boundary.sh PINNED_SOURCE [LIVE_REPORT] [ACCEPTANCE_MARKER]}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
report=${2:-$repo/test-results/2026-07-26-a660-firmware-request-only-v4-live-accepted.md}
marker=${3:-$repo/manifests/acceptance/a660-firmware-request-only-v4-live.accepted}

expected_commit=d9ac316489f4258d389d6298659d5e9c22183400
expected_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92
report_sha=f5e1226923f82528e8cc2ad2727d38834c64761d7691559e295da43fafcfbd8c
marker_sha=912846d98ef6ee9fb3c0fa9f0b455c49d47a2f43ff72e2ba1d14c1c284cbfe32

msm_dir=$source_dir/drivers/gpu/drm/msm
adreno_device=$msm_dir/adreno/adreno_device.c
adreno_gpu=$msm_dir/adreno/adreno_gpu.c
a6xx_catalog=$msm_dir/adreno/a6xx_catalog.c
a6xx_gpu=$msm_dir/adreno/a6xx_gpu.c
a6xx_gpu_h=$msm_dir/adreno/a6xx_gpu.h
msm_gpu=$msm_dir/msm_gpu.c
msm_gpu_h=$msm_dir/msm_gpu.h
msm_gem=$msm_dir/msm_gem.c
msm_gem_h=$msm_dir/msm_gem.h
msm_gem_vma=$msm_dir/msm_gem_vma.c
msm_iommu=$msm_dir/msm_iommu.c
acceptance_verifier=$repo/scripts/device/verify-a660-firmware-request-only-v4-live-acceptance.sh

fail() {
	echo "FAIL $*" >&2
	exit 1
}

check_hash() {
	file=$1
	expected=$2
	label=$3
	if [ ! -f "$file" ] || [ -L "$file" ] || [ ! -r "$file" ]; then
		fail "$label is missing, linked, or unreadable: $file"
	fi
	actual=$(sha256sum "$file" | cut -d ' ' -f 1)
	[ "$actual" = "$expected" ] ||
		fail "$label hash mismatch: expected $expected, got $actual"
}

line_once() {
	text=$1
	needle=$2
	label=$3
	stats=$(printf '%s\n' "$text" |
		awk -v needle="$needle" '
			index($0, needle) { count++; line = NR }
			END { print count + 0 ":" line + 0 }
		')
	count=${stats%%:*}
	line=${stats#*:}
	[ "$count" -eq 1 ] ||
		fail "$label count is $count, expected 1"
	printf '%s\n' "$line"
}

for command in awk cut git grep sed sha256sum tr wc; do
	command -v "$command" >/dev/null ||
		fail "missing command: $command"
done

[ -d "$source_dir" ] || fail "missing source directory: $source_dir"
[ -x "$acceptance_verifier" ] ||
	fail "missing executable acceptance verifier: $acceptance_verifier"
[ "$(git -C "$source_dir" rev-parse --is-inside-work-tree)" = true ] ||
	fail 'source is not a Git worktree'
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ] ||
	fail 'pinned source commit changed'
[ "$(git -C "$source_dir" rev-parse 'HEAD^{tree}')" = "$expected_tree" ] ||
	fail 'pinned source tree changed'
[ -z "$(git -C "$source_dir" status --porcelain)" ] ||
	fail 'pinned source worktree is not clean'

check_hash "$report" "$report_sha" 'A660 request-only v4 live report'
check_hash "$marker" "$marker_sha" 'A660 request-only v4 acceptance marker'
"$acceptance_verifier" "$report" "$marker" >/dev/null

check_hash "$adreno_device" \
	e7d3de968a744c61394e708cfc416a1aead514c09e71e2a68342260000479599 \
	'adreno_device.c'
check_hash "$adreno_gpu" \
	3bd1c6a4d15f1f31ecfbda2ea1d1a07d6b122eb2864adfaf6178e8942bc9fbe0 \
	'adreno_gpu.c'
check_hash "$a6xx_catalog" \
	f1089d825f7b52029520509a39de23c6c05c4ef432e6dff0b084dbdb4bf547b8 \
	'a6xx_catalog.c'
check_hash "$a6xx_gpu" \
	29733589c6375930852cb26cfee674f83008084e6bdb792fd86164ea487bf85d \
	'a6xx_gpu.c'
check_hash "$a6xx_gpu_h" \
	fefca6579b234fda7c0afdcf07d5c2dbb80aade92674c45380c661e259d9f9bb \
	'a6xx_gpu.h'
check_hash "$msm_gpu" \
	5a20c0a5151a8da2646380cddf14f6cdfa34a8f953b5330fe613774ae695daa6 \
	'msm_gpu.c'
check_hash "$msm_gpu_h" \
	b477ecc7f2396b4b65cb28eda9f454c885368277b421e5a11a2209ea4b317b2d \
	'msm_gpu.h'
check_hash "$msm_gem" \
	49b304a0602361647d9cd86acc5b798b93bfcb2c275fa88e4b0eb05eb0290b53 \
	'msm_gem.c'
check_hash "$msm_gem_h" \
	76840d1c84d6cc3b3b34b094c799f4d682998d10ac3d7888bf189b7540b869f1 \
	'msm_gem.h'
check_hash "$msm_gem_vma" \
	7bca4eda8aa3711b3fc0b3e3b74ff4f775ca94e6e13296cee761ee588ed4c1a2 \
	'msm_gem_vma.c'
check_hash "$msm_iommu" \
	d196c1c9efb4af66729bf8eaeb26510f707b7acc1bc4edb43530315602785e29 \
	'msm_iommu.c'

a660_catalog=$(sed -n \
	'/[.]chip_ids = ADRENO_CHIP_IDS(0x06060001)/,/^[[:space:]]*}, {/p' \
	"$a6xx_catalog")
[ -n "$a660_catalog" ] || fail 'missing exact A660.1 catalog entry'
for catalog_contract in \
	'.revn = 660,' \
	'[ADRENO_FW_SQE] = "a660_sqe.fw",' \
	'[ADRENO_FW_GMU] = "a660_gmu.bin",' \
	'ADRENO_QUIRK_HAS_HW_APRIV' \
	'.funcs = &a6xx_gpu_funcs,'
do
	line_once "$a660_catalog" "$catalog_contract" \
		"A660 catalog contract $catalog_contract" >/dev/null
done
[ "$(printf '%s\n' "$a660_catalog" |
	grep -c '\[ADRENO_FW_')" -eq 2 ] ||
	fail 'A660.1 catalog firmware list is not exactly SQE plus GMU'
if printf '%s\n' "$a660_catalog" |
	grep -Eq 'ADRENO_FW_AQE|ADRENO_QUIRK_PREEMPTION'
then
	fail 'A660.1 unexpectedly selects AQE firmware or automatic preemption'
fi

adreno_load_block=$(sed -n \
	'/^struct msm_gpu \*adreno_load_gpu(/,/^}/p' "$adreno_device")
a6xx_init_block=$(sed -n \
	'/^static struct msm_gpu \*a6xx_gpu_init(/,/^}/p' "$a6xx_gpu")
a6xx_ucode_block=$(sed -n \
	'/^static int a6xx_ucode_load(/,/^}/p' "$a6xx_gpu")
a6xx_version_block=$(sed -n \
	'/^static bool a6xx_ucode_check_version(/,/^}/p' "$a6xx_gpu")
fw_bo_block=$(sed -n \
	'/^struct drm_gem_object \*adreno_fw_create_bo(/,/^}/p' "$adreno_gpu")
gem_prot_block=$(sed -n '/^int msm_gem_prot(/,/^}/p' "$msm_gem")
gem_pin_block=$(sed -n \
	'/^int msm_gem_pin_vma_locked(/,/^}/p' "$msm_gem")
gem_kernel_block=$(sed -n \
	'/^void \*msm_gem_kernel_new(/,/^}/p' "$msm_gem")
gem_kernel_put_block=$(sed -n \
	'/^void msm_gem_kernel_put(/,/^}/p' "$msm_gem")
gem_unpin_block=$(sed -n \
	'/^void msm_gem_unpin_iova(/,/^}/p' "$msm_gem")
gem_vma_map_block=$(sed -n \
	'/^msm_gem_vma_map(/,/^}/p' "$msm_gem_vma")
gem_vma_unmap_block=$(sed -n \
	'/^void msm_gem_vma_unmap(/,/^}/p' "$msm_gem_vma")
iommu_map_block=$(sed -n \
	'/^static int msm_iommu_map(/,/^}/p' "$msm_iommu")
iommu_unmap_block=$(sed -n \
	'/^static int msm_iommu_unmap(/,/^}/p' "$msm_iommu")
a6xx_destroy_block=$(sed -n \
	'/^static void a6xx_destroy(/,/^}/p' "$a6xx_gpu")

for block in "$adreno_load_block" "$a6xx_init_block" "$a6xx_ucode_block" \
	"$a6xx_version_block" "$fw_bo_block" "$gem_prot_block" \
	"$gem_pin_block" "$gem_kernel_block" "$gem_kernel_put_block" \
	"$gem_unpin_block" "$gem_vma_map_block" "$gem_vma_unmap_block" \
	"$iommu_map_block" "$iommu_unmap_block" "$a6xx_destroy_block"
do
	[ -n "$block" ] || fail 'could not extract one or more source blocks'
done

line_once "$(sed -n '1,30p' "$adreno_device")" \
	'int enable_preemption = -1;' \
	'default preemption setting' >/dev/null
line_once "$a6xx_init_block" 'int ret, nr_rings = 1;' \
	'A6xx default ring count' >/dev/null
line_once "$a6xx_init_block" \
	'!!(info->quirks & ADRENO_QUIRK_HAS_HW_APRIV);' \
	'A6xx HW_APRIV projection' >/dev/null
line_once "$a6xx_init_block" \
	'(info->quirks & ADRENO_QUIRK_PREEMPTION)))' \
	'A6xx automatic preemption gate' >/dev/null

firmware_line=$(line_once "$adreno_load_block" \
	'adreno_load_fw(adreno_gpu)' 'Adreno firmware load')
ucode_line=$(line_once "$adreno_load_block" \
	'if (gpu->funcs->ucode_load) {' 'Adreno ucode load')
runtime_enable_line=$(line_once "$adreno_load_block" \
	'pm_runtime_enable(&pdev->dev);' 'GPU runtime-PM enable')
runtime_get_line=$(line_once "$adreno_load_block" \
	'pm_runtime_get_sync(&pdev->dev);' 'GPU runtime-PM resume')
hardware_line=$(line_once "$adreno_load_block" \
	'msm_gpu_hw_init(gpu);' 'GPU hardware initialization')
if [ "$firmware_line" -ge "$ucode_line" ] ||
	[ "$ucode_line" -ge "$runtime_enable_line" ] ||
	[ "$runtime_enable_line" -ge "$runtime_get_line" ] ||
	[ "$runtime_get_line" -ge "$hardware_line" ]
then
	fail 'Adreno firmware/ucode/runtime-power/hardware order changed'
fi

sqe_line=$(line_once "$a6xx_ucode_block" \
	'a6xx_gpu->sqe_bo = adreno_fw_create_bo(gpu,' \
	'A6xx SQE object allocation')
version_line=$(line_once "$a6xx_ucode_block" \
	'a6xx_ucode_check_version(a6xx_gpu, a6xx_gpu->sqe_bo)' \
	'A6xx SQE version check')
aqe_line=$(line_once "$a6xx_ucode_block" \
	'if (!a6xx_gpu->aqe_bo && adreno_gpu->fw[ADRENO_FW_AQE]) {' \
	'A6xx optional AQE gate')
shadow_gate_line=$(line_once "$a6xx_ucode_block" \
	'if ((adreno_gpu->base.hw_apriv || a6xx_gpu->has_whereami) &&' \
	'A6xx shadow gate')
shadow_line=$(line_once "$a6xx_ucode_block" \
	'a6xx_gpu->shadow = msm_gem_kernel_new(gpu->dev,' \
	'A6xx shadow object allocation')
reglist_line=$(line_once "$a6xx_ucode_block" \
	'a6xx_gpu->pwrup_reglist_ptr = msm_gem_kernel_new(gpu->dev, PAGE_SIZE,' \
	'A6xx power-up reglist allocation')
if [ "$sqe_line" -ge "$version_line" ] ||
	[ "$version_line" -ge "$aqe_line" ] ||
	[ "$aqe_line" -ge "$shadow_gate_line" ] ||
	[ "$shadow_gate_line" -ge "$shadow_line" ] ||
	[ "$shadow_line" -ge "$reglist_line" ]
then
	fail 'A6xx SQE/AQE/shadow/reglist allocation order changed'
fi

for ucode_contract in \
	'MSM_BO_WC | MSM_BO_MAP_PRIV,' \
	'&a6xx_gpu->shadow_iova);' \
	'&a6xx_gpu->pwrup_reglist_iova);' \
	'msm_gem_object_set_name(a6xx_gpu->sqe_bo, "sqefw");' \
	'msm_gem_object_set_name(a6xx_gpu->shadow_bo, "shadow");' \
	'msm_gem_object_set_name(a6xx_gpu->pwrup_reglist_bo, "pwrup_reglist");'
do
	printf '%s\n' "$a6xx_ucode_block" |
		grep -Fq "$ucode_contract" ||
		fail "A6xx ucode path omits: $ucode_contract"
done
[ "$(printf '%s\n' "$a6xx_ucode_block" |
	grep -Fc 'msm_gem_kernel_new(gpu->dev')" -eq 2 ] ||
	fail 'A6xx ucode path no longer has exact shadow-plus-reglist GEM calls'
if printf '%s\n' "$a6xx_ucode_block" |
	grep -Fq '!a6xx_gpu->pwrup_reglist_bo'
then
	fail 'power-up reglist allocation unexpectedly became guarded'
fi

a660_version_branch=$(sed -n \
	'/else if (!strcmp(sqe_name, "a660_sqe.fw")) {/,/} else {/p' \
	"$a6xx_gpu")
line_once "$a660_version_branch" 'ret = true;' \
	'A660 SQE acceptance' >/dev/null
if printf '%s\n' "$a660_version_branch" | grep -Fq 'has_whereami'
then
	fail 'A660 SQE branch unexpectedly changes WHERE_AM_I state'
fi

for fw_bo_contract in \
	'msm_gem_kernel_new(gpu->dev, fw->size - 4,' \
	'MSM_BO_WC | MSM_BO_GPU_READONLY, gpu->vm, &bo, iova);' \
	'memcpy(ptr, &fw->data[4], fw->size - 4);' \
	'msm_gem_put_vaddr(bo);'
do
	line_once "$fw_bo_block" "$fw_bo_contract" \
		"SQE firmware BO step $fw_bo_contract" >/dev/null
done

for gem_kernel_contract in \
	'struct drm_gem_object *obj = msm_gem_new(dev, size, flags);' \
	'ret = msm_gem_get_and_pin_iova(obj, vm, iova);' \
	'vaddr = msm_gem_get_vaddr(obj);'
do
	line_once "$gem_kernel_block" "$gem_kernel_contract" \
		"GEM kernel allocation step $gem_kernel_contract" >/dev/null
done
for gem_pin_contract in \
	'pages = msm_gem_get_pages_locked(obj, MSM_MADV_WILLNEED);' \
	'return msm_gem_vma_map(vma, prot, msm_obj->sgt);'
do
	line_once "$gem_pin_block" "$gem_pin_contract" \
		"GEM pin step $gem_pin_contract" >/dev/null
done
for gem_prot_contract in \
	'int prot = IOMMU_READ;' \
	'if (!(msm_obj->flags & MSM_BO_GPU_READONLY))' \
	'prot |= IOMMU_WRITE;' \
	'if (msm_obj->flags & MSM_BO_MAP_PRIV)' \
	'prot |= IOMMU_PRIV;'
do
	line_once "$gem_prot_block" "$gem_prot_contract" \
		"GEM protection step $gem_prot_contract" >/dev/null
done
line_once "$gem_vma_map_block" \
	'ret = vm_map_op(vm, &(struct msm_vm_map_op){' \
	'GPUVA map operation' >/dev/null
line_once "$(sed -n '250,267p' "$msm_gem_vma")" \
	'return vm->mmu->funcs->map(vm->mmu, op->iova, op->sgt, op->offset,' \
	'GPUVM-to-MMU map dispatch' >/dev/null
line_once "$iommu_map_block" \
	'ret = iommu_map_sgtable(iommu->domain, iova, sgt, prot);' \
	'MSM IOMMU scatterlist map' >/dev/null
line_once "$gem_unpin_block" \
	'put_iova_spaces(obj, vm, true, "close");' \
	'GEM IOVA close rollback' >/dev/null
line_once "$gem_vma_unmap_block" \
	'vm_unmap_op(vm, &(struct msm_vm_unmap_op){' \
	'GPUVA unmap operation' >/dev/null
line_once "$(sed -n '245,257p' "$msm_gem_vma")" \
	'vm->mmu->funcs->unmap(vm->mmu, op->iova, op->range);' \
	'GPUVM-to-MMU unmap dispatch' >/dev/null
line_once "$iommu_unmap_block" \
	'iommu_unmap(iommu->domain, iova, len);' \
	'MSM IOMMU unmap' >/dev/null

for forbidden in pm_runtime_ regulator_ qcom_scm a6xx_hfi \
	a6xx_gmu_resume a6xx_gmu_start adreno_zap gpu_write gpu_read \
	gmu_write gmu_read
do
	if printf '%s\n' "$a6xx_ucode_block" | grep -Fq "$forbidden"
	then
		fail "A6xx ucode allocation unexpectedly performs $forbidden"
	fi
done

for cleanup_contract in \
	'msm_gem_put_vaddr(bo);' \
	'msm_gem_unpin_iova(bo, vm);' \
	'drm_gem_object_put(bo);'
do
	line_once "$gem_kernel_put_block" "$cleanup_contract" \
		"GEM kernel rollback step $cleanup_contract" >/dev/null
done
for existing_cleanup in \
	'msm_gem_unpin_iova(a6xx_gpu->sqe_bo, gpu->vm);' \
	'drm_gem_object_put(a6xx_gpu->sqe_bo);' \
	'msm_gem_unpin_iova(a6xx_gpu->shadow_bo, gpu->vm);' \
	'drm_gem_object_put(a6xx_gpu->shadow_bo);'
do
	line_once "$a6xx_destroy_block" "$existing_cleanup" \
		"A6xx existing cleanup $existing_cleanup" >/dev/null
done
if printf '%s\n' "$a6xx_destroy_block" |
	grep -Fq 'pwrup_reglist_bo'
then
	fail 'normal A6xx destroy now releases the power-up reglist; re-audit boundary'
fi
if printf '%s\n' "$a6xx_destroy_block" |
	grep -Eq 'msm_gem_put_vaddr|msm_gem_kernel_put'
then
	fail 'normal A6xx destroy now drops retained CPU vmaps; re-audit boundary'
fi
line_once "$(sed -n '404,416p' "$msm_gem_h")" \
	'return (msm_obj->vmap_count == 0) && msm_obj->vaddr;' \
	'GEM CPU-vmap release condition' >/dev/null

# Exact first-call A660.1 result under the default -1 preemption policy:
# one SQE object, one shadow object, and one power-up reglist object;
# no AQE object; three new GPU-VM mappings. SQE is read-only to the GPU,
# while shadow and reglist are read/write privileged mappings.
#
# A future one-shot diagnostic must explicitly release all three objects and mappings.
# It must do so before it returns. SQE needs unpin-plus-put after its CPU vaddr was
# already dropped; shadow and reglist need msm_gem_kernel_put(). This is
# mandatory because normal a6xx_destroy does not release pwrup_reglist_bo.
# Also, normal a6xx_destroy does not drop the shadow CPU vaddr.
# The seam is before GPU/GMU runtime power, register access, HFI, and ZAP/SCM,
# but it is not hardware-free: iommu_map_sgtable updates the accepted SMMU path.
echo 'PASS A660 ucode allocation is source-isolatable with three SMMU mappings and mandatory explicit rollback'

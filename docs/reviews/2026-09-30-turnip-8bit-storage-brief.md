# Review brief: enabling storageBuffer8BitAccess on Adreno 660 (Turnip, Mesa 26.2.3)

Goal: DXVK >= 3.0 hard-requires VkPhysicalDeviceVulkan12Features::storageBuffer8BitAccess.
Turnip (Mesa 26.2.3) exposes it only on a7xx (`storage_8bit` prop). The phone has an
Adreno 660 (a6xx gen4: has_isam_v, storage_16bit, has_ssbo_imm_offsets).

Proposed change: packages/mesa/0001-tu-enable-storageBuffer8BitAccess-on-a6xx-gen4.patch
(sets storage_8bit = True in a6xx_gen4). Packaging: packages/mesa/PKGBUILD, README.md.
Test program: packages/mesa/s8test/; test results in packages/mesa/README.md (s8test 400+ iterations, dEQP-VK 8-bit + SSBO regression sets all pass;
and its racy-RMW control variant fails as expected).

Mesa 26.2.3 source (read-only): /home/deck/.cache/claude-mesa8/mesa (has the patch applied
in the worktree). Relevant: src/freedreno/common/freedreno_devices.py,
src/freedreno/ir3/ir3_a6xx.c (emit_load_uav / emit_intrinsic_store_ssbo 8-bit cases),
src/freedreno/ir3/ir3_compiler_nir.c (emit_intrinsic_load_ssbo), ir3_nir.c,
ir3_nir_lower_io_offsets.c, src/freedreno/vulkan/tu_shader.cc (lower_ssbo_descriptor_instr),
tu_descriptor_set.cc (write_buffer_descriptor_addr, descriptor_size), tu_device.cc,
tu_cmd_buffer.cc (dynamic SSBO descriptors), fdl/fd6_view.cc (fdl6_buffer_view_init).
Upstream history: MR 28254 ("tu: KHR_8bit_storage support", a750 only) and MR 39124 (all a7xx).
Issue 9979 comment: "Blob doesn't expose it on A6XX."

Questions:
1. Is there any a7xx-only assumption in the 8-bit SSBO path (ISA encoding of typed
   ldib/stib with u16 type and R8_UINT descriptor, imm offsets, bindless/nonuniform handling,
   descriptor count/size, push/dynamic/mutable descriptors, descriptor buffer, robustness)
   that would be wrong on a6xx gen4? Anything gated on chip >= 7 or gen >= 7 that the
   8-bit path relies on?
2. Correctness of byte stores under concurrency: typed stib to an R8_UINT buffer view should
   be a true byte store (as imageStore to r8ui texel buffers). Any reason to doubt that on a6xx?
3. Anything else that changes for a6xx gen4 when storage_8bit is set (e.g. other GPUs in
   a6xx_gen4, pipeline cache, GL driver) that could regress?
Answer concisely with file:line evidence. Do not modify files.

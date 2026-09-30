/* s8test: checks the Vulkan features DXVK 3.1 hard-requires and exercises
 * 8-bit SSBO loads/stores (VK_KHR_8bit_storage) with a compute shader.
 *
 *   s8test features            -> print missing DXVK-required features
 *   s8test run <iterations> [robust=1] [spv=s8test.spv]
 *                              -> run the 8-bit storage tests
 *
 * Build: glslangValidator --target-env vulkan1.3 -V s8test.comp -o s8test.spv
 *        glslangValidator --target-env vulkan1.3 -DRMW -V s8test.comp -o s8rmw.spv
 *        cc -O2 -I<mesa>/include s8test.c -o s8test -lvulkan
 * s8rmw.spv replaces the byte stores with a racy 32-bit read-modify-write
 * (negative control: it must FAIL).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <vulkan/vulkan.h>

#define CK(x) do { VkResult r_ = (x); if (r_ != VK_SUCCESS) { \
   fprintf(stderr, "FAIL %s = %d (line %d)\n", #x, r_, __LINE__); exit(2); } } while (0)

static VkInstance inst;
static VkPhysicalDevice pdev;
static VkDevice dev;
static VkQueue queue;
static uint32_t qfam;
static VkPhysicalDeviceMemoryProperties memprops;

static int has_ext(const char *name)
{
   uint32_t n = 0;
   vkEnumerateDeviceExtensionProperties(pdev, NULL, &n, NULL);
   VkExtensionProperties *e = calloc(n, sizeof(*e));
   vkEnumerateDeviceExtensionProperties(pdev, NULL, &n, e);
   int found = 0;
   for (uint32_t i = 0; i < n; i++)
      if (!strcmp(e[i].extensionName, name)) found = 1;
   free(e);
   return found;
}

static void init_instance(void)
{
   VkApplicationInfo app = { VK_STRUCTURE_TYPE_APPLICATION_INFO, .apiVersion = VK_API_VERSION_1_3,
                             .pApplicationName = "s8test" };
   VkInstanceCreateInfo ici = { VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, .pApplicationInfo = &app };
   CK(vkCreateInstance(&ici, NULL, &inst));
   uint32_t n = 8; VkPhysicalDevice pds[8];
   CK(vkEnumeratePhysicalDevices(inst, &n, pds));
   pdev = VK_NULL_HANDLE;
   for (uint32_t i = 0; i < n; i++) {
      VkPhysicalDeviceProperties p; vkGetPhysicalDeviceProperties(pds[i], &p);
      printf("device %u: %s api %u.%u.%u driver 0x%x\n", i, p.deviceName, VK_VERSION_MAJOR(p.apiVersion),
             VK_VERSION_MINOR(p.apiVersion), VK_VERSION_PATCH(p.apiVersion), p.driverVersion);
      if (!pdev && strstr(p.deviceName, "Adreno")) pdev = pds[i];
   }
   if (!pdev) { fprintf(stderr, "no Adreno device\n"); exit(2); }
   vkGetPhysicalDeviceMemoryProperties(pdev, &memprops);
}

static int check_features(void)
{
   VkPhysicalDeviceRobustness2FeaturesEXT rob2 = { VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ROBUSTNESS_2_FEATURES_EXT };
   VkPhysicalDeviceDepthClipEnableFeaturesEXT dce = { VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DEPTH_CLIP_ENABLE_FEATURES_EXT, &rob2 };
   VkPhysicalDeviceMaintenance5FeaturesKHR m5 = { VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_MAINTENANCE_5_FEATURES_KHR, &dce };
   VkPhysicalDeviceMaintenance6FeaturesKHR m6 = { VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_MAINTENANCE_6_FEATURES_KHR, &m5 };
   VkPhysicalDeviceVulkan13Features v13 = { VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_3_FEATURES, &m6 };
   VkPhysicalDeviceVulkan12Features v12 = { VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES, &v13 };
   VkPhysicalDeviceVulkan11Features v11 = { VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_1_FEATURES, &v12 };
   VkPhysicalDeviceFeatures2 f2 = { VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2, &v11 };
   vkGetPhysicalDeviceFeatures2(pdev, &f2);
   VkPhysicalDeviceFeatures *c = &f2.features;
   VkPhysicalDeviceProperties p; vkGetPhysicalDeviceProperties(pdev, &p);
   int bad = 0;
#define R(cond, name) do { if (!(cond)) { printf("MISSING %s\n", name); bad++; } } while (0)
   R(p.apiVersion >= VK_API_VERSION_1_3, "Vulkan 1.3");
   R(c->depthBiasClamp, "depthBiasClamp"); R(c->depthClamp, "depthClamp"); R(c->dualSrcBlend, "dualSrcBlend");
   R(c->fillModeNonSolid, "fillModeNonSolid"); R(c->fragmentStoresAndAtomics, "fragmentStoresAndAtomics");
   R(c->fullDrawIndexUint32, "fullDrawIndexUint32"); R(c->geometryShader, "geometryShader");
   R(c->imageCubeArray, "imageCubeArray"); R(c->independentBlend, "independentBlend");
   R(c->multiDrawIndirect, "multiDrawIndirect"); R(c->multiViewport, "multiViewport");
   R(c->occlusionQueryPrecise, "occlusionQueryPrecise"); R(c->robustBufferAccess, "robustBufferAccess");
   R(c->sampleRateShading, "sampleRateShading"); R(c->samplerAnisotropy, "samplerAnisotropy");
   R(c->shaderClipDistance, "shaderClipDistance"); R(c->shaderCullDistance, "shaderCullDistance");
   R(c->shaderImageGatherExtended, "shaderImageGatherExtended"); R(c->shaderInt16, "shaderInt16");
   R(c->shaderInt64, "shaderInt64"); R(c->shaderSampledImageArrayDynamicIndexing, "shaderSampledImageArrayDynamicIndexing");
   R(c->textureCompressionBC, "textureCompressionBC");
   R(v11.shaderDrawParameters, "shaderDrawParameters"); R(v11.storageBuffer16BitAccess, "storageBuffer16BitAccess");
   R(v12.bufferDeviceAddress, "bufferDeviceAddress"); R(v12.descriptorIndexing, "descriptorIndexing");
   R(v12.storageBuffer8BitAccess, "storageBuffer8BitAccess");
   R(v12.descriptorBindingSampledImageUpdateAfterBind, "descriptorBindingSampledImageUpdateAfterBind");
   R(v12.descriptorBindingUpdateUnusedWhilePending, "descriptorBindingUpdateUnusedWhilePending");
   R(v12.descriptorBindingPartiallyBound, "descriptorBindingPartiallyBound");
   R(v12.hostQueryReset, "hostQueryReset"); R(v12.runtimeDescriptorArray, "runtimeDescriptorArray");
   R(v12.samplerMirrorClampToEdge, "samplerMirrorClampToEdge"); R(v12.scalarBlockLayout, "scalarBlockLayout");
   R(v12.shaderInt8, "shaderInt8"); R(v12.timelineSemaphore, "timelineSemaphore");
   R(v12.uniformBufferStandardLayout, "uniformBufferStandardLayout"); R(v12.vulkanMemoryModel, "vulkanMemoryModel");
   R(v13.inlineUniformBlock, "inlineUniformBlock"); R(v13.computeFullSubgroups, "computeFullSubgroups");
   R(v13.dynamicRendering, "dynamicRendering"); R(v13.maintenance4, "maintenance4");
   R(v13.shaderDemoteToHelperInvocation, "shaderDemoteToHelperInvocation");
   R(v13.shaderZeroInitializeWorkgroupMemory, "shaderZeroInitializeWorkgroupMemory");
   R(v13.subgroupSizeControl, "subgroupSizeControl"); R(v13.synchronization2, "synchronization2");
   R(has_ext("VK_EXT_depth_clip_enable") && dce.depthClipEnable, "depthClipEnable");
   R(has_ext("VK_EXT_robustness2") && rob2.robustBufferAccess2, "robustBufferAccess2");
   R(has_ext("VK_EXT_robustness2") && rob2.nullDescriptor, "nullDescriptor");
   R(has_ext("VK_KHR_load_store_op_none"), "VK_KHR_load_store_op_none");
   R(has_ext("VK_KHR_maintenance5") && m5.maintenance5, "maintenance5");
   R(has_ext("VK_KHR_maintenance6") && m6.maintenance6, "maintenance6");
   R(has_ext("VK_KHR_swapchain"), "VK_KHR_swapchain");
   R(p.limits.maxPushConstantsSize >= 256, "256 bytes of push data");
   printf("info: uniformAndStorageBuffer8BitAccess=%u storagePushConstant8=%u storageBufferDescriptor-limits: minStorageBufferOffsetAlignment=%llu maxStorageBufferRange=%u\n",
          v12.uniformAndStorageBuffer8BitAccess, v12.storagePushConstant8,
          (unsigned long long)p.limits.minStorageBufferOffsetAlignment, p.limits.maxStorageBufferRange);
   printf(bad ? "features: %d DXVK-required feature(s) missing\n" : "features: all DXVK 3.1 required features present\n", bad);
   return bad;
}

/* ---------------------------------------------------------------- run */

typedef struct { VkBuffer buf; VkDeviceMemory mem; void *map; VkDeviceSize size; } Buf;

static Buf mkbuf(VkDeviceSize size)
{
   Buf b = { .size = size };
   VkBufferCreateInfo bci = { VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO, .size = size,
      .usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT };
   CK(vkCreateBuffer(dev, &bci, NULL, &b.buf));
   VkMemoryRequirements mr; vkGetBufferMemoryRequirements(dev, b.buf, &mr);
   uint32_t want = VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT;
   uint32_t ti = UINT32_MAX;
   for (uint32_t i = 0; i < memprops.memoryTypeCount; i++)
      if ((mr.memoryTypeBits & (1u << i)) && (memprops.memoryTypes[i].propertyFlags & want) == want) { ti = i; break; }
   VkMemoryAllocateInfo mai = { VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO, .allocationSize = mr.size, .memoryTypeIndex = ti };
   CK(vkAllocateMemory(dev, &mai, NULL, &b.mem));
   CK(vkBindBufferMemory(dev, b.buf, b.mem, 0));
   CK(vkMapMemory(dev, b.mem, 0, VK_WHOLE_SIZE, 0, &b.map));
   return b;
}

static void *readfile(const char *path, size_t *len)
{
   FILE *f = fopen(path, "rb"); if (!f) { perror(path); exit(2); }
   fseek(f, 0, SEEK_END); *len = ftell(f); fseek(f, 0, SEEK_SET);
   void *d = malloc(*len); if (fread(d, 1, *len, f) != *len) exit(2); fclose(f); return d;
}

/* One pipeline: set 0 has 4 bindings: 0 = SSBO (readonly bytes), 1 = SSBO out
 * (u32), 2 = SSBO dynamic (bytes written), 3 = SSBO small robustness window.
 * Push constants: mode, n, seed, mask. */
struct pc { uint32_t mode, n, seed, skip; };

static VkPipeline pipe_;
static VkPipelineLayout layout;
static VkDescriptorSetLayout dsl;

static void mkpipe(const char *spv)
{
   VkDescriptorSetLayoutBinding b[4] = {
      { 0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_COMPUTE_BIT },
      { 1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_COMPUTE_BIT },
      { 2, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER_DYNAMIC, 1, VK_SHADER_STAGE_COMPUTE_BIT },
      { 3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_COMPUTE_BIT },
   };
   VkDescriptorSetLayoutCreateInfo dci = { VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO, .bindingCount = 4, .pBindings = b };
   CK(vkCreateDescriptorSetLayout(dev, &dci, NULL, &dsl));
   VkPushConstantRange pcr = { VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(struct pc) };
   VkPipelineLayoutCreateInfo lci = { VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO, .setLayoutCount = 1, .pSetLayouts = &dsl,
                                      .pushConstantRangeCount = 1, .pPushConstantRanges = &pcr };
   CK(vkCreatePipelineLayout(dev, &lci, NULL, &layout));
   size_t len; void *code = readfile(spv, &len);
   VkShaderModuleCreateInfo smi = { VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO, .codeSize = len, .pCode = code };
   VkShaderModule sm; CK(vkCreateShaderModule(dev, &smi, NULL, &sm));
   VkComputePipelineCreateInfo cpi = { VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO,
      .stage = { VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO, .stage = VK_SHADER_STAGE_COMPUTE_BIT, .module = sm, .pName = "main" },
      .layout = layout };
   CK(vkCreateComputePipelines(dev, VK_NULL_HANDLE, 1, &cpi, NULL, &pipe_));
}

static uint32_t xs(uint32_t *s) { *s ^= *s << 13; *s ^= *s >> 17; *s ^= *s << 5; return *s; }
static uint8_t valfn(uint32_t j, uint32_t seed) { return (uint8_t)((j * 2654435761u + seed * 97u) >> 13); }

int main(int argc, char **argv)
{
   init_instance();
   if (argc < 2 || !strcmp(argv[1], "features"))
      return check_features() ? 1 : 0;

   int iters = argc > 2 ? atoi(argv[2]) : 50;
   int robust = argc > 3 ? atoi(argv[3]) : 1;
   const char *spv = argc > 4 ? argv[4] : "s8test.spv";
   if (check_features()) printf("(continuing anyway)\n");

   float prio = 1.0f;
   uint32_t nq = 8; VkQueueFamilyProperties qp[8];
   vkGetPhysicalDeviceQueueFamilyProperties(pdev, &nq, qp);
   for (qfam = 0; qfam < nq; qfam++) if (qp[qfam].queueFlags & VK_QUEUE_COMPUTE_BIT) break;
   VkDeviceQueueCreateInfo qci = { VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO, .queueFamilyIndex = qfam, .queueCount = 1, .pQueuePriorities = &prio };
   VkPhysicalDeviceRobustness2FeaturesEXT rob2 = { VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ROBUSTNESS_2_FEATURES_EXT,
      .robustBufferAccess2 = robust ? VK_TRUE : VK_FALSE, .nullDescriptor = VK_TRUE };
   VkPhysicalDeviceVulkan12Features v12 = { VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES, &rob2,
      .storageBuffer8BitAccess = VK_TRUE, .shaderInt8 = VK_TRUE, .vulkanMemoryModel = VK_TRUE, .scalarBlockLayout = VK_TRUE };
   VkPhysicalDeviceVulkan11Features v11 = { VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_1_FEATURES, &v12, .storageBuffer16BitAccess = VK_TRUE };
   VkPhysicalDeviceFeatures2 f2 = { VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2, &v11,
      .features = { .robustBufferAccess = robust ? VK_TRUE : VK_FALSE, .shaderInt16 = VK_TRUE } };
   const char *exts[] = { "VK_EXT_robustness2" };
   VkDeviceCreateInfo dci = { VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO, &f2, .queueCreateInfoCount = 1, .pQueueCreateInfos = &qci,
                              .enabledExtensionCount = 1, .ppEnabledExtensionNames = exts };
   CK(vkCreateDevice(pdev, &dci, NULL, &dev));
   vkGetDeviceQueue(dev, qfam, 0, &queue);
   printf("device created (robustBufferAccess%s)\n", robust ? " + robustBufferAccess2" : " off");

   const uint32_t N = 1u << 20;            /* bytes / invocations */
   const uint32_t DYN = 256;               /* dynamic offset into bytes buffer */
   Buf in = mkbuf(N + 64), out = mkbuf((VkDeviceSize)N * 16), bytes = mkbuf(N + DYN + 64), win = mkbuf(64);
   mkpipe(spv);

   VkDescriptorPoolSize ps[2] = { { VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 3 }, { VK_DESCRIPTOR_TYPE_STORAGE_BUFFER_DYNAMIC, 1 } };
   VkDescriptorPoolCreateInfo pci = { VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO, .maxSets = 1, .poolSizeCount = 2, .pPoolSizes = ps };
   VkDescriptorPool pool; CK(vkCreateDescriptorPool(dev, &pci, NULL, &pool));
   VkDescriptorSetAllocateInfo dai = { VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO, .descriptorPool = pool, .descriptorSetCount = 1, .pSetLayouts = &dsl };
   VkDescriptorSet set; CK(vkAllocateDescriptorSets(dev, &dai, &set));
   /* binding 0 starts 3 bytes into... no: offsets must be aligned; use an
    * unaligned *range* on binding 3 (13 bytes) for robustness checks. */
   VkDescriptorBufferInfo bi[4] = { { in.buf, 0, N }, { out.buf, 0, (VkDeviceSize)N * 16 }, { bytes.buf, 0, N }, { win.buf, 0, 13 } };
   VkWriteDescriptorSet w[4];
   for (int i = 0; i < 4; i++)
      w[i] = (VkWriteDescriptorSet){ VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = set, .dstBinding = i, .descriptorCount = 1,
         .descriptorType = i == 2 ? VK_DESCRIPTOR_TYPE_STORAGE_BUFFER_DYNAMIC : VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, .pBufferInfo = &bi[i] };
   vkUpdateDescriptorSets(dev, 4, w, 0, NULL);

   VkCommandPoolCreateInfo cpci = { VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO, .queueFamilyIndex = qfam,
                                    .flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT };
   VkCommandPool cp; CK(vkCreateCommandPool(dev, &cpci, NULL, &cp));
   VkCommandBufferAllocateInfo cbai = { VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO, .commandPool = cp, .level = VK_COMMAND_BUFFER_LEVEL_PRIMARY, .commandBufferCount = 1 };
   VkCommandBuffer cb; CK(vkAllocateCommandBuffers(dev, &cbai, &cb));
   VkFenceCreateInfo fci = { VK_STRUCTURE_TYPE_FENCE_CREATE_INFO };
   VkFence fence; CK(vkCreateFence(dev, &fci, NULL, &fence));

   long fails = 0, checked = 0;
   uint32_t rng = 0x12345678;
   for (int it = 0; it < iters; it++) {
      uint32_t mode = it % 5;   /* 0: loads, 1-4: store patterns (see shader) */
      uint32_t seed = xs(&rng);
      uint8_t *ip = in.map, *bp = bytes.map, *wp = win.map;
      for (uint32_t i = 0; i < N + 64; i++) ip[i] = (uint8_t)xs(&rng);
      memset(bp, 0xAA, N + DYN + 64);
      memset(out.map, 0xEE, (size_t)N * 16);
      for (int i = 0; i < 64; i++) wp[i] = (uint8_t)(0x40 + i);
      struct pc pc = { mode, N, seed, (seed >> 3) & 3 };

      CK(vkResetCommandBuffer(cb, 0));
      VkCommandBufferBeginInfo cbbi = { VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO, .flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT };
      CK(vkBeginCommandBuffer(cb, &cbbi));
      vkCmdBindPipeline(cb, VK_PIPELINE_BIND_POINT_COMPUTE, pipe_);
      uint32_t dynoff = DYN;
      vkCmdBindDescriptorSets(cb, VK_PIPELINE_BIND_POINT_COMPUTE, layout, 0, 1, &set, 1, &dynoff);
      vkCmdPushConstants(cb, layout, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(pc), &pc);
      vkCmdDispatch(cb, N / 64, 1, 1);
      CK(vkEndCommandBuffer(cb));
      VkSubmitInfo si = { VK_STRUCTURE_TYPE_SUBMIT_INFO, .commandBufferCount = 1, .pCommandBuffers = &cb };
      CK(vkQueueSubmit(queue, 1, &si, fence));
      CK(vkWaitForFences(dev, 1, &fence, VK_TRUE, UINT64_MAX));
      CK(vkResetFences(dev, 1, &fence));

      uint32_t *op = out.map;
      long f0 = fails;
      if (mode == 0) {
         for (uint32_t i = 0; i < N; i++) {
            uint32_t exp_u = ip[i], exp_s = (uint32_t)(int32_t)(int8_t)ip[i];
            uint32_t j = (i * 7u + seed) % N;  /* random-ish second load */
            uint32_t exp2 = ip[j] + 3u * ip[(j + 1) % N];
            if (op[4*i] != exp_u || op[4*i+1] != exp_s || op[4*i+2] != exp2) {
               if (fails - f0 < 5) printf("  load mismatch i=%u: got %08x %08x %08x want %08x %08x %08x\n",
                                          i, op[4*i], op[4*i+1], op[4*i+2], exp_u, exp_s, exp2);
               fails++;
            }
            checked++;
         }
         /* robustness window: 13-byte range, invocations 0..31 read win[i] */
         for (uint32_t i = 0; i < 32; i++) {
            uint32_t got = op[4*i+3];
            uint32_t want = i < 13 ? (uint32_t)(0x40 + i) : 0;
            int ok = got == want || (i >= 13 && i < 16 && got == (uint32_t)(0x40 + i));
            if (!robust) ok = i >= 13 || got == want;
            if (!ok) {
               if (fails - f0 < 10) printf("  robust load i=%u got %08x want %08x\n", i, got, want);
               fails++;
            }
            checked++;
         }
      } else {
         for (uint32_t j = 0; j < N + DYN + 64; j++) {
            uint8_t want = 0xAA;
            if (j >= DYN && j < DYN + N) {
               uint32_t b = j - DYN;
               int written = mode == 1 || mode == 3 || (mode == 2 && (b & 3) != pc.skip) ||
                             (mode == 4 && b != 0);
               if (written) want = valfn(b, seed);
            }
            if (bp[j] != want) {
               if (fails - f0 < 5) printf("  store mismatch byte %u: got %02x want %02x\n", j, bp[j], want);
               fails++;
            }
            checked++;
         }
         /* robust stores: invocations 0..63 store win[i]; only 0..12 are in range
          * (13..15 may be written if robustStorageBufferAccessSizeAlignment is 4) */
         for (uint32_t i = 0; i < 64; i++) {
            uint8_t in_r = (uint8_t)(0xC0 ^ i), out_r = (uint8_t)(0x40 + i);
            int ok = i < 13 ? wp[i] == in_r : (i < 16 ? (wp[i] == in_r || wp[i] == out_r) : wp[i] == out_r);
            if (!robust) ok = i < 13 ? wp[i] == in_r : 1;
            if (!ok) {
               if (fails - f0 < 10) printf("  robust store byte %u got %02x\n", i, wp[i]);
               fails++;
            }
            checked++;
         }
      }
      if (fails != f0) printf("iteration %d mode %u: %ld mismatches\n", it, mode, fails - f0);
   }
   printf("RESULT: %d iterations, %ld checks, %ld mismatches -> %s\n", iters, checked, fails, fails ? "FAIL" : "PASS");
   return fails ? 1 : 0;
}

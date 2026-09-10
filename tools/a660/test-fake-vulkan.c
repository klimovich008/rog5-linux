// SPDX-License-Identifier: MIT
/*
 * Test-only Vulkan implementation for rog5-vulkan-submit.c.
 *
 * This is linked directly into an offline test binary. It is never installed
 * on the phone and deliberately exposes only the Vulkan calls used by the
 * bounded A660 submit helper.
 */

#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include <vulkan/vulkan.h>

static const char *fake_mode(void)
{
	const char *mode = getenv("ROG5_FAKE_VULKAN_MODE");

	return mode == NULL ? "success" : mode;
}

static bool mode_is(const char *expected)
{
	return strcmp(fake_mode(), expected) == 0;
}

static void reject_unsafe_destroy(void)
{
	if (mode_is("submit_fail") || mode_is("wait_timeout"))
		_Exit(99);
}

static uint32_t physical_device_count(void)
{
	return mode_is("duplicate") ? 2U : 1U;
}

VKAPI_ATTR VkResult VKAPI_CALL
vkCreateInstance(const VkInstanceCreateInfo *create_info,
		 const VkAllocationCallbacks *allocator, VkInstance *instance)
{
	(void)create_info;
	(void)allocator;
	*instance = (VkInstance)(uintptr_t)0x100U;
	return VK_SUCCESS;
}

VKAPI_ATTR void VKAPI_CALL
vkDestroyInstance(VkInstance instance, const VkAllocationCallbacks *allocator)
{
	(void)instance;
	(void)allocator;
	reject_unsafe_destroy();
}

VKAPI_ATTR VkResult VKAPI_CALL
vkEnumeratePhysicalDevices(VkInstance instance, uint32_t *count,
			   VkPhysicalDevice *devices)
{
	uint32_t available = physical_device_count();

	(void)instance;
	if (devices == NULL) {
		*count = available;
		return VK_SUCCESS;
	}
	if (*count < available)
		return VK_INCOMPLETE;
	for (uint32_t index = 0; index < available; index++)
		devices[index] =
			(VkPhysicalDevice)(uintptr_t)(0x200U + index);
	*count = available;
	return VK_SUCCESS;
}

VKAPI_ATTR void VKAPI_CALL
vkGetPhysicalDeviceProperties(VkPhysicalDevice physical_device,
			      VkPhysicalDeviceProperties *properties)
{
	const char *name = mode_is("none") ?
		"Turnip Adreno (TM) 650" : "Turnip Adreno (TM) 660";

	(void)physical_device;
	memset(properties, 0, sizeof(*properties));
	properties->apiVersion = VK_MAKE_API_VERSION(0, 1, 1, 0);
	(void)strncpy(properties->deviceName, name,
		      sizeof(properties->deviceName) - 1U);
}

VKAPI_ATTR void VKAPI_CALL
vkGetPhysicalDeviceQueueFamilyProperties(
	VkPhysicalDevice physical_device, uint32_t *count,
	VkQueueFamilyProperties *properties)
{
	(void)physical_device;
	if (properties == NULL) {
		*count = 1U;
		return;
	}
	memset(&properties[0], 0, sizeof(properties[0]));
	properties[0].queueCount = 1U;
	properties[0].queueFlags =
		mode_is("no_queue") ? 0U : VK_QUEUE_GRAPHICS_BIT;
	*count = 1U;
}

VKAPI_ATTR VkResult VKAPI_CALL
vkCreateDevice(VkPhysicalDevice physical_device,
	       const VkDeviceCreateInfo *create_info,
	       const VkAllocationCallbacks *allocator, VkDevice *device)
{
	(void)physical_device;
	(void)create_info;
	(void)allocator;
	*device = (VkDevice)(uintptr_t)0x300U;
	return VK_SUCCESS;
}

VKAPI_ATTR void VKAPI_CALL
vkDestroyDevice(VkDevice device, const VkAllocationCallbacks *allocator)
{
	(void)device;
	(void)allocator;
	reject_unsafe_destroy();
}

VKAPI_ATTR void VKAPI_CALL
vkGetDeviceQueue(VkDevice device, uint32_t queue_family_index,
		 uint32_t queue_index, VkQueue *queue)
{
	(void)device;
	(void)queue_family_index;
	(void)queue_index;
	*queue = (VkQueue)(uintptr_t)0x400U;
}

VKAPI_ATTR VkResult VKAPI_CALL
vkCreateCommandPool(VkDevice device,
		    const VkCommandPoolCreateInfo *create_info,
		    const VkAllocationCallbacks *allocator,
		    VkCommandPool *command_pool)
{
	(void)device;
	(void)create_info;
	(void)allocator;
	*command_pool = (VkCommandPool)(uintptr_t)0x500U;
	return VK_SUCCESS;
}

VKAPI_ATTR void VKAPI_CALL
vkDestroyCommandPool(VkDevice device, VkCommandPool command_pool,
		     const VkAllocationCallbacks *allocator)
{
	(void)device;
	(void)command_pool;
	(void)allocator;
	reject_unsafe_destroy();
}

VKAPI_ATTR VkResult VKAPI_CALL
vkAllocateCommandBuffers(
	VkDevice device, const VkCommandBufferAllocateInfo *allocate_info,
	VkCommandBuffer *command_buffers)
{
	(void)device;
	(void)allocate_info;
	command_buffers[0] = (VkCommandBuffer)(uintptr_t)0x600U;
	return VK_SUCCESS;
}

VKAPI_ATTR VkResult VKAPI_CALL
vkBeginCommandBuffer(VkCommandBuffer command_buffer,
		     const VkCommandBufferBeginInfo *begin_info)
{
	(void)command_buffer;
	(void)begin_info;
	return VK_SUCCESS;
}

VKAPI_ATTR VkResult VKAPI_CALL
vkEndCommandBuffer(VkCommandBuffer command_buffer)
{
	(void)command_buffer;
	return VK_SUCCESS;
}

VKAPI_ATTR VkResult VKAPI_CALL
vkCreateFence(VkDevice device, const VkFenceCreateInfo *create_info,
	      const VkAllocationCallbacks *allocator, VkFence *fence)
{
	(void)device;
	(void)create_info;
	(void)allocator;
	*fence = (VkFence)(uintptr_t)0x700U;
	return VK_SUCCESS;
}

VKAPI_ATTR void VKAPI_CALL
vkDestroyFence(VkDevice device, VkFence fence,
	       const VkAllocationCallbacks *allocator)
{
	(void)device;
	(void)fence;
	(void)allocator;
	reject_unsafe_destroy();
}

VKAPI_ATTR VkResult VKAPI_CALL
vkQueueSubmit(VkQueue queue, uint32_t submit_count,
	      const VkSubmitInfo *submits, VkFence fence)
{
	(void)queue;
	(void)submit_count;
	(void)submits;
	(void)fence;
	return mode_is("submit_fail") ? VK_ERROR_DEVICE_LOST : VK_SUCCESS;
}

VKAPI_ATTR VkResult VKAPI_CALL
vkWaitForFences(VkDevice device, uint32_t fence_count,
		const VkFence *fences, VkBool32 wait_all, uint64_t timeout)
{
	(void)device;
	(void)fence_count;
	(void)fences;
	(void)wait_all;
	(void)timeout;
	return mode_is("wait_timeout") ? VK_TIMEOUT : VK_SUCCESS;
}

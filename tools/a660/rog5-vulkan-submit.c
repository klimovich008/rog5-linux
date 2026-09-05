// SPDX-License-Identifier: MIT
/*
 * Minimal A660 Vulkan queue-submit acceptance helper.
 *
 * This deliberately creates no window, image, shader, or persistent cache.
 * It submits one empty primary command buffer and waits on one bounded fence.
 */

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <vulkan/vulkan.h>

#define MAX_PHYSICAL_DEVICES 32U
#define MAX_QUEUE_FAMILIES 128U
#define FENCE_TIMEOUT_NS UINT64_C(5000000000)

static bool is_a660_name(const char *name)
{
	return strstr(name, "Adreno (TM) 660") != NULL ||
	       strstr(name, "Adreno 660") != NULL ||
	       strstr(name, "FD660") != NULL;
}

static void print_safe_name(const char *name)
{
	const unsigned char *cursor = (const unsigned char *)name;

	while (*cursor != '\0') {
		unsigned char value = *cursor++;

		if (value < 0x20 || value > 0x7e || value == '=')
			value = '?';
		putchar(value);
	}
}

static int fail_result(const char *operation, VkResult result)
{
	fprintf(stderr, "FAIL %s result=%d\n", operation, result);
	return 1;
}

int main(int argc, char **argv)
{
	const VkApplicationInfo application_info = {
		.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
		.pApplicationName = "rog5-vulkan-submit",
		.applicationVersion = 1,
		.pEngineName = "none",
		.engineVersion = 1,
		.apiVersion = VK_API_VERSION_1_1,
	};
	const VkInstanceCreateInfo instance_info = {
		.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
		.pApplicationInfo = &application_info,
	};
	VkPhysicalDevice physical_devices[MAX_PHYSICAL_DEVICES];
	VkPhysicalDevice selected_physical = VK_NULL_HANDLE;
	VkPhysicalDeviceProperties selected_properties = { 0 };
	VkQueueFamilyProperties queue_properties[MAX_QUEUE_FAMILIES];
	VkCommandBuffer command_buffer = VK_NULL_HANDLE;
	VkCommandPool command_pool = VK_NULL_HANDLE;
	VkInstance instance = VK_NULL_HANDLE;
	VkDevice device = VK_NULL_HANDLE;
	VkFence fence = VK_NULL_HANDLE;
	VkQueue queue = VK_NULL_HANDLE;
	uint32_t physical_count = 0;
	uint32_t selected_queue = UINT32_MAX;
	uint32_t matching_devices = 0;
	VkResult result;
	int status = 1;

	if (argc != 2 || strcmp(argv[1], "--require-a660") != 0) {
		fputs("usage: rog5-vulkan-submit --require-a660\n", stderr);
		return 2;
	}

	result = vkCreateInstance(&instance_info, NULL, &instance);
	if (result != VK_SUCCESS)
		return fail_result("vkCreateInstance", result);

	result = vkEnumeratePhysicalDevices(instance, &physical_count, NULL);
	if (result != VK_SUCCESS) {
		status = fail_result("vkEnumeratePhysicalDevices", result);
		goto out;
	}
	if (physical_count == 0 || physical_count > MAX_PHYSICAL_DEVICES) {
		fputs("FAIL physical-device inventory is outside policy\n", stderr);
		goto out;
	}
	{
		uint32_t observed_count = physical_count;

		result = vkEnumeratePhysicalDevices(instance, &observed_count,
						    physical_devices);
		if (result != VK_SUCCESS) {
			status = fail_result("vkEnumeratePhysicalDevices", result);
			goto out;
		}
		if (observed_count != physical_count) {
			fputs("FAIL physical-device inventory changed\n", stderr);
			goto out;
		}
	}

	for (uint32_t index = 0; index < physical_count; index++) {
		VkPhysicalDeviceProperties properties;
		uint32_t queue_count = 0;
		uint32_t queue_family = UINT32_MAX;

		vkGetPhysicalDeviceProperties(physical_devices[index],
					      &properties);
		if (!is_a660_name(properties.deviceName))
			continue;

		vkGetPhysicalDeviceQueueFamilyProperties(physical_devices[index],
							 &queue_count, NULL);
		if (queue_count == 0 || queue_count > MAX_QUEUE_FAMILIES) {
			fputs("FAIL A660 queue inventory is outside policy\n",
			      stderr);
			goto out;
		}
		{
			uint32_t observed_count = queue_count;

			vkGetPhysicalDeviceQueueFamilyProperties(
				physical_devices[index], &observed_count,
				queue_properties);
			if (observed_count != queue_count) {
				fputs("FAIL A660 queue inventory changed\n",
				      stderr);
				goto out;
			}
		}
		for (uint32_t queue_index = 0; queue_index < queue_count;
		     queue_index++) {
			VkQueueFlags useful = VK_QUEUE_GRAPHICS_BIT |
					      VK_QUEUE_COMPUTE_BIT;

			if (queue_properties[queue_index].queueCount > 0 &&
			    (queue_properties[queue_index].queueFlags & useful)) {
				queue_family = queue_index;
				break;
			}
		}
		if (queue_family == UINT32_MAX) {
			fputs("FAIL A660 has no graphics or compute queue\n",
			      stderr);
			goto out;
		}
		matching_devices++;
		selected_physical = physical_devices[index];
		selected_properties = properties;
		selected_queue = queue_family;
	}
	if (matching_devices != 1) {
		fprintf(stderr,
			"FAIL expected exactly one A660 physical device count=%u\n",
			matching_devices);
		goto out;
	}

	{
		const float priority = 1.0f;
		const VkDeviceQueueCreateInfo queue_info = {
			.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
			.queueFamilyIndex = selected_queue,
			.queueCount = 1,
			.pQueuePriorities = &priority,
		};
		const VkDeviceCreateInfo device_info = {
			.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
			.queueCreateInfoCount = 1,
			.pQueueCreateInfos = &queue_info,
		};

		result = vkCreateDevice(selected_physical, &device_info, NULL,
					&device);
		if (result != VK_SUCCESS) {
			status = fail_result("vkCreateDevice", result);
			goto out;
		}
	}

	vkGetDeviceQueue(device, selected_queue, 0, &queue);
	if (queue == VK_NULL_HANDLE) {
		fputs("FAIL vkGetDeviceQueue returned no queue\n", stderr);
		goto out;
	}

	{
		const VkCommandPoolCreateInfo pool_info = {
			.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
			.flags = VK_COMMAND_POOL_CREATE_TRANSIENT_BIT,
			.queueFamilyIndex = selected_queue,
		};

		result = vkCreateCommandPool(device, &pool_info, NULL,
					     &command_pool);
		if (result != VK_SUCCESS) {
			status = fail_result("vkCreateCommandPool", result);
			goto out;
		}
	}

	{
		const VkCommandBufferAllocateInfo allocation_info = {
			.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
			.commandPool = command_pool,
			.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY,
			.commandBufferCount = 1,
		};

		result = vkAllocateCommandBuffers(device, &allocation_info,
						  &command_buffer);
		if (result != VK_SUCCESS) {
			status = fail_result("vkAllocateCommandBuffers", result);
			goto out;
		}
	}

	{
		const VkCommandBufferBeginInfo begin_info = {
			.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
			.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT,
		};

		result = vkBeginCommandBuffer(command_buffer, &begin_info);
		if (result != VK_SUCCESS) {
			status = fail_result("vkBeginCommandBuffer", result);
			goto out;
		}
		result = vkEndCommandBuffer(command_buffer);
		if (result != VK_SUCCESS) {
			status = fail_result("vkEndCommandBuffer", result);
			goto out;
		}
	}

	{
		const VkFenceCreateInfo fence_info = {
			.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO,
		};

		result = vkCreateFence(device, &fence_info, NULL, &fence);
		if (result != VK_SUCCESS) {
			status = fail_result("vkCreateFence", result);
			goto out;
		}
	}

	{
		const VkSubmitInfo submit_info = {
			.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO,
			.commandBufferCount = 1,
			.pCommandBuffers = &command_buffer,
		};

		result = vkQueueSubmit(queue, 1, &submit_info, fence);
		/*
		 * VK_ERROR_DEVICE_LOST is equivalent to successful submission
		 * when deciding whether work is pending. Let process teardown
		 * reclaim objects after every submit error.
		 */
		if (result != VK_SUCCESS)
			return fail_result("vkQueueSubmit", result);
	}
	result = vkWaitForFences(device, 1, &fence, VK_TRUE,
				 FENCE_TIMEOUT_NS);
	/*
	 * A failed wait does not prove the submitted work is no longer in flight.
	 * Let process teardown reclaim Vulkan objects instead of destroying them.
	 */
	if (result != VK_SUCCESS)
		return fail_result("vkWaitForFences", result);

	fputs("format=rog5-vulkan-submit-v1\n", stdout);
	fputs("device_name=", stdout);
	print_safe_name(selected_properties.deviceName);
	putchar('\n');
	printf("api_version=%u.%u.%u\n",
	       VK_API_VERSION_MAJOR(selected_properties.apiVersion),
	       VK_API_VERSION_MINOR(selected_properties.apiVersion),
	       VK_API_VERSION_PATCH(selected_properties.apiVersion));
	printf("queue_family=%u\n", selected_queue);
	fputs("submit=pass\n", stdout);
	status = 0;

out:
	if (fence != VK_NULL_HANDLE)
		vkDestroyFence(device, fence, NULL);
	if (command_pool != VK_NULL_HANDLE)
		vkDestroyCommandPool(device, command_pool, NULL);
	if (device != VK_NULL_HANDLE)
		vkDestroyDevice(device, NULL);
	if (instance != VK_NULL_HANDLE)
		vkDestroyInstance(instance, NULL);
	return status;
}

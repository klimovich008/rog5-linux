/*
 * Copyright (C) 2013, NVIDIA Corporation.  All rights reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sub license,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice (including the
 * next paragraph) shall be included in all copies or substantial portions
 * of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 * DEALINGS IN THE SOFTWARE.
 */
// SPDX-License-Identifier: MIT
/* Exact Linux v7.1.4 (7a5cef0db479) lifecycle functions; extracted, not modeled. */

void drm_panel_prepare(struct drm_panel *panel)
{
	struct drm_panel_follower *follower;
	int ret;

	if (!panel)
		return;

	if (panel->prepared) {
		dev_warn(panel->dev, "Skipping prepare of already prepared panel\n");
		return;
	}

	mutex_lock(&panel->follower_lock);

	if (panel->funcs && panel->funcs->prepare) {
		ret = panel->funcs->prepare(panel);
		if (ret < 0)
			goto exit;
	}
	panel->prepared = true;

	list_for_each_entry(follower, &panel->followers, list) {
		if (!follower->funcs->panel_prepared)
			continue;

		ret = follower->funcs->panel_prepared(follower);
		if (ret < 0)
			dev_info(panel->dev, "%ps failed: %d\n",
				 follower->funcs->panel_prepared, ret);
	}

exit:
	mutex_unlock(&panel->follower_lock);
}

void drm_panel_unprepare(struct drm_panel *panel)
{
	struct drm_panel_follower *follower;
	int ret;

	if (!panel)
		return;

	/*
	 * If you are seeing the warning below it likely means one of two things:
	 * - Your panel driver incorrectly calls drm_panel_unprepare() in its
	 *   shutdown routine. You should delete this.
	 * - You are using panel-edp or panel-simple and your DRM modeset
	 *   driver's shutdown() callback happened after the panel's shutdown().
	 *   In this case the warning is harmless though ideally you should
	 *   figure out how to reverse the order of the shutdown() callbacks.
	 */
	if (!panel->prepared) {
		dev_warn(panel->dev, "Skipping unprepare of already unprepared panel\n");
		return;
	}

	mutex_lock(&panel->follower_lock);

	list_for_each_entry(follower, &panel->followers, list) {
		if (!follower->funcs->panel_unpreparing)
			continue;

		ret = follower->funcs->panel_unpreparing(follower);
		if (ret < 0)
			dev_info(panel->dev, "%ps failed: %d\n",
				 follower->funcs->panel_unpreparing, ret);
	}

	if (panel->funcs && panel->funcs->unprepare) {
		ret = panel->funcs->unprepare(panel);
		if (ret < 0)
			goto exit;
	}
	panel->prepared = false;

exit:
	mutex_unlock(&panel->follower_lock);
}

void drm_panel_enable(struct drm_panel *panel)
{
	struct drm_panel_follower *follower;
	int ret;

	if (!panel)
		return;

	if (panel->enabled) {
		dev_warn(panel->dev, "Skipping enable of already enabled panel\n");
		return;
	}

	mutex_lock(&panel->follower_lock);

	if (panel->funcs && panel->funcs->enable) {
		ret = panel->funcs->enable(panel);
		if (ret < 0)
			goto exit;
	}
	panel->enabled = true;

	ret = backlight_enable(panel->backlight);
	if (ret < 0)
		DRM_DEV_INFO(panel->dev, "failed to enable backlight: %d\n",
			     ret);

	list_for_each_entry(follower, &panel->followers, list) {
		if (!follower->funcs->panel_enabled)
			continue;

		ret = follower->funcs->panel_enabled(follower);
		if (ret < 0)
			dev_info(panel->dev, "%ps failed: %d\n",
				 follower->funcs->panel_enabled, ret);
	}

exit:
	mutex_unlock(&panel->follower_lock);
}

void drm_panel_disable(struct drm_panel *panel)
{
	struct drm_panel_follower *follower;
	int ret;

	if (!panel)
		return;

	/*
	 * If you are seeing the warning below it likely means one of two things:
	 * - Your panel driver incorrectly calls drm_panel_disable() in its
	 *   shutdown routine. You should delete this.
	 * - You are using panel-edp or panel-simple and your DRM modeset
	 *   driver's shutdown() callback happened after the panel's shutdown().
	 *   In this case the warning is harmless though ideally you should
	 *   figure out how to reverse the order of the shutdown() callbacks.
	 */
	if (!panel->enabled) {
		dev_warn(panel->dev, "Skipping disable of already disabled panel\n");
		return;
	}

	mutex_lock(&panel->follower_lock);

	list_for_each_entry(follower, &panel->followers, list) {
		if (!follower->funcs->panel_disabling)
			continue;

		ret = follower->funcs->panel_disabling(follower);
		if (ret < 0)
			dev_info(panel->dev, "%ps failed: %d\n",
				 follower->funcs->panel_disabling, ret);
	}

	ret = backlight_disable(panel->backlight);
	if (ret < 0)
		DRM_DEV_INFO(panel->dev, "failed to disable backlight: %d\n",
			     ret);

	if (panel->funcs && panel->funcs->disable) {
		ret = panel->funcs->disable(panel);
		if (ret < 0)
			goto exit;
	}
	panel->enabled = false;

exit:
	mutex_unlock(&panel->follower_lock);
}

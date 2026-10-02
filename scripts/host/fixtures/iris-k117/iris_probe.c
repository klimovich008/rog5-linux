// SPDX-License-Identifier: GPL-2.0-only
/*
 * Copyright (c) 2022-2024 Qualcomm Innovation Center, Inc. All rights reserved.
 */

#include <linux/clk.h>
#include <linux/interconnect.h>
#include <linux/module.h>
#include <linux/pm_domain.h>
#include <linux/pm_opp.h>
#include <linux/pm_runtime.h>
#include <linux/reset.h>
#include <linux/soc/qcom/ubwc.h>

#include "iris_core.h"
#include "iris_instance.h"

/*
 * ROG5: SM8350 (OEM firmware) restrictions, lifted only at module load:
 * the encoder hung the SoC at session start in the k115 trial, and VP9 failed
 * with a session error before HFI_PROPERTY_PARAM_SECURE_SESSION was sent.
 */
static bool experimental_encoder;
module_param(experimental_encoder, bool, 0444);
MODULE_PARM_DESC(experimental_encoder, "SM8350: register the encoder node (can hang the SoC)");

static bool experimental_vp9;
module_param(experimental_vp9, bool, 0444);
MODULE_PARM_DESC(experimental_vp9, "SM8350: advertise VP9 decoding");
#include "iris_ctrls.h"
#include "iris_vidc.h"

static int iris_init_icc(struct iris_core *core)
{
	const struct icc_info *icc_tbl;
	u32 i = 0;

	icc_tbl = core->iris_platform_data->icc_tbl;

	core->icc_count = core->iris_platform_data->icc_tbl_size;
	core->icc_tbl = devm_kzalloc(core->dev,
				     sizeof(struct icc_bulk_data) * core->icc_count,
				     GFP_KERNEL);
	if (!core->icc_tbl)
		return -ENOMEM;

	for (i = 0; i < core->icc_count; i++) {
		core->icc_tbl[i].name = icc_tbl[i].name;
		core->icc_tbl[i].avg_bw = icc_tbl[i].bw_min_kbps;
		core->icc_tbl[i].peak_bw = 0;
	}

	return devm_of_icc_bulk_get(core->dev, core->icc_count, core->icc_tbl);
}

static int iris_init_power_domains(struct iris_core *core)
{
	int ret;

	struct dev_pm_domain_attach_data iris_pd_data = {
		.pd_names = core->iris_platform_data->pmdomain_tbl,
		.num_pd_names = core->iris_platform_data->pmdomain_tbl_size,
		.pd_flags = PD_FLAG_NO_DEV_LINK,
	};

	struct dev_pm_domain_attach_data iris_opp_pd_data = {
		.pd_names = core->iris_platform_data->opp_pd_tbl,
		.num_pd_names = core->iris_platform_data->opp_pd_tbl_size,
		.pd_flags = PD_FLAG_DEV_LINK_ON | PD_FLAG_REQUIRED_OPP,
	};

	struct dev_pm_opp_config iris_opp_clk_data = {
		.clk_names = core->iris_platform_data->opp_clk_tbl,
		.config_clks = dev_pm_opp_config_clks_simple,
	};

	ret = devm_pm_domain_attach_list(core->dev, &iris_pd_data, &core->pmdomain_tbl);
	if (ret < 0)
		return ret;

	ret =  devm_pm_domain_attach_list(core->dev, &iris_opp_pd_data, &core->opp_pmdomain_tbl);
	/* backwards compatibility for incomplete ABI SM8250 */
	if (ret == -ENODEV &&
	    of_device_is_compatible(core->dev->of_node, "qcom,sm8250-venus")) {
		iris_opp_pd_data.num_pd_names--;
		ret = devm_pm_domain_attach_list(core->dev, &iris_opp_pd_data,
						 &core->opp_pmdomain_tbl);
	}
	if (ret < 0)
		return ret;

	ret = devm_pm_opp_set_config(core->dev, &iris_opp_clk_data);
	if (ret)
		return ret;

	return devm_pm_opp_of_add_table(core->dev);
}

static int iris_init_clocks(struct iris_core *core)
{
	int ret;

	ret = devm_clk_bulk_get_all(core->dev, &core->clock_tbl);
	if (ret < 0)
		return ret;

	core->clk_count = ret;

	return 0;
}

static int iris_init_reset_table(struct iris_core *core,
				 struct reset_control_bulk_data **resets,
				 const char * const *rst_tbl, u32 rst_tbl_size)
{
	u32 i = 0;

	*resets = devm_kzalloc(core->dev,
			       sizeof(struct reset_control_bulk_data) * rst_tbl_size,
			       GFP_KERNEL);
	if (!*resets)
		return -ENOMEM;

	for (i = 0; i < rst_tbl_size; i++)
		(*resets)[i].id = rst_tbl[i];

	return devm_reset_control_bulk_get_exclusive(core->dev, rst_tbl_size, *resets);
}

static int iris_init_resets(struct iris_core *core)
{
	int ret;

	ret = iris_init_reset_table(core, &core->resets,
				    core->iris_platform_data->clk_rst_tbl,
				    core->iris_platform_data->clk_rst_tbl_size);
	if (ret)
		return ret;

	if (!core->iris_platform_data->controller_rst_tbl_size)
		return 0;

	return iris_init_reset_table(core, &core->controller_resets,
				     core->iris_platform_data->controller_rst_tbl,
				     core->iris_platform_data->controller_rst_tbl_size);
}

static int iris_init_resources(struct iris_core *core)
{
	int ret;

	ret = iris_init_icc(core);
	if (ret)
		return ret;

	ret = iris_init_power_domains(core);
	if (ret)
		return ret;

	ret = iris_init_clocks(core);
	if (ret)
		return ret;

	return iris_init_resets(core);
}

static int iris_register_video_device(struct iris_core *core, enum domain_type type)
{
	struct video_device *vdev;
	int ret;

	vdev = video_device_alloc();
	if (!vdev)
		return -ENOMEM;

	vdev->release = video_device_release;
	vdev->fops = core->iris_v4l2_file_ops;
	vdev->vfl_dir = VFL_DIR_M2M;
	vdev->v4l2_dev = &core->v4l2_dev;
	vdev->device_caps = V4L2_CAP_VIDEO_M2M_MPLANE | V4L2_CAP_STREAMING;

	if (type == DECODER) {
		strscpy(vdev->name, "qcom-iris-decoder", sizeof(vdev->name));
		vdev->ioctl_ops = core->iris_v4l2_ioctl_ops_dec;
		core->vdev_dec = vdev;
	} else if (type == ENCODER) {
		strscpy(vdev->name, "qcom-iris-encoder", sizeof(vdev->name));
		vdev->ioctl_ops = core->iris_v4l2_ioctl_ops_enc;
		core->vdev_enc = vdev;
	} else {
		ret = -EINVAL;
		goto err_vdev_release;
	}

	/*
	 * ROG5: the node can be opened (udev's v4l_id does at once) as soon
	 * as it is registered, and iris_open() uses the driver data.
	 */
	video_set_drvdata(vdev, core);
	ret = video_register_device(vdev, VFL_TYPE_VIDEO, -1);
	if (ret)
		goto err_vdev_release;

	return 0;

err_vdev_release:
	video_device_release(vdev);

	return ret;
}

static void iris_remove(struct platform_device *pdev)
{
	struct iris_core *core;

	core = platform_get_drvdata(pdev);
	if (!core)
		return;
	iris_mark(core, "remove");

	/* ROG5: no containment work may start or run after this */
	mutex_lock(&core->lock);
	core->removing = true;
	mutex_unlock(&core->lock);
	cancel_delayed_work_sync(&core->sys_error_handler);
	iris_core_deinit(core);
	/*
	 * ROG5: a core whose firmware could not be shut down keeps its line
	 * enabled; no handler may run once the lock below is destroyed.
	 */
	disable_irq(core->irq);

	video_unregister_device(core->vdev_dec);
	video_unregister_device(core->vdev_enc);

	v4l2_device_unregister(&core->v4l2_dev);

	mutex_destroy(&core->lock);
}

static void iris_sys_error_handler(struct work_struct *work)
{
	struct iris_core *core =
			container_of(work, struct iris_core, sys_error_handler.work);

	/* ROG5: contain instead of reloading (see iris_core_fatal()) */
	iris_core_contain_fatal(core);
}

static int iris_probe(struct platform_device *pdev)
{
	struct device *dev = &pdev->dev;
	struct iris_core *core;
	u64 dma_mask;
	int ret;

	core = devm_kzalloc(&pdev->dev, sizeof(*core), GFP_KERNEL);
	if (!core)
		return -ENOMEM;
	core->dev = dev;

	core->state = IRIS_CORE_DEINIT;
	mutex_init(&core->lock);
	init_completion(&core->core_init_done);

	core->response_packet = devm_kzalloc(core->dev, IFACEQ_CORE_PKT_SIZE, GFP_KERNEL);
	if (!core->response_packet)
		return -ENOMEM;

	INIT_LIST_HEAD(&core->instances);
	INIT_DELAYED_WORK(&core->sys_error_handler, iris_sys_error_handler);

	core->reg_base = devm_platform_ioremap_resource(pdev, 0);
	if (IS_ERR(core->reg_base))
		return PTR_ERR(core->reg_base);

	core->irq = platform_get_irq(pdev, 0);
	if (core->irq < 0)
		return core->irq;

	core->iris_platform_data = of_device_get_match_data(core->dev);
	core->iris_firmware_desc = core->iris_platform_data->firmware_desc;
	core->iris_firmware_data = core->iris_firmware_desc->firmware_data;

	/* ROG5: encoder and VP9 gated on SM8350 (see the parameters above) */
	core->enc_enabled = true;
	core->dec_fmts_size = core->iris_platform_data->inst_iris_fmts_size;
	if (core->iris_platform_data->oem) {
		const struct iris_oem_quirks *oem = core->iris_platform_data->oem;

		if (oem->encoder_experimental && !experimental_encoder)
			core->enc_enabled = false;
		if (oem->vp9_experimental && !experimental_vp9 &&
		    core->dec_fmts_size > IRIS_FMT_VP9)
			core->dec_fmts_size = IRIS_FMT_VP9;
		dev_info(dev, "SM8350 OEM firmware mode: encoder %s, VP9 %s\n",
			 core->enc_enabled ? "EXPERIMENTAL" : "off",
			 core->dec_fmts_size > IRIS_FMT_VP9 ? "EXPERIMENTAL" : "off");
	}

	core->ubwc_cfg = qcom_ubwc_config_get_data();
	if (IS_ERR(core->ubwc_cfg))
		return PTR_ERR(core->ubwc_cfg);

	ret = devm_request_threaded_irq(core->dev, core->irq, iris_hfi_isr,
					iris_hfi_isr_handler,
					IRQF_TRIGGER_HIGH | IRQF_NO_AUTOEN,
					"iris", core);
	if (ret)
		return ret;

	iris_init_ops(core);

	ret = iris_init_resources(core);
	if (ret)
		return ret;

	iris_session_init_caps(core);

	/*
	 * ROG5: everything an opener or a PM callback needs (driver data, DMA
	 * mask, runtime PM) is set up before the nodes are published.
	 */
	platform_set_drvdata(pdev, core);

	dma_mask = core->iris_platform_data->dma_mask;

	ret = dma_set_mask_and_coherent(dev, dma_mask);
	if (ret)
		return ret;

	dma_set_max_seg_size(&pdev->dev, DMA_BIT_MASK(32));
	dma_set_seg_boundary(&pdev->dev, DMA_BIT_MASK(32));

	pm_runtime_set_autosuspend_delay(core->dev, AUTOSUSPEND_DELAY_VALUE);
	pm_runtime_use_autosuspend(core->dev);
	ret = devm_pm_runtime_enable(core->dev);
	if (ret)
		return ret;

	ret = v4l2_device_register(dev, &core->v4l2_dev);
	if (ret)
		return ret;

	ret = iris_register_video_device(core, DECODER);
	if (ret)
		goto err_v4l2_unreg;

	if (core->enc_enabled) {
		ret = iris_register_video_device(core, ENCODER);
		if (ret)
			goto err_vdev_unreg_dec;
	}

	iris_mark(core, "probe done");

	return 0;

err_vdev_unreg_dec:
	video_unregister_device(core->vdev_dec);
err_v4l2_unreg:
	v4l2_device_unregister(&core->v4l2_dev);

	return ret;
}

/*
 * ROG5: the PM callbacks never wait for the interrupt thread: that thread
 * can wait for inst->lock held by a task that waits for this very runtime PM
 * transition (pm_runtime_resume_and_get() on a command), or call it itself.
 * iris_vpu_power_off() therefore only disables the line without waiting,
 * and the thread touches VPU registers only while core->powered (checked
 * under core->lock, which power off holds). After a fatal error the hardware
 * is left to iris_core_contain_fatal().
 */
static int __maybe_unused iris_pm_suspend(struct device *dev)
{
	struct iris_core *core;
	int ret = 0;

	core = dev_get_drvdata(dev);

	mutex_lock(&core->lock);
	/* ROG5: resources held after a fault stay on, suppliers included */
	if (core->fw_held) {
		dev_warn_ratelimited(dev, "video core held after a fault: not suspending\n");
		ret = -EBUSY;
		goto exit;
	}
	/*
	 * Fatal error latched but not contained yet (the containment work
	 * shuts the firmware down): the hardware is still on, so is the
	 * device, until that work has run.
	 */
	if (core->powered && (core->fatal || core->state != IRIS_CORE_INIT)) {
		ret = -EBUSY;
		goto exit;
	}
	if (core->state != IRIS_CORE_INIT || core->fatal)
		goto exit;

	iris_mark(core, "runtime suspend");
	ret = iris_hfi_pm_suspend(core);
	iris_mark(core, "runtime suspend done: %d", ret);

exit:
	mutex_unlock(&core->lock);

	return ret;
}

static int __maybe_unused iris_pm_resume(struct device *dev)
{
	struct iris_core *core;
	int ret = 0;

	core = dev_get_drvdata(dev);

	mutex_lock(&core->lock);
	if (core->state != IRIS_CORE_INIT || core->fatal)
		goto exit;

	iris_mark(core, "runtime resume");
	ret = iris_hfi_pm_resume(core);
	iris_mark(core, "runtime resume done: %d", ret);
	pm_runtime_mark_last_busy(core->dev);

exit:
	mutex_unlock(&core->lock);

	return ret;
}

/*
 * ROG5: `echo 1 > firmware_unload` shuts an idle video core down (firmware
 * PAS shutdown, power off), which releases the module pin taken while the
 * firmware runs; `modprobe -r qcom_iris` is refused until then.
 */
static ssize_t firmware_unload_store(struct device *dev, struct device_attribute *attr,
				     const char *buf, size_t count)
{
	struct iris_core *core = dev_get_drvdata(dev);
	bool val;
	int ret;

	ret = kstrtobool(buf, &val);
	if (ret)
		return ret;
	if (!val)
		return count;

	ret = iris_core_unload_idle(core);

	return ret ? ret : count;
}
static DEVICE_ATTR_WO(firmware_unload);

static struct attribute *iris_attrs[] = {
	&dev_attr_firmware_unload.attr,
	NULL
};
ATTRIBUTE_GROUPS(iris);

static const struct dev_pm_ops iris_pm_ops = {
	SET_SYSTEM_SLEEP_PM_OPS(pm_runtime_force_suspend,
				pm_runtime_force_resume)
	SET_RUNTIME_PM_OPS(iris_pm_suspend, iris_pm_resume, NULL)
};

static const struct of_device_id iris_dt_match[] = {
	{
		.compatible = "qcom,qcs8300-iris",
		.data = &qcs8300_data,
	},
	{
		.compatible = "qcom,sc7280-venus",
		.data = &sc7280_data,
	},
	{
		/* ROG5: before the sm8250-venus fallback it is listed with */
		.compatible = "qcom,sm8350-iris",
		.data = &sm8350_data,
	},
	{
		.compatible = "qcom,sm8250-venus",
		.data = &sm8250_data,
	},
	{
		.compatible = "qcom,sm8550-iris",
		.data = &sm8550_data,
	},
	{
		.compatible = "qcom,sm8650-iris",
		.data = &sm8650_data,
	},
	{
		.compatible = "qcom,sm8750-iris",
		.data = &sm8750_data,
	},
	{
		.compatible = "qcom,x1p42100-iris",
		.data = &x1p42100_data,
	},
	{ },
};
MODULE_DEVICE_TABLE(of, iris_dt_match);

static struct platform_driver qcom_iris_driver = {
	.probe = iris_probe,
	.remove = iris_remove,
	.driver = {
		.name = "qcom-iris",
		.of_match_table = iris_dt_match,
		.pm = &iris_pm_ops,
		/* ROG5: no unbind under a held core (iris_core_mark_held()) */
		.suppress_bind_attrs = true,
		.dev_groups = iris_groups,
	},
};

module_platform_driver(qcom_iris_driver);
MODULE_DESCRIPTION("Qualcomm iris video driver");
MODULE_LICENSE("GPL");

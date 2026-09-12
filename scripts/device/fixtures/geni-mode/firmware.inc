// SPDX-License-Identifier: GPL-2.0
/*
 *  Copyright (c) 2017-2018, The Linux Foundation. All rights reserved.
 *  Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
 */

/* Exact Linux7.1.4 drivers/soc/qcom/qcom-geni-se.c; no hardware implementation in harness. */
/* BEGIN EXACT EXTRACT */
int geni_load_se_firmware(struct geni_se *se, enum geni_se_protocol_type protocol)
{
	const char *fw_name;
	const struct firmware *fw;
	enum geni_se_xfer_mode mode = GENI_SE_FIFO;
	int ret;

	if (protocol >= ARRAY_SIZE(protocol_name)) {
		dev_err(se->dev, "Invalid geni-se protocol: %d", protocol);
		return -EINVAL;
	}

	ret = device_property_read_string(se->wrapper->dev, "firmware-name", &fw_name);
	if (ret) {
		dev_err(se->dev, "Failed to read firmware-name property: %d\n", ret);
		return -EINVAL;
	}

	if (of_property_read_bool(se->dev->of_node, "qcom,enable-gsi-dma"))
		mode = GENI_GPI_DMA;

	/* GSI mode is not supported by the UART driver; therefore, setting FIFO mode */
	if (protocol == GENI_SE_UART)
		mode = GENI_SE_FIFO;

	ret = request_firmware(&fw, fw_name, se->dev);
	if (ret) {
		if (ret == -ENOENT)
			return -EPROBE_DEFER;

		dev_err(se->dev, "Failed to request firmware '%s' for protocol %d: ret: %d\n",
			fw_name, protocol, ret);
		return ret;
	}

	ret = geni_load_se_fw(se, fw, mode, protocol);
	release_firmware(fw);

	if (ret) {
		dev_err(se->dev, "Failed to load SE firmware for protocol %d: ret: %d\n",
			protocol, ret);
		return ret;
	}

	dev_dbg(se->dev, "Firmware load for %s protocol is successful for xfer mode: %d\n",
		protocol_name[protocol], mode);
	return 0;
}

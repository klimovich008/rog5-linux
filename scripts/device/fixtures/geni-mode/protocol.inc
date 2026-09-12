// SPDX-License-Identifier: GPL-2.0
// Copyright (c) 2017-2018, The Linux Foundation. All rights reserved.

/* Exact Linux7.1.4 drivers/i2c/busses/i2c-qcom-geni.c; no hardware implementation in harness. */
/* BEGIN EXACT EXTRACT */
	proto = geni_se_read_proto(&gi2c->se);
	if (proto == GENI_SE_INVALID_PROTO) {
		ret = geni_load_se_firmware(&gi2c->se, GENI_SE_I2C);
		if (ret) {
			dev_err_probe(dev, ret, "i2c firmware load failed ret: %d\n", ret);
			goto err_resources;
		}
	} else if (proto != GENI_SE_I2C) {
		ret = dev_err_probe(dev, -ENXIO, "Invalid proto %d\n", proto);
		goto err_resources;
	}

	if (desc && desc->no_dma_support) {
		fifo_disable = false;
		gi2c->no_dma = true;
	} else {
		fifo_disable = readl_relaxed(gi2c->se.base + GENI_IF_DISABLE_RO) & FIFO_IF_DISABLE;
	}

	if (fifo_disable) {
		/* FIFO is disabled, so we can only use GPI DMA */
		gi2c->gpi_mode = true;
		ret = setup_gpi_dma(gi2c);
		if (ret)
			goto err_resources;

		dev_dbg(dev, "Using GPI DMA mode for I2C\n");
	} else {
		gi2c->gpi_mode = false;
		tx_depth = geni_se_get_tx_fifo_depth(&gi2c->se);

		/* I2C Master Hub Serial Elements doesn't have the HW_PARAM_0 register */
		if (!tx_depth && desc)
			tx_depth = desc->tx_fifo_depth;

		if (!tx_depth) {
			ret = dev_err_probe(dev, -EINVAL,
					    "Invalid TX FIFO depth\n");
			goto err_resources;
		}

		gi2c->tx_wm = tx_depth - 1;
		geni_se_init(&gi2c->se, gi2c->tx_wm, tx_depth);
		geni_se_config_packing(&gi2c->se, BITS_PER_BYTE,
				       PACKING_BYTES_PW, true, true, true);

		dev_dbg(dev, "i2c fifo/se-dma mode. fifo depth:%d\n", tx_depth);
	}


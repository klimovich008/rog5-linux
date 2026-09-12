// SPDX-License-Identifier: GPL-2.0
// Copyright (c) 2017-2018, The Linux Foundation. All rights reserved.

/* Exact Linux7.1.4 drivers/i2c/busses/i2c-qcom-geni.c; no hardware implementation in harness. */
/* BEGIN EXACT EXTRACT */
static int setup_gpi_dma(struct geni_i2c_dev *gi2c)
{
	int ret;

	geni_se_select_mode(&gi2c->se, GENI_GPI_DMA);
	gi2c->tx_c = dma_request_chan(gi2c->se.dev, "tx");
	if (IS_ERR(gi2c->tx_c)) {
		ret = dev_err_probe(gi2c->se.dev, PTR_ERR(gi2c->tx_c),
				    "Failed to get tx DMA ch\n");
		goto err_tx;
	}

	gi2c->rx_c = dma_request_chan(gi2c->se.dev, "rx");
	if (IS_ERR(gi2c->rx_c)) {
		ret = dev_err_probe(gi2c->se.dev, PTR_ERR(gi2c->rx_c),
				    "Failed to get rx DMA ch\n");
		goto err_rx;
	}

	dev_dbg(gi2c->se.dev, "Grabbed GPI dma channels\n");
	return 0;

err_rx:
	dma_release_channel(gi2c->tx_c);
err_tx:
	return ret;
}

// SPDX-License-Identifier: GPL-2.0
// Copyright (c) 2017-2018, The Linux Foundation. All rights reserved.

/* Exact Linux7.1.4 drivers/i2c/busses/i2c-qcom-geni.c; no hardware implementation in harness. */
/* BEGIN EXACT EXTRACT */
	dma_buf = gi2c->no_dma ? NULL : i2c_get_dma_safe_msg_buf(msg, 32);
	if (dma_buf)
		geni_se_select_mode(se, GENI_SE_DMA);
	else
		geni_se_select_mode(se, GENI_SE_FIFO);


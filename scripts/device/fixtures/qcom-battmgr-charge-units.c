// SPDX-License-Identifier: GPL-2.0-only
/* Original driver:
 * Copyright (c) 2019-2020, The Linux Foundation. All rights reserved.
 * Copyright (c) 2022, Linaro Ltd
 * Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
 */
/* Extracts of Linux 7.1.4 qcom_battmgr.c, with host-only test scaffolding.
 * The marked fragments are checked against retained source by the runner.
 * Tests unit selection/readout, not GLINK transport or physical regulation.
 */
#include <errno.h>
#include <stdio.h>

/* source: variants */
enum qcom_battmgr_variant {
	QCOM_BATTMGR_SC8280XP,
	QCOM_BATTMGR_SM8350,
	QCOM_BATTMGR_SM8550,
	QCOM_BATTMGR_X1E80100,
};
/* end: variants */
/* source: units */
enum qcom_battmgr_unit {
	QCOM_BATTMGR_UNIT_mWh = 0,
	QCOM_BATTMGR_UNIT_mAh = 1
};
/* end: units */

struct qcom_battmgr {
	enum qcom_battmgr_variant variant;
	enum qcom_battmgr_unit unit;
	struct { int design_capacity, last_full_capacity; } info;
};
enum {
	POWER_SUPPLY_PROP_CHARGE_FULL_DESIGN,
	POWER_SUPPLY_PROP_CHARGE_FULL,
	POWER_SUPPLY_PROP_ENERGY_FULL_DESIGN,
	POWER_SUPPLY_PROP_ENERGY_FULL,
};
struct value { int intval; };

static void probe(struct qcom_battmgr *battmgr)
{
	const int sm8350_bat_psy_desc = 1, sm8550_bat_psy_desc = 2;
	const int *psy_desc = NULL;
/* source: protocol-selection */
	if (battmgr->variant == QCOM_BATTMGR_SC8280XP ||
	    battmgr->variant == QCOM_BATTMGR_X1E80100) {
/* end: protocol-selection */
		/* Laptop unit comes from BATTMGR_BAT_INFO, represented by input. */
/* source: phone-probe */
	} else {
		if (battmgr->variant == QCOM_BATTMGR_SM8550)
			psy_desc = &sm8550_bat_psy_desc;
		else
			psy_desc = &sm8350_bat_psy_desc;

/* end: phone-probe */
	}
	(void)psy_desc;
}

static int read_capacity(struct qcom_battmgr *battmgr, int prop,
			 struct value *val)
{
	enum qcom_battmgr_unit unit = battmgr->unit;
	switch (prop) {
/* source: charge-readout */
	case POWER_SUPPLY_PROP_CHARGE_FULL_DESIGN:
		if (unit != QCOM_BATTMGR_UNIT_mAh)
			return -ENODATA;
		val->intval = battmgr->info.design_capacity;
		break;
	case POWER_SUPPLY_PROP_CHARGE_FULL:
		if (unit != QCOM_BATTMGR_UNIT_mAh)
			return -ENODATA;
		val->intval = battmgr->info.last_full_capacity;
		break;
/* end: charge-readout */
/* source: energy-readout */
	case POWER_SUPPLY_PROP_ENERGY_FULL_DESIGN:
		if (unit != QCOM_BATTMGR_UNIT_mWh)
			return -ENODATA;
		val->intval = battmgr->info.design_capacity;
		break;
	case POWER_SUPPLY_PROP_ENERGY_FULL:
		if (unit != QCOM_BATTMGR_UNIT_mWh)
			return -ENODATA;
		val->intval = battmgr->info.last_full_capacity;
		break;
/* end: energy-readout */
	default:
		return -EINVAL;
	}
	return 0;
}

int main(void)
{
	int failures = 0;
	for (int variant = 0; variant < 4; variant++) {
		for (int initial_unit = 0; initial_unit < 2; initial_unit++) {
			struct qcom_battmgr b = { .variant = variant,
				.unit = initial_unit, .info = { 6000000, 5800000 } };
			int expected_unit = (variant == QCOM_BATTMGR_SM8350 ||
				variant == QCOM_BATTMGR_SM8550) ? 1 : initial_unit;
			probe(&b);
			for (int prop = 0; prop < 4; prop++) {
				struct value val = { .intval = -1 };
				int rc = read_capacity(&b, prop, &val);
				int available = (prop < 2) == expected_unit;
				int expected_value = prop % 2 ? 5800000 : 6000000;
				if ((int)b.unit != expected_unit ||
				    rc != (available ? 0 : -ENODATA) ||
				    val.intval != (available ? expected_value : -1)) {
					fprintf(stderr, "variant=%d initial=%d prop=%d unit=%d rc=%d value=%d\n",
						variant, initial_unit, prop, b.unit, rc, val.intval);
					failures++;
				}
			}
		}
	}
	return failures ? 1 : 0;
}

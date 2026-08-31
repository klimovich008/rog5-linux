// SPDX-License-Identifier: GPL-2.0-only
/* Exact-board S12 re-vote diagnostic. No radio or disable path. */
#include <dt-bindings/regulator/qcom,rpmh-regulator.h>
#include <linux/bits.h>
#include <linux/delay.h>
#include <linux/device.h>
#include <linux/err.h>
#include <linux/errno.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_platform.h>
#include <linux/platform_device.h>
#include <linux/regulator/consumer.h>
#include <linux/string.h>
#include <soc/qcom/cmd-db.h>
#include <soc/qcom/rpmh.h>

#define S12_REVOTE_UV 1224000
#define S12_OEM_MV 1350
#define S12_MAX_UV 1360000
#define CONSUMER_NODE "/rog5-s12-revote"

static char *action = "query";
module_param(action, charp, 0400);
MODULE_PARM_DESC(action, "query, mode, held-enable, held-oem; no radio");
enum vote_action { QUERY, MODE, HELD_ENABLE, HELD_OEM };
static enum vote_action selected_action;
static struct regulator *s12;
static struct platform_device *consumer;
static struct platform_device *pmic_device;
static bool holding;

static int voltage_bounds_allowed(u32 minimum, u32 maximum)
{
	return minimum == S12_REVOTE_UV && maximum == S12_MAX_UV;
}

static int raw_state_matches(u32 voltage, u32 enabled, u32 mode,
			     unsigned int expected_mv,
			     unsigned int expected_mode)
{
	/* Bit31 is retained in logs, not interpreted as validity or status. */
	if ((expected_mv != S12_REVOTE_UV / 1000 && expected_mv != S12_OEM_MV) ||
	    (expected_mode != 3 && expected_mode != 6))
		return 0;
	if ((voltage & ~(BIT(31) | 0x1fffU)) ||
	    (enabled & ~(BIT(31) | 1U)) || (mode & ~(BIT(31) | 7U)))
		return 0;
	return (voltage & 0x1fffU) == expected_mv &&
		(enabled & 1U) == 1 && (mode & 7U) == expected_mode;
}

static int read_and_check(const char *phase, unsigned int expected_mv,
			  unsigned int expected_mode)
{
	u32 values[3];
	unsigned int i, attempt;
	int ret;

	for (i = 0; i < ARRAY_SIZE(values); i++) {
		struct tcs_cmd cmd = { .addr = 0x40100 + 4 * i };

		for (attempt = 0; attempt < 5; attempt++) {
			ret = rpmh_read(&pmic_device->dev, &cmd);
			/* Only EAGAIN proves that no request was queued. */
			if (ret != -EAGAIN)
				break;
			if (attempt < 4)
				msleep(20);
		}
		if (ret) {
			pr_err("ROG5_S12_RAW phase=%s address=%#x result=%d "
			       "raw=unavailable\n", phase, cmd.addr, ret);
			return ret;
		}
		values[i] = cmd.data;
		pr_info("ROG5_S12_RAW phase=%s address=%#x result=0 raw=%#x\n",
			phase, cmd.addr, cmd.data);
	}
	ret = raw_state_matches(values[0], values[1], values[2],
				expected_mv, expected_mode) ?
		0 : -ERANGE;
	pr_info("ROG5_S12_CHECK phase=%s result=%d expected_mode=%u\n",
		phase, ret, expected_mode);
	return ret;
}

static int request_oem_voltage(void)
{
	int ret;

	if (!holding)
		return -EPERM;
	ret = read_and_check("before-oem", S12_REVOTE_UV / 1000, 6);
	if (ret)
		return ret;
	/* The ASIC-scoped kernel point must represent the OEM request exactly.
	 * Use the regulator API so its cache and consumer constraint agree.
	 */
	pr_info("ROG5_S12_OEM enter request_mv=%u\n", S12_OEM_MV);
	ret = regulator_set_voltage(s12, S12_OEM_MV * 1000, S12_OEM_MV * 1000);
	pr_info("ROG5_S12_OEM return result=%d\n", ret);
	if (ret)
		return ret;
	ret = read_and_check("after-oem", S12_OEM_MV, 6);
	if (ret)
		return ret;
	if (regulator_get_voltage(s12) != S12_OEM_MV * 1000)
		return -EIO;
	pr_info("ROG5_S12_OEM cache_consistent=1\n");
	return 0;
}

static int finish_init_result(int ret)
{
	/* Module-init failure must never discard an already established hold. */
	if (holding) {
		if (ret)
			pr_err("ROG5_S12_VOTE held-postcheck-failed=%d; "
			       "hold retained until reboot\n", ret);
		return 0;
	}
	return ret;
}

static int modes_allowed(unsigned int first, unsigned int second)
{
	/* Vendor AUTO=3 is mainline HPM. Never allow NORMAL->FAST coercion. */
	return first == RPMH_REGULATOR_MODE_RET &&
		second == RPMH_REGULATOR_MODE_AUTO;
}

static void report_cached_state(void)
{
	int mode = (int)regulator_get_mode(s12);
	int voltage = regulator_get_voltage(s12);
	int enabled = regulator_is_enabled(s12);

	pr_info("ROG5_S12_VOTE ready held=%u cached_mode=%d mode_state=%s "
		"cached_uv=%d voltage_state=%s cached_enabled=%d enabled_state=%s\n",
		holding, mode, mode < 0 ? "error" : mode ? "present" : "absent",
		voltage, voltage < 0 ? "error" : "present",
		enabled, enabled < 0 ? "error" : "present");
}

static int apply_active_vote(void)
{
	int mode = (int)regulator_get_mode(s12);
	bool hold_action = selected_action == HELD_ENABLE ||
			   selected_action == HELD_OEM;
	int ret;

	pr_info("ROG5_S12_VOTE before cached_mode=%d action=%s\n", mode, action);
	if (regulator_get_voltage(s12) != S12_REVOTE_UV)
		return -ERANGE;
	if (mode != (hold_action ?
		     REGULATOR_MODE_NORMAL : REGULATOR_MODE_STANDBY))
		return -EPERM;
	ret = read_and_check("before", S12_REVOTE_UV / 1000,
			     hold_action ? 6 : 3);
	if (ret)
		return ret;
	if (selected_action == QUERY)
		return 0;
	if (selected_action == MODE) {
		ret = regulator_set_mode(s12, REGULATOR_MODE_NORMAL);
		pr_info("ROG5_S12_VOTE mode-return result=%d\n", ret);
		if (ret)
			return ret;
		if ((int)regulator_get_mode(s12) != REGULATOR_MODE_NORMAL)
			return -EIO;
		return read_and_check("after", S12_REVOTE_UV / 1000, 6);
	}

	/* This is a distinct later action, never an automatic mode retry. */
	pr_info("ROG5_S12_VOTE hold-enter\n");
	ret = regulator_enable(s12);
	pr_info("ROG5_S12_VOTE hold-return result=%d\n", ret);
	if (ret)
		return ret;
	/* Keep our independent enable reference even if Wi-Fi probe unwinds.
	 * No ordinary unload may release this critical shared rail.
	 */
	holding = true;
	__module_get(THIS_MODULE);
	if (selected_action == HELD_OEM)
		return request_oem_voltage();
	return read_and_check("after", S12_REVOTE_UV / 1000, 6);
}

static int __init s12_vote_init(void)
{
	struct device_node *pmu, *rail, *supply, *pcie;
	struct device_node *parent_supply = NULL;
	const char *pmic;
	u32 modes[2], minimum, maximum, initial, drv_id;
	int ret = -ENODEV;

	if (!action)
		return -EINVAL;
	if (!strcmp(action, "query"))
		selected_action = QUERY;
	else if (!strcmp(action, "mode"))
		selected_action = MODE;
	else if (!strcmp(action, "held-enable"))
		selected_action = HELD_ENABLE;
	else if (!strcmp(action, "held-oem"))
		selected_action = HELD_OEM;
	else
		return -EINVAL;
	pr_info("ROG5_S12_VOTE action=%s identity-check\n", action);
	if (!of_machine_is_compatible("asus,rog-phone5"))
		return -ENODEV;
	pmu = of_find_node_by_path(CONSUMER_NODE);
	rail = of_find_node_by_path("/soc@0/rsc@18200000/regulators-0/smps12");
	pcie = of_find_node_by_path("/soc@0/pcie@1c00000");
	supply = pmu ? of_parse_phandle(pmu, "vddpmu-supply", 0) : NULL;
	if (!pmu || !rail || supply != rail || !pcie ||
	    of_device_is_available(pcie) ||
	    !of_device_is_compatible(pmu, "rog5,s12-revote-diagnostic") ||
	    !of_device_is_compatible(rail->parent, "qcom,pm8350-rpmh-regulators") ||
	    of_property_read_string(rail->parent, "qcom,pmic-id", &pmic) ||
	    strcmp(pmic, "b") || cmd_db_read_addr("smpb12") != 0x40100 ||
	    of_property_count_u32_elems(rail, "regulator-allowed-modes") != 2 ||
	    of_property_read_u32_array(rail, "regulator-allowed-modes", modes, 2) ||
	    !modes_allowed(modes[0], modes[1]) ||
	    of_property_read_u32(rail, "regulator-initial-mode", &initial) || initial ||
	    of_property_read_u32(rail, "regulator-min-microvolt", &minimum) ||
	    of_property_read_u32(rail, "regulator-max-microvolt", &maximum) ||
	    !voltage_bounds_allowed(minimum, maximum) ||
	    of_property_read_bool(rail, "regulator-always-on") ||
	    of_property_read_bool(rail, "regulator-boot-on"))
		goto put_nodes;
	pmic_device = of_find_device_by_node(rail->parent);
	if (!pmic_device || !pmic_device->dev.driver ||
	    !pmic_device->dev.parent ||
	    !of_device_is_compatible(dev_of_node(pmic_device->dev.parent),
				     "qcom,rpmh-rsc") ||
	    of_property_read_u32(dev_of_node(pmic_device->dev.parent),
				 "qcom,drv-id", &drv_id) || drv_id != 2 ||
	    !dev_get_drvdata(pmic_device->dev.parent))
		goto put_nodes;
	parent_supply = of_parse_phandle(rail->parent, "vdd-s12-supply", 0);
	if (!parent_supply ||
	    !of_device_is_compatible(parent_supply, "regulator-fixed") ||
	    !of_property_read_bool(parent_supply, "regulator-always-on") ||
	    of_find_property(parent_supply, "gpio", NULL) ||
	    of_find_property(parent_supply, "gpios", NULL))
		goto put_nodes;
	consumer = of_find_device_by_node(pmu);
	if (!consumer)
		goto put_nodes;
	ret = -EBUSY;
	if (!device_trylock(&consumer->dev))
		goto put_consumer;
	if (consumer->dev.driver)
		goto unlock_consumer;
	/* Independent module lifetime, not the future PMU driver's devres. */
	s12 = of_regulator_get_optional(&consumer->dev, pmu, "vddpmu");
	if (IS_ERR(s12)) {
		ret = PTR_ERR(s12);
		s12 = NULL;
		goto unlock_consumer;
	}
	ret = regulator_is_supported_voltage(s12, S12_OEM_MV * 1000,
					    S12_OEM_MV * 1000);
	if (ret == 1)
		ret = apply_active_vote();
	else if (!ret)
		ret = -EOPNOTSUPP;
	if (!ret)
		report_cached_state();
	if (!holding) {
		regulator_put(s12);
		s12 = NULL;
	}
unlock_consumer:
	device_unlock(&consumer->dev);
put_consumer:
	if (!holding) {
		put_device(&consumer->dev);
		consumer = NULL;
	}
put_nodes:
	if (pmic_device) {
		put_device(&pmic_device->dev);
		pmic_device = NULL;
	}
	of_node_put(pcie);
	of_node_put(parent_supply);
	of_node_put(supply);
	of_node_put(rail);
	of_node_put(pmu);
	return finish_init_result(ret);
}

static void __exit s12_vote_exit(void)
{
	/* The hold action pins the module; force-unload is unsupported. */
	if (holding)
		return;
	/* Query/mode already released their references without undoing the mode. */
	/* Never restore RET while UFS or another shared consumer may be active. */
}

module_init(s12_vote_init);
module_exit(s12_vote_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("ROG5 protected S12 hold and cache-coherent OEM voltage");

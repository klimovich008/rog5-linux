// SPDX-License-Identifier: GPL-2.0-only
/* Temporary, exact-board active-UFS vote. No voltage API or disable path. */
#include <dt-bindings/regulator/qcom,rpmh-regulator.h>
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

static char *action = "query";
module_param(action, charp, 0400);
MODULE_PARM_DESC(action, "query, mode, or held-enable (requires verified AUTO)");
enum vote_action { QUERY, MODE, HELD_ENABLE };
static enum vote_action selected_action;
static struct regulator *s12;
static struct platform_device *consumer;
static bool holding;

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
	int ret;

	pr_info("ROG5_S12_VOTE before cached_mode=%d action=%s\n", mode, action);
	if (selected_action == QUERY)
		return 0;
	if (selected_action == MODE) {
		ret = regulator_set_mode(s12, REGULATOR_MODE_NORMAL);
		pr_info("ROG5_S12_VOTE mode-return result=%d\n", ret);
		if (ret)
			return ret;
		return (int)regulator_get_mode(s12) == REGULATOR_MODE_NORMAL ?
			0 : -EIO;
	}

	/* This is a distinct later action, never an automatic mode retry. */
	if (mode != REGULATOR_MODE_NORMAL)
		return -EPERM;
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
	return 0;
}

static int __init s12_vote_init(void)
{
	struct device_node *pmu, *rail, *supply, *parent_supply = NULL;
	const char *pmic;
	u32 modes[2], minimum, maximum, initial;
	int ret = -ENODEV;

	if (!action)
		return -EINVAL;
	if (!strcmp(action, "query"))
		selected_action = QUERY;
	else if (!strcmp(action, "mode"))
		selected_action = MODE;
	else if (!strcmp(action, "held-enable"))
		selected_action = HELD_ENABLE;
	else
		return -EINVAL;
	pr_info("ROG5_S12_VOTE action=%s identity-check\n", action);
	if (!of_machine_is_compatible("asus,rog-phone5"))
		return -ENODEV;
	pmu = of_find_node_by_path("/wcn6855-pmu");
	rail = of_find_node_by_path("/soc@0/rsc@18200000/regulators-0/smps12");
	supply = pmu ? of_parse_phandle(pmu, "vddpmu-supply", 0) : NULL;
	if (!pmu || !rail || supply != rail ||
	    !of_device_is_compatible(pmu, "qcom,wcn6855-pmu") ||
	    !of_device_is_compatible(rail->parent, "qcom,pm8350-rpmh-regulators") ||
	    of_property_read_string(rail->parent, "qcom,pmic-id", &pmic) ||
	    strcmp(pmic, "b") || cmd_db_read_addr("smpb12") != 0x40100 ||
	    of_property_count_u32_elems(rail, "regulator-allowed-modes") != 2 ||
	    of_property_read_u32_array(rail, "regulator-allowed-modes", modes, 2) ||
	    !modes_allowed(modes[0], modes[1]) ||
	    of_property_read_u32(rail, "regulator-initial-mode", &initial) || initial ||
	    of_property_read_u32(rail, "regulator-min-microvolt", &minimum) ||
	    of_property_read_u32(rail, "regulator-max-microvolt", &maximum) ||
	    minimum != 1350000 || maximum != 1352000)
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
	ret = apply_active_vote();
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
	of_node_put(parent_supply);
	of_node_put(supply);
	of_node_put(rail);
	of_node_put(pmu);
	return ret;
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
MODULE_DESCRIPTION("ROG5 exact S12 mode-only probe and protected active vote");

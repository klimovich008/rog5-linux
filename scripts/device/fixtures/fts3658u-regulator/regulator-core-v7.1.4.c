// SPDX-License-Identifier: GPL-2.0-or-later
//
// core.c  --  Voltage/Current Regulator framework.
//
// Copyright 2007, 2008 Wolfson Microelectronics PLC.
// Copyright 2008 SlimLogic Ltd.
//
// Author: Liam Girdwood <lrg@slimlogic.co.uk>

static int _regulator_handle_consumer_disable(struct regulator *regulator)
{
	struct regulator_dev *rdev = regulator->rdev;

	lockdep_assert_held_once(&rdev->mutex.base);

	if (!regulator->enable_count) {
		rdev_err(rdev, "Underflow of regulator enable count\n");
		return -EINVAL;
	}

	regulator->enable_count--;
	if (regulator->uA_load && regulator->enable_count == 0)
		return drms_uA_update(rdev);

	return 0;
}

static int _regulator_disable(struct regulator *regulator)
{
	struct regulator_dev *rdev = regulator->rdev;
	int ret = 0;

	lockdep_assert_held_once(&rdev->mutex.base);

	if (WARN(regulator->enable_count == 0,
		 "unbalanced disables for %s\n", rdev_get_name(rdev)))
		return -EIO;

	if (regulator->enable_count == 1) {
	/* disabling last enable_count from this regulator */
		/* are we the last user and permitted to disable ? */
		if (rdev->use_count == 1 &&
		    (rdev->constraints && !rdev->constraints->always_on)) {

			/* we are last user */
			if (regulator_ops_is_valid(rdev, REGULATOR_CHANGE_STATUS)) {
				ret = _notifier_call_chain(rdev,
							   REGULATOR_EVENT_PRE_DISABLE,
							   NULL);
				if (ret & NOTIFY_STOP_MASK)
					return -EINVAL;

				ret = _regulator_do_disable(rdev);
				if (ret < 0) {
					rdev_err(rdev, "failed to disable: %pe\n", ERR_PTR(ret));
					_notifier_call_chain(rdev,
							REGULATOR_EVENT_ABORT_DISABLE,
							NULL);
					return ret;
				}
				_notifier_call_chain(rdev, REGULATOR_EVENT_DISABLE,
						NULL);
			}

			rdev->use_count = 0;
		} else if (rdev->use_count > 1) {
			rdev->use_count--;
		}
	}

	if (ret == 0)
		ret = _regulator_handle_consumer_disable(regulator);

	if (ret == 0 && rdev->coupling_desc.n_coupled > 1)
		ret = regulator_balance_voltage(rdev, PM_SUSPEND_ON);

	if (ret == 0 && rdev->use_count == 0 && rdev->supply)
		ret = _regulator_disable(rdev->supply);

	return ret;
}

static int _regulator_handle_consumer_enable(struct regulator *regulator)
{
	int ret;
	struct regulator_dev *rdev = regulator->rdev;

	lockdep_assert_held_once(&rdev->mutex.base);

	regulator->enable_count++;
	if (regulator->uA_load && regulator->enable_count == 1) {
		ret = drms_uA_update(rdev);
		if (ret)
			regulator->enable_count--;
		return ret;
	}

	return 0;
}

static int _regulator_enable(struct regulator *regulator)
{
	struct regulator_dev *rdev = regulator->rdev;
	int ret;

	lockdep_assert_held_once(&rdev->mutex.base);

	if (rdev->use_count == 0 && rdev->supply) {
		ret = _regulator_enable(rdev->supply);
		if (ret < 0)
			return ret;
	}

	/* balance only if there are regulators coupled */
	if (rdev->coupling_desc.n_coupled > 1) {
		ret = regulator_balance_voltage(rdev, PM_SUSPEND_ON);
		if (ret < 0)
			goto err_disable_supply;
	}

	ret = _regulator_handle_consumer_enable(regulator);
	if (ret < 0)
		goto err_disable_supply;

	if (rdev->use_count == 0) {
		/*
		 * The regulator may already be enabled if it's not switchable
		 * or was left on
		 */
		ret = _regulator_is_enabled(rdev);
		if (ret == -EINVAL || ret == 0) {
			if (!regulator_ops_is_valid(rdev,
					REGULATOR_CHANGE_STATUS)) {
				ret = -EPERM;
				goto err_consumer_disable;
			}

			ret = _regulator_do_enable(rdev);
			if (ret < 0)
				goto err_consumer_disable;

			_notifier_call_chain(rdev, REGULATOR_EVENT_ENABLE,
					     NULL);
		} else if (ret < 0) {
			rdev_err(rdev, "is_enabled() failed: %pe\n", ERR_PTR(ret));
			goto err_consumer_disable;
		}
		/* Fallthrough on positive return values - already enabled */
	}

	if (regulator->enable_count == 1)
		rdev->use_count++;

	return 0;

err_consumer_disable:
	_regulator_handle_consumer_disable(regulator);

err_disable_supply:
	if (rdev->use_count == 0 && rdev->supply)
		_regulator_disable(rdev->supply);

	return ret;
}


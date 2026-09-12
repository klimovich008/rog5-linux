// SPDX-License-Identifier: GPL-2.0
/* Faulted provider callbacks; accounting is the exact kernel core below. */
#include <stdbool.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define lockdep_assert_held_once(x) ((void)0)
#define REGULATOR_CHANGE_STATUS 1
#define REGULATOR_EVENT_PRE_DISABLE 1
#define REGULATOR_EVENT_ABORT_DISABLE 2
#define REGULATOR_EVENT_DISABLE 3
#define NOTIFY_STOP_MASK 0x8000
#define PM_SUSPEND_ON 0
#define rdev_err(...) ((void)0)
#define dev_err(dev, ...) ((void)(dev))
#define WARN(condition, ...) ((condition) ? (++underflows, 1) : 0)
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL %s:%d %s\n", __FILE__, __LINE__, #x); exit(1); } } while (0)
struct regulator;
struct constraints { bool always_on; };
struct regulator_dev { int use_count; struct regulator *supply; struct constraints *constraints; struct { int n_coupled; } coupling_desc; int disable_error, enable_error; };
struct regulator { struct regulator_dev *rdev; int enable_count, uA_load; };
static int underflows;
static int drms_uA_update(struct regulator_dev *rdev) { return 0; }
static bool regulator_ops_is_valid(struct regulator_dev *rdev, int operation) { return true; }
static int _notifier_call_chain(struct regulator_dev *rdev, int event, void *data) { return 0; }
static int regulator_balance_voltage(struct regulator_dev *rdev, int state) { return 0; }
static int _regulator_do_disable(struct regulator_dev *rdev) { int error=rdev->disable_error; rdev->disable_error=0; return error; }

#define REGULATOR_EVENT_ENABLE 4
static int _regulator_is_enabled(struct regulator_dev *rdev) { return 0; }
static int _regulator_do_enable(struct regulator_dev *rdev) { int error=rdev->enable_error; rdev->enable_error=0; return error; }

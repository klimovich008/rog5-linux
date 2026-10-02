#!/usr/bin/env python3
"""Offline tests of rog5-dp-power-measure against a fake sysfs, kernel log and
gdbus/systemctl stubs (the gdbus stub plays mutter + msm: a DPMS on appends
the DP link line the kernel would log for the current msm.dp_link_policy and
sets the input current and MMCX corner that link would cost)."""
import getpass
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("rog5-dp-power-measure")

GDBUS = textwrap.dedent("""\
    #!/bin/sh
    # args: call ... PowerSaveMode <N>
    r=$ROG5_DPM_ROOT
    for a; do last=$a; done
    echo "gdbus $last policy=$(cat $r/sys/module/msm/parameters/dp_link_policy)" >>$r/calls
    [ "$last" = "<0>" ] || exit 0
    case $(cat $r/sys/module/msm/parameters/dp_link_policy) in
    0) l=4 k=540000 ma=500000 c=192 ;;
    2) l=2 k=540000 ma=490000 c=192 ;;
    *) l=4 k=270000 ma=470000 c=128
       n1=$(( $(cat $r/n_efficient 2>/dev/null || echo 0) + 1 )); echo $n1 >$r/n_efficient
       if [ -e $r/fallback_on_2 ] && [ $n1 = 2 ]; then
         l=4 k=540000 ma=500000 c=192
         echo "6,$(( $(wc -l <$ROG5_DPM_KMSG) + 100 )),0,-;msm_dpu ae01000.display-controller: [drm] DP: link policy: 4 lanes x 270000 kHz failed (rc=-110), training 4 lanes x 540000 kHz" >>$ROG5_DPM_KMSG
       fi ;;
    esac
    n=$(wc -l <$ROG5_DPM_KMSG)
    echo "6,$((n + 100)),0,-;msm_dpu ae01000.display-controller: [drm] DP: 3840x1080@60 pclk 266500 kHz, $l lanes x $k kHz, bpp 30, widebus 1, tpg 0" >>$ROG5_DPM_KMSG
    echo $ma >$r/sys/class/power_supply/qcom-battmgr-usb/current_now
    echo $c >$r/sys/kernel/debug/pm_genpd/mmcx/perf_state
    """)

SYSTEMCTL = textwrap.dedent("""\
    #!/bin/sh
    echo "systemctl $*" >>$ROG5_DPM_ROOT/calls
    [ "${FAIL_VERB:-}" = "$2" ] && exit 1
    exit 0
    """)


class Fixture:
    def __init__(self, param=True, connected=True):
        self.tmp = tempfile.TemporaryDirectory()
        r = Path(self.tmp.name)
        self.root = r
        files = {
            "sys/class/power_supply/qcom-battmgr-usb/online": "1",
            "sys/class/power_supply/qcom-battmgr-usb/voltage_now": "5000000",
            "sys/class/power_supply/qcom-battmgr-usb/current_now": "400000",
            "sys/class/power_supply/qcom-battmgr-wls/online": "0",
            "sys/class/power_supply/qcom-battmgr-bat/power_now": "0",
            "sys/class/power_supply/qcom-battmgr-bat/voltage_now": "8600000",
            "sys/class/power_supply/qcom-battmgr-bat/current_now": "0",
            "sys/class/power_supply/qcom-battmgr-bat/capacity": "80",
            "sys/class/power_supply/qcom-battmgr-bat/charge_behaviour":
                "auto [inhibit-charge] force-discharge",
            "sys/class/thermal/thermal_zone36/type": "skin-thermal",
            "sys/class/thermal/thermal_zone36/temp": "33000",
            "sys/class/thermal/thermal_zone37/type": "xo-thermal",
            "sys/class/thermal/thermal_zone37/temp": "34500",
            "sys/class/drm/card1-DP-1/status": "connected" if connected else "disconnected",
            "sys/class/drm/card1-DP-1/modes": "3840x1080\n1920x1080",
            "sys/kernel/debug/pm_genpd/mmcx/perf_state": "192",
            "sys/kernel/debug/clk/disp_cc_mdss_mdp_clk/clk_rate": "300000000",
            "proc/stat": "cpu  100 0 100 800 0 0 0 0 0 0",
            "proc/sys/kernel/osrelease": "7.2.7-rog5-production",
            "kmsg": "6,1,0,-;msm_dpu ae01000.display-controller: [drm] DP: 3840x1080@60 "
                    "pclk 266500 kHz, 4 lanes x 540000 kHz, bpp 30, widebus 1, tpg 0",
        }
        if param:
            files["sys/module/msm/parameters/dp_link_policy"] = "1"
        for rel, text in files.items():
            p = r / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text + "\n")
        for name, body in (("gdbus", GDBUS), ("systemctl", SYSTEMCTL),
                           ("inhibit", "#!/bin/sh\nexec sleep 30\n")):
            p = r / "bin" / name
            p.parent.mkdir(exist_ok=True)
            p.write_text(body)
            p.chmod(0o755)
        self.env = dict(os.environ, ROG5_DPM_ROOT=str(r), ROG5_DPM_KMSG=str(r / "kmsg"),
                        ROG5_DPM_GDBUS=str(r / "bin/gdbus"),
                        ROG5_DPM_SYSTEMCTL=str(r / "bin/systemctl"),
                        ROG5_DPM_INHIBIT=str(r / "bin/inhibit"),
                        ROG5_DPM_USER=getpass.getuser(), ROG5_DPM_NOSLEEP="1",
                        ROG5_DPM_BASE=str(r / "results"))

    def run(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], env=self.env,
                              capture_output=True, text=True, timeout=120)

    def read(self, rel):
        return (self.root / rel).read_text().strip()

    def result_dir(self):
        (d,) = list((self.root / "results").iterdir())
        return d

    def close(self):
        self.tmp.cleanup()


class Tests(unittest.TestCase):
    def setUp(self):
        self.f = None

    def tearDown(self):
        if self.f:
            self.f.close()

    def test_matrix_rotates_measures_and_restores(self):
        f = self.f = Fixture()
        r = f.run("matrix", "--rounds=3", "--seconds=4", "--interval=1", "--settle=0")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        wins = json.loads((f.result_dir() / "windows.json").read_text())
        self.assertEqual([w["label"] for w in wins],
                         ["max", "narrow", "efficient", "narrow", "efficient", "max",
                          "efficient", "max", "narrow"])
        by = {w["label"]: w for w in wins}
        self.assertEqual((by["max"]["link"]["lanes"], by["max"]["link"]["rate_khz"]), (4, 540000))
        self.assertEqual((by["narrow"]["link"]["lanes"], by["narrow"]["link"]["rate_khz"]), (2, 540000))
        self.assertEqual((by["efficient"]["link"]["lanes"], by["efficient"]["link"]["rate_khz"]),
                         (4, 270000))
        self.assertEqual(by["efficient"]["link"]["fill_pct"], 92.5)
        self.assertEqual(by["efficient"]["mmcx"], [128])
        self.assertAlmostEqual(by["max"]["w_mean"], 2.5)
        summary = (f.result_dir() / "summary.txt").read_text()
        self.assertIn("-150+-0 mW", summary)   # efficient vs max: 0.03 A x 5 V
        self.assertIn("-50+-0 mW", summary)    # narrow vs max
        # policy restored, and one more DPMS cycle applied it
        self.assertEqual(f.read("sys/module/msm/parameters/dp_link_policy"), "1")
        calls = f.read("calls").splitlines()
        self.assertEqual(calls[-1], "gdbus <0> policy=1")
        self.assertFalse((f.root / "run/rog5-dp-power-measure/saved.json").exists())
        self.assertNotIn("systemctl", "".join(calls))   # input power: charger untouched

    def test_battery_mode_switches_and_restores_the_charger(self):
        f = self.f = Fixture()
        bat = "sys/class/power_supply/qcom-battmgr-bat/"
        (f.root / bat / "power_now").write_text("-2100000\n")
        r = f.run("matrix", "--configs=efficient", "--rounds=1", "--seconds=2",
                  "--interval=1", "--settle=0", "--power=battery")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        wins = json.loads((f.result_dir() / "windows.json").read_text())
        self.assertAlmostEqual(wins[0]["w_mean"], 2.1)
        calls = f.read("calls")
        self.assertIn("systemctl --quiet stop rog5-charge-policy", calls)
        self.assertIn("systemctl --quiet start rog5-charge-policy", calls)
        # restored to the value that was selected before the run
        self.assertEqual(f.read(bat + "charge_behaviour"), "inhibit-charge")

    def test_fallback_rounds_are_reported_apart(self):
        f = self.f = Fixture()
        (f.root / "fallback_on_2").touch()
        r = f.run("matrix", "--configs=max,efficient", "--rounds=3", "--seconds=2",
                  "--interval=1", "--settle=0")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        wins = json.loads((f.result_dir() / "windows.json").read_text())
        eff = [w for w in wins if w["label"] == "efficient"]
        self.assertEqual([w["fallback"] for w in eff], [False, True, False])
        summary = (f.result_dir() / "summary.txt").read_text()
        self.assertIn("efficient*  4x270M 30bpp 92.5%", summary)
        self.assertIn("efficient*  4x540M 30bpp 46.3% FB", summary)
        self.assertIn("compare rows, not configs", summary)

    def test_charge_policy_stop_failure_aborts_before_force_discharge(self):
        f = self.f = Fixture()
        f.env["FAIL_VERB"] = "stop"
        r = f.run("matrix", "--configs=efficient", "--rounds=1", "--seconds=1",
                  "--interval=1", "--settle=0", "--power=battery")
        self.assertIn("could not stop rog5-charge-policy", r.stdout)
        self.assertEqual(f.read("sys/class/power_supply/qcom-battmgr-bat/charge_behaviour"),
                         "inhibit-charge")
        self.assertNotIn("force-discharge", f.read("sys/class/power_supply/qcom-battmgr-bat/"
                                                    "charge_behaviour"))

    def test_failed_restore_step_keeps_the_record(self):
        f = self.f = Fixture()
        run = f.root / "run/rog5-dp-power-measure"
        run.mkdir(parents=True)
        (run / "saved.json").write_text(json.dumps(
            {"dp_link_policy": "0", "charge_behaviour": "auto", "charge_policy_active": True}))
        f.env["FAIL_VERB"] = "start"
        r = f.run("restore")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAILED rog5-charge-policy started", r.stdout)
        # the other steps still ran, and the record stays for a rerun
        self.assertEqual(f.read("sys/module/msm/parameters/dp_link_policy"), "0")
        self.assertEqual(f.read("sys/class/power_supply/qcom-battmgr-bat/charge_behaviour"), "auto")
        self.assertTrue((run / "saved.json").exists())
        del f.env["FAIL_VERB"]
        self.assertEqual(f.run("restore").returncode, 0)
        self.assertFalse((run / "saved.json").exists())

    def test_failed_cleanup_after_a_measurement_fails_the_run(self):
        f = self.f = Fixture()
        f.env["FAIL_VERB"] = "start"
        r = f.run("matrix", "--configs=efficient", "--rounds=1", "--seconds=2",
                  "--interval=1", "--settle=0", "--power=battery")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("FAILED rog5-charge-policy started", r.stdout)
        self.assertTrue((f.root / "run/rog5-dp-power-measure/saved.json").exists())

    def test_sample_needs_no_policy_parameter(self):
        f = self.f = Fixture(param=False)
        r = f.run("sample", "--label=before", "--seconds=2", "--interval=1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        wins = json.loads((f.result_dir() / "windows.json").read_text())
        self.assertEqual(wins[0]["label"], "before")
        self.assertEqual(wins[0]["link"]["lanes"], 4)
        self.assertFalse((f.root / "calls").exists())   # no retrain, nothing written

    def test_matrix_refuses_without_0145_or_monitor(self):
        f = self.f = Fixture(param=False)
        r = f.run("matrix", "--seconds=1", "--interval=1")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("dp_link_policy", r.stderr)
        f.close()
        f = self.f = Fixture(connected=False)
        r = f.run("matrix", "--seconds=1", "--interval=1")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not connected", r.stderr)

    def test_restore_after_a_killed_run(self):
        f = self.f = Fixture()
        run = f.root / "run/rog5-dp-power-measure"
        run.mkdir(parents=True)
        (run / "saved.json").write_text(json.dumps(
            {"dp_link_policy": "0", "charge_behaviour": "auto", "charge_policy_active": True}))
        (f.root / "sys/module/msm/parameters/dp_link_policy").write_text("2\n")
        r = f.run("restore")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(f.read("sys/module/msm/parameters/dp_link_policy"), "0")
        self.assertEqual(f.read("sys/class/power_supply/qcom-battmgr-bat/charge_behaviour"), "auto")
        self.assertIn("start rog5-charge-policy", f.read("calls"))
        self.assertIn("nothing to restore", f.run("restore").stdout)


if __name__ == "__main__":
    unittest.main()

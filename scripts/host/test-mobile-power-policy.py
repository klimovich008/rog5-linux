#!/usr/bin/env python3
"""Bounded battery/cable-removal policy fixtures; no physical qualification."""
import copy
import importlib.util
from pathlib import Path
import unittest
import json
import tempfile

spec = importlib.util.spec_from_file_location('mobile_policy', Path(__file__).with_name('assess-mobile-power.py'))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


class MobilePolicy(unittest.TestCase):
    def setUp(self):
        self.identity = dict(serial='fixture-phone', boot_id='fixture-boot',
                             bundle='fixture-mobile', release='fixture-kernel')
        self.sample = dict(identity=self.identity.copy(), monotonic=100,
                           health='Good', battery_temp_decic=300, voltage_uv=8500000,
                           capacity_percent=80, usb_online=False,
                           thermal_millic={'fixture-cpu': 42000, 'fixture-pmic': 39000},
                           network_ready=True, local_ui_ready=True)

    def test_private_profile_binds_identity_and_topology_without_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'phone.local.json'
            profile=dict(schema=1,serial='fixture-phone',product='lahaina',usb_path='9-9.9',
                         expected_slot='b',rescue_slot='a',authority='identity only; no operation authorization')
            path.write_text(json.dumps(profile));path.chmod(0o600)
            observed={key:profile[key] for key in ('serial','product','usb_path','expected_slot')}
            expected={key:value for key,value in self.identity.items() if key!='serial'}
            result=M.assess_private(path,self.sample,expected_runtime=expected,observed_device=observed,
                                    thermal_zones=['fixture-cpu','fixture-pmic'],now=101)
            self.assertEqual(result['status'],'CANDIDATE_OBSERVATION_ONLY')
            self.assertFalse(result['hardware_authorized'])
            observed['usb_path']='9-8.8'
            with self.assertRaisesRegex(ValueError,'topology'):
                M.assess_private(path,self.sample,expected_runtime=expected,observed_device=observed,
                                 thermal_zones=['fixture-cpu','fixture-pmic'],now=101)

    def assess(self, previous=None):
        return M.assess(self.sample, identity=self.identity,
                        thermal_zones=['fixture-cpu', 'fixture-pmic'], now=101,
                        previous=previous)

    def test_battery_start_is_observation_only(self):
        result = self.assess()
        self.assertEqual(result['status'], 'CANDIDATE_OBSERVATION_ONLY')
        self.assertEqual(result['power_source'], 'battery')
        self.assertFalse(result['hardware_authorized'])
        self.assertFalse(result['persistent_commit_allowed'])
        self.assertFalse(result['energy_margin_qualified'])
        self.assertIsNone(result['estimated_remaining_runtime_seconds'])

    def test_cable_removal_keeps_local_session_candidate(self):
        previous = dict(self.sample, monotonic=99, usb_online=True)
        self.sample['network_ready'] = False
        result = self.assess(previous)
        self.assertTrue(result['cable_removed'])
        self.assertEqual(result['network'], 'degraded-local-only')

    def test_missing_local_ui_cannot_use_degraded_policy(self):
        self.sample.update(network_ready=False, local_ui_ready=False)
        self.assertEqual(self.assess()['status'], 'HOLD')

    def test_margins_and_thermal_boundaries_fail_closed(self):
        original = copy.deepcopy(self.sample)
        for name, value in [('capacity_percent', 49), ('voltage_uv', 8399999),
                            ('voltage_uv', 8800001), ('battery_temp_decic', 400),
                            ('battery_temp_decic', -1), ('health', 'Unknown'),
                            ('capacity_percent', True), ('usb_online', 0),
                            ('monotonic', 90), ('monotonic', float('nan'))]:
            with self.subTest(name=name, value=value):
                self.sample = dict(original, **{name: value})
                self.assertEqual(self.assess()['status'], 'HOLD')

    def test_continuation_stops_at_candidate_margin(self):
        previous = dict(self.sample, monotonic=99)
        self.sample['capacity_percent'] = 39
        self.assertEqual(self.assess(previous)['status'], 'HOLD')

    def test_missing_hot_or_unsupported_zone_holds(self):
        for temperatures in [{}, {'fixture-cpu': 42000},
                             {'fixture-cpu': 60000, 'fixture-pmic': 39000},
                             {'fixture-cpu': None, 'fixture-pmic': 39000}]:
            self.sample['thermal_millic'] = temperatures
            self.assertEqual(self.assess()['status'], 'HOLD')

    def test_cable_removal_cannot_reuse_other_boot_or_old_sample(self):
        previous = dict(self.sample, monotonic=99, usb_online=True)
        for alteration in [dict(identity=dict(self.identity, boot_id='other')),
                           dict(monotonic=90), dict(monotonic=100)]:
            self.assertEqual(self.assess(dict(previous, **alteration))['status'], 'HOLD')

    def test_unsafe_unplug_observation_is_not_accepted(self):
        previous = dict(self.sample, monotonic=99, usb_online=True)
        self.sample['battery_temp_decic'] = 405
        self.assertEqual(self.assess(previous)['status'], 'HOLD')


if __name__ == '__main__':
    unittest.main(verbosity=2)

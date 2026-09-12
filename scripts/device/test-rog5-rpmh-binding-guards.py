#!/usr/bin/env python3
"""Cheap config regressions; real RPMh schema validation is a separate test."""
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).with_name('test-rog5-rpmh-binding.py')
spec = importlib.util.spec_from_file_location('rpmh_binding', SOURCE)
binding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(binding)
OFF = '# CONFIG_ARM_PSCI_CPUIDLE_DOMAIN is not set\n'
ON = 'CONFIG_ARM_PSCI_CPUIDLE_DOMAIN=y\n'


class DomainConfig(unittest.TestCase):
    def test_single_disabled(self):
        self.assertTrue(binding.domain_provider_disabled(OFF))
        self.assertTrue(binding.domain_provider_disabled('CONFIG_ARM_PSCI_CPUIDLE_DOMAIN=n\n'))

    def test_enabled(self):
        self.assertFalse(binding.domain_provider_disabled(ON))

    def test_duplicate_off_then_on(self):
        self.assertFalse(binding.domain_provider_disabled(OFF + ON))

    def test_duplicate_on_then_off(self):
        self.assertFalse(binding.domain_provider_disabled(ON + OFF))

    def test_duplicate_disabled(self):
        self.assertFalse(binding.domain_provider_disabled(OFF + OFF))

    def test_missing_and_unrecognized(self):
        self.assertFalse(binding.domain_provider_disabled(''))
        self.assertFalse(binding.domain_provider_disabled('CONFIG_ARM_PSCI_CPUIDLE_DOMAIN=m\n'))

    def test_current_production_fragment(self):
        fragment = SOURCE.parents[2] / 'configs/kernel/rog5-mainline.fragment'
        self.assertTrue(binding.domain_provider_disabled(fragment.read_text()))


if __name__ == '__main__':
    unittest.main()

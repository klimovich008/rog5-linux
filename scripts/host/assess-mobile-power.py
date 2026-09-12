#!/usr/bin/env python3
"""Offline mobile observation policy; never grants boot/commit/write authority.

This candidate is deliberately separate from the accepted USB-powered health
gate. Inputs must come from a future identity-bound, complete telemetry reader.
Capacity margins are provisional; no measured remaining-runtime claim is made.
"""
import math

MAX_AGE_SECONDS = 5
OBSERVATION_SECONDS = 600
START_CAPACITY_PERCENT = 50
STOP_CAPACITY_PERCENT = 40
RESERVE_CAPACITY_PERCENT = 20


def assess(snapshot, *, identity, thermal_zones, now, previous=None):
    result = dict(status='HOLD', reason=None, installed=False,
                  hardware_authorized=False, persistent_commit_allowed=False,
                  observation_seconds=OBSERVATION_SECONDS,
                  estimated_remaining_runtime_seconds=None,
                  energy_margin_qualified=False)
    try:
        def need(condition, reason):
            if not condition:
                raise ValueError(reason)

        def integer(value, low, high, name):
            need(type(value) is int and low <= value <= high, 'invalid ' + name)
            return value

        def validate(value):
            need(type(value) is dict and set(value) == {
                'identity', 'monotonic', 'health', 'battery_temp_decic',
                'voltage_uv', 'capacity_percent', 'usb_online', 'thermal_millic',
                'network_ready', 'local_ui_ready'}, 'snapshot schema')
            need(value['identity'] == identity, 'telemetry identity changed')
            stamp = value['monotonic']
            need(type(stamp) in (int, float) and math.isfinite(stamp)
                 and 0 <= stamp <= now and now - stamp <= MAX_AGE_SECONDS,
                 'stale or invalid telemetry')
            need(value['health'] == 'Good', 'battery health')
            integer(value['battery_temp_decic'], 0, 399, 'battery temperature')
            # Retain the intersection of current radio/standalone voltage gates.
            integer(value['voltage_uv'], 8400000, 8800000, 'battery voltage')
            integer(value['capacity_percent'], 0, 100, 'capacity')
            for name in ('usb_online', 'network_ready', 'local_ui_ready'):
                need(type(value[name]) is bool, 'invalid ' + name)
            temperatures = value['thermal_millic']
            need(type(temperatures) is dict and thermal_zones
                 and set(temperatures) == set(thermal_zones), 'incomplete thermal inventory')
            for name, temperature in temperatures.items():
                integer(temperature, 0, 59999, 'thermal zone ' + name)

        need(type(identity) is dict and set(identity) == {'serial', 'boot_id', 'bundle', 'release'}
             and identity['serial'] != 'REPLACE_WITH_PRIVATE_SERIAL'
             and all(type(value) is str and value for value in identity.values()),
             'expected phone identity absent')
        need(type(now) in (int, float) and math.isfinite(now) and now >= 0, 'invalid clock')
        validate(snapshot)
        if previous is not None:
            validate(previous)
            need(previous['monotonic'] < snapshot['monotonic'], 'non-increasing observation')
        floor = START_CAPACITY_PERCENT if previous is None else STOP_CAPACITY_PERCENT
        need(snapshot['capacity_percent'] >= floor, 'capacity observation margin')
        # A degraded network is tolerable only with a working local interface.
        # This does not redefine headless Wi-Fi health or acknowledge a trial.
        need(snapshot['local_ui_ready'], 'local recovery interface unavailable')
        removed = bool(previous and previous['usb_online'] and not snapshot['usb_online'])
        result.update(status='CANDIDATE_OBSERVATION_ONLY',
                      power_source='usb' if snapshot['usb_online'] else 'battery',
                      cable_removed=removed,
                      network='ready' if snapshot['network_ready'] else 'degraded-local-only',
                      capacity_margin_percentage_points=snapshot['capacity_percent'] - RESERVE_CAPACITY_PERCENT,
                      wifi_power_save='candidate-on-requires-separate-radio-validation')
    except (ValueError, KeyError, TypeError) as error:
        result['reason'] = str(error)
    return result


def assess_private(profile_path, snapshot, *, expected_runtime, observed_device,
                   thermal_zones, now, previous=None):
    """Offline consumer of the private profile; all observations remain inputs.

    Reading identity configuration is not a phone query, authorization, signing
    input, or an alternative to the existing sealed admission process.
    """
    import importlib.util
    from pathlib import Path
    location = Path(__file__).with_name('load-private-device-profile.py')
    spec = importlib.util.spec_from_file_location('private_identity', location)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    profile = reader.load(profile_path)
    if type(expected_runtime) is not dict or set(expected_runtime) != {'boot_id', 'bundle', 'release'}:
        raise ValueError('independent expected runtime identity required')
    expected_device = {key: profile[key] for key in ('serial', 'product', 'usb_path', 'expected_slot')}
    if observed_device != expected_device:
        raise ValueError('observed device/topology differs from private profile')
    identity = dict(expected_runtime, serial=profile['serial'])
    return assess(snapshot, identity=identity, thermal_zones=thermal_zones,
                  now=now, previous=previous)


if __name__ == '__main__':
    raise SystemExit('Import-only offline proposal; no device access or policy activation')

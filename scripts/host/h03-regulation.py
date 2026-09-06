#!/usr/bin/env python3
"""H03 Full-state outcome math, not an identity/admission or qualification gate.

Only the host-supervised acceptance path may qualify H03 after separately
binding source/artifacts, H02, boot, transport, firmware and collection times.
No phone access, control writes, fallback changes or evidence imports here.
"""
import math


def validate_full_sample(sample):
    """Abort unsafe/incomplete Full telemetry as soon as it is observed."""
    numbers = (
        'capacity', 'current_ua', 'counter_uah', 'voltage_uv', 'voltage_max_uv',
        'temp_dc', 'usb_online', 'usb_voltage_uv', 'usb_current_ua',
        'input_limit_ua',
    )
    if type(sample) is not dict:
        raise ValueError('sample must be a record')
    if any(type(sample.get(field)) is not int for field in numbers):
        raise ValueError('required telemetry must be integer readings')
    if any(not -(2**31) <= sample[field] < 2**31 for field in numbers):
        raise ValueError('telemetry exceeds signed power-supply ABI')
    elapsed = sample.get('elapsed_s')
    if type(elapsed) not in (int, float) or not math.isfinite(elapsed):
        raise ValueError('missing/nonfinite measurement time')
    if not 0 <= elapsed <= 660:
        raise ValueError('observation deadline exceeded')
    if (sample.get('status'), sample['capacity'], sample.get('health')) != (
            'Full', 100, 'Good'):
        raise ValueError('not healthy firmware Full throughout')
    if sample['usb_online'] != 1 or sample.get('role') != 'device/sink':
        raise ValueError('external input/role changed')
    if not (sample['usb_voltage_uv'] > 0 and
            0 < sample['usb_current_ua'] <= sample['input_limit_ua']):
        raise ValueError('input current absent or above reported limit')
    if not (0 <= sample['temp_dc'] < 400 and
            8_400_000 <= sample['voltage_uv'] <=
            min(9_000_000, sample['voltage_max_uv'])):
        raise ValueError('power/thermal observation unsafe')
    if abs(sample['current_ua']) > 25_000:
        raise ValueError('outside declared Full-state current band')


def evaluate_full(samples):
    """Evaluate the predeclared 600s Full branch; reject incomplete evidence."""
    if type(samples) is not list or len(samples) != 61:
        raise ValueError('61 actual samples required')
    for sample in samples:
        validate_full_sample(sample)
    span = samples[-1]['elapsed_s'] - samples[0]['elapsed_s']
    if span < 600:
        raise ValueError('short observation')
    integral = 0
    for before, after in zip(samples, samples[1:]):
        interval = after['elapsed_s'] - before['elapsed_s']
        if not 8 <= interval <= 12:
            raise ValueError('missing, stale or late sample')
        integral += interval * (before['current_ua'] + after['current_ua']) / 2
    delta = samples[-1]['counter_uah'] - samples[0]['counter_uah']
    if integral < 0 or delta < 0:
        raise ValueError('net discharge cannot qualify as Full maintenance')
    if delta > 25_000 * span / 3600:
        raise ValueError('counter jump contradicts bounded Full current')
    return dict(outcome='full-state-maintenance', span_seconds=span,
                mean_current_ua=integral/span, counter_delta_uah=delta,
                h03_qualified=False)

"""Exact production display assembly and result validation, import-only.

The caller must supply the admitted identity callback and an independently owned
supervisor/cleanup path. Source pins protect this local assembly; they are not
admission, device authorization or proof of installed artifact bytes. No CLI,
claim, signing, staging or device I/O occurs on import.
"""
import copy
import hashlib
import math
import os
from pathlib import Path
import re
import stat

HERE = Path(__file__).resolve().parent
SOURCE_PINS = {'display-endpoint.py': '0d0eb43a7be8525eef8f38d5a895749eb2c0f764a472c75beb76b3aad859b6ee', 'display-firmware.py': 'd3bfdbe1249f7651263291954f94ad9c1e5c81c78ce967eed5da9663f387dafb', 'display-providers.py': 'c9f9753083ed4f5806ad8caff67f588ab990f665d2e4ec86c9c2e2492a84c62d', 'load-production-display.py': 'b3a69a53ff31fdadfdc78226568099c3474c1df05ae18e9a0ad5e890621cf77b'}
ORDER = (
    'qcom-refgen-regulator.ko', 'gpucc-sm8350.ko', 'drm_kms_helper.ko',
    'cec.ko', 'drm_display_helper.ko', 'drm_client_lib.ko', 'drm_dp_aux_bus.ko',
    'drm_exec.ko', 'drm_gpuvm.ko', 'gpu-sched.ko', 'mdt_loader.ko',
    'ubwc_config.ko', 'msm.ko', 'panel-asus-rog5-ams678.ko',
)


def need(ok, reason):
    if not ok: raise ValueError(reason)


def identity_valid(identity):
    need(type(identity) is dict and identity.get('release') == '7.1.4-rog5-production'
         and type(identity.get('boot_id')) is str
         and re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', identity['boot_id'])
         and type(identity.get('owner')) is str and re.fullmatch('[0-9a-f]{32}', identity['owner']),
         'production receipt identity required')


def validate_blank(value, identity):
    identity_valid(identity)
    need(type(value) is dict and value.get('status') == 'PASS_ZERO_BRIGHTNESS_COMMAND'
         and type(value.get('write_bytes')) is int and value['write_bytes'] == 2
         and type(value.get('brightness_readback')) is int and value['brightness_readback'] == 0
         and value.get('physical_darkness_verified') is False
         and value.get('full_health_verified') is False
         and value.get('framebuffer_qualified') is False, 'production zero receipt missing or invalid')
    for key in ('before','after'):
        item = value.get(key)
        need(type(item) is dict and item.get('identity') == identity
             and type(item.get('path')) is str and item['path'].startswith('/'), 'zero endpoint identity')
    need(value['before']['path'] == value['after']['path']
         and type(value['after'].get('brightness')) is int and value['after']['brightness'] == 0,
         'zero endpoint/readback changed')
    return value


def validate_result(value, identity):
    identity_valid(identity)
    need(type(value) is dict and value.get('status') == 'PASS_MODULES_AND_BLANK'
         and value.get('entered') is True and value.get('panel_attempted') is True
         and 'error' in value and value['error'] is None and value.get('cleanup_errors') == [],
         'production component did not complete')
    for key in ('retry_allowed','physical_scanout_verified','physical_darkness_verified',
                'full_health_verified','admission_granted'):
        need(value.get(key) is False, 'production component scope: '+key)
    for key in ('driver_reprobes','drm_opens'):
        need(type(value.get(key)) is int and value[key] == 0, 'production operation count: '+key)
    need(type(value.get('seconds')) in (int,float) and math.isfinite(value['seconds'])
         and 0 <= value['seconds'] <= 85, 'production component elapsed bound')
    need(value.get('checkpoints') == ['refgen','gpucc','msm']
         and value.get('preconsumer_checks') == ['msm','panel_asus_rog5_ams678'],
         'production provider checkpoint receipts')
    rows = value.get('insertions')
    need(type(rows) is list and len(rows) == len(ORDER), 'production insertion count')
    for row, name in zip(rows, ORDER):
        need(type(row) is dict and row.get('filename') == name
             and row.get('status') == 'PASS_INSERTION' and row.get('reaped') is True
             and type(row.get('returncode')) is int and row['returncode'] == 0
             and type(row.get('pid')) is int and row['pid'] > 0
             and row.get('stdout') == row.get('stderr') == ''
             and 'error' in row and row['error'] is None and row.get('retry_allowed') is False,
             'production insertion receipt: '+name)
        need(type(row.get('seconds')) in (int,float) and math.isfinite(row['seconds'])
             and 0 <= row['seconds'] <= 5, 'production insertion elapsed bound')
    endpoint = value.get('endpoint')
    need(type(endpoint) is dict and endpoint.get('status') == 'PASS_FRAMEBUFFER_SYSFS'
         and endpoint.get('identity') == identity and endpoint.get('name') == 'msmdrmfb'
         and endpoint.get('virtual_size') == [1080,2448]
         and type(endpoint.get('bits_per_pixel')) is int and endpoint['bits_per_pixel'] == 32
         and type(endpoint.get('mode')) is str
         and re.fullmatch('[UDVS]:1080x2448p-60', endpoint['mode'])
         and endpoint.get('device_opened') is False and endpoint.get('pixel_layout_verified') is False
         and endpoint.get('physical_scanout_verified') is False, 'production framebuffer receipt')
    validate_blank(value.get('blank'), identity)
    # A secondary zero may exist after an action error, which must never have
    # been promoted to a successful component result.
    need(value.get('cleanup_blank') is None, 'unexpected recovery in successful component')
    return value


def dependency(name):
    need(name in SOURCE_PINS and re.fullmatch('[0-9a-f]{64}', SOURCE_PINS[name]), 'reviewed dependency pin required')
    path = HERE/name
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    with os.fdopen(fd,'rb') as stream:
        before = os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= 65536, 'component source type/size')
        raw = stream.read(65537)
        need(len(raw) == before.st_size and hashlib.sha256(raw).hexdigest() == SOURCE_PINS[name],
             'component source digest: '+name)
        def stamp(st):
            return (st.st_dev,st.st_ino,st.st_mode,st.st_uid,st.st_gid,st.st_size,st.st_mtime_ns,st.st_ctime_ns)
        need(stamp(before) == stamp(os.fstat(stream.fileno())) == stamp(path.lstat()), 'component source changed')
    # Execute exactly the bytes checked above, not a second path read or stale
    # pyc. Source ownership and enclosing directory are the admission layer's
    # separate responsibility; this helper grants no target authority.
    import types
    result = types.ModuleType('production_'+name.replace('-','_').replace('.','_'))
    result.__file__ = str(path)
    exec(compile(raw,str(path),'exec'),result.__dict__)
    return result


class Component:
    def __init__(self, identity_check):
        endpoint = dependency('display-endpoint.py')
        firmware = dependency('display-firmware.py')
        providers = dependency('display-providers.py')
        self.modules = dependency('load-production-display.py')
        self.endpoint = endpoint.Endpoint(identity_check)
        self.loader = self.modules.Loader(self.endpoint,firmware.open_inputs,
                        lambda phase,boot: providers.checkpoint(phase,boot,self.endpoint.identity))

    def identity(self, boot):
        return self.endpoint.identity(boot)

    def expected(self, boot, owner):
        result = copy.deepcopy(self.identity(boot))
        identity_valid(result)
        need(result['boot_id'] == boot and result['owner'] == owner, 'component owner/boot changed')
        return result

    def entry_intent(self, boot, owner):
        return self.modules.entry_intent(self.expected(boot,owner))

    def validate_blank(self, value, boot, owner):
        return validate_blank(value,self.expected(boot,owner))

    def validate_result(self, value, boot, owner):
        return validate_result(value,self.expected(boot,owner))


if __name__ == '__main__':
    raise SystemExit('Import-only: requires separately admitted production identity and supervisor')

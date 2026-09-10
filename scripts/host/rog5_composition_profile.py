"""Exact repository composition profile; classification, never boot authority."""
import hashlib
import json
from pathlib import Path
import re
from types import MappingProxyType

PROFILE_ID = 'kernel-hw-05941-a607a2bb249c918b'
MANIFEST = Path(__file__).resolve().parents[2]/'configs/composition/headless-05941-v1.json'


def need(value, reason):
    if not value:
        raise ValueError(reason)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'duplicate composition profile field')
        result[key] = value
    return result


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _plain(value):
    if hasattr(value, 'items'):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _digest(value):
    need(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), 'profile digest')


def _path(value):
    need(isinstance(value, str) and re.fullmatch('[A-Za-z0-9_./-]{1,255}', value)
         and not value.startswith('/') and all(p not in ('', '.', '..') for p in value.split('/')),
         'profile member path')


def _validate_profile(p):
    need(p['format'] == 'rog5-composition-profile-v1' and p['id'] == PROFILE_ID
         and p['bundle'] == p['target_id'] == p['id'], 'profile identity')
    need(re.fullmatch('[0-9a-f]{40}', p['source_revision'])
         and p['release'] == '7.1.4-g'+p['source_revision'][:12], 'profile source/release')
    _digest(p['vm_image_sha256'])
    _digest(p['trial_id']); _digest(p['manifest_sha256']); _digest(p['signature_sha256'])
    need(set(p['artifacts']) == {'kernel', 'dtb', 'initramfs', 'boot_bundle', 'recovery'}, 'profile artifacts')
    for item in p['artifacts'].values():
        need(set(item) == {'sha256', 'size'} and type(item['size']) is int
             and 0 < item['size'] <= 160*1024**2, 'profile artifact bounds')
        _digest(item['sha256'])
    need(len(p['modules']) == 54 and len(p['loose_members']) == 32
         and len(p['nested_files']) == 51, 'profile module counts')
    seen = set(); loose = {}; nested = {}
    for canonical, item in p['modules'].items():
        _path(canonical); _digest(item['sha256'])
        need(item['name'] == Path(canonical).stem.replace('-', '_') and item['name'] not in seen,
             'profile duplicate/module name'); seen.add(item['name'])
        need(item['destinations'], 'profile module destination missing')
        for dest in item['destinations']:
            _path(dest['path'])
            need(dest['container'] in ('newc', 'radio-tar'), 'profile container')
            table = loose if dest['container'] == 'newc' else nested
            need(dest['path'] not in table, 'duplicate module destination')
            table[dest['path']] = item['sha256']
    need(loose == {n: v['sha256'] for n, v in p['loose_members'].items()}, 'profile loose mapping')
    need(nested == {n: v['sha256'] for n, v in p['nested_files'].items() if n.endswith('.ko')}
         and len(nested) == 37, 'profile nested mapping')
    for table in ('loose_members', 'sealed_members', 'nested_files'):
        for name, row in p[table].items():
            _path(name); _digest(row['sha256'])
            need(type(row['size']) is int and 0 <= row['size'] <= 64*1024**2, 'profile member bound')
            if table != 'nested_files':
                need(len(row['fields']) == 12 and row['fields'][5] == row['size'], 'profile newc fields')
    need(set(p['groups']) == {'indicator', 'display', 'hardware'}, 'profile groups')
    for label, count in (('indicator', 4), ('display', 2), ('hardware', 4)):
        group = p['groups'][label]; prefix = group['prefix']; _path(prefix.rstrip('/'))
        need(prefix.endswith('/') and len(group['module_order']) == count
             and len(set(group['module_order'])) == count, 'profile inert order')
        need(set(group['module_order']) == {n for n in group['members'] if n.endswith('.ko')},
             'profile inert inventory/order')
        need(all(n == prefix[:-1] or n.startswith(prefix) for n in group['members'])
             and prefix[:-1] in group['members'], 'profile inert prefix')
        for name in group['module_order']:
            need(group['members'][name] == p['loose_members'][name], 'profile inert/module mapping')
    need(set(p['radio_extra_roots']) == {'ath', 'mhi_pci_generic', 'ath11k_ahb', 'rfkill-gpio'}
         and len(p['radio_extra_roots']) == 4, 'profile radio extras')
    pdr = p['pdr_exception']; _digest(pdr['raw_sha256']); _digest(pdr['packaged_sha256'])
    need(pdr['canonical'] == 'drivers/soc/qcom/pdr_interface.ko'
         and pdr['packaged_sha256'] == p['modules'][pdr['canonical']]['sha256']
         and pdr['raw_sha256'] != pdr['packaged_sha256'], 'profile packaged PDR')
    statuses = {'kernel': 'PASS', 'modules': 'PASS_RAW_MODULE_TWINS',
                'closure': 'PASS_STATIC_SELECTED54_EXPORT_CLOSURE',
                'payload_a': 'PASS_UNSIGNED_EXACT059_PAYLOAD', 'payload_b': 'PASS_UNSIGNED_EXACT059_PAYLOAD',
                'components': 'PASS_REGISTRATION_ONLY', 'baseline': 'PASS_BASELINE_LOADER_ONLY',
                'packaging': 'PACKAGING_TWINS_PASS'}
    need(set(p['qualification']) == set(statuses), 'profile qualification inventory')
    for role, status in statuses.items():
        proof = p['qualification'][role]; _digest(proof['sha256']); _path(proof['receipt'])
        need(proof['status'] == status, 'profile qualification status')
        if role in ('components', 'baseline'):
            need(proof['kernel_sha256'] == p['artifacts']['kernel']['sha256'], 'profile VM kernel binding')


def load_profile():
    need(MANIFEST.resolve() == MANIFEST and MANIFEST.is_file()
         and MANIFEST.stat().st_size <= 128*1024, 'profile manifest path/bound')
    raw = MANIFEST.read_bytes()
    need(len(raw) <= 128*1024, 'profile manifest bound')
    p = json.loads(raw, object_pairs_hook=_unique)
    _validate_profile(p)
    p['profile_sha256'] = hashlib.sha256(raw).hexdigest()
    return _freeze(p)


def lookup_profile(candidate):
    return load_profile() if candidate == PROFILE_ID else None


def candidate_record(candidate):
    p = lookup_profile(candidate)
    if p is None:
        return None
    return MappingProxyType(dict(target_bundle=p['bundle'], manifest_sha256=p['manifest_sha256'],
        boot_image_sha256=p['artifacts']['boot_bundle']['sha256'],
        recovery_initramfs_sha256=p['artifacts']['recovery']['sha256'],
        ram_boot_image_size=p['artifacts']['boot_bundle']['size']))


def select_profile(kernel_sha256, dtb_sha256, initramfs_sha256, release):
    p = load_profile(); a = p['artifacts']
    actual = (kernel_sha256, dtb_sha256, initramfs_sha256, release)
    expected = (a['kernel']['sha256'], a['dtb']['sha256'], a['initramfs']['sha256'], p['release'])
    if actual == expected:
        return p
    # The headless DT is shared with f17 and cannot alone select this profile.
    need(release != p['release'] and kernel_sha256 != a['kernel']['sha256']
         and initramfs_sha256 != a['initramfs']['sha256'], 'partial/mismatched exact059 artifact profile')
    return None


def summary(p):
    return {key: _plain(p[key]) for key in ('id', 'source_revision', 'release', 'profile_sha256',
                                           'artifacts', 'qualification', 'vm_image_sha256')}


def _member(members, name, expected):
    need(name in members, 'profile missing member: '+name)
    fields, data = members[name]
    need(type(data) is bytes and len(fields) == 13 and tuple(fields[1:]) == tuple(expected['fields'])
         and len(data) == expected['size'], 'profile member metadata: '+name)
    need(hashlib.sha256(data).hexdigest() == expected['sha256'], 'profile member hash: '+name)


def validate_loose_members(members, p):
    need({n for n in members if n.endswith('.ko')} == set(p['loose_members']), 'profile loose module inventory')
    for table in ('loose_members', 'sealed_members'):
        for name, expected in p[table].items():
            _member(members, name, expected)
    need(members['rog5-native-wifi/kernel-release'][1] == (p['release']+'\n').encode(), 'profile release marker')
    for group in p['groups'].values():
        prefix = group['prefix']
        need({n for n in members if n == prefix[:-1] or n.startswith(prefix)} == set(group['members']),
             'profile inert prefix inventory')
        for name, expected in group['members'].items():
            _member(members, name, expected)
    return {'profile': p['id'], 'loose_modules': len(p['loose_members']), 'physical_probe': 'NOT RUN'}


def validate_members(members, p, nested_files):
    """Consume existing parsed nested files; retain no additional artifact bytes."""
    evidence = validate_loose_members(members, p)
    need(set(nested_files) == set(p['nested_files']), 'profile nested inventory')
    for name, expected in p['nested_files'].items():
        data = nested_files[name]
        need(type(data) is bytes and len(data) == expected['size']
             and hashlib.sha256(data).hexdigest() == expected['sha256'], 'profile nested member identity: '+name)
    return dict(evidence, unique_modules=len(p['modules']), nested_modules=37, nested_metadata_files=14,
                pdr_btf_scope=p['pdr_exception']['policy'])


def inert_members(members, p, label):
    group = p['groups'][label]
    # Full loose recognition prevents mixing otherwise-valid groups/profiles.
    validate_loose_members(members, p)
    paths = set(group['module_order'])
    pending = [dict(path=n, sha256=p['loose_members'][n]['sha256'], status='NOT RUN',
                    scope=label+' hardware module load') for n in sorted(paths)]
    return paths, pending

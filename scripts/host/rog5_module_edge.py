"""Static-only inspection of the sealed S12 -> Wi-Fi activation dependency.

members uses the archive parser's {path: (newc_fields, bytes)} contract. The
caller must authenticate the archive/signature; hashes here bind the inspected
bytes, not their provenance. No subprocess, filesystem write, module insertion or
hardware access occurs. Provider DWARF is deliberately not consulted (its
R_AARCH64_NONE is unsupported); its unmodified split BTF/base supplies types.
Requires pyelftools and libbpf.so.1 with btf__parse_raw_split. Missing host support is
EdgeUnavailable; absent/malformed artifact metadata is ValueError.
"""

import ctypes as C
import hashlib
import io
import os
import re
import stat
import struct


SYMBOL = 'rog5_s12_validate_hold'
PROVIDER = 'rog5-native-wifi/rog5-s12-ufs-vote.ko'
CONSUMER = 'rog5-native-wifi/rog5-wifi-activate.ko'
PROTOTYPE = 'signed int32(void)'


class EdgeUnavailable(RuntimeError):
    """Host lacks a required static-inspection library/API."""


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _elf(data):
    try:
        from elftools.elf.elffile import ELFFile
    except ImportError as exc:
        raise EdgeUnavailable('module edge requires pyelftools') from exc
    _require(len(data) >= 64 and data[:7] == b'\x7fELF\x02\x01\x01',
             'module must be ELF64 little-endian')
    elf = ELFFile(io.BytesIO(data))
    _require(elf['e_type'] == 'ET_REL' and elf['e_machine'] == 'EM_AARCH64'
             and elf['e_version'] == 'EV_CURRENT', 'module must be ARM64 ELF REL')
    names = set()
    for section in elf.iter_sections():
        _require(section.name not in names, 'duplicate ELF section name')
        names.add(section.name)
        if section['sh_type'] != 'SHT_NOBITS':
            _require(section['sh_offset'] + section['sh_size'] <= len(data),
                     'ELF section outside module')
    return elf


def _section(elf, name, kind='SHT_PROGBITS'):
    sec = elf.get_section_by_name(name)
    _require(sec is not None and sec['sh_type'] == kind,
             'missing/invalid ELF section: ' + name)
    return sec


def _symbol(elf, name):
    table = _section(elf, '.symtab', 'SHT_SYMTAB')
    matches = [(i, s) for i, s in enumerate(table.iter_symbols()) if s.name == name]
    _require(len(matches) == 1, 'missing/ambiguous symbol: ' + name)
    return matches[0]


def _defined(elf, sym, section_name=None, executable=False):
    idx = sym['st_shndx']
    _require(type(idx) is int and 0 < idx < elf.num_sections(),
             'symbol must have a real section')
    sec = elf.get_section(idx)
    _require(sec['sh_type'] == 'SHT_PROGBITS' and sec['sh_flags'] & 2,
             'symbol must be in allocated PROGBITS')
    _require(section_name is None or sec.name == section_name, 'wrong symbol section')
    _require(not executable or sec['sh_flags'] & 4, 'function not in executable section')
    _require(sym['st_value'] < sec['sh_size']
             and sym['st_value'] + sym['st_size'] <= sec['sh_size'],
             'symbol outside section')
    return sec


def _metadata(elf, name, depends, vermagic):
    raw = _section(elf, '.modinfo').data()
    _require(raw.endswith(b'\0'), 'unterminated modinfo')
    values = {}
    for item in raw.split(b'\0'):
        if not item:
            continue
        key, sep, value = item.partition(b'=')
        _require(bool(sep), 'invalid modinfo field')
        values.setdefault(key.decode('ascii'), []).append(value.decode('ascii'))
    for key, wanted in {'name': name, 'depends': depends, 'license': 'GPL',
                        'vermagic': vermagic}.items():
        _require(values.get(key) == [wanted], 'module ' + key + ' mismatch/duplicate')


def _relocations(elf):
    """Only RELA entries are relevant to this exact AArch64 export/call edge."""
    for sec in elf.iter_sections():
        if sec['sh_type'] not in ('SHT_RELA', 'SHT_REL'):
            continue
        _require(sec['sh_type'] == 'SHT_RELA' and sec['sh_entsize'] == 24
                 and sec['sh_size'] % 24 == 0, 'invalid AArch64 relocation table')
        table = elf.get_section(sec['sh_link'])
        _require(table.name == '.symtab' and table['sh_type'] == 'SHT_SYMTAB',
                 'relocations must link the real symtab')
        _require(0 < sec['sh_info'] < elf.num_sections(), 'invalid relocation target')
        target = elf.get_section(sec['sh_info'])
        for reloc in sec.iter_relocations():
            _require(reloc['r_info_sym'] < table.num_symbols(), 'invalid relocation symbol')
            yield target, reloc, table.get_symbol(reloc['r_info_sym'])


def _export(elf):
    func_idx, func = _symbol(elf, SYMBOL)
    _require(func['st_info']['bind'] == 'STB_GLOBAL'
             and func['st_info']['type'] == 'STT_FUNC'
             and func['st_other']['visibility'] == 'STV_DEFAULT'
             and func['st_size'] > 0, 'provider must define a real global FUNC')
    _defined(elf, func, executable=True)
    _, export = _symbol(elf, '__ksymtab_' + SYMBOL)
    table = _defined(elf, export, '__ksymtab')
    # This sealed kernel uses parallel __kflagstab bytes, not __ksymtab_gpl.
    _require(table['sh_size'] % 12 == 0 and export['st_value'] % 12 == 0
             and export['st_value'] + 12 <= table['sh_size'], 'invalid export entry')
    _, flag = _symbol(elf, '__flags_' + SYMBOL)
    flags = _defined(elf, flag, '__kflagstab')
    slot = export['st_value'] // 12
    _require(flags['sh_size'] == table['sh_size'] // 12 and flag['st_value'] == slot
             and flags.data()[slot] == 1, 'provider export is not GPL-only')
    wanted = {}
    for delta, prefix, value in ((4, '__kstrtab_', SYMBOL.encode()),
                               (8, '__kstrtabns_', b'')):
        _, sym = _symbol(elf, prefix + SYMBOL)
        sec = _defined(elf, sym, '__ksymtab_strings')
        start = sym['st_value']
        end = sec.data().find(b'\0', start)
        _require(end >= start and sec.data()[start:end] == value,
                 'export name/namespace mismatch')
        wanted[delta] = (sym['st_shndx'], start)
    relocs = []
    for target, r, sym in _relocations(elf):
        _require(target.name not in ('__kflagstab', '__ksymtab_strings'),
                 'export flags/strings must not be relocated')
        if (target.name == '__ksymtab'
                and export['st_value'] <= r['r_offset'] < export['st_value'] + 12):
            relocs.append((r, sym))
    _require(len(relocs) == 3, 'export requires three PREL32 relocations')
    seen = set()
    for r, sym in relocs:
        delta = r['r_offset'] - export['st_value']
        _require(delta in (0, 4, 8) and delta not in seen
                 and r['r_info_type'] == 261, 'invalid/duplicate export PREL32')
        seen.add(delta)
        _require(table.data()[r['r_offset']:r['r_offset'] + 4] == bytes(4),
                 'nonzero export relocation placeholder')
        if delta == 0:
            _require(r['r_info_sym'] == func_idx and r['r_addend'] == 0,
                     'export does not relocate to provider function')
        else:
            _require((sym['st_shndx'], sym['st_value'] + r['r_addend']) == wanted[delta],
                     'export name/namespace relocation mismatch')
    return {'symbol': SYMBOL, 'binding': 'GLOBAL FUNC', 'gpl_only': True,
            'namespace': '', 'relocation': 'R_AARCH64_PREL32'}


def _call(elf):
    idx, sym = _symbol(elf, SYMBOL)
    _require(sym['st_info']['bind'] == 'STB_GLOBAL'
             and sym['st_info']['type'] in ('STT_NOTYPE', 'STT_FUNC')
             and sym['st_shndx'] == 'SHN_UNDEF'
             and sym['st_other']['visibility'] == 'STV_DEFAULT'
             and sym['st_value'] == sym['st_size'] == 0,
             'consumer must have a strong undefined symbol')
    calls = [(target, r) for target, r, _ in _relocations(elf)
             if r['r_info_sym'] == idx and target['sh_flags'] & 2]
    _require(len(calls) == 1, 'consumer requires exactly one direct call')
    target, reloc = calls[0]
    offset = reloc['r_offset']
    _require(target['sh_type'] == 'SHT_PROGBITS' and target['sh_flags'] & 4
             and reloc['r_info_type'] == 283 and reloc['r_addend'] == 0
             and offset % 4 == 0 and offset + 4 <= target['sh_size'],
             'consumer call must be executable CALL26 with zero addend')
    _require(struct.unpack_from('<I', target.data(), offset)[0] == 0x94000000,
             'CALL26 does not point to a direct BL placeholder')
    return {'symbol': SYMBOL, 'binding': 'GLOBAL UND',
            'relocation': 'R_AARCH64_CALL26', 'section': target.name, 'offset': offset}


def _libbpf():
    try:
        lib = C.CDLL('libbpf.so.1')
        for name, args, result in (
            ('btf__new', [C.c_void_p, C.c_uint32], C.c_void_p),
            ('btf__parse_raw_split', [C.c_char_p, C.c_void_p], C.c_void_p),
            ('libbpf_get_error', [C.c_void_p], C.c_long),
            ('btf__type_cnt', [C.c_void_p], C.c_uint32),
            ('btf__type_by_id', [C.c_void_p, C.c_uint32], C.POINTER(C.c_uint32)),
            ('btf__name_by_offset', [C.c_void_p, C.c_uint32], C.c_char_p),
            ('btf__free', [C.c_void_p], None),
        ):
            fn = getattr(lib, name)
            fn.argtypes, fn.restype = args, result
        return lib
    except (OSError, AttributeError) as exc:
        raise EdgeUnavailable('module edge requires libbpf.so.1 with split BTF APIs') from exc


def _btf_type(elf):
    base_data = _section(elf, '.BTF.base').data()
    split_data = _section(elf, '.BTF').data()
    lib = _libbpf()
    base_buf = C.create_string_buffer(base_data)
    base = lib.btf__new(base_buf, len(base_data))
    _require(bool(base) and not lib.libbpf_get_error(base), 'invalid provider BTF base')
    split = None
    try:
        # Ubuntu 24.04's libbpf lacks the exported memory constructor. Use its
        # older raw-split API over an anonymous descriptor, never a caller path
        # or altered BTF. libbpf copies the parsed bytes before the fd closes.
        with os.fdopen(os.memfd_create('rog5-a01-btf',os.MFD_CLOEXEC),'w+b') as raw:
            raw.write(split_data);raw.flush();raw.seek(0)
            parsed = lib.btf__parse_raw_split(('/proc/self/fd/'+str(raw.fileno())).encode(),base)
        _require(bool(parsed) and not lib.libbpf_get_error(parsed), 'invalid provider split BTF')
        split = parsed

        def get(type_id, kind):
            _require(0 < type_id < lib.btf__type_cnt(split), 'invalid BTF type reference')
            t = lib.btf__type_by_id(split, type_id)
            _require(bool(t) and (t[1] >> 24) & 31 == kind, 'BTF type kind mismatch')
            return t

        matches = []
        for i in range(lib.btf__type_cnt(base), lib.btf__type_cnt(split)):
            t = lib.btf__type_by_id(split, i)
            _require(bool(t), 'missing BTF type')
            if lib.btf__name_by_offset(split, t[0]) == SYMBOL.encode():
                _require((t[1] >> 24) & 31 == 12, 'provider BTF symbol is not FUNC')
                matches.append(i)
        _require(len(matches) == 1, 'missing/ambiguous provider BTF function')
        func = get(matches[0], 12)
        # The exact artifact's BTF FUNC linkage is STATIC (0) despite its ELF
        # global export; ELF/export records, not BTF linkage, prove visibility.
        proto_id = func[2]
        proto = get(proto_id, 13)
        _require(proto[1] == 13 << 24, 'provider BTF prototype has arguments/flags')
        return_id = proto[2]
        result = get(return_id, 1)
        _require(result[1] == 1 << 24 and result[2] == 4 and result[3] == 0x01000020,
                 'provider BTF result must be signed int32')
        return {'source': '.BTF + .BTF.base', 'prototype': PROTOTYPE,
                'function_type_id': matches[0], 'prototype_type_id': proto_id,
                'return_type_id': return_id,
                'btf_sha256': hashlib.sha256(split_data).hexdigest(),
                'base_sha256': hashlib.sha256(base_data).hexdigest()}
    finally:
        if split:
            lib.btf__free(split)
        lib.btf__free(base)


def _dwarf_type(elf):
    _section(elf, '.debug_info')
    _section(elf, '.debug_abbrev')
    dwarf = elf.get_dwarf_info()
    matches = []
    for cu in dwarf.iter_CUs():
        for die in cu.iter_DIEs():
            name = die.attributes.get('DW_AT_name')
            if name is not None and name.value == SYMBOL.encode():
                matches.append(die)
    _require(len(matches) == 1, 'missing/ambiguous consumer DWARF declaration')
    die = matches[0]
    _require(die.tag == 'DW_TAG_subprogram', 'consumer DWARF symbol is not subprogram')
    for flag in ('DW_AT_prototyped', 'DW_AT_declaration', 'DW_AT_external'):
        _require(flag in die.attributes and die.attributes[flag].value == 1,
                 'consumer DWARF missing ' + flag)
    _require(not list(die.iter_children()), 'consumer DWARF has arguments/variadic children')
    convention=die.attributes.get('DW_AT_calling_convention')
    _require(convention is None or convention.value==1,
             'consumer DWARF requires normal calling convention')
    result = die.get_DIE_from_attribute('DW_AT_type')
    _require(result is not None and result.tag == 'DW_TAG_base_type',
             'consumer DWARF result is not base type')
    for name, value in (('DW_AT_encoding', 5), ('DW_AT_byte_size', 4)):
        _require(name in result.attributes and result.attributes[name].value == value,
                 'consumer DWARF result must be signed int32')
    _require('DW_AT_bit_size' not in result.attributes
             or result.attributes['DW_AT_bit_size'].value == 32,
             'consumer DWARF result bit size mismatch')
    return {'source': '.debug_info (relocated DWARF)', 'prototype': PROTOTYPE,
            'declaration_offset': die.offset, 'return_type_offset': result.offset,
            'debug_info_sha256': hashlib.sha256(_section(elf, '.debug_info').data()).hexdigest()}


def inspect_edge(members, vermagic):
    """Return JSON-safe STATIC evidence, never a real-pair initialization PASS.

    The two paths are fixed; no fixture/shim path or fallback type is accepted.
    The caller binds returned module hashes to its authenticated sealed inputs.
    """
    try:
        _require(isinstance(vermagic, str) and re.fullmatch(
            r'[^\s]+ SMP preempt mod_unload aarch64', vermagic) is not None,
            'full ARM64 SMP/preempt/mod_unload vermagic required')
        rows, elfs = [], []
        for path, name, depends in ((PROVIDER, 'rog5_s12_ufs_vote', ''),
                                    (CONSUMER, 'rog5_wifi_activate', 'rog5-s12-ufs-vote')):
            _require(path in members, 'missing sealed module: ' + path)
            fields, data = members[path]
            _require(len(fields) == 13 and all(type(x) is int and x >= 0 for x in fields)
                     and list(fields[1:5]) == [stat.S_IFREG | 0o644, 0, 0, 1]
                     and isinstance(data, bytes) and fields[6] == len(data),
                     'unsafe module metadata: ' + path)
            elf = _elf(data)
            _metadata(elf, name, depends, vermagic)
            elfs.append(elf)
            rows.append({'path': path, 'sha256': hashlib.sha256(data).hexdigest(),
                         'name': name, 'depends': depends, 'license': 'GPL',
                         'vermagic': vermagic})
        rows[0]['export'] = _export(elfs[0])
        rows[1]['call'] = _call(elfs[1])
        rows[0]['type'] = _btf_type(elfs[0])
        rows[1]['type'] = _dwarf_type(elfs[1])
        return {'evidence': 'STATIC', 'scope': 'sealed module dependency and type metadata only',
                'dynamic_pair_initialization_proven': False,
                'kernel_btf_validation_proven': False, 'hardware_activation_proven': False,
                'symbol': SYMBOL, 'prototype': PROTOTYPE,
                'provider': rows[0], 'consumer': rows[1]}
    except (EdgeUnavailable, ValueError):
        raise
    except Exception as exc:
        # pyelftools uses several exception types for truncated/invalid ELF and
        # unsupported DWARF relocations. None is a successful/static fallback.
        raise ValueError('malformed module edge metadata: ' + str(exc)) from exc

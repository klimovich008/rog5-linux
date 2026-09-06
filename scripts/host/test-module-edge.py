#!/usr/bin/env python3
"""Hardware-free module-edge regressions; no compiler or private fixture needed.

Optional --archive PATH additionally checks the hash-pinned real sealed pair
and repeats applicable mutations against those bytes, without extraction.
Run with PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts/host python [-O] this-file.
"""

import argparse
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import struct
import sys
import unittest
from unittest.mock import patch

import rog5_module_edge as edge


MAGIC = '7.1.4-g1eea8970e87f SMP preempt mod_unload aarch64'
ARCHIVE_SHA256 = '16efb362d6c55f6275924fd3a0374384f4b7b61baae22a10037140daf39de70f'
REAL_HASHES = ('e1634c442ac035afa4391609d1650aeaa78599e28032f7251c18981a7d5ae910',
               'be82b5a5a30e4f2a55fd696247e8e77d16d9deeae3156da6ee6762c2611ff157')


def btf(types, strings):
    return struct.pack('<HBB5I', 0xeb9f, 1, 0, 24, 0, len(types), len(types), len(strings)) + types + strings


def dwarf(parameters=False, calling=1):
    # Tiny real DWARF4 CU, declaration, signed base type. Not mocked DIEs.
    abbrev = (b'\x01\x11\x01\0\0'
              b'\x02\x2e\x01\x03\x08\x27\x0c\x3c\x0c\x3f\x0c\x49\x13\x36\x0b\0\0'
              b'\x03\x24\0\x03\x08\x3e\x0b\x0b\x0b\0\0'
              b'\x04\x18\0\0\0\0')
    declaration = b'\x02' + edge.SYMBOL.encode() + b'\0\x01\x01\x01'
    children = (b'\x04' if parameters else b'') + b'\0'
    return_offset = 11 + 1 + len(declaration) + 5 + len(children)
    body = (struct.pack('<HIB', 4, 0, 8) + b'\x01' + declaration
            + struct.pack('<IB', return_offset, calling) + children + b'\x03int\0\x05\x04\0')
    return struct.pack('<I', len(body)) + body, abbrev


def fixture(provider, parameters=False, calling=1):
    """Construct just enough ELF in memory to test the actual parser/library."""
    sections = [('', b'', 0, 0, 0, 0, 0)]

    def add(name, data, kind=1, flags=0, link=0, info=0, entsize=0):
        sections.append((name, data, kind, flags, link, info, entsize))
        return len(sections) - 1

    text_idx = add('.text', struct.pack('<I', 0xd65f03c0 if provider else 0x94000000), flags=6)
    module = 'rog5_s12_ufs_vote' if provider else 'rog5_wifi_activate'
    dependency = '' if provider else 'rog5-s12-ufs-vote'
    add('.modinfo', f'name={module}\0depends={dependency}\0license=GPL\0vermagic={MAGIC}\0'.encode())
    names = bytearray(b'\0')
    syms = [bytes(24)]

    def symbol(name, info, idx, value=0, size=0):
        offset = len(names)
        names.extend(name.encode() + b'\0')
        syms.append(struct.pack('<IBBHQQ', offset, info, 0, idx, value, size))
        return len(syms) - 1

    if provider:
        export_idx = add('__ksymtab', bytes(12), flags=2)
        flag_idx = add('__kflagstab', b'\x01', flags=2)
        string_idx = add('__ksymtab_strings', b'\0' + edge.SYMBOL.encode() + b'\0', flags=2)
        symbol('__ksymtab_' + edge.SYMBOL, 0, export_idx)
        symbol('__flags_' + edge.SYMBOL, 0, flag_idx)
        name_idx = symbol('__kstrtab_' + edge.SYMBOL, 0, string_idx, 1)
        ns_idx = symbol('__kstrtabns_' + edge.SYMBOL, 0, string_idx)
        func_idx = symbol(edge.SYMBOL, 0x12, text_idx, size=4)
        base_strings = b'\0int\0'
        add('.BTF.base', btf(struct.pack('<4I', 1, 1 << 24, 4, 0x01000020), base_strings))
        types = struct.pack('<3I', 0, 13 << 24 | int(parameters), 1)
        if parameters:
            types += struct.pack('<2I', 0, 1)
        types += struct.pack('<3I', len(base_strings), 12 << 24, 2)
        add('.BTF', btf(types, edge.SYMBOL.encode() + b'\0'))
    else:
        func_idx = symbol(edge.SYMBOL, 0x10, 0)
        info, abbrev = dwarf(parameters, calling)
        add('.debug_info', info)
        add('.debug_abbrev', abbrev)
    str_idx = add('.strtab', bytes(names), kind=3)
    sym_idx = add('.symtab', b''.join(syms), kind=2, link=str_idx, info=func_idx, entsize=24)
    if provider:
        relocs = b''.join(struct.pack('<QQq', off, idx << 32 | 261, 0)
                          for off, idx in ((0, func_idx), (4, name_idx), (8, ns_idx)))
        add('.rela__ksymtab', relocs, kind=4, link=sym_idx, info=export_idx, entsize=24)
    else:
        add('.rela.text', struct.pack('<QQq', 0, func_idx << 32 | 283, 0),
            kind=4, link=sym_idx, info=text_idx, entsize=24)
    strings = b'\0' + b''.join(s[0].encode() + b'\0' for s in sections[1:]) + b'.shstrtab\0'
    shstr_idx = add('.shstrtab', strings, kind=3)
    blob = bytearray(64)
    headers = [bytes(64)]
    for name, data, kind, flags, link, info, entsize in sections[1:]:
        blob.extend(bytes((-len(blob)) % 8))
        offset = len(blob)
        blob.extend(data)
        headers.append(struct.pack('<IIQQQQIIQQ', strings.index(name.encode() + b'\0'),
                                   kind, flags, 0, offset, len(data), link, info, 1, entsize))
    blob.extend(bytes((-len(blob)) % 8))
    shoff = len(blob)
    blob.extend(b''.join(headers))
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    blob[:64] = struct.pack('<16sHHIQQQIHHHHHH', ident, 1, 183, 1, 0, 0, shoff,
                            0, 64, 0, 0, 64, len(headers), shstr_idx)
    return bytes(blob)


def member(data):
    return ([1, stat.S_IFREG | 0o644, 0, 0, 1, 0, len(data), 0, 0, 0, 0, 1, 0], data)


def synthetic():
    return {edge.PROVIDER: member(fixture(True)), edge.CONSUMER: member(fixture(False))}


def change(data, offset, replacement):
    return data[:offset] + replacement + data[offset + len(replacement):]


def section_change(data, name, offset, replacement):
    sec = edge._elf(data).get_section_by_name(name)
    return change(data, sec['sh_offset'] + offset, replacement)


def symbol_change(data, name, offset, replacement):
    elf = edge._elf(data)
    index, _ = edge._symbol(elf, name)
    return section_change(data, '.symtab', index * 24 + offset, replacement)


def section_header(data, name, offset, replacement):
    elf = edge._elf(data)
    idx = next(i for i, s in enumerate(elf.iter_sections()) if s.name == name)
    return change(data, elf['e_shoff'] + idx * 64 + offset, replacement)


def dwarf_change(data, name, replacement):
    elf = edge._elf(data)
    dw = elf.get_dwarf_info()
    die = next(d for cu in dw.iter_CUs() for d in cu.iter_DIEs()
               if d.attributes.get('DW_AT_name') and d.attributes['DW_AT_name'].value == edge.SYMBOL.encode())
    if name in ('DW_AT_encoding', 'DW_AT_byte_size'):
        die = die.get_DIE_from_attribute('DW_AT_type')
    return section_change(data, '.debug_info', die.attributes[name].offset, replacement)


def btf_return_change(data, relative, replacement):
    # Find the int record in the real base's type area, not a name substring.
    sec = edge._elf(data).get_section_by_name('.BTF.base')
    raw = sec.data()
    start = struct.unpack_from('<I', raw, 4)[0] + struct.unpack_from('<I', raw, 8)[0]
    end = start + struct.unpack_from('<I', raw, 12)[0]
    for pos in range(start, end, 16):
        if struct.unpack_from('<I', raw, pos + 12)[0] == 0x01000020:
            return section_change(data, '.BTF.base', pos + relative, replacement)
    raise ValueError('test fixture has no signed int BTF record')


def relocation_change(data, provider, offset, replacement):
    elf = edge._elf(data)
    if provider:
        return section_change(data, '.rela__ksymtab', offset, replacement)
    idx, _ = edge._symbol(elf, edge.SYMBOL)
    for sec in elf.iter_sections():
        if sec['sh_type'] == 'SHT_RELA' and elf.get_section(sec['sh_info'])['sh_flags'] & 2:
            for i, reloc in enumerate(sec.iter_relocations()):
                if reloc['r_info_sym'] == idx:
                    return section_change(data, sec.name, i * 24 + offset, replacement)
    raise ValueError('test fixture has no call')


def call_instruction_change(data):
    elf = edge._elf(data)
    idx, _ = edge._symbol(elf, edge.SYMBOL)
    for sec in elf.iter_sections():
        if sec['sh_type'] == 'SHT_RELA' and elf.get_section(sec['sh_info'])['sh_flags'] & 2:
            for reloc in sec.iter_relocations():
                if reloc['r_info_sym'] == idx:
                    target = elf.get_section(sec['sh_info'])
                    return section_change(data, target.name, reloc['r_offset'], struct.pack('<I', 0x14000000))
    raise ValueError('test fixture has no call instruction')


def duplicate_symbol(data):
    elf = edge._elf(data)
    index, _ = edge._symbol(elf, edge.SYMBOL)
    sec = elf.get_section_by_name('.symtab')
    # Duplicate the named record into the null slot; never accept ambiguity.
    return section_change(data, '.symtab', 0, sec.data()[index * 24:(index + 1) * 24])


def duplicate_modinfo(data):
    sec = edge._elf(data).get_section_by_name('.modinfo')
    return replace_section(data, '.modinfo', sec.data() + b'license=GPL\0')


def replace_section(data, name, raw):
    # Append only in memory, updating the section's file offset and length.
    data = section_header(data, name, 24, struct.pack('<QQ', len(data), len(raw)))
    return data + raw


class EdgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.members = synthetic()

    def check_valid(self, members):
        report = edge.inspect_edge(members, MAGIC)
        self.assertEqual(json.loads(json.dumps(report)), report)
        self.assertEqual(report['evidence'], 'STATIC')
        self.assertEqual(report['prototype'], 'signed int32(void)')
        for key in ('dynamic_pair_initialization_proven', 'kernel_btf_validation_proven',
                    'hardware_activation_proven'):
            self.assertIs(report[key], False)
        for role, path in (('provider', edge.PROVIDER), ('consumer', edge.CONSUMER)):
            self.assertEqual(report[role]['sha256'], hashlib.sha256(members[path][1]).hexdigest())
            self.assertEqual(report[role]['type']['prototype'], report['prototype'])
        return report

    def test_valid_static_only(self):
        self.check_valid(self.members)

    def test_strict_metadata(self):
        for path in self.members:
            for index, value in ((1, stat.S_IFLNK | 0o644), (1, stat.S_IFREG | 0o600),
                                 (1, stat.S_IFREG | 0o664), (1, stat.S_IFREG | 0o4644),
                                 (2, 1000), (3, 1000), (4, 0), (4, 2), (6, 1), (2, False)):
                with self.subTest(path=path, index=index, value=value):
                    members = dict(self.members)
                    fields, data = members[path]
                    fields = list(fields)
                    fields[index] = value
                    members[path] = fields, data
                    with self.assertRaisesRegex(ValueError, 'unsafe module metadata'):
                        edge.inspect_edge(members, MAGIC)

    def test_missing_module_or_substitute_path(self):
        for path in self.members:
            members = dict(self.members)
            members['fixture-shim.ko'] = members.pop(path)
            with self.assertRaisesRegex(ValueError, 'missing sealed module'):
                edge.inspect_edge(members, MAGIC)

    def test_full_vermagic(self):
        for magic in ('', MAGIC.split()[0], MAGIC + ' ', MAGIC.replace('preempt ', ''),
                      MAGIC.replace('aarch64', 'x86_64'), MAGIC.replace('g1ee', 'g2ee')):
            with self.subTest(magic=magic), self.assertRaisesRegex(ValueError, 'vermagic'):
                edge.inspect_edge(self.members, magic)

    def test_no_lib(self):
        with patch.object(ctypes, 'CDLL', side_effect=OSError('absent')):
            with self.assertRaises(edge.EdgeUnavailable):
                edge.inspect_edge(self.members, MAGIC)

    def test_missing_split_api(self):
        with patch.object(ctypes, 'CDLL', return_value=object()):
            with self.assertRaises(edge.EdgeUnavailable):
                edge.inspect_edge(self.members, MAGIC)

    def test_no_pyelftools(self):
        with patch.dict(sys.modules, {'elftools.elf.elffile': None}):
            with self.assertRaises(edge.EdgeUnavailable):
                edge.inspect_edge(self.members, MAGIC)

    def test_dwarf_variadic(self):
        members = dict(self.members)
        members[edge.CONSUMER] = member(fixture(False, parameters=True))
        with self.assertRaisesRegex(ValueError, 'arguments/variadic'):
            edge.inspect_edge(members, MAGIC)

    def test_dwarf_unprototyped(self):
        members = dict(self.members)
        members[edge.CONSUMER] = member(dwarf_change(fixture(False), 'DW_AT_prototyped', b'\0'))
        with self.assertRaisesRegex(ValueError, 'DW_AT_prototyped'):
            edge.inspect_edge(members, MAGIC)

    def test_nonstandard_calling_convention_is_not_same_abi(self):
        members=dict(self.members)
        members[edge.CONSUMER]=member(fixture(False,calling=2))
        with self.assertRaisesRegex(ValueError,'calling convention'):
            edge.inspect_edge(members,MAGIC)

    def test_btf_parameters(self):
        members = dict(self.members)
        members[edge.PROVIDER] = member(fixture(True, parameters=True))
        with self.assertRaisesRegex(ValueError, 'prototype has arguments'):
            edge.inspect_edge(members, MAGIC)

    def test_duplicate_call(self):
        members = dict(self.members)
        data = fixture(False)
        elf = edge._elf(data)
        sec = elf.get_section_by_name('.rela.text')
        data = replace_section(data, '.rela.text', sec.data() * 2)
        members[edge.CONSUMER] = member(data)
        with self.assertRaisesRegex(ValueError, 'exactly one direct call'):
            edge.inspect_edge(members, MAGIC)

    def test_dwarf_declaration_and_external(self):
        for attr in ('DW_AT_declaration', 'DW_AT_external'):
            members = dict(self.members)
            members[edge.CONSUMER] = member(dwarf_change(fixture(False), attr, b'\0'))
            with self.subTest(attr=attr), self.assertRaisesRegex(ValueError, attr):
                edge.inspect_edge(members, MAGIC)

    def test_btf_bad_reference(self):
        members = dict(self.members)
        data = fixture(True)
        # Split proto's return type points past the real combined type table.
        members[edge.PROVIDER] = member(section_change(data, '.BTF', 24 + 8, struct.pack('<I', 999)))
        with self.assertRaisesRegex(ValueError, 'BTF'):
            edge.inspect_edge(members, MAGIC)


# Each mutation runs through inspect_edge(), never a mocked successful parser.
MUTATIONS = [
    ('elf_magic', True, lambda d: change(d, 0, b'BAD!'), 'ELF'),
    ('elf_class', True, lambda d: change(d, 4, b'\x01'), 'ELF'),
    ('elf_endian', False, lambda d: change(d, 5, b'\x02'), 'ELF'),
    ('elf_exec', True, lambda d: change(d, 16, b'\x02\0'), 'REL'),
    ('elf_machine', False, lambda d: change(d, 18, b'\x3e\0'), 'ARM64'),
    ('elf_truncated', True, lambda d: d[:63], 'ELF'),
    ('section_out_of_bounds', True, lambda d: section_header(d, '.text', 24, struct.pack('<Q', len(d))), 'outside'),
    ('provider_weak', True, lambda d: symbol_change(d, edge.SYMBOL, 4, b'\x22'), 'global FUNC'),
    ('provider_object', True, lambda d: symbol_change(d, edge.SYMBOL, 4, b'\x11'), 'global FUNC'),
    ('provider_undefined', True, lambda d: symbol_change(d, edge.SYMBOL, 6, b'\0\0'), 'real section'),
    ('provider_zero_size', True, lambda d: symbol_change(d, edge.SYMBOL, 16, bytes(8)), 'global FUNC'),
    ('provider_hidden', True, lambda d: symbol_change(d, edge.SYMBOL, 5, b'\x02'), 'global FUNC'),
    ('provider_duplicate_symbol', True, duplicate_symbol, 'ambiguous symbol'),
    ('provider_not_executable', True, lambda d: section_header(d, '.text', 8, struct.pack('<Q', 2)), 'executable'),
    ('non_gpl_export', True, lambda d: section_change(d, '__kflagstab', 0, b'\0'), 'GPL-only'),
    ('namespace_nonempty', True, lambda d: section_change(d, '__ksymtab_strings', 0, b'X'), 'namespace'),
    ('export_bad_name', True, lambda d: section_change(d, '__ksymtab_strings', 1, b'X'), 'name/namespace'),
    ('export_wrong_relocation', True, lambda d: relocation_change(d, True, 8, struct.pack('<I', 257)), 'PREL32'),
    ('export_wrong_function', True, lambda d: relocation_change(d, True, 12, bytes(4)), 'provider function'),
    ('export_addend', True, lambda d: relocation_change(d, True, 16, struct.pack('<q', 4)), 'provider function'),
    ('export_namespace_relocation', True, lambda d: relocation_change(d, True, 64, struct.pack('<q', 1)), 'namespace'),
    ('export_duplicate_relocation', True, lambda d: relocation_change(d, True, 24, bytes(8)), 'PREL32'),
    ('export_missing', True, lambda d: d.replace(b'__ksymtab\0', b'__goneout\0'), 'section'),
    ('consumer_weak', False, lambda d: symbol_change(d, edge.SYMBOL, 4, b'\x20'), 'strong undefined'),
    ('consumer_defined', False, lambda d: symbol_change(d, edge.SYMBOL, 6, b'\x01\0'), 'strong undefined'),
    ('consumer_hidden', False, lambda d: symbol_change(d, edge.SYMBOL, 5, b'\x02'), 'strong undefined'),
    ('consumer_duplicate_symbol', False, duplicate_symbol, 'ambiguous symbol'),
    ('consumer_not_bl', False, call_instruction_change, 'direct BL'),
    ('consumer_jump26', False, lambda d: relocation_change(d, False, 8, struct.pack('<I', 282)), 'CALL26'),
    ('consumer_call_addend', False, lambda d: relocation_change(d, False, 16, struct.pack('<q', 4)), 'CALL26'),
    ('consumer_call_unaligned', False, lambda d: relocation_change(d, False, 0, struct.pack('<Q', 1)), 'CALL26'),
    ('consumer_wrong_symbol', False, lambda d: relocation_change(d, False, 12, bytes(4)), 'one direct call'),
    ('provider_license', True, lambda d: d.replace(b'license=GPL\0', b'license=MIT\0'), 'license'),
    ('consumer_license', False, lambda d: d.replace(b'license=GPL\0', b'license=MIT\0'), 'license'),
    ('modinfo_duplicate', True, duplicate_modinfo, 'license mismatch/duplicate'),
    ('consumer_dependency', False, lambda d: d.replace(b'depends=rog5-s12-ufs-vote', b'depends=rog5-s12-ufs-fake'), 'depends'),
    ('provider_identity', True, lambda d: d.replace(b'name=rog5_s12_ufs_vote', b'name=rog5_s12_ufs_fake'), 'name'),
    ('vermagic_token', False, lambda d: d.replace(b'SMP preempt', b'SMP zzzzzzz'), 'vermagic'),
    ('btf_unsigned', True, lambda d: btf_return_change(d, 12, struct.pack('<I', 32)), 'signed int32'),
    ('btf_wide', True, lambda d: btf_return_change(d, 8, struct.pack('<I', 8)), 'signed int32'),
    ('btf_base_magic', True, lambda d: section_change(d, '.BTF.base', 0, b'xx'), 'BTF base'),
    ('btf_split_magic', True, lambda d: section_change(d, '.BTF', 0, b'xx'), 'split BTF'),
    ('btf_wrong_symbol', True, lambda d: section_change(d, '.BTF', edge._section(edge._elf(d), '.BTF').data().index(edge.SYMBOL.encode()), b'X'), 'BTF function'),
    ('btf_missing', True, lambda d: d.replace(b'.BTF\0', b'.BAD\0'), 'section'),
    ('btf_base_missing', True, lambda d: d.replace(b'.BTF.base\0', b'.BAD.base\0'), 'section'),
    ('dwarf_missing', False, lambda d: d.replace(b'.debug_info\0', b'.debug_gone\0'), 'section'),
    ('dwarf_unsigned', False, lambda d: dwarf_change(d, 'DW_AT_encoding', b'\x07'), 'signed int32'),
    ('dwarf_wide', False, lambda d: dwarf_change(d, 'DW_AT_byte_size', b'\x08'), 'signed int32'),
    ('dwarf_wrong_return', False, lambda d: dwarf_change(d, 'DW_AT_type', bytes(4)), 'metadata|base type'),
]


def add_mutations(cls):
    for name, provider, mutate, message in MUTATIONS:
        def test(self, provider=provider, mutate=mutate, message=message):
            path = edge.PROVIDER if provider else edge.CONSUMER
            members = dict(self.members)
            fields, data = members[path]
            mutated = mutate(data)
            self.assertNotEqual(mutated, data, 'mutation must change artifact')
            fields = list(fields)
            fields[6] = len(mutated)
            members[path] = fields, mutated
            with self.assertRaisesRegex(ValueError, message):
                edge.inspect_edge(members, MAGIC)
        setattr(cls, 'test_mutation_' + name, test)


add_mutations(EdgeTests)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path)
    args, rest = parser.parse_known_args()
    if args.archive:
        blob = args.archive.read_bytes()
        if hashlib.sha256(blob).hexdigest() != ARCHIVE_SHA256:
            parser.error('archive SHA-256 mismatch')
        spec = importlib.util.spec_from_file_location(
            'composition', Path(__file__).with_name('check-release-composition.py'))
        composition = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(composition)
        real = composition.target_members(blob)

        class SealedTests(unittest.TestCase):
            members = real
            check_valid = EdgeTests.check_valid

            def test_exact_sealed_pair(self):
                report = self.check_valid(self.members)
                self.assertEqual(tuple(report[role]['sha256'] for role in ('provider', 'consumer')), REAL_HASHES)

        add_mutations(SealedTests)
    unittest.main(argv=[sys.argv[0], *rest])

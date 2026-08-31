#!/usr/bin/env python3
"""Exercise the exact vote decision without hardware or a kernel load."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / 'tools/s12_ufs_vote/rog5-s12-ufs-vote.c'

def function(text, name):
    start = text.index('static int ' + name + '(')
    body = text.index('{', start)
    depth = 1
    end = body + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]

class S12VoteTest(unittest.TestCase):
    def test_mainline_auto_pair_rejected_before_regulator_acquisition(self):
        text = SOURCE.read_text()
        body = function(text, 'modes_allowed')
        stub = '''#include <assert.h>
#define RPMH_REGULATOR_MODE_RET 0
#define RPMH_REGULATOR_MODE_AUTO 2
'''
        main = '''int main(void) {
 for (unsigned int first=0; first<5; first++)
  for (unsigned int second=0; second<5; second++)
   assert(modes_allowed(first,second) == (first==0 && second==2));
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            c = Path(tmp) / 'test.c'; binary = Path(tmp) / 'test'
            c.write_text(stub + body + '\n' + main)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            str(c), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True, timeout=3)
        self.assertLess(text.index('!modes_allowed(modes[0], modes[1])'),
                        text.index('s12 = of_regulator_get_optional('))

    def test_mode_and_held_enable_are_distinct_and_fail_closed(self):
        body = function(SOURCE.read_text(), 'apply_active_vote')
        stub = r'''
#include <assert.h>
#include <stdbool.h>
#include <errno.h>
#define REGULATOR_MODE_NORMAL 2
#define THIS_MODULE ((void *)1)
#define pr_info(...) ((void)0)
static void *s12;
enum vote_action { QUERY, MODE, HELD_ENABLE };
static enum vote_action selected_action;
static bool holding;
static int mode, mode_error, enable_error, mode_calls, enable_calls, pins, suppress;
static unsigned int regulator_get_mode(void *r) { (void)r; return mode; }
static int regulator_set_mode(void *r, unsigned int value) {
 (void)r; assert(value == REGULATOR_MODE_NORMAL); mode_calls++;
 if (!mode_error && !suppress) mode = value;
 return mode_error;
}
static int regulator_enable(void *r) {
 (void)r; assert(mode == REGULATOR_MODE_NORMAL); enable_calls++;
 return enable_error;
}
static void __module_get(void *m) { assert(m == THIS_MODULE); pins++; }
'''
        cases = [
            (0, 8, 0, 0, 0, 0, 0, 0, 0),
            (1, 8, 0, 0, 0, 0, 1, 0, 0),
            (1, 2, 0, 0, 0, 0, 1, 0, 0),
            (1, 8, -110, 0, 0, -110, 1, 0, 0),
            (1, 8, 0, 0, 1, -5, 1, 0, 0),
            (2, 8, 0, 0, 0, -1, 0, 0, 0),
            (2, 2, 0, 0, 0, 0, 0, 1, 1),
            (2, 2, 0, -110, 0, -110, 0, 1, 0),
        ]
        main = 'int main(void) {\n'
        for operation, initial, me, ee, sup, ret, mc, ec, pin in cases:
            main += (f'selected_action={operation}; holding=false; mode={initial}; '
                     f'mode_error={me}; enable_error={ee}; suppress={sup}; '
                     'mode_calls=enable_calls=pins=0; '
                     f'assert(apply_active_vote()=={ret}); '
                     f'assert(mode_calls=={mc} && enable_calls=={ec} && pins=={pin}); '
                     f'assert(holding=={pin});\n')
        main += 'return 0; }\n'
        with tempfile.TemporaryDirectory() as tmp:
            c = Path(tmp) / 'test.c'; binary = Path(tmp) / 'test'
            c.write_text(stub + body + '\n' + main)
            subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                            str(c), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True, timeout=3)

    def test_control_surface_and_identity_are_fixed(self):
        text = SOURCE.read_text()
        for forbidden in (r'\bregulator_disable\s*\(', r'\bregulator_set_voltage\s*\(',
                          r'\brpmh_write\s*\(', r'\bioremap\s*\(', r'\bwritel\s*\('):
            self.assertNotRegex(text, forbidden)
        self.assertIn('module_param(action, charp, 0400)', text)
        self.assertIn('of_machine_is_compatible("asus,rog-phone5")', text)
        self.assertIn('supply != rail', text)
        self.assertIn('cmd_db_read_addr("smpb12") != 0x40100', text)
        self.assertIn('!modes_allowed(modes[0], modes[1])', text)
        self.assertIn('minimum != 1350000 || maximum != 1352000', text)
        self.assertIn('of_regulator_get_optional(&consumer->dev, pmu, "vddpmu")', text)
        self.assertIn('device_trylock(&consumer->dev)', text)
        self.assertIn('if (consumer->dev.driver)', text)
        self.assertIn('regulator-always-on', text)
        cleanup = text.split('static void __exit s12_vote_exit(void)', 1)[1]
        self.assertIn('if (holding)', cleanup)
        self.assertNotIn('regulator_put(', cleanup)
        self.assertNotIn('regulator_set_mode(', cleanup)
        self.assertNotIn('module_put(', cleanup)

if __name__ == '__main__':
    unittest.main()

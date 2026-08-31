#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest

R=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('bindings',R/'scripts/host/check-controller-bindings.py')
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)


class ControllerBindings(unittest.TestCase):
    def test_actual_collision_shape_fails_only_in_combined_namespace(self):
        callback='def gate_events():\n    return [{"event":"USB_DATA_DISABLED"}]\n'
        preflight='gate_events=[{"event":"USB_GATE_WAITING"}]\n'
        tail='result=gate_events()\n'
        source=callback+preflight+tail
        self.assertIn('gate_events',checker.conflicts(source)[0])
        with self.assertRaises(TypeError):exec(source,{})
        fixed=callback+preflight.replace('gate_events=','gate_preflight_events=')+tail
        namespace={};exec(fixed,namespace)
        self.assertEqual(namespace['result'],[{'event':'USB_DATA_DISABLED'}])
        self.assertEqual(checker.conflicts(fixed),[])

    def test_module_control_flow_bindings_and_imports_are_checked(self):
        samples=['def f(): pass\nif True:\n f=[]\n',
            'def f(): pass\nfor f in [1]: pass\n',
            'def f(): pass\nwith open("fixture") as f: pass\n',
            'def f(): pass\ntry: pass\nexcept Exception as f: pass\n',
            'import json\njson=[]\n','sha=lambda x:x\nsha=[]\n']
        for source in samples:
            with self.subTest(source=source):self.assertTrue(checker.conflicts(source))

    def test_locals_and_attribute_writes_do_not_rebind_module_functions(self):
        source='import json\ndef f():\n return []\ndef g():\n f=1\n return f\njson.decoder=f\n'
        self.assertEqual(checker.conflicts(source),[])


if __name__=='__main__':unittest.main()

#!/usr/bin/env python3
"""Offline test of scripts/host/rog5-brightness-lab.py's local web API with a
fake phone (no SSH): only same-origin requests with the run's token and a
JSON body may change anything (audit 2026-10-02, 04-host-rest: a foreign
page's text/plain POST changed the brightness), and each lab run gets its
own SSH control directory."""
from __future__ import annotations

import http.client
import importlib.machinery
import importlib.util
import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
loader = importlib.machinery.SourceFileLoader('brightness_lab', str(REPO / 'scripts/host/rog5-brightness-lab.py'))
LAB = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
loader.exec_module(LAB)


class FakePhone:
    def __init__(self):
        self.values = []

    def state(self):
        return {'brightness': self.values[-1] if self.values else 0}

    def set_brightness(self, value):
        self.values.append(value)


class Api(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.phone = FakePhone()
        cls.srv = ThreadingHTTPServer(('127.0.0.1', 0), None)
        cls.port = cls.srv.server_address[1]
        cls.srv.RequestHandlerClass = LAB.make_handler(cls.phone, cls.port)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def post(self, headers, body=b'{"value": 77}'):
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        h = {'Host': f'127.0.0.1:{self.port}', 'Content-Type': 'application/json', 'X-ROG5-Token': LAB.TOKEN}
        h.update(headers)
        c.request('POST', '/api/brightness', body=body, headers={k: v for k, v in h.items() if v is not None})
        r = c.getresponse()
        return r.status, r.read()

    def test_same_origin_with_token_works(self):
        before = len(self.phone.values)
        status, _ = self.post({'Origin': f'http://127.0.0.1:{self.port}'})
        self.assertEqual(status, 200)
        self.assertEqual(len(self.phone.values), before + 1)

    def test_foreign_requests_change_nothing(self):
        before = len(self.phone.values)
        for headers in ({'Origin': 'https://evil.example'},
                        {'Content-Type': 'text/plain'},
                        {'X-ROG5-Token': None},
                        {'X-ROG5-Token': 'wrong'},
                        {'Host': f'evil.example:{self.port}'}):
            status, _ = self.post(headers)
            self.assertEqual(status, 403, headers)
        self.assertEqual(len(self.phone.values), before)

    def test_page_carries_the_token_and_state_needs_it(self):
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        c.request('GET', '/')
        page = c.getresponse().read().decode()
        self.assertIn(LAB.TOKEN, page)
        self.assertNotIn('@TOKEN@', page)
        c.request('GET', '/api/state')
        r = c.getresponse()
        r.read()
        self.assertEqual(r.status, 403)

    def test_private_control_directory_per_run(self):
        a, b = LAB.Phone('10.0.0.1'), LAB.Phone('10.0.0.2')
        try:
            self.assertNotEqual(a.control_dir, b.control_dir)
            self.assertEqual(os.stat(a.control_dir).st_mode & 0o777, 0o700)
            self.assertTrue(a.control.endswith('/%C'))
        finally:
            os.rmdir(a.control_dir)
            os.rmdir(b.control_dir)


if __name__ == '__main__':
    unittest.main()

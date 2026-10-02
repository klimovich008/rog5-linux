#!/usr/bin/env python3
"""Offline test of scripts/host/rog5-brightness-lab.py's local web API with a
fake phone (no SSH): only same-origin requests with the run's token and a
JSON body may change anything (audit 2026-10-02, 04-host-rest: a foreign
page's text/plain POST changed the brightness), and each lab run gets its
own SSH control directory."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import io
import unittest
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
        cls.port = 8765
        cls.handler = LAB.make_handler(cls.phone, cls.port)

    def request(self, method, path, headers=None, body=b''):
        # Feed a real HTTP request through BaseHTTPRequestHandler using an
        # in-memory socket. Security parsing is exercised without a listener.
        h = {'Host': f'127.0.0.1:{self.port}', 'Content-Length': str(len(body))}
        h.update(headers or {})
        request = (f'{method} {path} HTTP/1.0\r\n' + ''.join(
            f'{k}: {v}\r\n' for k, v in h.items() if v is not None) + '\r\n').encode() + body
        class Socket:
            def __init__(self):
                self.output = bytearray()
            def makefile(self, *args):
                return io.BytesIO(request)
            def sendall(self, data):
                self.output.extend(data)
        sock = Socket()
        self.handler(sock, ('127.0.0.1', 1), object())
        head, body = bytes(sock.output).split(b'\r\n\r\n', 1)
        return int(head.split()[1]), body

    def post(self, headers, body=b'{"value": 77}'):
        h = {'Content-Type': 'application/json', 'X-ROG5-Token': LAB.TOKEN}
        h.update(headers)
        return self.request('POST', '/api/brightness', h, body)

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
        status, page = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn(LAB.TOKEN, page.decode())
        self.assertNotIn('@TOKEN@', page.decode())
        self.assertEqual(self.request('GET', '/api/state')[0], 403)

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

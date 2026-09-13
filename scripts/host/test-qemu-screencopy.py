#!/usr/bin/env python3
"""Compile and exercise the screencopy client's actual event/pixel functions.

The mandatory Unix Wayland mock uses the real libwayland adapter, built by
default or explicitly supplied with ROG5_SCREENCOPY_CLIENT. VM captures remain
separate evidence, never phone qualification.
"""
import ctypes
import array
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import socket
import tempfile
import threading
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]


class Pixels(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint32) for name in
                ("format", "width", "height", "stride", "flags")] + [
        (name, ctypes.c_int) for name in
        ("offered", "flags_seen", "copying", "ready", "failed")]


class ScreencopyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which(os.environ.get("CC", "cc"))
        if not compiler:
            raise RuntimeError("BLOCKED: C compiler required")
        cls.scratch = tempfile.TemporaryDirectory(prefix="rog5-screencopy-")
        cls.addClassCleanup(cls.scratch.cleanup)
        library = Path(cls.scratch.name) / "capture.so"
        subprocess.run([compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                        "-O2", "-fPIC", "-shared", "-DSCREENCOPY_TEST",
                        str(ROOT / "tools/qemu-virtio-drm/screencopy.c"),
                        "-o", str(library)], check=True, timeout=20)
        cls.lib = ctypes.CDLL(str(library))
        pointer = ctypes.POINTER(Pixels)
        cls.lib.capture_offer.argtypes = [pointer] + [ctypes.c_uint32] * 4
        cls.lib.capture_flags.argtypes = [pointer, ctypes.c_uint32]
        cls.lib.capture_ready.argtypes = [pointer, ctypes.c_uint32]
        cls.lib.capture_write_ppm.argtypes = [pointer, ctypes.c_void_p, ctypes.c_int]

    def offered(self, fmt=1, width=2, height=2, stride=12):
        p = Pixels()
        self.assertEqual(self.lib.capture_offer(ctypes.byref(p), fmt, width, height, stride), 0)
        return p

    def ready(self, p, flags=0):
        p.copying = 1
        self.assertEqual(self.lib.capture_flags(ctypes.byref(p), flags), 0)
        self.assertEqual(self.lib.capture_ready(ctypes.byref(p), 999999999), 0)

    def write(self, p, raw):
        data = ctypes.create_string_buffer(raw)
        with tempfile.TemporaryFile() as file:
            result = self.lib.capture_write_ppm(ctypes.byref(p), data, file.fileno())
            file.seek(0)
            return result, file.read()

    def test_native_word_channels_stride_and_alpha(self):
        raw = struct.pack("=6I", 0x80123456, 0xABFEDCBA, 0xFFFFFFFF,
                          0xFF010203, 0x007F00FF, 0xFFFFFFFF)
        for fmt in (0, 1):
            with self.subTest(fmt=fmt):
                p = self.offered(fmt)
                self.ready(p)
                self.assertEqual(self.write(p, raw),
                                 (0, b"P6\n2 2\n255\n\x12\x34\x56\xfe\xdc\xba\x01\x02\x03\x7f\x00\xff"))

    def test_y_invert_only_changes_row_order(self):
        p = self.offered()
        self.ready(p, 1)
        raw = struct.pack("=6I", 0x112233, 0x445566, 0, 0x778899, 0xAABBCC, 0)
        self.assertEqual(self.write(p, raw),
                         (0, b"P6\n2 2\n255\n\x77\x88\x99\xaa\xbb\xcc\x11\x22\x33\x44\x55\x66"))

    def test_dimension_stride_format_and_memory_limits(self):
        invalid = [(1, 0, 1, 4), (1, 1, 0, 4), (1, 541, 1, 2164),
                   (1, 1, 1225, 4), (1, 2, 2, 4), (1, 1, 1, 5),
                   (2, 1, 1, 4), (0x34325258, 1, 1, 4),
                   (1, 1, 1224, 0xFFFFFFFC), (1, 1, 1, 8388612)]
        for values in invalid:
            with self.subTest(values=values):
                p = Pixels()
                self.assertEqual(self.lib.capture_offer(ctypes.byref(p), *values), -1)
                self.assertEqual(p.failed, 1)
        self.offered(width=540, height=1224, stride=2160)
        self.offered(width=1, height=1, stride=8388608)

    def test_duplicate_offer_fails_without_replacing_metadata(self):
        p = self.offered()
        self.assertEqual(self.lib.capture_offer(ctypes.byref(p), 0, 1, 1, 4), -1)
        self.assertEqual((p.width, p.height, p.stride, p.failed), (2, 2, 12, 1))

    def test_ready_requires_copy_and_flags(self):
        for copying in (0, 1):
            p = self.offered()
            p.copying = copying
            self.assertEqual(self.lib.capture_ready(ctypes.byref(p), 0), -1)
            self.assertFalse(p.ready)

    def test_flags_reject_unknown_duplicate_and_wrong_order(self):
        for mode in ("not-copying", "unknown", "duplicate", "after-ready", "failed"):
            with self.subTest(mode=mode):
                p = self.offered()
                p.copying = mode != "not-copying"
                flags = 2 if mode == "unknown" else 0
                if mode in ("duplicate", "after-ready"):
                    self.assertEqual(self.lib.capture_flags(ctypes.byref(p), 0), 0)
                if mode == "after-ready":
                    self.assertEqual(self.lib.capture_ready(ctypes.byref(p), 0), 0)
                if mode == "failed":
                    p.failed = 1
                self.assertEqual(self.lib.capture_flags(ctypes.byref(p), flags), -1)

    def test_bad_timestamp_duplicate_ready_and_failure_are_terminal(self):
        p = self.offered()
        p.copying = 1
        self.lib.capture_flags(ctypes.byref(p), 0)
        self.assertEqual(self.lib.capture_ready(ctypes.byref(p), 1000000000), -1)
        self.assertEqual(self.lib.capture_ready(ctypes.byref(p), 0), -1)
        p = self.offered()
        self.ready(p)
        self.assertEqual(self.lib.capture_ready(ctypes.byref(p), 0), -1)
        self.assertEqual(self.write(p, bytes(24)), (-1, b""))

    def test_no_pixel_output_before_ready_or_after_failure(self):
        p = self.offered()
        self.assertEqual(self.write(p, bytes(24)), (-1, b""))
        self.ready(p)
        p.failed = 1
        self.assertEqual(self.write(p, bytes(24)), (-1, b""))

    def test_write_failure_is_reported(self):
        p = self.offered()
        self.ready(p)
        data = ctypes.create_string_buffer(bytes(24))
        self.assertEqual(self.lib.capture_write_ppm(ctypes.byref(p), data, -1), -1)
        with open("/dev/full", "wb", buffering=0) as full:
            self.assertEqual(self.lib.capture_write_ppm(ctypes.byref(p), data, full.fileno()), -1)


class BuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        specification = importlib.util.spec_from_file_location(
            "capture_builder", ROOT / "scripts/host/build-qemu-screencopy.py")
        cls.builder = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(cls.builder)

    def test_existing_output_refused_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "preserve"
            marker.write_text("historical")
            with self.assertRaises(FileExistsError):
                self.builder.build(Path(directory))
            self.assertEqual(list(Path(directory).iterdir()), [marker])
            self.assertEqual(marker.read_text(), "historical")

    def test_missing_compiler_records_blocked_and_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new"
            with mock.patch.dict(os.environ, {"CC": "/nonexistent/rog5-compiler"}), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(self.builder.build(output), 2)
            report = json.loads((output / "provenance.json").read_text())
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["outputs"], {})
            self.assertEqual(report["exit_status"], 2)

    def test_modified_xml_fails_before_tool_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            xml = Path(directory) / "altered.xml"
            xml.write_text("unreviewed protocol")
            output = Path(directory) / "new"
            with mock.patch.object(self.builder, "XML", xml), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(self.builder.build(output), 1)
            report = json.loads((output / "provenance.json").read_text())
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["commands"], [])
            self.assertIn("identity mismatch", report["error"])


class TransportTests(unittest.TestCase):
    """A real Unix Wayland peer exercises the compiled libwayland client."""

    @classmethod
    def setUpClass(cls):
        supplied = os.environ.get("ROG5_SCREENCOPY_CLIENT")
        if supplied:
            cls.client = str(Path(supplied).resolve(strict=True))
        else:
            cls.scratch = tempfile.TemporaryDirectory(prefix="rog5-client-build-")
            cls.addClassCleanup(cls.scratch.cleanup)
            output = Path(cls.scratch.name) / "client"
            result = subprocess.run([os.environ.get("PYTHON", "python3"),
                                     str(ROOT / "scripts/host/build-qemu-screencopy.py"),
                                     "--output", str(output)],
                                    capture_output=True, text=True, timeout=60)
            if result.returncode:
                raise RuntimeError("mandatory transport client build failed/blocked:\n" +
                                   result.stdout[-8192:] + result.stderr[-8192:])
            cls.client = str(output / "screencopy")

    def run_capture(self, mode="success", existing=False):
        with tempfile.TemporaryDirectory(prefix="rog5-wayland-") as directory:
            path = Path(directory)
            output = path / "capture.ppm"
            if existing:
                output.write_bytes(b"preserve")
            listener = socket.socket(socket.AF_UNIX)
            listener.bind(str(path / "wayland-test"))
            listener.listen(1)
            listener.settimeout(7)
            errors = []

            def server():
                descriptors = []
                try:
                    with listener.accept()[0] as peer:
                        peer.settimeout(7)
                        if mode == "disconnect":
                            return
                        if mode == "stall":
                            while peer.recv(4096):
                                pass
                            return
                        ids = {1: "display"}
                        pending = bytearray()

                        def send(object_id, opcode, payload):
                            peer.sendall(struct.pack("=II", object_id,
                                                     ((8 + len(payload)) << 16) | opcode) + payload)

                        def string(value):
                            value = value.encode() + b"\0"
                            return struct.pack("=I", len(value)) + value + bytes(-len(value) % 4)

                        while True:
                            while len(pending) < 8 or len(pending) < (struct.unpack_from("=I", pending, 4)[0] >> 16):
                                data, control, _, _ = peer.recvmsg(4096, socket.CMSG_SPACE(16))
                                if not data:
                                    return
                                pending.extend(data)
                                for level, kind, payload in control:
                                    if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                                        fds = array.array("i")
                                        fds.frombytes(payload[:len(payload) - len(payload) % fds.itemsize])
                                        descriptors.extend(fds)
                            object_id, word = struct.unpack_from("=II", pending)
                            size, opcode = word >> 16, word & 65535
                            payload = bytes(pending[8:size])
                            del pending[:size]
                            kind = ids.get(object_id)
                            if kind == "display" and opcode == 1:
                                registry, = struct.unpack("=I", payload)
                                ids[registry] = "registry"
                                names = [(1, "wl_output", 1), (2, "wl_shm", 1)]
                                if mode != "missing-manager":
                                    version = int(mode[-1]) if mode.startswith("legacy-v") else 3
                                    names.append((3, "zwlr_screencopy_manager_v1", version))
                                if mode == "multiple-outputs":
                                    names.append((4, "wl_output", 1))
                                for name, interface, version in names:
                                    send(registry, 0, struct.pack("=I", name) + string(interface) + struct.pack("=I", version))
                            elif kind == "display" and opcode == 0:
                                callback, = struct.unpack("=I", payload)
                                send(callback, 0, struct.pack("=I", 1))
                                send(1, 1, struct.pack("=I", callback))
                            elif kind == "registry" and opcode == 0:
                                length, = struct.unpack_from("=I", payload, 4)
                                interface = payload[8:8 + length - 1].decode()
                                new_id, = struct.unpack_from("=I", payload, 8 + ((length + 3) & ~3) + 4)
                                ids[new_id] = interface
                            elif kind == "zwlr_screencopy_manager_v1" and opcode == 0:
                                frame, = struct.unpack_from("=I", payload)
                                ids[frame] = "frame"
                                if mode == "failed-event":
                                    send(frame, 3, b"")
                                else:
                                    send(frame, 0, struct.pack("=IIII", 1, 2, 2, 12))
                                    if not mode.startswith("legacy-v"):
                                        send(frame, 6, b"")
                            elif kind == "wl_shm" and opcode == 0:
                                pool, size = struct.unpack("=II", payload)
                                ids[pool] = "pool"
                                if size != 24 or len(descriptors) != 1:
                                    raise AssertionError("unexpected shared-memory allocation")
                            elif kind == "pool" and opcode == 0:
                                new_id, offset, width, height, stride, fmt = struct.unpack("=6I", payload)
                                if (offset, width, height, stride, fmt) != (0, 2, 2, 12, 1):
                                    raise AssertionError("incorrect buffer contract")
                                ids[new_id] = "buffer"
                            elif kind == "frame" and opcode == 0:
                                os.pwrite(descriptors[0], struct.pack("=6I", 0x112233, 0x445566, 0,
                                                                    0x778899, 0xAABBCC, 0), 0)
                                send(object_id, 1, struct.pack("=I", 1))
                                send(object_id, 2, struct.pack("=III", 0, 42, 123))
                except (BrokenPipeError, ConnectionResetError):
                    pass
                except BaseException as error:
                    errors.append(error)
                finally:
                    for fd in descriptors:
                        os.close(fd)

            thread = threading.Thread(target=server, daemon=True)
            thread.start()
            try:
                env = dict(os.environ, XDG_RUNTIME_DIR=directory, WAYLAND_DISPLAY="wayland-test")
                env.pop("WAYLAND_SOCKET", None)
                result = subprocess.run([self.client, str(output)], env=env, capture_output=True, timeout=7)
                thread.join(timeout=1)
                self.assertFalse(thread.is_alive(), "mock peer outlived client")
                self.assertEqual(errors, [])
                return result, output.read_bytes() if output.exists() else None
            finally:
                listener.close()

    def test_real_shm_copy_and_y_invert(self):
        result, data = self.run_capture()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(data, b"P6\n2 2\n255\n\x77\x88\x99\xaa\xbb\xcc\x11\x22\x33\x44\x55\x66")
        self.assertIn(b'"status":"PASS"', result.stdout)

    def test_existing_output_is_preserved(self):
        result, data = self.run_capture(existing=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(data, b"preserve")
        self.assertNotIn(b'"PASS"', result.stdout)

    def test_v1_v2_copy_without_buffer_done(self):
        for mode in ("legacy-v1", "legacy-v2"):
            with self.subTest(mode=mode):
                result, data = self.run_capture(mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(data, b"P6\n2 2\n255\n\x77\x88\x99\xaa\xbb\xcc\x11\x22\x33\x44\x55\x66")

    def test_missing_manager_multiple_outputs_and_failed_event(self):
        for mode in ("missing-manager", "multiple-outputs", "failed-event", "disconnect"):
            with self.subTest(mode=mode):
                result, data = self.run_capture(mode)
                self.assertNotEqual(result.returncode, 0)
                self.assertIsNone(data)
                self.assertNotIn(b'"PASS"', result.stdout)

    def test_stalled_server_has_hard_deadline(self):
        result, data = self.run_capture("stall")
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(data)
        self.assertNotIn(b'"PASS"', result.stdout)

if __name__ == "__main__":
    unittest.main()

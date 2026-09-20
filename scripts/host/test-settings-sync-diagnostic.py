#!/usr/bin/env python3
"""Exercise the actual VM interposer with controlled callees; real GLib is qualified separately."""
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'tools/qemu-virtio-drm/settings-sync-diagnostic.c'


class SettingsSyncDiagnostic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build_temp = tempfile.TemporaryDirectory(prefix='rog5-settings-build-')
        cls.addClassCleanup(cls.build_temp.cleanup)
        cls.build = Path(cls.build_temp.name)
        cls.probe = cls.build / 'probe.so'
        cls.without_unref = cls.build / 'without-unref.so'
        fake = cls.build / 'fake.c'
        fake.write_text('''#include <errno.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
int calls, bad_errno;
char fixture_application, fixture_other;
int unrefs, unref_bad;
void g_object_unref(void *object) {
    if (errno != EBUSY) unref_bad++;
    if (object != &fixture_application && object != &fixture_other) unref_bad++;
    unrefs++;
    if (getenv("FIXTURE_UNREF_BLOCK") && object == &fixture_application && unrefs > 2)
        for (;;) pause();
    errno = EILSEQ;
}
void g_settings_sync(void) {
    if (errno != E2BIG) bad_errno++;
    calls++;
    if (getenv("FIXTURE_BLOCK")) for (;;) pause();
    errno = EDOM;
}
static void (*handlers[2])(void *, void *);
int application_calls, connections, disconnects, app_bad;
unsigned long g_signal_connect_data(void *app, const char *signal,
        void (*handler)(void), void *data, void (*destroy)(void *, void *), int flags) {
    if (app != &fixture_application || strcmp(signal, "shutdown") || data || destroy ||
        flags != connections || connections > 1) { app_bad++; return 0; }
    handlers[connections++] = (void (*)(void *, void *))handler;
    return (unsigned long)connections;
}
void g_signal_handler_disconnect(void *app, unsigned long id) {
    if (app != &fixture_application || id != (unsigned long)disconnects+1) app_bad++;
    disconnects++;
    const char *block = getenv("FIXTURE_DISCONNECT_BLOCK");
    if (block && atoi(block) == disconnects) for (;;) pause();
    errno = EFAULT;
}
int g_application_run(void *app, int argc, char **argv) {
    const char *block = getenv("FIXTURE_APP_BLOCK");
    if (app != &fixture_application || argc != 2 || strcmp(argv[1], "app")) app_bad++;
    if (errno != E2BIG) app_bad++;
    application_calls++;
    if (handlers[0]) handlers[0](app, NULL);
    if (errno != E2BIG) app_bad++;
    if (block && !strcmp(block, "during")) for (;;) pause();
    g_settings_sync();
    if (handlers[1]) handlers[1](app, NULL);
    if (errno != EDOM) app_bad++;
    if (block && !strcmp(block, "after")) for (;;) pause();
    errno = ERANGE;
    return 37;
}
''')
        caller = cls.build / 'caller.c'
        caller.write_text('''#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>
extern void g_settings_sync(void);
extern int calls, bad_errno;
int main(int argc, char **argv) {
    int count = argc > 1 ? atoi(argv[1]) : 1;
    for (int i = 0; i < count; i++) {
        errno = E2BIG;
        g_settings_sync();
        if (errno != EDOM) return 21;
    }
    if (calls != count) return 22;
    if (bad_errno) return 23;
    const char *child = getenv("FIXTURE_EXEC_CHILD");
    if (child) {
        pid_t pid = fork();
        int status;
        if (pid < 0) return 26;
        if (pid == 0) { execl(child, child, (char *)0); _exit(27); }
        if (waitpid(pid, &status, 0) != pid || !WIFEXITED(status)) return 28;
        return WEXITSTATUS(status);
    }
    return 0;
}
''')
        app = cls.build / 'application.c'
        app.write_text('''#include <errno.h>
#include <stdlib.h>
#include <unistd.h>
extern int g_application_run(void *, int, char **);
extern int application_calls, connections, disconnects, app_bad;
extern char fixture_application, fixture_other;
extern int unrefs, unref_bad;
extern void g_object_unref(void *);
static int unref_checked(void *object) {
    errno = EBUSY;
    g_object_unref(object);
    return errno != EILSEQ;
}
int main(int argc, char **argv) {
    if (unref_checked(&fixture_application) || unref_checked(&fixture_other)) return 32;
    errno = E2BIG;
    int result = g_application_run(&fixture_application, argc, argv);
    if (result != 37 || errno != ERANGE) return 30;
    if (application_calls != 1 || connections != 2 || disconnects != 2 || app_bad) return 31;
    if (unref_checked(&fixture_other) || unref_checked(&fixture_application) ||
        unref_checked(&fixture_application)) return 33;
    if (unrefs != 5 || unref_bad) return 34;
    if (getenv("FIXTURE_FINALIZE_BLOCK")) for (;;) pause();
    return 0;
}
''')
        empty = cls.build / 'empty.c'
        empty.write_text('''#include <stdlib.h>
int main(void) {
    if (getenv("LD_PRELOAD")) return 24;
    if (getenv("ROG5_SETTINGS_SYNC_LOG")) return 25;
    return 0;
}
''')
        commands = [
            ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared',
             str(SOURCE), '-o', str(cls.probe), '-ldl', '-pthread'],
            ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared',
             '-DROG5_NO_UNREF_PROBE', str(SOURCE), '-o', str(cls.without_unref),
             '-ldl', '-pthread'],
            ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared',
             str(fake), '-o', str(cls.build / 'libfake.so')],
            ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', str(caller),
             '-L' + str(cls.build), '-Wl,-rpath,' + str(cls.build), '-lfake',
             '-o', str(cls.build / 'caller')],
            ['cc', '-Wall', '-Wextra', '-Werror', str(app),
             '-L' + str(cls.build), '-Wl,-rpath,' + str(cls.build), '-lfake',
             '-o', str(cls.build / 'application')],
            ['cc', '-Wall', '-Wextra', '-Werror', str(empty),
             '-o', str(cls.build / 'empty')],
        ]
        for command in commands:
            subprocess.run(command, check=True, capture_output=True, timeout=15)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rog5-settings-log-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / 'sync.log'
        self.log.touch(mode=0o600)
        self.env = dict(os.environ, LD_PRELOAD=str(self.probe),
                        ROG5_SETTINGS_SYNC_LOG=str(self.log))

    def run_caller(self, count=1, executable='caller'):
        return subprocess.run([str(self.build / executable), str(count)],
                              env=self.env, capture_output=True, timeout=2)

    def stages(self):
        return [line.split()[1].split('=')[1]
                for line in self.log.read_text().splitlines()]

    def test_real_call_once_and_errno_transparent(self):
        result = self.run_caller()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.stages(), ['loaded', 'BEGIN', 'END'])
        self.assertIn('phase=loaded resolved=true ', self.log.read_text())
        for line in self.log.read_text().splitlines():
            self.assertRegex(line, r'^ROG5_SETTINGS_SYNC phase=\S+ (?:resolved=true )?pid=\d+ '
                             r'clock=CLOCK_MONOTONIC seconds=\d+\.\d{9}$')

    def test_repeated_calls_resolve_only_once(self):
        result = self.run_caller(3)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.stages(), ['loaded'] + ['BEGIN', 'END'] * 3)

    def test_exec_child_does_not_inherit_probe_or_log_environment(self):
        self.env['FIXTURE_EXEC_CHILD'] = str(self.build / 'empty')
        result = self.run_caller()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.stages(), ['loaded', 'BEGIN', 'END'])

    def test_application_shutdown_order_and_return_errno(self):
        result = self.run_caller('app', executable='application')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.stages(), ['loaded', 'APP_RUN_BEGIN', 'SHUTDOWN_BEFORE',
                                        'BEGIN', 'END', 'SHUTDOWN_AFTER', 'APP_RUN_END',
                                        'APP_DISCONNECT_ONE_END', 'APP_OBSERVERS_REMOVED',
                                        'APP_UNREF_BEGIN', 'APP_UNREF_END', 'DSO_FINI'])
        self.assertLessEqual(self.log.stat().st_size, 1536)

    def test_no_unref_control_preserves_lifecycle_and_forwarding(self):
        symbols = subprocess.check_output(['nm', '-D', '--defined-only',
                                          str(self.without_unref)], text=True, timeout=2)
        exports = {line.split()[-1] for line in symbols.splitlines()}
        self.assertNotIn('g_object_unref', exports)
        self.assertTrue({'g_application_run', 'g_settings_sync'} <= exports)
        self.env['LD_PRELOAD'] = str(self.without_unref)
        result = self.run_caller('app', executable='application')
        self.assertEqual(result.returncode, 0, result.stderr)
        # The actual fixture also verifies all five direct unrefs, errno,
        # arguments, signal handlers and the application return value.
        self.assertEqual(self.stages(), ['loaded', 'APP_RUN_BEGIN', 'SHUTDOWN_BEFORE',
                                        'BEGIN', 'END', 'SHUTDOWN_AFTER', 'APP_RUN_END',
                                        'APP_DISCONNECT_ONE_END', 'APP_OBSERVERS_REMOVED',
                                        'DSO_FINI'])
        self.log.write_text('')
        self.env['FIXTURE_EXEC_CHILD'] = str(self.build / 'empty')
        self.assertEqual(self.run_caller().returncode, 0)
        self.assertEqual(self.stages(), ['loaded', 'BEGIN', 'END'])
        self.log.write_text('')
        self.log.chmod(0o644)
        self.assertEqual(self.run_caller().returncode, 125)
        self.assertEqual(self.log.read_bytes(), b'')

    def test_no_unref_control_does_not_claim_blocked_call_completion(self):
        self.env.update(LD_PRELOAD=str(self.without_unref), FIXTURE_UNREF_BLOCK='1')
        expected = ['loaded', 'APP_RUN_BEGIN', 'SHUTDOWN_BEFORE', 'BEGIN', 'END',
                    'SHUTDOWN_AFTER', 'APP_RUN_END', 'APP_DISCONNECT_ONE_END',
                    'APP_OBSERVERS_REMOVED']
        process = subprocess.Popen([str(self.build / 'application'), 'app'], env=self.env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   start_new_session=True)
        try:
            deadline = time.monotonic()+2
            while len(self.stages()) < len(expected) and time.monotonic() < deadline:
                time.sleep(.005)
            self.assertEqual(self.stages(), expected)
            self.assertIsNone(process.poll())
        finally:
            if process.poll() is None: os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=2)
        self.assertEqual(self.stages(), expected)

    def test_interrupted_application_distinguishes_shutdown_and_post_shutdown(self):
        for where, expected in [('during', ['loaded', 'APP_RUN_BEGIN', 'SHUTDOWN_BEFORE']),
                                ('after', ['loaded', 'APP_RUN_BEGIN', 'SHUTDOWN_BEFORE',
                                           'BEGIN', 'END', 'SHUTDOWN_AFTER'])]:
            with self.subTest(where=where):
                self.log.write_text('')
                env = dict(self.env, FIXTURE_APP_BLOCK=where)
                process = subprocess.Popen([str(self.build / 'application'), 'app'], env=env,
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                           start_new_session=True)
                try:
                    deadline = time.monotonic()+2
                    while len(self.stages()) < len(expected) and time.monotonic() < deadline:
                        time.sleep(.005)
                    self.assertEqual(self.stages(), expected)
                    self.assertIsNone(process.poll())
                finally:
                    if process.poll() is None: os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=2)
                self.assertEqual(self.stages(), expected)

    def test_blocked_disconnect_unref_and_finalization_have_no_false_end(self):
        run_end = ['loaded', 'APP_RUN_BEGIN', 'SHUTDOWN_BEFORE', 'BEGIN', 'END',
                   'SHUTDOWN_AFTER', 'APP_RUN_END']
        disconnected = run_end + ['APP_DISCONNECT_ONE_END', 'APP_OBSERVERS_REMOVED']
        for variable, value, expected in [
            ('FIXTURE_DISCONNECT_BLOCK', '1', run_end),
            ('FIXTURE_DISCONNECT_BLOCK', '2', run_end + ['APP_DISCONNECT_ONE_END']),
            ('FIXTURE_UNREF_BLOCK', '1', disconnected + ['APP_UNREF_BEGIN']),
            ('FIXTURE_FINALIZE_BLOCK', '1', disconnected + ['APP_UNREF_BEGIN', 'APP_UNREF_END']),
        ]:
            with self.subTest(variable=variable, value=value):
                self.log.write_text('')
                env = dict(self.env, **{variable: value})
                process = subprocess.Popen([str(self.build / 'application'), 'app'], env=env,
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                           start_new_session=True)
                try:
                    deadline = time.monotonic()+2
                    while len(self.stages()) < len(expected) and time.monotonic() < deadline:
                        time.sleep(.005)
                    self.assertEqual(self.stages(), expected)
                    self.assertIsNone(process.poll())
                finally:
                    if process.poll() is None: os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=2)
                self.assertEqual(self.stages(), expected)

    def test_absent_environment_refused(self):
        del self.env['ROG5_SETTINGS_SYNC_LOG']
        self.assertEqual(self.run_caller().returncode, 125)

    def test_missing_log_is_not_created(self):
        self.log.unlink()
        self.assertEqual(self.run_caller().returncode, 125)
        self.assertFalse(self.log.exists())

    def test_insecure_mode_refused(self):
        self.log.chmod(0o644)
        self.assertEqual(self.run_caller().returncode, 125)
        self.assertEqual(self.log.read_bytes(), b'')

    def test_hardlinked_log_refused(self):
        os.link(self.log, self.root / 'alias')
        self.assertEqual(self.run_caller().returncode, 125)
        self.assertEqual(self.log.read_bytes(), b'')

    def test_symlink_refused(self):
        target = self.root / 'target'
        self.log.rename(target)
        self.log.symlink_to(target)
        self.assertEqual(self.run_caller().returncode, 125)
        self.assertEqual(target.read_bytes(), b'')

    def test_fifo_refused_without_hanging(self):
        self.log.unlink()
        os.mkfifo(self.log, 0o600)
        self.assertEqual(self.run_caller().returncode, 125)
        # With a reader, open succeeds; fstat must still reject the FIFO.
        reader = os.open(self.log, os.O_RDONLY | os.O_NONBLOCK)
        try:
            self.assertEqual(self.run_caller().returncode, 125)
            self.assertEqual(os.read(reader, 256), b'')
        finally:
            os.close(reader)

    def test_directory_refused(self):
        self.env['ROG5_SETTINGS_SYNC_LOG'] = str(self.root)
        self.assertEqual(self.run_caller().returncode, 125)

    def test_unresolved_symbol_explicit_failure(self):
        self.assertEqual(self.run_caller(executable='empty').returncode, 125)
        self.assertEqual(self.stages(), ['resolve-failed'])

    def test_existing_size_limit_refused(self):
        self.log.write_bytes(b'x' * 1536)
        self.assertEqual(self.run_caller().returncode, 125)
        self.assertEqual(self.log.stat().st_size, 1536)

    def test_record_limit_is_explicit_failure(self):
        self.assertEqual(self.run_caller(200).returncode, 125)
        self.assertEqual(len(self.stages()), 12)
        self.assertLess(self.log.stat().st_size, 1536)

    def test_interrupted_real_call_has_begin_without_end(self):
        self.env['FIXTURE_BLOCK'] = '1'
        process = subprocess.Popen([str(self.build / 'caller')], env=self.env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   start_new_session=True)
        try:
            deadline = time.monotonic() + 2
            while 'BEGIN' not in self.stages() and time.monotonic() < deadline:
                time.sleep(0.005)
            self.assertEqual(self.stages(), ['loaded', 'BEGIN'])
            self.assertIsNone(process.poll())
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=2)
        self.assertEqual(process.returncode, -signal.SIGKILL)
        self.assertNotIn('END', self.stages())


if __name__ == '__main__':
    unittest.main()

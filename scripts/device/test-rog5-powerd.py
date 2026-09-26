#!/usr/bin/env python3
"""rog5-powerd against a fake sysfs: profile limits, the socket protocol,
persistence and restoring the full range on stop."""
import os, signal, socket, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
DAEMON = os.path.join(HERE, 'rog5-powerd')
POLICIES = {
    'policy0': [300000, 998400, 1497600, 1804800],
    'policy4': [710400, 1209600, 1766400, 2419200],
    'policy7': [844800, 1305600, 1900800, 2841600],
}
GPU = [315000000, 443000000, 540000000, 840000000]


def put(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as handle:
        handle.write(value)


def get(path):
    with open(path) as handle:
        return int(handle.read())


def check(condition, message):
    if not condition:
        raise SystemExit('FAIL ' + message)


def limits(root):
    out = {}
    for name in POLICIES:
        base = f'{root}/devices/system/cpu/cpufreq/{name}'
        out[name] = (get(base + '/scaling_min_freq'), get(base + '/scaling_max_freq'))
    base = f'{root}/class/devfreq/3d00000.gpu'
    out['gpu'] = (get(base + '/min_freq'), get(base + '/max_freq'))
    return out


def request(path, line):
    for _ in range(100):
        if os.path.exists(path):
            break
        time.sleep(0.05)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(path)
        client.sendall(line.encode() + b'\n')
        return client.recv(64).decode()


def main():
    with tempfile.TemporaryDirectory() as tmp:
        sysfs, run, state = (os.path.join(tmp, name) for name in ('sys', 'run', 'state'))
        for name, freqs in POLICIES.items():
            base = f'{sysfs}/devices/system/cpu/cpufreq/{name}'
            put(base + '/scaling_available_frequencies', ' '.join(map(str, freqs)) + ' \n')
            put(base + '/scaling_min_freq', str(freqs[0]))
            put(base + '/scaling_max_freq', str(freqs[-1]))
        base = f'{sysfs}/class/devfreq/3d00000.gpu'
        put(base + '/available_frequencies', ' '.join(map(str, GPU)))
        put(base + '/min_freq', str(GPU[0]))
        put(base + '/max_freq', str(GPU[-1]))
        put(f'{run}/battery_discharge.tsv', 'keep\n')
        env = dict(os.environ, ROG5_POWERD_SYSFS=sysfs, ROG5_POWERD_RUN=run, ROG5_POWERD_STATE=state)
        sock = os.path.join(run, 'profile.sock')

        daemon = subprocess.Popen([sys.executable, DAEMON], env=env, stderr=subprocess.DEVNULL)
        try:
            check(request(sock, 'power-saver') == 'ok power-save\n', 'alias accepted')
            saved = limits(sysfs)
            check(saved['policy4'] == (710400, 1766400) and saved['policy7'] == (844800, 1900800)
                  and saved['policy0'] == (300000, 1497600) and saved['gpu'] == (315000000, 540000000),
                  f'power-save caps {saved}')
            with open(f'{run}/power_profile.env') as handle:
                check(handle.read() == 'POWER_PROFILE=power-save\n', 'env published')
            check(request(sock, 'performance') == 'ok performance\n', 'performance accepted')
            fast = limits(sysfs)
            check(fast['policy4'] == (1209600, 2419200) and fast['gpu'] == (443000000, 840000000),
                  f'performance floors {fast}')
            check(request(sock, 'turbo').startswith('error'), 'unknown profile refused')
            check(limits(sysfs) == fast, 'unknown profile changes nothing')
        finally:
            daemon.send_signal(signal.SIGTERM)
            daemon.wait(timeout=10)
        restored = limits(sysfs)
        check(all(restored[name] == (freqs[0], freqs[-1]) for name, freqs in POLICIES.items())
              and restored['gpu'] == (GPU[0], GPU[-1]), f'full range on stop {restored}')
        check(not os.path.exists(sock) and not os.path.exists(f'{run}/power_profile.env'), 'socket removed')
        check(os.path.exists(f'{run}/battery_discharge.tsv'), 'other files kept')

        daemon = subprocess.Popen([sys.executable, DAEMON], env=env, stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):
                if os.path.exists(sock):
                    break
                time.sleep(0.05)
            check(limits(sysfs)['policy4'] == (1209600, 2419200), 'choice restored at start')
        finally:
            daemon.send_signal(signal.SIGTERM)
            daemon.wait(timeout=10)
    print('PASS rog5-powerd')


if __name__ == '__main__':
    main()

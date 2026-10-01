#!/usr/bin/python3
"""Speaker protection quick-stop check (run on the phone as root).

Reproduces the 2026-10-01 wedge: the CS35L45 protection firmware missed a
pause when the speaker PCM was opened and closed within ~100 ms, and played
silence from then on (CSPL_TEMPERATURE frozen, every later pause failed).

1. waits until PipeWire has closed hw:0,0 (MultiMedia1);
2. opens and closes hw:0,0 CYCLES times with 10 ms of silence (aplay);
3. plays a TONE_SECONDS tone and samples CSPL_TEMPERATURE and HALO_HEARTBEAT
   of both amplifiers while it plays;
4. reports the kernel log lines of the run (mailbox failures, slow pauses,
   reloads) and PASS when both firmwares ran during the tone and the last
   stop paused them.

The tone is audible (TONE_DB dBFS). Changes no mixer control; the kernel
(0151) may reload a firmware that did not pause.

  speaker-quick-stop-check.py [--cycles 10] [--gap 0.3] [--tone-db -20]
"""
import argparse
import math
import re
import struct
import subprocess
import sys
import time

AMPS = (('RCV', '5-0030'), ('SPK', '5-0031'))
PCM_STATUS = '/proc/asound/card0/pcm0p/sub0/status'
CSPL = 'DSP1 Protection cd '
SYSTEM = 'DSP1 Protection 4fa00 '
INITIAL_TEMPERATURE = 0x00064000
EVENTS = re.compile(r'cs35l45|DSP1 event failed|speaker-quick-stop-check')
APLAY = ['aplay', '-q', '-D', 'hw:0,0', '-t', 'raw', '-f', 'S16_LE', '-r', '48000', '-c', '2']


def kmsg(text):
    with open('/dev/kmsg', 'w') as f:
        f.write(f'speaker-quick-stop-check: {text}\n')


def control(name):
    """BYTES control as a big-endian integer, or None when unreadable."""
    out = subprocess.run(['amixer', '-c0', 'cget', f'name={name}'], capture_output=True, text=True).stdout
    match = re.search(r': values=([0-9a-fx,]+)', out)
    if not match:
        return None
    return int(''.join(b[2:].zfill(2) for b in match.group(1).split(',')), 16)


def snapshot():
    state = {}
    for prefix, _ in AMPS:
        state[prefix] = {
            'temperature': control(f'{prefix} {CSPL}CSPL_TEMPERATURE'),
            'heartbeat': control(f'{prefix} {SYSTEM}HALO_HEARTBEAT'),
            'cspl_state': control(f'{prefix} {CSPL}CSPL_STATE'),
            'cspl_errorno': control(f'{prefix} {CSPL}CSPL_ERRORNO'),
            'fw_mbox_sts': control(f'{prefix} DSP1 Protection f208 STS'),
            'pause_state': control(f'{prefix} DSP1 Protection f206 STATE'),
        }
    return state


def fmt(state):
    return '; '.join(f'{p} ' + ' '.join(f'{k}={v if v is None else hex(v)}' for k, v in s.items())
                     for p, s in state.items())


def pcm_closed():
    try:
        with open(PCM_STATUS) as f:
            return f.read().strip() == 'closed'
    except OSError:
        return False


def wait_closed(seconds):
    deadline = time.monotonic() + seconds
    while not pcm_closed():
        if time.monotonic() > deadline:
            return False
        time.sleep(0.2)
    return True


def tone(seconds, db):
    amplitude = 32767 * 10 ** (db / 20)
    frames = []
    for i in range(int(48000 * seconds)):
        value = int(amplitude * math.sin(2 * math.pi * 440 * i / 48000))
        frames.append(struct.pack('<hh', value, value))
    return b''.join(frames)


def kernel_lines(marker):
    out = subprocess.run(['dmesg'], capture_output=True, text=True).stdout.splitlines()
    begin = max((i for i, line in enumerate(out) if marker in line), default=0)
    return [line for line in out[begin:] if EVENTS.search(line)]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--cycles', type=int, default=10)
    parser.add_argument('--gap', type=float, default=0.3, help='seconds between quick opens')
    parser.add_argument('--tone-seconds', type=float, default=3.0)
    parser.add_argument('--tone-db', type=float, default=-20.0)
    args = parser.parse_args()

    if not wait_closed(30):
        print('FAIL hw:0,0 is in use (PipeWire closes it 5 s after the last sound)')
        return 2
    marker = f'begin {time.time():.0f}'
    kmsg(marker)
    print('before:', fmt(snapshot()))

    silence = bytes(4 * 480)  # 10 ms
    for i in range(args.cycles):
        began = time.monotonic()
        rc = subprocess.run(APLAY, input=silence, capture_output=True).returncode
        print(f'quick open/close {i + 1}: rc {rc}, {1000 * (time.monotonic() - began):.0f} ms')
        time.sleep(args.gap)
    # a firmware the kernel stopped is booted again 0.5 s later (~1 s per amp)
    time.sleep(3)
    print('after quick cycles:', fmt(snapshot()))

    kmsg('tone')
    player = subprocess.Popen(APLAY, stdin=subprocess.PIPE)
    data = tone(args.tone_seconds, args.tone_db)
    early = late = None
    try:
        third = len(data) // 3 // 4 * 4
        player.stdin.write(data[:third])
        player.stdin.flush()
        time.sleep(0.3)
        early = snapshot()
        player.stdin.write(data[third:])
        player.stdin.flush()
        time.sleep(args.tone_seconds / 2)
        late = snapshot()
    finally:
        player.stdin.close()
        player.wait()
    time.sleep(1)
    after = snapshot()
    print('tone early:', fmt(early))
    print('tone late: ', fmt(late))
    print('after tone:', fmt(after))

    lines = kernel_lines(marker)
    print('kernel log since the start:')
    for line in lines:
        print('  ' + line)

    ok = True
    tone_lines = lines[next((i for i, line in enumerate(lines) if 'speaker-quick-stop-check: tone' in line), 0):]
    for prefix, device in AMPS:
        e, l, a = early[prefix], late[prefix], after[prefix]
        moved = None not in (e['temperature'], l['temperature']) and e['temperature'] != l['temperature']
        beat = None not in (e['heartbeat'], l['heartbeat']) and e['heartbeat'] != l['heartbeat']
        frozen = l['temperature'] == INITIAL_TEMPERATURE
        failed = [line for line in tone_lines if f'{device}: Failed to set mailbox cmd' in line
                  or f'{device}: Protection firmware did not pause' in line or f'{prefix} DSP1 event failed' in line]
        verdict = (moved or beat) and not frozen and not failed
        ok = ok and verdict
        print(f'{prefix}: temperature {"moving" if moved else "static"}'
              f'{" (initial value, frozen)" if frozen else ""}, heartbeat {"advancing" if beat else "static"}, '
              f'tone stop {"failed" if failed else "ok"}, firmware mailbox after stop '
              f'{"unknown" if a["fw_mbox_sts"] is None else hex(a["fw_mbox_sts"])} '
              f'(0x1000000000000 when paused, as on 2026-10-01): {"PASS" if verdict else "FAIL"}')
    quick = [line for line in lines if 'Failed to set mailbox cmd' in line or 'did not pause' in line]
    print(f'{len(quick)} missed pause/resume line(s) during the run; '
          f'{sum("took" in line for line in lines)} slow pause/resume line(s); '
          f'{sum("reloaded" in line for line in lines)} reload(s)')
    print('PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Brightness test page for the AMS678 panel (development tool).

Serves a slider on http://10.77.0.2:8088 (the USB link only). Each value is
sent one of three ways:
  driver  /sys/class/backlight/*/brightness (panel driver: 0x51 in LP)
  hs      raw 0x51 [hi, lo] in HS through rog5-panel-dcs-probe (stock order)
  lp      raw 0x51 [hi, lo] in LP through the same probe
  lp1/hs1 raw 0x51 with one byte (the slider runs 0-255) in LP or HS
"Push frames" swipes between the home pages so a command-mode panel gets
new frames. While the page is open the display is kept awake with a virtual
Shift press every 20 s. Only fixed-length 0x51 writes are possible (the probe
refuses anything else).
"""
import glob, html, http.server, json, os, sys, threading, time, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vtouch import VirtualKeyboard, VirtualTouch  # noqa: E402

PROBE = '/sys/kernel/debug/rog5-panel-dcs'
BACKLIGHT = glob.glob('/sys/class/backlight/*/brightness')[0]
ADDRESS = os.environ.get('ROG5_UI_ADDRESS', '10.77.0.2')
lock = threading.Lock()
log = []
last_seen = [0.0]
keyboard = VirtualKeyboard()


def note(text):
    log.append(time.strftime('%H:%M:%S ') + text)
    del log[:-12]


def display_on():
    """The CRTC's atomic 'active' state (Denial blanks through it; the
    connector's legacy dpms file keeps saying On)."""
    try:
        state = open('/sys/kernel/debug/dri/1/state').read()
    except OSError:
        return False
    return '\tactive=1' in state.split('crtc[', 1)[-1].split('\n\n', 1)[0]


def ensure_display_on():
    # Never send panel commands while the panel and DSI link are powered down.
    if display_on():
        return
    keyboard.press()
    for _ in range(30):
        time.sleep(0.1)
        if display_on():
            time.sleep(0.3)
            return
    raise RuntimeError('display is off and did not wake; nothing sent')


def apply(value, mode):
    value = max(0, min(255 if mode.endswith('1') else 1023, int(value)))
    hi, lo = value >> 8, value & 0xff
    with lock:
        ensure_display_on()
        if mode == 'driver':
            with open(BACKLIGHT, 'w') as f:
                f.write(str(value))
            note(f'driver {value} -> 51 {hi:02x} {lo:02x} (LP)')
        elif mode in ('hs1', 'lp1'):
            if not os.path.exists(PROBE):
                raise RuntimeError('rog5_panel_dcs_probe is not loaded')
            with open(PROBE, 'w') as f:
                f.write(f'51 {value:02x} {mode[:2]}')
            note(f'raw {mode[:2].upper()} 1-byte {value} -> 51 {value:02x}')
        elif mode in ('hs', 'lp'):
            if not os.path.exists(PROBE):
                raise RuntimeError('rog5_panel_dcs_probe is not loaded')
            with open(PROBE, 'w') as f:
                f.write(f'51 {hi:02x} {lo:02x} {mode}')
            note(f'raw {mode.upper()} {value} -> 51 {hi:02x} {lo:02x}')
        else:
            raise ValueError(mode)


def push_frames():
    with lock:
        v = VirtualTouch()
        try:
            for _ in range(2):
                v.swipe(950, 1900, 130, 1900, 0.25)
                time.sleep(1.0)
                v.swipe(130, 1900, 950, 1900, 0.25)
                time.sleep(1.0)
        finally:
            v.close()
        note('pushed frames (page swipes)')


def keep_awake():
    while True:
        time.sleep(20)
        if time.time() - last_seen[0] < 60:
            with lock:
                keyboard.press()


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ROG5 brightness</title><style>
body{font:16px system-ui;background:#111;color:#eee;max-width:640px;margin:24px auto;padding:0 16px}
input[type=range]{width:100%;height:40px} .row{margin:18px 0} button{font:inherit;padding:8px 14px}
label{margin-right:16px} pre{background:#222;padding:10px;min-height:9em} .v{font-size:40px;font-weight:600}
</style></head><body><h2>ROG5 brightness test</h2>
<div class="row"><span class="v" id="v">%(value)d</span> / <span id="max">1023</span> &nbsp; <span id="b"></span></div>
<div class="row"><input type="range" id="s" min="0" max="1023" value="%(value)d"></div>
<div class="row">
<label><input type="radio" name="m" value="driver" checked> driver (LP, Denial's path)</label>
<label><input type="radio" name="m" value="hs"> raw HS (stock)</label>
<label><input type="radio" name="m" value="lp"> raw LP</label><br>
<label><input type="radio" name="m" value="lp1"> 1-byte LP (0-255)</label>
<label><input type="radio" name="m" value="hs1"> 1-byte HS (0-255)</label></div>
<div class="row"><button id="f">Push frames</button> <button id="m1">-1</button> <button id="p1">+1</button>
<button id="p16">+16</button> <button id="m16">-16</button></div>
<pre id="log"></pre>
<script>
const s=document.getElementById('s'),v=document.getElementById('v'),lg=document.getElementById('log'),b=document.getElementById('b');
function mode(){return document.querySelector('input[name=m]:checked').value}
function one(){return mode().endsWith('1')}
let t=null, wasOne=false;
function hex(x){return x.toString(16).padStart(2,'0')}
function send(){v.textContent=s.value;const x=+s.value;
 b.textContent=one()?'bytes 51 '+hex(x):'bytes 51 '+hex(x>>8)+' '+hex(x&255);
 clearTimeout(t);t=setTimeout(()=>fetch('set?v='+s.value+'&m='+mode()).then(r=>r.json()).then(show),60)}
function rescale(){const o=one();if(o===wasOne)return;const x=+s.value;
 s.max=o?255:1023;s.value=o?0:x<<2;document.getElementById('max').textContent=s.max;wasOne=o;v.textContent=s.value}
for(const r of document.querySelectorAll('input[name=m]'))r.onchange=()=>{rescale();b.textContent='(mode changed; move the slider to send)'};
function show(d){lg.textContent=d.log.join('\\n')}
s.oninput=send;
for(const [id,d] of [['m1',-1],['p1',1],['p16',16],['m16',-16]])document.getElementById(id).onclick=()=>{s.value=Math.max(0,Math.min(+s.max,+s.value+d));send()};
document.getElementById('f').onclick=()=>fetch('frames').then(r=>r.json()).then(show);
setInterval(()=>fetch('ping').then(r=>r.json()).then(show),5000);
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def reply(self, body, kind='application/json', code=200):
        data = body.encode()
        self.send_response(code)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        last_seen[0] = time.time()
        url = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(url.query)
        try:
            if url.path == '/':
                value = int(open(BACKLIGHT).read())
                return self.reply(PAGE.replace('%(value)d', str(value)), 'text/html; charset=utf-8')
            if url.path == '/set':
                apply(query['v'][0], query['m'][0])
            elif url.path == '/frames':
                push_frames()
            elif url.path != '/ping':
                return self.reply('{}', code=404)
        except Exception as e:  # show the problem in the page log
            note('error: ' + html.escape(str(e)))
        self.reply(json.dumps({'log': log}))

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    threading.Thread(target=keep_awake, daemon=True).start()
    note(f'serving on http://{ADDRESS}:8088')
    http.server.ThreadingHTTPServer((ADDRESS, 8088), Handler).serve_forever()

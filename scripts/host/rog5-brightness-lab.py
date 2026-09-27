#!/usr/bin/env python3
"""ROG5 brightness lab: a local web page on the host that drives the phone's
panel brightness live, for precise human observation.

    python3 scripts/host/rog5-brightness-lab.py [--address 169.254.77.2] [--port 8765]

Then open http://127.0.0.1:8765/ (the page opens automatically).
- The slider (0-1023), the +-1/+-16 buttons and the number box write
  /sys/class/backlight/ae94000.dsi.0/brightness on the phone over the
  project's pinned SSH identity (one multiplexed connection, so a change
  lands in tens of milliseconds).
- The page shows the DBV bytes the panel driver sends: 51 hh ll
  (DCS 0x51 + 2 data bytes, the stock shape the user allowed).
- The experiment switches write the runtime module parameters that exist on
  the running kernel: msm dma_fifo_ctrl (0x33, 0x110033 or -1) and the panel's
  bl_hs (LP or HS brightness writes). Missing parameters are shown as such.
- "Record" appends the current value, parameters and your note to
  ~/.local/state/rog5-brightness-lab/observations.jsonl, which Claude/Fable
  read afterwards.
Listens on 127.0.0.1 only.
"""
import argparse, datetime, html, json, os, shlex, subprocess, sys, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

KEY = '/home/deck/.local/state/rog5-v13-live-inputs-20260823-r1/deployment-ssh-key'
KNOWN = '/home/deck/.local/state/rog5-native-root-release-v6-20260829-r1/v7-stable-known-hosts'
BL = '/sys/class/backlight/ae94000.dsi.0'
PARAMS = {'dma_fifo_ctrl': '/sys/module/msm/parameters/dma_fifo_ctrl',
          'bl_hs': '/sys/module/panel_asus_rog5_ams678/parameters/bl_hs'}
LOG = Path.home()/'.local/state/rog5-brightness-lab/observations.jsonl'
LOCK = threading.Lock()


class Phone:
    def __init__(self, address):
        self.address = address
        self.control = f'/tmp/rog5-brightness-lab-{os.getuid()}.sock'

    def run(self, cmd, timeout=15):
        args = ['ssh', '-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
                '-o', 'IdentityAgent=none', '-o', 'StrictHostKeyChecking=yes',
                '-o', f'HostKeyAlias={self.address}', '-o', f'UserKnownHostsFile={KNOWN}',
                '-o', 'ConnectTimeout=4', '-o', 'ControlMaster=auto', '-o', f'ControlPath={self.control}',
                '-o', 'ControlPersist=10m', '-i', KEY, f'root@{self.address}', cmd]
        with LOCK:
            r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        if r.returncode:
            raise RuntimeError((r.stderr or r.stdout).strip() or f'ssh exit {r.returncode}')
        return r.stdout

    def state(self):
        out = self.run('for f in %s/brightness %s/actual_brightness %s/max_brightness %s %s /sys/class/drm/card1-DSI-1/dpms; do '
                       'if [ -e "$f" ]; then printf "%%s=%%s\\n" "$f" "$(cat "$f")"; else printf "%%s=missing\\n" "$f"; fi; done'
                       % (BL, BL, BL, PARAMS['dma_fifo_ctrl'], PARAMS['bl_hs']))
        vals = dict(line.split('=', 1) for line in out.splitlines() if '=' in line)
        return {'brightness': vals.get(f'{BL}/brightness'), 'actual': vals.get(f'{BL}/actual_brightness'),
                'max': vals.get(f'{BL}/max_brightness'), 'dma_fifo_ctrl': vals.get(PARAMS['dma_fifo_ctrl']),
                'bl_hs': vals.get(PARAMS['bl_hs']), 'dpms': vals.get('/sys/class/drm/card1-DSI-1/dpms'),
                'address': self.address}

    def set_brightness(self, value):
        value = max(0, min(1023, int(value)))
        self.run(f'echo {value} > {BL}/brightness')
        return value

    def set_param(self, name, value):
        if name not in PARAMS:
            raise ValueError('unknown parameter')
        allowed = {'dma_fifo_ctrl': {'51', '1114163', '-1'}, 'bl_hs': {'Y', 'N'}}[name]
        if str(value) not in allowed:
            raise ValueError(f'{name} must be one of {sorted(allowed)}')
        self.run(f'test -e {PARAMS[name]} && echo {shlex.quote(str(value))} > {PARAMS[name]}')

    def wake(self):
        self.run('command -v rog5-desktop >/dev/null && rog5-desktop wake', timeout=20)


PAGE = r'''<!doctype html><html><head><meta charset="utf-8"><title>ROG5 brightness lab</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{font:16px system-ui,sans-serif;background:#111;color:#eee;margin:24px;max-width:900px}
input[type=range]{width:100%;height:40px}button{font-size:16px;padding:8px 14px;margin:4px;background:#333;color:#eee;border:1px solid #555;border-radius:6px}
.row{margin:14px 0}.big{font-size:40px;font-weight:600}.mono{font-family:monospace}.warn{color:#f96}.ok{color:#8d8}
textarea{width:100%;height:60px;background:#222;color:#eee;border:1px solid #555}
label{margin-right:16px}
</style></head><body>
<h2>ROG5 brightness lab</h2>
<div class="row"><span class="big" id="v">-</span> / 1023 &nbsp; <span class="mono" id="bytes"></span>
&nbsp; screen: <span id="dpms">?</span> &nbsp; <button onclick="wake()">Wake screen</button></div>
<div class="row"><input type="range" id="s" min="0" max="1023" value="512"></div>
<div class="row">
<button onclick="step(-16)">-16</button><button onclick="step(-1)">-1</button>
<input id="n" type="number" min="0" max="1023" style="width:90px;font-size:18px"><button onclick="setv(+document.getElementById('n').value)">Set</button>
<button onclick="step(1)">+1</button><button onclick="step(16)">+16</button>
<button onclick="setv(1023)">1023</button><button onclick="setv(768)">768</button><button onclick="setv(512)">512</button><button onclick="setv(256)">256</button><button onclick="setv(128)">128</button>
</div>
<div class="row">DMA FIFO watermark (msm dma_fifo_ctrl): <span id="fifo">?</span><br>
<label><input type="radio" name="fifo" value="51"> 0x33 (stock with Iris)</label>
<label><input type="radio" name="fifo" value="1114163"> 0x110033 (stock without Iris)</label>
<label><input type="radio" name="fifo" value="-1"> hardware default</label></div>
<div class="row">Brightness write mode (panel bl_hs): <span id="hs">?</span><br>
<label><input type="radio" name="hs" value="N"> LP (low power)</label>
<label><input type="radio" name="hs" value="Y"> HS (high speed, like stock)</label></div>
<div class="row">What do you see at this value?<br><textarea id="note" placeholder="e.g. same as 512 / slightly darker than 700 / black"></textarea>
<button onclick="record()">Record observation</button> <span id="msg"></span></div>
<p class="mono" id="err" style="color:#f66"></p>
<script>
let cur=null, pending=null, busy=false;
function hex(v){return v.toString(16).padStart(2,'0')}
function show(st){
  document.getElementById('dpms').textContent=st.dpms;
  document.getElementById('fifo').textContent=st.dma_fifo_ctrl; document.getElementById('hs').textContent=st.bl_hs;
  for(const r of document.getElementsByName('fifo')) r.checked=(r.value==st.dma_fifo_ctrl);
  for(const r of document.getElementsByName('hs')) r.checked=(r.value==st.bl_hs);
  if(st.brightness!==undefined && st.brightness!==null){cur=+st.brightness; paint()}}
function paint(){document.getElementById('v').textContent=cur; document.getElementById('s').value=cur; document.getElementById('n').value=cur;
  document.getElementById('bytes').textContent='51 '+hex(cur>>8)+' '+hex(cur&255)}
async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
  const j=await r.json(); document.getElementById('err').textContent=j.error||''; if(j.state) show(j.state); return j}
async function flush(){ if(busy||pending===null) return; busy=true; const v=pending; pending=null; await api('/api/brightness',{value:v}); busy=false; flush()}
function setv(v){cur=Math.max(0,Math.min(1023,Math.round(v))); paint(); pending=cur; flush()}
function step(d){setv((cur||0)+d)}
document.getElementById('s').addEventListener('input',e=>setv(+e.target.value));
for(const r of document.getElementsByName('fifo')) r.addEventListener('change',e=>api('/api/param',{name:'dma_fifo_ctrl',value:e.target.value}));
for(const r of document.getElementsByName('hs')) r.addEventListener('change',e=>api('/api/param',{name:'bl_hs',value:e.target.value}));
async function wake(){await api('/api/wake',{})}
async function record(){const n=document.getElementById('note').value; const j=await api('/api/note',{note:n,value:cur});
  if(!j.error){document.getElementById('msg').textContent='recorded ('+j.count+')'; document.getElementById('note').value=''}}
document.addEventListener('keydown',e=>{if(e.target.tagName==='TEXTAREA'||e.target.tagName==='INPUT'&&e.target.type==='number')return;
  if(e.key==='ArrowLeft')step(e.shiftKey?-16:-1); if(e.key==='ArrowRight')step(e.shiftKey?16:1)});
api('/api/state'); setInterval(()=>api('/api/state'),5000);
</script></body></html>'''


def make_handler(phone):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def reply(self, code, obj=None, body=None, ctype='application/json'):
            data = body.encode() if body is not None else json.dumps(obj).encode()
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == '/':
                return self.reply(200, body=PAGE, ctype='text/html; charset=utf-8')
            if self.path == '/api/state':
                try:
                    return self.reply(200, {'state': phone.state()})
                except Exception as e:
                    return self.reply(200, {'error': str(e)})
            self.reply(404, {'error': 'not found'})

        def do_POST(self):
            try:
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
                if self.path == '/api/brightness':
                    phone.set_brightness(body['value'])
                elif self.path == '/api/param':
                    phone.set_param(body['name'], body['value'])
                elif self.path == '/api/wake':
                    phone.wake()
                elif self.path == '/api/note':
                    st = phone.state()
                    LOG.parent.mkdir(parents=True, exist_ok=True)
                    rec = {'time': datetime.datetime.now().isoformat(timespec='seconds'), 'value': body.get('value'),
                           'dbv_bytes': '51 %02x %02x' % (int(body.get('value') or 0) >> 8, int(body.get('value') or 0) & 255),
                           'note': body.get('note', ''), 'state': st}
                    with LOG.open('a') as f:
                        f.write(json.dumps(rec) + '\n')
                    return self.reply(200, {'state': st, 'count': sum(1 for _ in LOG.open())})
                else:
                    return self.reply(404, {'error': 'not found'})
                self.reply(200, {'state': phone.state()})
            except Exception as e:
                self.reply(200, {'error': str(e)})
    return Handler


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--address', default=None, help='phone address (default: 169.254.77.2, then 10.77.0.2)')
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--no-browser', action='store_true')
    a = ap.parse_args()
    phone = None
    for addr in ([a.address] if a.address else ['169.254.77.2', '10.77.0.2']):
        try:
            p = Phone(addr); p.state(); phone = p; break
        except Exception as e:
            print(f'{addr}: {e}', file=sys.stderr)
    if phone is None:
        sys.exit('phone not reachable')
    srv = ThreadingHTTPServer(('127.0.0.1', a.port), make_handler(phone))
    url = f'http://127.0.0.1:{a.port}/'
    print(f'brightness lab on {url} (phone {phone.address}); log {LOG}; Ctrl+C to stop')
    if not a.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()

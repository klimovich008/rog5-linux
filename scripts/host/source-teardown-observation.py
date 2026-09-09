"""Boot-bound source teardown evidence. No boot, deployment or claim authority."""
import hashlib
import json
from pathlib import Path
import re
import copy
import os
import stat

FORMAT='rog5-source-teardown-v1'
INTENT_FORMAT='rog5-source-teardown-intent-v1'
DIAGNOSTIC_FORMAT='rog5-source-teardown-diagnostic-v1'
PHASES=('teardown','mounts','loops','physical','receipt')
DIAGNOSTIC_KEYS=('format','boot_id','nonce','shutdown_sha256','observer_sha256','phase','clean','state')
HEX=re.compile('[0-9a-f]{64}')
BOOT=re.compile('[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}')
KEYS=('format','boot_id','nonce','shutdown_sha256','observer_sha256',
      'physical_nodes','mounts','loops','physical_ro','result')
REPO=Path(__file__).resolve().parents[2]

def require(condition,reason):
    if not condition:raise ValueError(reason)

def sha(raw):return hashlib.sha256(raw).hexdigest()

def timing():
    contract=json.loads((REPO/'configs/release-acceptance.json').read_text())
    value=contract['defaults']['source_teardown']
    require(set(value)=={'observer_seconds','receipt_seconds'}
        and all(type(v) is int for v in value.values())
        and 0<value['observer_seconds']<value['receipt_seconds']<=60,'source teardown timing')
    return value

def identity(value):
    require(type(value) is dict and set(value)=={'boot_id','serial','bundle','release'},'source identity fields')
    require(all(type(v) is str for v in value.values()) and BOOT.fullmatch(value['boot_id'])
        and re.fullmatch('[A-Z0-9]{1,32}',value['serial'])
        and re.fullmatch('[a-z0-9][a-z0-9-]{0,79}',value['bundle'])
        and re.fullmatch('[A-Za-z0-9._+-]{1,80}',value['release']),'source identity values')
    return value

def intent(value):
    fields={'format','identity','nonce','shutdown_sha256','observer_sha256','physical_nodes'}
    require(type(value) is dict and set(value) in (fields,fields|{'diagnostics'}),'source teardown intent fields')
    require('diagnostics' not in value or value['diagnostics'] is True,'source diagnostic opt-in')
    require(value['format']==INTENT_FORMAT,'source teardown intent format')
    identity(value['identity'])
    require(all(type(value[k]) is str and HEX.fullmatch(value[k]) for k in
        ('nonce','shutdown_sha256','observer_sha256')),'source teardown intent hashes')
    require(type(value['physical_nodes']) is int and value['physical_nodes']==117,'source physical scope')
    return value

def parse_diagnostic(raw,expected):
    expected=intent(expected)
    require(expected.get('diagnostics') is True,'unrequested source diagnostic')
    require(type(raw) is bytes and 0<len(raw)<=512 and raw.endswith(b'\n') and b'\r' not in raw,
            'source diagnostic size/framing')
    try:rows=[line.split('=',1) for line in raw.decode('ascii').split('\n')[:-1]]
    except UnicodeDecodeError as error:raise ValueError('source diagnostic ASCII') from error
    require(len(rows)==len(DIAGNOSTIC_KEYS) and all(len(row)==2 for row in rows)
        and tuple(row[0] for row in rows)==DIAGNOSTIC_KEYS,'source diagnostic fields/order')
    value=dict(rows)
    require(value['format']==DIAGNOSTIC_FORMAT and value['boot_id']==expected['identity']['boot_id']
        and all(value[k]==expected[k] for k in ('nonce','shutdown_sha256','observer_sha256')),
        'source diagnostic identity mismatch')
    require(value['phase'] in PHASES and value['clean'] in ('0','1') and value['state'] in ('begin','fail'),
        'source diagnostic values')
    require(value['clean']=='1' or value['phase']=='teardown','unclean source diagnostic phase')
    return value

def read_intent(path,pin):
    require(type(pin) is str and HEX.fullmatch(pin),'source intent digest')
    require(path.is_absolute(),'absolute source intent path required')
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),'rb') as stream:
        metadata=os.fstat(stream.fileno())
        require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink==1
            and not metadata.st_mode & 0o022 and metadata.st_size<=2048,'unsafe source intent file')
        raw=stream.read(2049)
    require(len(raw)<=2048 and sha(raw)==pin,'source intent digest mismatch')
    def unique(pairs):
        value={}
        for key,item in pairs:
            require(key not in value,'duplicate source intent field')
            value[key]=item
        return value
    return intent(json.loads(raw,object_pairs_hook=unique))

def parse(raw,expected):
    expected=intent(expected)
    require(type(raw) is bytes and 0<len(raw)<=512 and raw.endswith(b'\n') and b'\r' not in raw,
        'source receipt size/framing')
    try:rows=[line.split('=',1) for line in raw.decode('ascii').split('\n')[:-1]]
    except UnicodeDecodeError as error:raise ValueError('source receipt ASCII') from error
    require(len(rows)==len(KEYS) and all(len(row)==2 for row in rows)
        and tuple(row[0] for row in rows)==KEYS,'source receipt fields/order')
    value=dict(rows)
    require(value==dict(format=FORMAT,boot_id=expected['identity']['boot_id'],nonce=expected['nonce'],
        shutdown_sha256=expected['shutdown_sha256'],observer_sha256=expected['observer_sha256'],
        physical_nodes=str(expected['physical_nodes']),mounts='clear',loops='clear',physical_ro='all',result='PASS'),
        'source receipt mismatch or incomplete teardown')
    return value

class Observation:
    """One expected receipt on the still-connected source; never a target stage."""
    def __init__(self,expected,source_boot_id,armed_monotonic):
        import math
        self.expected=copy.deepcopy(intent(expected))
        require(self.expected['identity']['boot_id']==source_boot_id,'different source boot intent')
        require(type(armed_monotonic) in (int,float) and math.isfinite(armed_monotonic)
            and armed_monotonic>=0,'source arm time')
        self.armed=armed_monotonic;self.deadline=self.armed+timing()['receipt_seconds'];self.receipt=None
        self.diagnostics=[];self.failed=False
    def diagnose(self,raw,now):
        import math
        try:
            require(not self.failed and self.receipt is None,'closed source diagnostic observation')
            previous=self.diagnostics[-1]['monotonic'] if self.diagnostics else self.armed
            require(type(now) in (int,float) and math.isfinite(now) and previous<=now<=self.deadline,
                    'stale source diagnostic')
            value=parse_diagnostic(raw,self.expected)
            if value['state']=='begin':
                require(len(self.diagnostics)<len(PHASES) and value['phase']==PHASES[len(self.diagnostics)]
                    and all(v['record']['clean']=='1' for v in self.diagnostics),'source diagnostic phase order')
            else:
                require(bool(self.diagnostics) and all(value[k]==self.diagnostics[-1]['record'][k]
                    for k in ('phase','clean')),'source diagnostic failure without matching phase')
                self.failed=True
            record=dict(record=value,monotonic=now,payload_sha256=sha(raw))
            self.diagnostics.append(record)
            return record
        except ValueError:
            self.failed=True
            raise
    def observe(self,raw,now):
        import math
        require(not self.failed,'failed source diagnostic observation')
        if self.expected.get('diagnostics'):
            require(len(self.diagnostics)==len(PHASES) and all(v['record']['clean']=='1'
                and v['record']['state']=='begin' for v in self.diagnostics),'incomplete source diagnostics')
            require(type(now) in (int,float) and now>=self.diagnostics[-1]['monotonic'],
                    'source receipt precedes diagnostics')
        require(self.receipt is None,'repeated source teardown receipt')
        require(type(now) in (int,float) and math.isfinite(now)
            and self.armed<=now<=self.deadline,'stale source teardown receipt')
        value=parse(raw,self.expected)
        self.receipt=dict(record=value,monotonic=now,payload_sha256=sha(raw))
        return self.receipt

def prepare(source_shutdown,source_sha256,source_identity,nonce,*,diagnostics=False):
    """Deterministic RAM-only derivative; accepted source and target stay unchanged."""
    source_identity=copy.deepcopy(identity(source_identity))
    require(type(diagnostics) is bool,'source diagnostic mode')
    require(type(nonce) is str and HEX.fullmatch(nonce),'source intent nonce')
    original=(REPO/'initramfs/persistent-root-shutdown-standalone').read_bytes()
    require(type(source_shutdown) is bytes and source_shutdown==original
        and sha(source_shutdown)==source_sha256,'source shutdown differs from reviewed accepted bytes')
    text=source_shutdown.decode('ascii');anchor='for api in run dev sys proc; do\n'
    reboot='"$bb" reboot -f 2>/dev/null || true'
    require(text.count(anchor)==text.count(reboot)==1,'source shutdown injection anchors')
    hook=('if [ -f /rog5-source-teardown ] && [ ! -L /rog5-source-teardown ]; then\n'
        '\t"$bb" timeout -s KILL '+str(timing()['observer_seconds'])+
        ' "$bb" sh /rog5-source-teardown "$clean" "${1:-reboot}"'+
        (' --diagnostics' if diagnostics else '')+' || true\nfi\n')
    shutdown=text.replace(anchor,hook+anchor).replace(reboot,'/usr/libexec/rog5-reboot-bootloader || true').encode()
    observer=(REPO/'initramfs/source-teardown-observer').read_bytes()
    spec=dict(format=INTENT_FORMAT,identity=source_identity,nonce=nonce,
        shutdown_sha256=sha(shutdown),observer_sha256=sha(observer),physical_nodes=117)
    if diagnostics:spec['diagnostics']=True
    intent(spec)
    fields=dict(boot_id=source_identity['boot_id'],release=source_identity['release'],nonce=nonce,
        shutdown_sha256=spec['shutdown_sha256'],observer_sha256=spec['observer_sha256'],physical_nodes='117')
    settings=''.join(k+'='+v+'\n' for k,v in fields.items()).encode()
    checksum=(sha(shutdown)+'  shutdown\n'+sha(observer)+'  rog5-source-teardown\n'+
        sha(settings)+'  rog5-source-teardown.intent\n').encode()
    return spec,{'shutdown':shutdown,'rog5-source-teardown':observer,
        'rog5-source-teardown.intent':settings,'rog5-source-teardown.sha256':checksum}

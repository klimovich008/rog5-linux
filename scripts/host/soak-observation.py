"""S07 observation predicates; no device access or qualification authority."""
import math,re
ERROR=re.compile(r'(^|\n)(BUG:|WARNING:|Oops:|Kernel panic)|I/O error|EXT4-fs (error|abort)|Remounting filesystem read-only|ufshcd[^\n]*(error|fail)|\bUFS\b[^\n]*(error|fail)|soft lockup|hard LOCKUP|blocked for more than',re.I)
def require(ok,reason):
 if not ok:raise ValueError(reason)
def timing(contract):
 t=contract['defaults']['server_soak'];deadline=next(row['deadline_seconds'] for row in contract['tests'] if row['id']=='S07')
 require(set(t)=={'observation_seconds','heartbeat_seconds','preflight_seconds','warmup_seconds','cleanup_seconds',
  'max_file_windows','network_bytes','network_deadline_seconds'} and all(type(v) is int and v>0 for v in t.values()),'soak timing fields')
 require(t['observation_seconds']==3600 and t['heartbeat_seconds']==10 and t['max_file_windows']<=128
  and t['network_bytes']==64*1024**2 and t['network_deadline_seconds']<=90,'soak measurement/scope')
 require(t['preflight_seconds']+t['warmup_seconds']+t['observation_seconds']+t['cleanup_seconds']<=deadline
  and t['cleanup_seconds']>=t['network_deadline_seconds']+60,'soak timeout lattice')
 return t
def kmsg(records,cursor):
 require(type(cursor) is int and cursor>=-1,'invalid kernel log cursor')
 require(type(records) is list and len(records)<=4096,'kernel log batch bound')
 for raw in records:
  require(type(raw) is str and len(raw.encode())<=8192 and raw.endswith('\n'),'truncated/oversize kernel record')
  header,message=raw.split(';',1);fields=header.split(',')
  require(len(fields)==4 and all(re.fullmatch('[0-9]+',v) for v in fields[:3]),'kernel record header')
  priority,sequence,stamp=map(int,fields[:3])
  require(priority<=191 and fields[3] in ('-','c') and sequence==cursor+1,'kernel log gap/replay')
  # /dev/kmsg encodes severity in the low three syslog-priority bits.
  # https://www.kernel.org/doc/Documentation/ABI/testing/dev-kmsg
  require((priority & 7)>4,'new warning-or-higher kernel log record')
  require(not ERROR.search(message),'new kernel failure record')
  cursor=sequence
 return cursor
def ext4(before,after):
 require(set(before)==set(after)=={'loop1','sda23','sda24'},'missing filesystem counters')
 for name in before:
  for item in (before[name],after[name]):
   require(item['status']=='present' and type(item['value']) is str and re.fullmatch('[0-9]+',item['value']),
    'missing/malformed previously available counter')
  require(before[name]==after[name],'new filesystem error or counter reset')
def progress(before,after,identity):
 require(before['identity']==after['identity']==identity,'boot/release changed')
 for key in ('host_monotonic','target_uptime'):
  require(all(type(v[key]) in (int,float) and math.isfinite(v[key]) and v[key]>=0 for v in (before,after)),
   'invalid clock')
 host=after['host_monotonic']-before['host_monotonic'];target=after['target_uptime']-before['target_uptime']
 require(0<host<=15 and target>0 and abs(host-target)<=2,'missed/stale soak heartbeat')
def io_progress(before,after,windows):
 require(type(windows) is int and 1<=windows<=128,'invalid file-window count')
 for name in ('loop1','sda23'):
  values=[]
  for sample in (before,after):
   fields=sample[name].split()
   require(len(fields)==17 and all(re.fullmatch('[0-9]+',v) for v in fields),'invalid block statistics')
   values.append(list(map(int,fields)))
  # Linux block statistics report sectors in fixed 512-byte units.
  required=windows*(64*1024**2//512)
  require(all(values[1][i]-values[0][i]>=required for i in (2,6)),
   'missing corresponding backing-device read/write activity')

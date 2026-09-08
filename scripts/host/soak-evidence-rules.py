"""Pure S07 evidence predicates. No device contact or private-source execution."""
import math
import re

SIZE=64*1024**2

def need(ok,reason):
    if not ok:raise ValueError(reason)

def number(value):
    need(type(value) in (int,float) and math.isfinite(value) and value>=0,'invalid observation time')
    return value

def coverage(rows,start,end,maximum):
    need(type(rows) is list and rows,'missing workload')
    previous=None
    for row in rows:
        begin=number(row['started']);finish=number(row['finished'])
        need(0<finish-begin<=maximum,'workload operation deadline')
        if previous is not None:need(0<=begin-previous<=5,'workload overlap or scheduling gap')
        previous=finish
    need(rows[0]['started']<=start and rows[-1]['finished']>=end,'workload does not span the measured hour')

def timeline(run,events,limits,total):
    need(run['status']=='COMPONENT_PASS' and 'reason' not in run
         and run['s07_qualified'] is False and run['release_qualified'] is False
         and run['workers_stopped'] is True,'incomplete/failed soak')
    for key,value in (('deadline_seconds',total),('observation_seconds',limits['observation_seconds']),
                      ('heartbeat_seconds',limits['heartbeat_seconds']),('max_file_windows',limits['max_file_windows']),
                      ('file_bytes',SIZE),('network_bytes',SIZE)):
        need(type(run[key]) is int and run[key]==value,'changed soak limit: '+key)
    begin=number(run['started_monotonic']);elapsed=number(run['seconds'])
    start=number(run['observation_started']);end=number(run['observation_finished'])
    need(elapsed<=total and begin<=start<end<=begin+elapsed,'invalid total observation interval')
    need(start-begin<=limits['preflight_seconds']+limits['warmup_seconds']
         and limits['observation_seconds']<=end-start<=limits['observation_seconds']+15
         and begin+elapsed-end<=limits['cleanup_seconds'],'warmup/hour/cleanup deadline')
    allowed={'command-entered','command-returned','transfer-entered','transfer-returned','storage-completed','soak-started'}
    need(type(events) is list and events,'missing raw event stream')
    previous=begin;starts=[]
    for n,event in enumerate(events,1):
        need(type(event['sequence']) is int and event['sequence']==n and event['event'] in allowed,'event order/failure')
        stamp=number(event['monotonic']);need(previous<=stamp<=begin+elapsed,'event clock outside run');previous=stamp
        if event['event']=='soak-started':starts.append(event)
    need(len(starts)==1 and start<=starts[0]['monotonic']<=start+1,'unbound measured-hour start')
    stats=run['stats'];need(set(stats)=={'storage','network','samples'},'workload fields')
    need(1<=len(stats['storage'])<=limits['max_file_windows'],'storage write-volume limit')
    coverage(stats['storage'],start,end,60);coverage(stats['network'],start,end,limits['network_deadline_seconds'])
    warmup=min(stats[key][0]['started'] for key in ('storage','network'))
    need(0<=warmup-begin<=limits['preflight_seconds'] and 0<=start-warmup<=limits['warmup_seconds'],
         'preflight or warmup budget exceeded')
    need(360<=len(stats['samples'])<=374,'missing ten-second heartbeat series')
    return stats

def command_pairs(events,raw,sha,decode):
    pending={};commands=[];transfers=[];expected={'events','run'}
    for event in events:
        kind=event['event'];n=event['sequence']
        if kind in ('command-entered','transfer-entered'):
            name=f'{n:04d}.script';expected.add(name)
            need(sha(raw[name])==event['script_sha256'] and raw[name],'changed executed script')
            pending[n]=event
        elif kind in ('command-returned','transfer-returned'):
            key=event['command'];need(type(key) is int and key in pending,'unmatched/duplicate command exit')
            entered=pending.pop(key)
            need(kind==entered['event'].replace('entered','returned'),'mixed command types')
            if kind=='command-returned':
                prefix=f'{key:04d}';expected.update((prefix+'.stdout',prefix+'.stderr'))
                stdout=raw[prefix+'.stdout'];stderr=raw[prefix+'.stderr']
                need(type(event['returncode']) is int and event['returncode']==0 and not stderr
                     and len(stdout)<4194304 and sha(stdout)==event['stdout_sha256'],'failed/changed raw command')
                limit=60 if entered['label']=='storage-window' else 20
                need(entered['timeout']==limit and 0<event['monotonic']-entered['monotonic']<=limit,'command deadline')
                commands.append((entered,event,decode(stdout)))
            else:transfers.append((entered,event))
    need(not pending,'incomplete command/transfer')
    return commands,transfers,expected

def observations(run,commands,B,O):
    identity=run['identity'];heartbeats=[row for row in commands if row[0]['label']=='heartbeat']
    samples=run['stats']['samples'];need(len(heartbeats)==len(samples)+2,'missing raw heartbeat')
    expected=[run['baseline'],*samples,run['final']];previous=None;cursor=None
    for index,((entered,returned,raw),bound) in enumerate(zip(heartbeats,expected)):
        B.ROOT.validate(raw,identity)
        need(raw['thermal'] and all(re.fullmatch('-?[0-9]+',v) and int(v)<60000 for v in raw['thermal'].values()),'unsafe/missing thermal')
        stamp=number(bound['host_monotonic'])
        need(returned['monotonic']<=stamp<=returned['monotonic']+2,'unbound host sample clock')
        value=dict(raw,host_monotonic=stamp)
        if index in (0,len(expected)-1):need(value==bound,'changed full boundary sample')
        else:
            need(set(bound)=={'host_monotonic','target_uptime','cursor','power','disk_stats','ext4'}
                 and all(value[k]==bound[k] for k in bound if k!='cursor'),'changed heartbeat summary')
        O.ext4(run['baseline']['ext4'],raw['ext4'])
        if index==0:
            records=raw['kmsg'];need(records and raw['advice_available'] is True,'missing log/cache-advice baseline')
            # Baseline errors are retained, not retroactively treated as new events.
            sequences=[int(row.split(';',1)[0].split(',')[1]) for row in records]
            need(all(b==a+1 for a,b in zip(sequences,sequences[1:])),'baseline log gap')
            cursor=sequences[-1]
        else:
            need(type(raw['kmsg_first_available']) is int and raw['kmsg_first_available']<=cursor+1,'kernel log overrun')
            cursor=O.kmsg(raw['kmsg'],cursor)
            if index<len(expected)-1:
                need(cursor==bound['cursor'],'changed kernel cursor')
                O.progress(previous,value,identity)
            completed=sum(row['finished']<=entered['monotonic'] for row in run['stats']['storage'])
            if completed:O.io_progress(run['baseline']['disk_stats'],raw['disk_stats'],completed)
        previous=value
    need(heartbeats[1][0]['monotonic']<=run['observation_started']
         and samples[-1]['host_monotonic']>=run['observation_started']+3600,'heartbeats do not cover hour')
    O.io_progress(run['baseline']['disk_stats'],run['final']['disk_stats'],len(run['stats']['storage']))
    before=run['baseline']['scratch_scope'];after=run['final']['scratch_scope']
    for key in ('path','dev','inode','mode','uid','gid','test_directory_exists','namespace_inode'):
        need(before[key]==after[key],'scratch namespace changed')
    need(before['path']=='/persist' and before['test_directory_exists'] is True
         and type(before['namespace_inode']) is int and before['namespace_inode']>0,'preserved namespace missing')
    return heartbeats

def storage(run,commands,events,raw,sources,T,sha):
    cases=[row for row in commands if row[0]['label']=='storage-window']
    stats=run['stats']['storage'];need(len(cases)==len(stats),'unreported scratch operation')
    completions=[e for e in events if e['event']=='storage-completed']
    need(len(completions)==len(stats),'missing scratch completion event')
    nonces=set();scope=run['baseline']['scratch_scope'];identity=run['identity']
    for index,((entered,returned,value),row,done) in enumerate(zip(cases,stats,completions)):
        need(value==row['result'] and row['started']<=entered['monotonic']<returned['monotonic']<=row['finished']
             and row['finished']-returned['monotonic']<=2 and type(done['index']) is int and done['index']==index
             and row['finished']<=done['monotonic']<=row['finished']+2,'unbound scratch result/timing')
        nonce=value['nonce'];T.validate(nonce,SIZE);need(nonce not in nonces,'reused scratch nonce');nonces.add(nonce)
        request=dict(phase='prepare',origin_boot_id=identity['boot_id'],identity=identity,scope=scope,nonce=nonce,size=SIZE)
        need(entered['request']==request,'changed storage scope/request')
        script='REQUEST='+repr(request)+'\nOPS_SOURCE='+repr(sources['ops'].decode())+'\nGUARD_SOURCE='+repr(sources['guard'].decode())+'\n'+sources['window'].decode()
        need(raw[f"{entered['sequence']:04d}.script"]==script.encode(),'changed exact scratch command')
        need(value['status']=='PASS' and value['s07_qualified'] is False and value['identity']==identity
             and type(value['size']) is int and value['size']==SIZE and value['cleanup'] is True
             and 30<=number(value['seconds'])<=50 and type(value['readbacks']) is int and value['readbacks']>=1
             and value['ops_sha256']==sha(sources['ops']) and value['guard_sha256']==sha(sources['guard']),'incomplete scratch window')
        file=value['file'];meta=file['file']
        need(file['name']=='s04-'+nonce[:32] and file['nonce']==nonce and file['sha256']==T.expected_digest(nonce,SIZE)
             and file['parent_inode']==scope['namespace_inode']
             and type(file['directory_inode']) is int and file['directory_inode']>0,'scratch identity/readback')
        need(set(meta)=={'inode','size','mode','uid','gid','nlink'} and all(type(v) is int for v in meta.values())
             and meta['inode']>0 and meta['size']==SIZE and meta['mode']==0o400
             and meta['uid']==meta['gid']==0 and meta['nlink']==1,'scratch file scope/metadata')
        for power in (value['power_before'],value['power_after']):
            need(all(type(power[k]) is str and re.fullmatch('-?[0-9]+',power[k]) for k in ('temp','voltage_now'))
                 and power['health']=='Good' and 0<=int(power['temp'])<400
                 and 8400000<=int(power['voltage_now'])<=8800000,'unsafe scratch power')
        need(value['thermal_after'] and all(int(v)<60000 for v in value['thermal_after'].values()),'unsafe scratch thermal')
    return nonces

def network(run,pairs,raw,T,sha,decode,endpoint,observer_sha256,nonces):
    rows=run['stats']['network'];need(len(rows)==len(pairs),'unreported network operation')
    expected=set();covered=set();links=run['links']
    need([link['name'] for link in links]==['usb','wifi'],'network link ordering')
    for index,(row,(entered,returned)) in enumerate(zip(rows,pairs)):
        link=links[(index//2)%2];direction,action=(('upload','receive'),('download','send'))[index%2]
        nonce=row['nonce'];T.validate(nonce,SIZE);need(nonce not in nonces,'reused transfer nonce');nonces.add(nonce)
        need(row['link']==entered['link']==link and row['direction']==entered['direction']==direction
             and nonce==entered['nonce'] and row['result']==returned['result'],'network scope/receipt mismatch')
        need(entered['monotonic']<=row['started']<=entered['monotonic']+2
             and row['finished']<=returned['monotonic']<=row['finished']+2,'network command timing')
        value=row['result']
        need(type(value['bytes']) is int and value['bytes']==SIZE and value['sha256']==T.expected_digest(nonce,SIZE)
             and type(value['returncode']) is int and value['returncode']==0 and value['s02_qualified'] is False
             and 0<number(value['duration_seconds'])<=90
             and 0<=row['finished']-row['started']-value['duration_seconds']<=2,'incomplete transfer or changed deadline')
        script=endpoint(run['identity'],link,action,nonce,SIZE)
        need(raw[f"{entered['sequence']:04d}.script"]==script.encode(),'changed exact transfer endpoint')
        prefix=f"transfer-{entered['sequence']:04d}/";names={prefix+x for x in ('entered.json','result.json','stderr.bin')};expected|=names
        before=decode(raw[prefix+'entered.json']);after=decode(raw[prefix+'result.json']);error=raw[prefix+'stderr.bin']
        need(before['status']=='ENTERED' and after['status']=='TERMINAL' and after['overflow'] is False
             and type(after['returncode']) is int and after['returncode']==0 and not error
             and after['stderr_bytes']==0 and after['stderr_sha256']==sha(error),'failed/incomplete transfer child')
        for key in ('started_monotonic','command_sha256','limit_bytes','observer_sha256'):
            need(before[key]==after[key],'changed child observer identity')
        need(before['limit_bytes']==4096 and before['observer_sha256']==observer_sha256
             and re.fullmatch('[0-9a-f]{64}',before['command_sha256']) and before['command_sha256']==entered['command_sha256']
             and row['started']<=before['started_monotonic']<row['finished']
             and 0<number(after['seconds'])<=90
             and before['started_monotonic']+after['seconds']<=row['finished'],'child observation bounds')
        covered.add((link['name'],direction))
    need(covered=={(name,direction) for name in ('usb','wifi') for direction in ('upload','download')},'missing transport/direction')
    return expected

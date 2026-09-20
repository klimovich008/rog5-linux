"""GPU RAM staging and bounded duplex transport. Import-only.

An outer coordinator must provide admitted new-boot health, independent logger
liveness and recovery ownership. This file does not grant those authorities.
"""
import base64,hashlib,importlib.util,json,os,re,selectors,signal,stat,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;D=HERE.parent
NORMAL_SECONDS=78;CLOSURE_SECONDS=14;RENEW_SECONDS=.75;OUTPUT_LIMIT=262144
SOURCE_PINS = {'backend.py': '840ba5ad5c1bfe2059bfc580fb45da4e8f3fef59f8e6627789cfe5ed38904a0d', 'module-io.py': 'c028b4ddd27ed43af9e7eda48c4dd21e5a685a1bda0ee61209eaa12df8f87620', 'load-display.py': '5c298ba05fe7a6f338471cd178a10b49cd9c03914f4a696ad442e7e0dbc1838d', 'endpoint.py': '1c8c173d59a69cc514365844d179813b16d5ae6e7696ecfc9e12ccb999e654ca', 'initialize.py': '373eb2bc855619e19901dd152344407ed3b119c6441e2d57b9716a7423181a38', 'provider-proof.py': 'f73a9c55474fc38645e8b3f83809debc2b5fe1238dd69e291bf3c345e5b294d9', 'provider-backend.py': '38dfdeff0180c9311f721bf76bb15d5b6edbd659dd5ea5466355be64c178faa1', 'provider.py': '3cc937fa611f0a85f75d234f75c8d3123e609735305a601f1077ce7a6a6f8924', 'reprobe.py': 'c2486e2c35ffc180b70d975523431169e338eff3774f14240b2b0353240562a5'}
def need(ok, why):
    if not ok:
        raise ValueError(why)

def raw(path, limit=1048576):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        st=os.fstat(fd)
        need(path.resolve()==path and stat.S_ISREG(st.st_mode) and st.st_uid==1000
             and st.st_nlink==1 and not stat.S_IMODE(st.st_mode)&0o022
             and 0<st.st_size<=limit,'host source/evidence metadata')
        data=b''
        while chunk:=os.read(fd,min(65536,limit+1-len(data))):
            data+=chunk
            need(len(data)<=limit,'host source/evidence bound')
        def stamp(s):
            return (s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        need(len(data)==st.st_size and stamp(st)==stamp(os.fstat(fd))==stamp(path.lstat()),'host file changed')
        return data
    finally:
        os.close(fd)

def load(name,path,pin):
    need(hashlib.sha256(raw(path)).hexdigest()==pin,'qualified source changed: '+str(path))
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
B=load('gpu_backend',HERE/'backend.py',SOURCE_PINS['backend.py'])
save=B.save
W=load('gpu_transport_worker',D/'oled-startup-live-driver-r1/ssh-worker.py','250647044223f7aa91ef174487e2c7318cf3c435b62f3154d0f4568f04afbefb')
SOURCE=dict(clean=True,revision='f02083f40d999bf095670b4c1a937058c7b035f0',worktree_digest='642669b91ba7db4188e039d92d420b25cd666f1b8f7ae4e76dcd35bcb7409e71')
QUERY=D/'gpu-query-arm64-r1/a/rog5-gpu-query.deploy'

def target(boot):
    need(re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',boot) and boot!='946acb59-744e-4bbc-b291-ac6b2e05f3fe','new GPU boot required')
    return dict(boot_id=boot,bundle='gpu-136f7-a9b1bc89566205b6',release='7.1.4-g136f75ae869a')

STAGE = "\nimport base64,hashlib,importlib.util,json,os,stat\nfrom pathlib import Path\ndef need(ok,why):\n    if not ok: raise ValueError(why)\nneed(os.geteuid()==0,'target root required')\nfiles={n:base64.b64decode(v,validate=True) for n,v in DATA['files'].items()}\nmanifest_raw=base64.b64decode(DATA['manifest'],validate=True)\nmanifest=json.loads(manifest_raw)\nneed(set(files)=={'backend.py', 'provider-proof.py', 'reprobe.py', 'initialize.py', 'provider.py', 'module-io.py', 'endpoint.py', 'load-display.py', 'provider-backend.py'},'fixed staging inventory')\nneed(hashlib.sha256(manifest_raw).hexdigest()==DATA['manifest_sha256'],'manifest input changed')\nneed({n:hashlib.sha256(v).hexdigest() for n,v in files.items()}==manifest['files'],'source input changed')\nneed(sum(map(len,files.values()))<131072,'RAM staging source byte bound')\nquery=base64.b64decode(DATA['query'],validate=True)\nneed(len(query)==542016 and hashlib.sha256(query).hexdigest()==DATA['query_sha256'],'RAM query identity')\nendpoint={'__name__':'staging_endpoint'}\nexec(compile(files['endpoint.py'],'endpoint.py','exec'),endpoint)\nwho=endpoint['identity'](manifest['boot_id'])\ndirectory=Path(DATA['namespace'])\nneed(directory==Path('/run/initramfs')/('rog5-gpu-iommu-display-'+manifest['owner']),'RAM namespace')\nneed(directory.parent.resolve()==directory.parent and directory.parent.stat().st_uid==0\n     and not stat.S_IMODE(directory.parent.stat().st_mode)&0o022,'RAM parent')\nneed(not os.path.lexists('/run/initramfs/rog5-gpu-iommu-display-entered.json') and not os.path.lexists('/run/initramfs/rog5-gpu-iommu-initialize-entered.json'),'prior GPU entry')\nrun_st=Path('/run').lstat();parent_st=directory.parent.lstat()\nneed(stat.S_ISDIR(run_st.st_mode) and run_st.st_uid==run_st.st_gid==0\n     and stat.S_IMODE(run_st.st_mode) in (0o755,0o1777),'RAM root metadata')\nneed(parent_st.st_uid==parent_st.st_gid==0 and stat.S_IMODE(parent_st.st_mode)==0o755\n     and parent_st.st_dev==run_st.st_dev,'RAM parent metadata/device')\ndevice=str(os.major(run_st.st_dev))+':'+str(os.minor(run_st.st_dev))\nmounts=[line.split(' - ',1)[1].split()[0] for line in Path('/proc/self/mountinfo').read_text().splitlines()\n        if line.split()[4]=='/run' and line.split()[2]==device]\nneed(mounts==['tmpfs'],'RAM filesystem')\nneed(type(manifest['owner'])is str and __import__('re').fullmatch('[0-9a-f]{32}',manifest['owner']),'GPU owner')\nneed(manifest['boot_id']!='946acb59-744e-4bbc-b291-ac6b2e05f3fe','source boot refused')\ndirectory.mkdir(mode=0o700)\nfor name,value in dict(files,**{'manifest.json':manifest_raw,'rog5-gpu-query':query}).items():\n    fd=os.open(directory/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o755 if name=='rog5-gpu-query' else 0o600)\n    try:\n        need(os.write(fd,value)==len(value),'short RAM staging write')\n        os.fsync(fd)\n    finally: os.close(fd)\nfd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)\ntry: os.fsync(fd)\nfinally: os.close(fd)\nspec=importlib.util.spec_from_file_location('staged_backend',directory/'backend.py')\nbackend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend)\nneed(backend.context(directory,DATA['manifest_sha256'])==manifest,'staged backend context')\nneed(endpoint['identity'](manifest['boot_id'])==who,'identity changed during staging')\nprint(json.dumps(dict(status='PASS_RAM_STAGE',identity=who,namespace=str(directory),\n                     manifest_sha256=DATA['manifest_sha256'],files=manifest['files'],query_sha256=DATA['query_sha256'])))\n"

def sources():
    files={name:raw(HERE/name,65536) for name in SOURCE_PINS}
    need({name:hashlib.sha256(data).hexdigest() for name,data in files.items()}==SOURCE_PINS,
         'target backend/component sources changed')
    return files

def identity(owner):
    return dict(phase='gpu-iommu-display',boot_id=owner.admission['boot_id'],owner=owner.admission['owner'],
                monitor_receipt_sha256=owner.receipt_sha)

def stage_plan(owner):
    who=identity(owner)
    need(re.fullmatch('[0-9a-f]{32}',who['owner']) and re.fullmatch('[0-9a-f]{64}',who['monitor_receipt_sha256']),
         'staging owner/receipt')
    target(who['boot_id'])
    files=sources()
    query=raw(QUERY,542016)
    need(len(query)==542016 and hashlib.sha256(query).hexdigest()==B.QUERY_SHA,'GPU query binary changed')
    manifest=dict(who,format='rog5-gpu-iommu-display-backend-v1',files=SOURCE_PINS)
    manifest_bytes=B.encoded(manifest)
    manifest_sha=hashlib.sha256(manifest_bytes).hexdigest()
    namespace='/run/initramfs/rog5-gpu-iommu-display-'+who['owner']
    data=dict(query=base64.b64encode(query).decode(),query_sha256=B.QUERY_SHA,namespace=namespace,manifest=base64.b64encode(manifest_bytes).decode(),
              manifest_sha256=manifest_sha,files={n:base64.b64encode(v).decode() for n,v in files.items()})
    # This payload is generated only from pinned local files, never user code.
    script='DATA='+repr(data)+'\n'+STAGE
    return dict(identity=who,namespace=namespace,manifest_sha256=manifest_sha,script=script,
                script_sha256=hashlib.sha256(script.encode()).hexdigest())

def stage(owner,output):
    owner.check()
    plan=stage_plan(owner)
    save(output/'stage-intent.json',{k:v for k,v in plan.items() if k!='script'})
    request=W.request(json.dumps(dict(format='rog5-one-usb-command-v1',mode='normal',
                     remote='python3 -I -B -',script=plan['script'],source=SOURCE,timeout=35)).encode())
    reply=W.perform(request,W.load_deployed())
    save(output/'stage-transport.json',reply)
    need(reply.get('status')=='PASS_TRANSPORT_COMPLETED' and reply.get('mode')=='normal'
         and reply.get('source')==SOURCE and reply.get('command_invoked') is True,'RAM staging transport')
    cmd=reply['command']
    out=base64.b64decode(cmd['stdout_base64'],validate=True)
    err=base64.b64decode(cmd['stderr_base64'],validate=True)
    need(cmd['returncode']==0 and cmd['timed_out'] is False and cmd['reaped'] is True
         and 0<len(out)<=16384 and not err and hashlib.sha256(out).hexdigest()==cmd['stdout_sha256']
         and hashlib.sha256(err).hexdigest()==cmd['stderr_sha256'],'RAM staging closure/output')
    expected=dict(status='PASS_RAM_STAGE',identity=target(owner.admission['boot_id']),
                  namespace=plan['namespace'],manifest_sha256=plan['manifest_sha256'],files=SOURCE_PINS,query_sha256=B.QUERY_SHA)
    need(B.decode(out)==expected,'RAM staging result differs')
    owner.check()
    save(output/'stage-result.json',expected)
    return plan

def ssh_argv(owner,plan):
    owner.check()
    deployed=W.load_deployed()
    cap=deployed.CAPTURE
    need(cap.ACCEPTANCE.source_identity()==SOURCE,'host source changed')
    need(cap.usb_mode(W.SERIAL)==('target',cap.INTERFACE),'USB identity/topology changed')
    deployed.host_gate(dict(serial=W.SERIAL))
    W.credentials()
    argv=deployed.ssh_command(W.KEY,W.HOSTS)
    need(argv[0]=='/usr/bin/ssh' and argv[-1]=='root@10.77.0.2','fixed SSH command')
    need(plan['namespace']=='/run/initramfs/rog5-gpu-iommu-display-'+owner.admission['owner']
         and re.fullmatch('[0-9a-f]{64}',plan['manifest_sha256']),'fixed target command')
    # Every interpolated part is fixed text or validated lowercase hexadecimal.
    return [*argv,'python3 -I -B '+plan['namespace']+'/backend.py --manifest-sha256 '+plan['manifest_sha256']]

def expected_intent(who):
    return B.intent(who)

def terminal(value,who):
    need(type(value)is dict and all(value.get(k)==v for k,v in who.items())
         and value.get('format')=='rog5-gpu-iommu-display-backend-result-v1'
         and value.get('status') in ('PASS_GPU_INITIALIZATION_AND_CLEANUP','FAIL')
         and value.get('entered') is True and value.get('acknowledged') is True
         and value.get('retry_allowed') is False and value.get('physical_scanout_verified') is False
         and value.get('physical_darkness_verified') is False,'terminal target identity/status')
    need(type(value.get('cleanup_errors'))is list,'terminal cleanup shape')
    reaped=True
    for field in ('action_process','cleanup_process'):
        process=value.get(field)
        good=(type(process)is dict and type(process.get('pid'))is int and process['pid']>1
              and process.get('reaped') is True and process.get('group_absent') is True
              and type(process.get('exitcode'))is int)
        reaped=reaped and good
    need(type(value.get('remote_reaped'))is bool and value['remote_reaped']==reaped,'target reaping claim differs')
    blank=value.get('blank')
    if blank is not None:
        need(type(blank)is dict and blank.get('status')=='PASS_ZERO_BRIGHTNESS_COMMAND'
             and type(blank.get('brightness_readback'))is int and blank['brightness_readback']==0
             and blank.get('after',{}).get('identity')==target(who['boot_id'])
             and type(blank['after'].get('brightness'))is int and blank['after']['brightness']==0,'zero evidence differs')
    if value['status']=='PASS_GPU_INITIALIZATION_AND_CLEANUP':
        component=value.get('component')
        need(reaped and blank is not None and value['cleanup_errors']==[] and value.get('error')is None
             and value['action_process']['exitcode']==value['cleanup_process']['exitcode']==0,
             'positive GPU result lacks closure')
        B.validate_component(component, who['boot_id'], who['owner'])
    need(value.get('hardware_acceleration_verified') is False,'unproven acceleration claim')
    return value

def exchange(owner,argv,output):
    """Actual duplex loop. argv is generated by ssh_argv in the production run.

    Test callers substitute only the transport process and phone/monitor boundary.
    Uncertain SSH start consumes the host phase reservation; never silently retry.
    """
    who=identity(owner)
    expected=expected_intent(who)
    save(owner.phase/'entered.json',dict(who,format='rog5-gpu-iommu-display-host-entry-v1',
         expected_intent=expected,started_monotonic=time.monotonic(),retry_allowed=False))
    child=None
    logs=[]
    failure=None
    target=None
    ready=ack=False
    sequence=0
    started=time.monotonic()
    deadline=started+NORMAL_SECONDS
    renew=started
    buffers={'stdout':b'','stderr':b''}
    counts={'stdout':0,'stderr':0}
    discard=False
    closed=False

    def fail(reason):
        nonlocal failure,deadline,closed
        if failure is None:
            failure=str(reason)[:2000]
            deadline=min(deadline,time.monotonic()+CLOSURE_SECONDS)
        if child is not None and not closed:
            child.stdin.close()
            closed=True

    def send(command,intent=None):
        nonlocal sequence,renew
        owner.check(seconds=5)
        sequence+=1
        B.send(child.stdin.fileno(),dict(who,sequence=sequence,command=command,intent_sha256=intent))
        renew=time.monotonic()+RENEW_SECONDS

    try:
        for name in ('stdout','stderr'):
            fd=os.open(output/('ssh.'+name),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            logs.append(os.fdopen(fd,'wb'))
        owner.check(seconds=5)
        child=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                               bufsize=0,start_new_session=True,env={'PATH':'/usr/bin:/bin','LC_ALL':'C'})
        save(output/'ssh-process.json',dict(pid=child.pid,argv=argv,started_monotonic=started))
        with selectors.DefaultSelector() as selector:
            for name in buffers:
                stream=getattr(child,name)
                os.set_blocking(stream.fileno(),False)
                selector.register(stream,selectors.EVENT_READ,name)
            while selector.get_map() or child.poll() is None:
                if time.monotonic()>=deadline:
                    raise TimeoutError('SSH closure deadline')
                if ready and target is None and failure is None and time.monotonic()>=renew:
                    try: send('lease')
                    except Exception as exc: fail(exc)
                for key,_ in selector.select(.05):
                    data=os.read(key.fd,4096)
                    if not data:
                        selector.unregister(key.fileobj)
                        if key.data=='stdout' and target is None: fail('SSH stdout closed before terminal')
                        continue
                    limit=OUTPUT_LIMIT if key.data=='stdout' else 4096
                    available=max(0,limit-counts[key.data])
                    logs[0 if key.data=='stdout' else 1].write(data[:available])
                    counts[key.data]+=len(data)
                    if counts[key.data]>limit:
                        fail('SSH output bound')
                        if key.data=='stdout': discard=True
                    if key.data=='stderr':
                        fail('SSH stderr is nonempty')
                        continue
                    if discard: continue
                    buffers['stdout']+=data
                    while b'\n' in buffers['stdout']:
                        line,buffers['stdout']=buffers['stdout'].split(b'\n',1)
                        try:
                            row=B.decode(line)
                            need(set(row)=={*who,'event','payload'} and all(row[k]==v for k,v in who.items()),'SSH event identity')
                            need(target is None,'data after terminal')
                            if row['event']=='transport-ready':
                                need(not ready and row['payload']==dict(lease_seconds=3.0,maximum_seconds=60.0),'transport-ready differs')
                                ready=True
                                if failure is None: send('start')
                            elif row['event']=='enter-request':
                                payload=row['payload']
                                need(ready and not ack and type(payload)is dict and set(payload)=={'intent','intent_sha256'}
                                     and B.encoded(payload['intent'])==B.encoded(expected)
                                     and payload['intent_sha256']==hashlib.sha256(B.encoded(expected)).hexdigest(),'module intent differs')
                                if failure is None:
                                    save(output/'entry-ack.json',dict(who,**payload,acknowledged_monotonic=time.monotonic()))
                                    send('enter-ack',payload['intent_sha256'])
                                    ack=True
                            elif row['event']=='component-progress':
                                need(ack and type(row['payload'])is dict,'GPU progress before entry')
                                need(len(list(output.glob('component-progress-*.json')))<16,'GPU progress bound')
                                save(output/('component-progress-%02d.json' % len(list(output.glob('component-progress-*.json')))),row['payload'])
                            elif row['event']=='terminal':
                                need(ack,'terminal before acknowledged entry')
                                target=terminal(row['payload'],who)
                                deadline=min(deadline,time.monotonic()+5)
                            else:
                                raise ValueError('unexpected SSH event')
                        except Exception as exc:
                            fail(exc)
                    if len(buffers['stdout'])>B.LINE:
                        fail('unterminated SSH record bound')
                        buffers['stdout']=b''
                        discard=True
            child.wait(timeout=1)
            need(not buffers['stdout'],'truncated SSH record')
            need(target is not None,'target terminal record absent')
            need(child.returncode==(0 if target['status']=='PASS_GPU_INITIALIZATION_AND_CLEANUP' else 1),'SSH exit differs from target')
    except Exception as exc:
        fail(exc)
    finally:
        if child is not None:
            if child.poll() is None:
                os.killpg(child.pid,signal.SIGKILL)
            child.wait(timeout=3)
            for name in ('stdin','stdout','stderr'):
                getattr(child,name).close()
        for log in logs:
            log.flush();os.fsync(log.fileno());log.close()
    result=dict(who,format='rog5-gpu-iommu-display-component-result-v1',
                status='COMPONENT_PASS' if failure is None and target and target['status']=='PASS_GPU_INITIALIZATION_AND_CLEANUP' else 'FAIL',
                blank=target['blank'] if target else None,remote_reaped=bool(target and target['remote_reaped']),
                cleanup_errors=target['cleanup_errors'] if target else [dict(stage='transport',reason='remote cleanup unproven')],
                ended_monotonic=time.monotonic(),started_monotonic=started,target=target,transport_error=failure,
                ssh_returncode=child.returncode if child else None,ssh_reaped=child is not None and child.poll() is not None,
                hardware_acceleration_verified=False,physical_scanout_verified=False,physical_darkness_verified=False,retry_allowed=False)
    save(owner.phase/'result.json',result)
    return result

if __name__=='__main__':raise SystemExit('Import-only: qualified live GPU coordinator required')

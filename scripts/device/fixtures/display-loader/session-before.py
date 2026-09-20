"""One explicit GPU session under the original boot controller's admission.

Called after the boot-only trial succeeds and before its launcher releases
credentials/bridges. Independent hardware receipts never rewrite boot evidence.
No retry, module unload, forced reboot, or physical/acceleration PASS.
"""
import base64,hashlib,importlib.util,json,math,os,stat,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;STATE=HERE.parent
OUTPUT=HERE/'session-r1'
LOGGER_SECONDS = 300
RECOVERY_RESERVE=2300  # 500-second session plus 1800 seconds retained for recovery.
SESSION_SECONDS = 500
PINS = {'gpu-iommu-session-r1/kernel-log.py': 'b690ae15bfced9c5cc3c9ab905209dc12dccb909678c31975fe6a32282a18d14', 'gpu-iommu-provider-r1/transport.py': 'a893eb01d60dd5a9d767a8d218397c6b338deba57f6c957dcc5b1f5aff633310', 'gpu-iommu-provider-r1/backend.py': '38dfdeff0180c9311f721bf76bb15d5b6edbd659dd5ea5466355be64c178faa1', 'gpu-iommu-provider-r1/module-io.py': 'c028b4ddd27ed43af9e7eda48c4dd21e5a685a1bda0ee61209eaa12df8f87620', 'gpu-iommu-provider-r1/provider.py': '3cc937fa611f0a85f75d234f75c8d3123e609735305a601f1077ce7a6a6f8924', 'gpu-iommu-provider-r1/reprobe.py': 'c2486e2c35ffc180b70d975523431169e338eff3774f14240b2b0353240562a5', 'gpu-iommu-display-r1/transport.py': '3d6f76bb421bf8f40967ac354d49e152248636b2272a1cf2653f8702e2a1a573', 'gpu-iommu-display-r1/backend.py': '840ba5ad5c1bfe2059bfc580fb45da4e8f3fef59f8e6627789cfe5ed38904a0d', 'gpu-iommu-display-r1/module-io.py': 'c028b4ddd27ed43af9e7eda48c4dd21e5a685a1bda0ee61209eaa12df8f87620', 'gpu-iommu-display-r1/load-display.py': '5c298ba05fe7a6f338471cd178a10b49cd9c03914f4a696ad442e7e0dbc1838d', 'gpu-iommu-display-r1/endpoint.py': '1c8c173d59a69cc514365844d179813b16d5ae6e7696ecfc9e12ccb999e654ca', 'gpu-iommu-display-r1/initialize.py': '373eb2bc855619e19901dd152344407ed3b119c6441e2d57b9716a7423181a38', 'gpu-iommu-display-r1/provider-proof.py': 'f73a9c55474fc38645e8b3f83809debc2b5fe1238dd69e291bf3c345e5b294d9', 'gpu-iommu-display-r1/provider-backend.py': '38dfdeff0180c9311f721bf76bb15d5b6edbd659dd5ea5466355be64c178faa1', 'gpu-iommu-display-r1/provider.py': '3cc937fa611f0a85f75d234f75c8d3123e609735305a601f1077ce7a6a6f8924', 'gpu-iommu-display-r1/reprobe.py': 'c2486e2c35ffc180b70d975523431169e338eff3774f14240b2b0353240562a5'}
HEALTH=STATE/'gpu-iommu-health-r1/successor-health.py'
HEALTH_SHA = '738f5d0b6bc6aef9f7b46babd7f53a46103696e8ce9624c21f2454d3de9bcb32'

def need(ok,why):
    if not ok:raise ValueError(why)

def load(name,path,pin):
    need(path.resolve()==path and path.stat().st_size<131072
         and hashlib.sha256(path.read_bytes()).hexdigest()==pin,'GPU session dependency changed')
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

T=load('gpu_session_transport',STATE/'gpu-iommu-display-r1/transport.py',PINS['gpu-iommu-display-r1/transport.py'])
P=load('gpu_session_provider',STATE/'gpu-iommu-provider-r1/transport.py',PINS['gpu-iommu-provider-r1/transport.py'])
K=load('gpu_session_log',HERE/'kernel-log.py',PINS['gpu-iommu-session-r1/kernel-log.py'])
H=load('gpu_session_health',HEALTH,HEALTH_SHA)
C=H.A.C
save=C.save

def cohort(ad):
    """Final boot admission must seal this complete session before any boot."""
    need(Path(ad.__file__).resolve()==STATE/'gpu-iommu-live-driver-r1/live-admission.py', 'GPU admission provider')
    locked=ad.inputs()['files']
    paths=[STATE/name for name in PINS]+[Path(__file__).resolve(),HEALTH,T.QUERY]
    for path in paths:
        key=str(path.relative_to(STATE));need(key in locked,'GPU session not in boot input lock: '+key)
        row=locked[key]
        ad.digest_file(path,row['size'],row['uid'],row['mode'],row['sha256'])
    for name,pin in PINS.items():
        need(hashlib.sha256(T.raw(STATE/name,131072)).hexdigest()==pin,'GPU session source changed')
    need(locked[str(HEALTH.relative_to(STATE))]['sha256']==HEALTH_SHA
         and locked[str(T.QUERY.relative_to(STATE))]['sha256']==T.B.QUERY_SHA,'GPU health/query lock differs')
    return {str(path.relative_to(STATE)):locked[str(path.relative_to(STATE))]['sha256'] for path in paths}

def admission(ad,controller,credentials,boot_result):
    cohort(ad)
    value=ad.common(controller.context)
    credentials.check()
    need(value['expires_monotonic']-time.monotonic()>=RECOVERY_RESERVE,'GPU recovery lifetime reserve')
    need(controller.output==ad.OUTPUT and controller.output==STATE/'gpu-iommu-controller-r1/execution', 'GPU boot controller output')
    actual=ad.receipt(ad.OUTPUT/'result.json',1048576)
    need(ad.A.exact_json(actual,boot_result) and boot_result.get('status')=='COMPONENT_PASS'
         and boot_result.get('successor_running') is True and boot_result.get('errors')==[], 'GPU requires completed healthy boot trial')
    need(boot_result['entered']==controller.entered and boot_result['phases']==list(controller.results)
         and controller.target_identity==boot_result['target_identity'], 'GPU boot controller history differs')
    target=T.target(boot_result['target_identity']['boot_id'])
    need(boot_result['target_identity']==target,'GPU target identity')
    health=controller.results.get('post_capture_health',{})
    closed=controller.results.get('close_capture',{})
    need(health.get('status')=='PASS' and health.get('identity')==target
         and health.get('current_boot_healthy') is True and health.get('physical_guards_passed') is True,
         'GPU predecessor full health absent')
    need(closed.get('status')=='PASS' and closed.get('capture_status')=='PASS'
         and closed.get('full_lifetime') is True and closed.get('cleanup_complete') is True, 'GPU predecessor capture incomplete')
    need(not any(name in controller.entered for name in ('locate_fallback','reboot_installed','stage_fallback','stage_target_recovery','restore_target_state')),
         'GPU trial already entered recovery')
    return value,target

class Owner:
    def __init__(self,ad,controller,credentials,target,entry_sha):
        self.ad,self.controller,self.credentials=ad,controller,credentials
        self.target=target;self.admission=dict(boot_id=target['boot_id'],owner=controller.context['owner'])
        self.receipt_sha=entry_sha;self.phase=None
        self.started=time.monotonic();self.health_at=None;self.logger=None
    def base(self,seconds=0):
        self.credentials.check()
        admitted=self.ad.common(self.controller.context)
        need(time.monotonic()+seconds<min(self.started+SESSION_SECONDS,admitted['expires_monotonic']), 'GPU session lifetime')
        need(hashlib.sha256(T.raw(OUTPUT/'entered.json',32768)).hexdigest()==self.receipt_sha, 'GPU session entry changed')
        return True
    def check(self,seconds=5):
        self.base(seconds)
        if self.logger is not None:self.logger.live(remaining=seconds)
        if self.health_at is not None:need(time.monotonic()-self.health_at<150,'GPU full health expired')
        return True

def collect_health(owner,label):
    owner.base(35)
    directory=OUTPUT/label;directory.mkdir(mode=0o700)
    boot=owner.target['boot_id'];script=H.script('target',boot)
    save(directory/'entered.json',dict(identity=owner.target,read_only=True,script_sha256=H.sha(script.encode())))
    request=T.W.request(json.dumps(dict(format='rog5-one-usb-command-v1',mode='normal',remote='python3 -I -B -',
        script=script,source=T.SOURCE,timeout=35)).encode())
    reply=T.W.perform(request,T.W.load_deployed());save(directory/'transport.json',reply)
    need(reply.get('status')=='PASS_TRANSPORT_COMPLETED' and reply.get('mode')=='normal'
         and reply.get('source')==T.SOURCE and reply.get('command_invoked') is True,'GPU health transport')
    command=reply['command'];out=base64.b64decode(command['stdout_base64'],validate=True)
    err=base64.b64decode(command['stderr_base64'],validate=True)
    need(H.sha(out)==command['stdout_sha256'] and H.sha(err)==command['stderr_sha256']
         and type(command.get('returncode')) is int and command['returncode']==0
         and command.get('reaped') is True and command.get('timed_out') is False and not err,
         'GPU health command closure/hash')
    value=H.validate(H.A.decode(out),'target',boot);owner.base()
    save(directory/'result.json',value);owner.health_at=time.monotonic();return value

def provider_result(value, owner):
    need(type(value) is dict and value.get('status')=='COMPONENT_PASS'
         and value.get('remote_reaped') is True and value.get('ssh_reaped') is True
         and value.get('cleanup_errors')==[], 'provider transport or cleanup failed')
    target=value.get('target')
    P.terminal(target,P.identity(owner))
    need(target['status']=='PASS_GPU_IOMMU_BINDING_AND_CLEANUP', 'provider did not complete')
    return hashlib.sha256(P.B.encoded(target)).hexdigest()

def display_result(value, owner, provider_sha):
    need(type(value) is dict and value.get('status')=='COMPONENT_PASS'
         and value.get('remote_reaped') is True and value.get('ssh_reaped') is True
         and value.get('blank') is not None and value.get('cleanup_errors')==[],
         'GPU component or cleanup failed')
    target=T.terminal(value.get('target'),T.identity(owner))
    need(target['status']=='PASS_GPU_INITIALIZATION_AND_CLEANUP', 'GPU initialization failed')
    proof=target['component']['provider']
    need(proof['result_sha256']==provider_sha, 'display used a different provider result')
    return dict(status='PASS_SAME_PROVIDER_HANDOFF',identity=owner.target,
                owner=owner.admission['owner'],provider_result_sha256=provider_sha)


def recovery(ad,controller,credentials):
    """Reuse still-owned fallback phases; no second RAM boot or forced reset."""
    credentials.check();ad.common(controller.context)
    before=list(controller.entered)
    try:
        controller.restore_fallback()
        result=dict(status='PASS_FALLBACK_RESTORED',selection_eligibility_restored=controller.selection_restored,
                    entered=controller.entered[len(before):],error=None)
        need(controller.selection_restored is True,'GPU fallback did not restore selection')
    except Exception as exc:
        result=dict(status='FAIL_RECOVERY_UNPROVEN',selection_eligibility_restored=False,
                    entered=controller.entered[len(before):],error=str(exc)[:1500])
    save(OUTPUT/'recovery.json',result);return result

def run(ad,controller,credentials,boot_result):
    """Both staged actions share one admitted owner and one bounded logger."""
    _,target=admission(ad,controller,credentials,boot_result)
    need(OUTPUT==HERE/'session-r1' and OUTPUT.resolve()==OUTPUT and os.getuid()==os.geteuid()==1000,
         'GPU session output/owner')
    OUTPUT.mkdir(mode=0o700)
    entry=dict(format='rog5-gpu-iommu-session-entry-v1',phase='gpu_initialize',mutation=True,
        context=controller.context,identity=target,cohort=cohort(ad),maximum_module_insertions=3,
        maximum_driver_probes=1,maximum_query_opens=1,maximum_query_ioctls=4,submit_calls=0,
        retry_allowed=False,logger_seconds=LOGGER_SECONDS,session_seconds=SESSION_SECONDS,
        boot_result_sha256=hashlib.sha256(T.raw(ad.OUTPUT/'result.json',1048576)).hexdigest())
    pin=save(OUTPUT/'entered.json',entry)
    owner=None;provider=component=after=logger=fallback=handoff=None;error=None;display_dispatched=False
    try:
        owner=Owner(ad,controller,credentials,target,pin)
        collect_health(owner,'health-before')
        provider_dir=OUTPUT/'provider';provider_dir.mkdir(mode=0o700)
        display_dir=OUTPUT/'display';display_dir.mkdir(mode=0o700)
        for directory in (provider_dir,display_dir):
            (directory/'staging').mkdir(mode=0o700)
            (directory/'hardware').mkdir(mode=0o700)
        # Stage code only while no operator window or hardware logger is running.
        provider_plan=P.stage(owner,provider_dir/'staging')
        display_plan=T.stage(owner,display_dir/'staging')
        collect_health(owner,'health-staged')
        owner.base(seconds=LOGGER_SECONDS+30)
        owner.logger=K.KernelLog(OUTPUT/'kernel-log',target['boot_id'],LOGGER_SECONDS)
        save(OUTPUT/'logger-ready.json',owner.logger.start())
        owner.check(seconds=260)
        owner.phase=provider_dir/'hardware'
        provider=P.exchange(owner,P.ssh_argv(owner,provider_plan),provider_dir)
        provider_sha=provider_result(provider,owner)
        owner.logger.live(remaining=170)
        collect_health(owner,'health-provider')
        owner.check(seconds=135)
        owner.phase=display_dir/'hardware'
        display_argv=T.ssh_argv(owner,display_plan)
        display_dispatched=True
        component=T.exchange(owner,display_argv,display_dir)
        handoff=display_result(component,owner,provider_sha)
        save(OUTPUT/'handoff.json',handoff)
        owner.logger.live(remaining=35)
        after=collect_health(owner,'health-after')
        owner.base(seconds=20)
        logger=owner.logger.close()
        owner.base()
        need(logger and logger.get('status')=='PASS' and logger.get('child_reaped') is True,
             'GPU logger closure failed')
    except Exception as exc:
        error=dict(type=type(exc).__name__,reason=str(exc)[:1500])
    finally:
        if owner is not None and owner.logger is not None and not owner.logger.closed:
            try:logger=owner.logger.close(cancel=True)
            except Exception as exc:
                error=dict(type=type(exc).__name__,reason='GPU logger cleanup: '+str(exc)[:1500],prior=error)
        if error is not None and after is None and owner is not None:
            try:after=collect_health(owner,'health-recovery')
            except Exception as exc:save(OUTPUT/'health-recovery-error.json',dict(error=str(exc)[:1500]))
        if error is not None and after is None:
            try:fallback=recovery(ad,controller,credentials)
            except Exception as exc:
                fallback=dict(status='FAIL_RECOVERY_UNPROVEN',error=str(exc)[:1500])
    # A failed display action can still have verified blank cleanup and healthy
    # target, without rewriting either component's failure. Provider-only failure
    # requires a closed read-only cleanup and never implies a working display.
    display_safe=bool(component and component.get('remote_reaped') is True
                      and component.get('blank') is not None and component.get('cleanup_errors')==[])
    provider_safe=bool(provider and provider.get('remote_reaped') is True
                       and provider.get('cleanup_snapshot') is not None and provider.get('cleanup_errors')==[])
    safe_target=bool(after and (display_safe if display_dispatched else provider_safe))
    final=dict(format='rog5-gpu-iommu-session-result-v1',
        status='PASS_GPU_INITIALIZATION_SESSION' if error is None else 'FAIL',identity=target,
        provider=provider,component=component,handoff=handoff,health_after=after,logger=logger,
        display_dispatched=display_dispatched,
        error=error,recovery=fallback,healthy_target_with_cleanup=safe_target,
        hardware_acceleration_verified=False,retry_allowed=False,release_qualified=False)
    save(OUTPUT/'result.json',final)
    return final


if __name__=='__main__':raise SystemExit('Import-only: final boot admission, live controller and recovery ownership required')

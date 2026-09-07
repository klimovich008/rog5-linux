"""Offline smoke-close eligibility. No process signalling or phone access."""
import copy, importlib.util, unittest
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
M=load('ordinary_smoke',HERE/'ordinary-boot-smoke.py')
F=load('ordinary_smoke_fixtures',HERE/'test-check-standalone-boot.py')

def fixture():
    d,record,hashes,producers=F.fixture()
    identity=d['root']['identity'];boot=identity['boot_id'];trial='1'*64
    def file(text):return dict(status='present',text=text,uid=0,gid=0,mode=0o444,nlink=1)
    health=dict(identity=copy.deepcopy(identity),uptime='65.0',files={
        'descriptor':file('format=rog5-persistent-wifi-health-v1\ntrial_id='+trial+
            '\nprimary_bundle='+identity['bundle']+'\nmode=try-once\n'),
        'healthy':file('format=rog5-native-wifi-healthy-v1\nboot_id='+boot+
            '\ntrial_id='+trial+'\nresult=PASS\n'),
        'ssh':file('format=rog5-persistent-ssh-identity-v1\nmode=load\n'
            'fingerprint=SHA256:'+'a'*43+'\nidentity_boot_id='+boot+'\n')},
        unit=dict(ActiveState='active',SubState='exited',Result='success',ExecMainStatus='0',
            ExecMainStartTimestampMonotonic='48723803',ExecMainExitTimestampMonotonic='58602748'))
    baseline=dict(status='PASS',s01_qualified=True,release_qualified=False,
        candidate=record['candidate'],identity=dict(identity,boot_id=d['entry']['source_boot_id']),
        artifact_hashes={'boot_bundle':record['boot_image_sha256'],'kernel':'a'*64})
    context=dict(identity=identity,record=record,artifact_hashes=baseline['artifact_hashes'],
        source=d['receipt']['source'],entry_monotonic=100,observed_monotonic=190,
        root=d['root_raw'],readiness=d['readiness']['actual'],health=health,
        events=[e for e in d['events'] if e['monotonic']<=190],source_boot_id=d['entry']['source_boot_id'])
    return baseline,context

class HealthTests(unittest.TestCase):
    def test_timeout_lattice_uses_contract_and_rejects_invalid_budgets(self):
        contract=M.B.ROOT.D.CAPTURE.ACCEPTANCE.load_contract()
        for values in ({'startup_seconds':301},{'preflight_seconds':31},
                       {'decision_seconds':True},{'receiver_stop_seconds':30}):
            changed=copy.deepcopy(contract);changed['defaults']['ordinary_smoke'].update(values)
            with patch.object(M.B.ROOT.D.CAPTURE.ACCEPTANCE,'load_contract',return_value=changed):
                with self.assertRaises(ValueError):M.timing()
    def test_real_output_shape(self):
        _,c=fixture();r=M.health(c['health'],c['identity'])
        self.assertAlmostEqual(r['commit_uptime_seconds'],58.602748)
    def test_stale_malformed_or_missing_records(self):
        for kind in ('descriptor','healthy','ssh'):
            with self.subTest(kind=kind):
                _,c=fixture();c['health']['files'][kind]['text']+='result=PASS\n'
                with self.assertRaises(ValueError):M.health(c['health'],c['identity'])
        _,c=fixture();c['health']['files']['healthy']['text']=c['health']['files']['healthy']['text'].replace(c['identity']['boot_id'],'old')
        with self.assertRaises(ValueError):M.health(c['health'],c['identity'])
    def test_absent_error_and_unsafe_metadata(self):
        for change in ({'status':'absent'},{'status':'error'},{'mode':0o644},{'uid':1},{'nlink':2},{'uid':False}):
            with self.subTest(change=change):
                _,c=fixture();c['health']['files']['healthy'].update(change)
                with self.assertRaises(ValueError):M.health(c['health'],c['identity'])
    def test_unit_incomplete_and_invalid_time(self):
        for key,value in (('ActiveState','activating'),('Result','exit-code'),('ExecMainStatus','1'),
                          ('ExecMainExitTimestampMonotonic','0'),('ExecMainExitTimestampMonotonic','66000000')):
            with self.subTest(key=key,value=value):
                _,c=fixture();c['health']['unit'][key]=value
                with self.assertRaises(ValueError):M.health(c['health'],c['identity'])
        for value in ('nan','inf','-1','301'):
            _,c=fixture();c['health']['uptime']=value
            with self.assertRaises(ValueError):M.health(c['health'],c['identity'])
    def test_wrong_trial_or_bundle(self):
        for old,new in (('1'*64,'2'*64),('try-once','normal')):
            _,c=fixture();c['health']['files']['descriptor']['text']=c['health']['files']['descriptor']['text'].replace(old,new)
            with self.assertRaises(ValueError):M.health(c['health'],c['identity'])

class CloseTests(unittest.TestCase):
    def test_eligible_never_qualifies_or_stops_anything(self):
        r=M.eligibility(*fixture())
        self.assertTrue(r['eligible']);self.assertFalse(r['s01_qualified']);self.assertFalse(r['release_qualified'])
        self.assertEqual(r['authority'],'none; coordinator must verify owned live capture and clean closure')
    def reject(self,change):
        b,c=fixture();change(b,c)
        with self.assertRaises((ValueError,KeyError,TypeError)):M.eligibility(b,c)
    def test_missing_full_qualification_or_wrong_release(self):
        self.reject(lambda b,c:b.update(s01_qualified=False))
        self.reject(lambda b,c:b.update(status='NOT RUN'))
        self.reject(lambda b,c:b.update(artifact_hashes={}))
    def test_repeated_boot_dirty_source_and_late_close(self):
        self.reject(lambda b,c:c.update(source_boot_id=c['identity']['boot_id']))
        self.reject(lambda b,c:c['source'].update(clean=False))
        self.reject(lambda b,c:c.update(observed_monotonic=401))
        self.reject(lambda b,c:c.update(observed_monotonic=float('nan')))
    def test_unsafe_power_storage_and_stale_readiness(self):
        self.reject(lambda b,c:c['root']['power'].update(temp='401'))
        self.reject(lambda b,c:c['root']['blocks'].update(sda24='0'))
        self.reject(lambda b,c:c['readiness'].update(marker_metadata='0:0:644:regular file:1'))
    def test_transport_loss_or_incomplete_preparation(self):
        self.reject(lambda b,c:c['events'].append(dict(event='transport-check-failed',monotonic=180)))
        self.reject(lambda b,c:c['events'].append(dict(event='transport',mode='absent',monotonic=180)))
        self.reject(lambda b,c:c['events'].pop(0))
        self.reject(lambda b,c:c['events'].clear())
    def test_interrupted_discovery_is_not_a_blanket_exception(self):
        b,c=fixture()
        c['events'].insert(-2,dict(event='usb-discovery-interrupted',monotonic=110,
            target_seen=False,phase='usb-discovery',errno=19,operation='product',
            observed_mode='absent',last_stage=None,last_startup=None))
        self.assertTrue(M.eligibility(b,c)['eligible'])
        self.reject(lambda b,c:c['events'].insert(-1,dict(event='usb-discovery-interrupted',
            monotonic=130,target_seen=False,phase='usb-discovery',errno=19,operation='product',
            observed_mode='absent',last_stage=None,last_startup=None)))
    def test_missing_execution_family_and_wrong_stage(self):
        self.reject(lambda b,c:c['record'].pop('execution'))
        self.reject(lambda b,c:c['events'][-1]['stage'].update(boot_id=c['source_boot_id']))
        self.reject(lambda b,c:c['events'][-1]['stage'].update(state='FAIL'))

def closed_fixture():
    baseline,context=fixture()
    end=dict(event='capture-ended',monotonic=192,status='NOT RUN',source_boot_id=context['source_boot_id'],
        source_disconnected=True,last_stage=context['events'][-1]['stage'])
    events=copy.deepcopy(context['events'])+[end]+[
        dict(event='host-cleanup',item=item,status='PASS',monotonic=193+i)
        for i,item in enumerate(('route','firewall','profile','address'))]
    closure=dict(source=context['source'],identity=context['identity'],operation='ordinary-boot-smoke',
        reboot_returncode=0,receiver_returncode=0,close_requested_monotonic=191,
        finished_monotonic=197,events=events)
    return baseline,context,closure

class ClosedTests(unittest.TestCase):
    def test_clean_close_is_not_full_qualification(self):
        result=M.closed(*closed_fixture())
        self.assertEqual(result['status'],'PASS');self.assertFalse(result['s01_qualified'])
        self.assertFalse(result['s05_qualified']);self.assertFalse(result['release_qualified'])
    def reject(self,change):
        b,c,end=closed_fixture();change(end)
        with self.assertRaises((ValueError,KeyError,TypeError)):M.closed(b,c,end)
    def test_failed_ambiguous_or_missing_exit(self):
        for field,value in (('receiver_returncode',1),('receiver_returncode',None),
                            ('reboot_returncode',255),('reboot_returncode',False)):
            self.reject(lambda end:end.update({field:value}))
    def test_stale_decision_and_late_cleanup(self):
        self.reject(lambda end:end.update(close_requested_monotonic=196))
        self.reject(lambda end:end.update(finished_monotonic=431))
        self.reject(lambda end:end['events'][-1].update(monotonic=250))
        self.reject(lambda end:end['events'].append(dict(event='transport',mode='target',monotonic=198)))
    def test_missing_failed_or_reordered_cleanup(self):
        self.reject(lambda end:end['events'].pop())
        self.reject(lambda end:end['events'][-1].update(status='FAIL'))
        self.reject(lambda end:end['events'][-1].update(item='route'))
    def test_changed_prefix_and_late_transport_loss(self):
        self.reject(lambda end:end['events'][0].update(monotonic=1))
        self.reject(lambda end:end['events'].insert(-5,dict(event='transport',mode='absent',monotonic=191)))
        self.reject(lambda end:end['events'].insert(-5,dict(event='transport-check-failed',monotonic=191)))
    def test_failed_capture_or_other_boot(self):
        self.reject(lambda end:end['events'][-5].update(status='FAIL'))
        self.reject(lambda end:end.update(operation='experimental-retry'))

def sequence_fixture():
    base,c,end=closed_fixture();run=dict(source=c['source'],started_monotonic=90,finished_monotonic=600,boots=[])
    previous=c['source_boot_id']
    for n in range(3):
        before,context,closure=closed_fixture();new=f'{n+3:08d}-3333-4333-8333-333333333333'
        original=context['identity']['boot_id'];old=context['source_boot_id']
        def replace(value):
            if isinstance(value,dict):
                return {k:(v+n*200 if k in ('monotonic','entry_monotonic','observed_monotonic',
                    'close_requested_monotonic','finished_monotonic') else replace(v)) for k,v in value.items()}
            if isinstance(value,list):return [replace(v) for v in value]
            if isinstance(value,str):return value.replace(original,new).replace(old,previous)
            return value
        run['boots'].append(dict(context=replace(context),closure=replace(closure),preflight_monotonic=95+n*200))
        previous=new
    return base,run

class SequenceTests(unittest.TestCase):
    def test_three_boots_are_only_a_component_until_pinned_replay(self):
        result=M.sequence(*sequence_fixture());self.assertEqual(result['status'],'PASS')
        self.assertEqual(len(set(result['boot_ids'])),3);self.assertFalse(result['s05_qualified'])
    def reject(self,change):
        b,run=sequence_fixture();change(run)
        with self.assertRaises((ValueError,KeyError,TypeError)):M.sequence(b,run)
    def test_missing_failed_intermediary_or_excess_boot(self):
        self.reject(lambda r:r['boots'].pop())
        self.reject(lambda r:r['boots'].append(r['boots'][0]))
        self.reject(lambda r:r['boots'][1]['closure'].update(reboot_returncode=255))
        self.reject(lambda r:r['boots'][1]['context'].update(source_boot_id=r['boots'][0]['context']['source_boot_id']))
    def test_total_deadline_preflight_and_source(self):
        self.reject(lambda r:r.update(finished_monotonic=1171))
        self.reject(lambda r:r['boots'][0].update(preflight_monotonic=50))
        self.reject(lambda r:r['boots'][1].update(preflight_monotonic=150))
        self.reject(lambda r:r['boots'][2]['context'].update(source={}))

if __name__=='__main__':unittest.main()

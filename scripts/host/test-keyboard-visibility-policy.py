#!/usr/bin/env python3
"""Execute actual keyboard visibility control with real Dart grace-period timers.

State/controller methods and the configured Duration are extracted from source;
provider/build-generation adapters do not qualify Flutter, VM or phone behavior.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import time
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('caret',HERE/'test-keyboard-caret-visibility.py')
caret=importlib.util.module_from_spec(spec);spec.loader.exec_module(caret)
CASES=['caret_only_false','caret_only_true','native_close','deactivate','activation',
       'manual_pan','manual_open_race','reset','old_generation','legacy']
FIELDS=r'''
 (bool,bool,bool,int)? _automaticSoftwareKeyboardPolicy;
 bool _quickSettingsDragStartedOpen=false,_quickSettingsDragMoved=false;
 bool _refreshInProgress=false,_refreshQueued=false,_hasLoadedWindowSnapshot=false;
 int _nextLaunchRequestId=1;Timer? _launchRequestTimer;bool? _lastMirroredNativeLock;
 StreamSubscription<DenialTextInputState>? _textInputStateSubscription;
 final Set<String> _backgroundLaunchAppIds={};
 final _bridge=Object();Object _inputLayoutCoordinator=Object();
 @RESET@
'''
MAIN=r'''
class ShellInputLayoutCoordinator {ShellInputLayoutCoordinator(Object bridge);}
Future<void> main(List<String> args) async {
 final mode=args.single;final c=Control();c._automaticSoftwareKeyboard=true;
 c.state=State.initial().copyWith(windows:[Window()],foregroundObjectId:7,
   edgePanelAnimationProgress:1);
 DenialTextInputCaret rectangle(double y)=>DenialTextInputCaret(windowId:7,surfaceId:70,
   rect:Rect.fromLTWH(0,y,0,20));
 void deliver({bool active=true,bool visible=false,bool legacy=false,int serial=1,double y=80})=>
   c._handleTextInputState(DenialTextInputState(active:active,inputPanelVisible:visible,
     legacy:legacy,contentHint:0,contentPurpose:0,activationSerial:serial,
     caret:active?rectangle(y):null));
 Future<void> settle()=>Future<void>.delayed(Control._automaticSoftwareKeyboardCloseGrace*2);
 try {
  if(mode=='caret_only_false'){
   deliver();await settle();require(!c.state.edgePanelVisible,'initial false settled');
   c.openEdgePanel();deliver(y:90);await settle();
   require(c.state.edgePanelVisible,'caret-only false policy cannot undo manual opening');
   near(c.state.textInputCaret!.rect.top,90,'new caret still updates');
  }else if(mode=='caret_only_true'){
   deliver(visible:true);require(c.state.edgePanelVisible,'native show');
   c.closeEdgePanel();deliver(visible:true,y:90);await settle();
   require(!c.state.edgePanelVisible,'caret-only true policy cannot undo manual closing');
  }else if(mode=='native_close'){
   deliver(visible:true);deliver(visible:false);await settle();
   require(!c.state.edgePanelVisible,'actual visible-to-hidden transition closes');
  }else if(mode=='deactivate'){
   deliver();await settle();c.openEdgePanel();deliver(active:false);await settle();
   require(!c.state.edgePanelVisible,'deactivation closes even if panel flag was already false');
   require(c.state.textInputCaret==null,'deactivation clears caret');
  }else if(mode=='activation'){
   deliver(serial:100);await settle();c.openEdgePanel();deliver(serial:1);await settle();
   require(!c.state.edgePanelVisible,'new activation re-applies false policy');
  }else if(mode=='manual_pan'){
   deliver(y:1100);await settle();c.openEdgePanel();
   c.updateEdgePanelViewportScroll(20,367.2,currentOffset:319.2);
   final scroll=c.state.edgePanelViewportScroll;
   deliver(y:1101);await settle();
   require(c.state.edgePanelVisible && c.state.edgePanelViewportManual,'geometry preserves manual panel and pan');
   near(c.state.edgePanelViewportScroll,scroll,'manual position retained');
  }else if(mode=='manual_open_race'){
   deliver();require(c._automaticSoftwareKeyboardCloseTimer!=null,'native close pending');
   c.openEdgePanel();await settle();
   require(c.state.edgePanelVisible,'explicit opening cancels previous pending close');
  }else if(mode=='reset'){
   deliver();await settle();c.openEdgePanel();c._resetBuildFields();deliver();await settle();
   require(!c.state.edgePanelVisible,'build reset clears cached policy');
  }else if(mode=='old_generation'){
   deliver();c._buildGeneration=2;c.state=c.state.copyWith(edgePanelVisible:true);await settle();
   require(c.state.edgePanelVisible,'old build timer cannot close replacement state');
  }else if(mode=='legacy'){
   deliver(visible:true,legacy:true);require(!c.state.edgePanelVisible,'unregistered legacy application remains refused');
   c._legacyTextInputAppIds.add('mousepad');deliver(visible:true,legacy:true,serial:2);
   require(c.state.edgePanelVisible,'registered legacy application remains supported');
  }else{throw StateError('unknown case');}
  print('PASS $mode grace=${Control._automaticSoftwareKeyboardCloseGrace.inMicroseconds}us');
 }finally{c._automaticSoftwareKeyboardCloseTimer?.cancel();c._launchRequestTimer?.cancel();}
}
'''

def unit_for(root,controller):
    unit,_,paths=caret.unit_for(root);unit=unit[:unit.index('void main(List<String> args)')]
    original=(root/'state/shell_controller.dart').read_text();text=controller.read_text();m=caret.animation.method
    for name in ['_handleTextInputState','openEdgePanel','closeEdgePanel']:
        a=m(original,'  void '+name+'(');b=m(text,'  void '+name+'(')
        if a not in unit:raise ValueError('actual method absent from unit: '+name)
        unit=unit.replace(a,b,1)
    match=re.search(r'  static const Duration _automaticSoftwareKeyboardCloseGrace = Duration\([\s\S]*?\n  \);',text)
    if not match:raise ValueError('exact close-grace constant unavailable')
    unit=unit.replace('static const _automaticSoftwareKeyboardCloseGrace=Duration(milliseconds:1);',match.group().strip())
    unit=unit.replace('bool isBuildGenerationActive(int generation)=>generation==1;',
                      'bool isBuildGenerationActive(int generation)=>generation==_buildGeneration;')
    fields=FIELDS
    if '(bool,bool,bool,int)? _automaticSoftwareKeyboardPolicy;' in unit:
        fields=fields.replace(' (bool,bool,bool,int)? _automaticSoftwareKeyboardPolicy;\n','')
    unit=unit.replace('class Control {','class Control {\n'+fields.replace('@RESET@',m(text,'  void _resetBuildFields(')),1)
    return unit+MAIN,paths


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--controller-file',type=Path,required=True)
    p.add_argument('--dart',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--case',choices=CASES,action='append',dest='selected_cases')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    root=a.source/'dart_shell/lib/src';unit,paths=unit_for(root,a.controller_file)
    script=a.output/'test.dart';script.write_text(unit)
    result={'scope':__doc__,'source_hashes':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in paths},
      'controller':{'path':str(a.controller_file),'sha256':hashlib.sha256(a.controller_file.read_bytes()).hexdigest()},
      'unit_sha256':hashlib.sha256(unit.encode()).hexdigest(),'runs':[],'VM':'NOT RUN','phone':'NOT RUN'}
    compilation_failed=False
    for mode in a.selected_cases or CASES:
        command=[a.dart,str(script),mode]
        if compilation_failed:
            result['runs'].append({'case':mode,'command':command,'status':'BLOCKED','reason':'shared unit failed compilation'});continue
        start=time.monotonic();r=subprocess.run(command,capture_output=True,text=True,timeout=45)
        (a.output/(mode+'.log')).write_text(r.stdout+r.stderr)
        result['runs'].append({'case':mode,'command':command,'exit_status':r.returncode,
                              'seconds':time.monotonic()-start,'status':'PASS' if r.returncode==0 else 'FAIL'})
        if r.returncode and ': Error:' in r.stdout+r.stderr:
            result['runs'][-1]['failure_kind']='compilation';compilation_failed=True
    result['counts']={s:sum(r['status']==s for r in result['runs']) for s in ['PASS','FAIL','BLOCKED']}
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['counts']))
    return int(bool(result['counts']['FAIL']))


if __name__=='__main__':raise SystemExit(main())

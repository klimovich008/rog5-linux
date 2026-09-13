#!/usr/bin/env python3
"""Execute actual publisher selection/scheduling and caret paint/input methods.

Provider invalidation is a thin record-equality adapter, not a Riverpod runtime.
The actual build select expression, post-frame callback, window configure tracker,
shared caret geometry and native input layout run. No Flutter rasterization,
Wayland delivery, VM or phone qualification is inferred.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('caret',HERE/'test-keyboard-caret-visibility.py')
caret=importlib.util.module_from_spec(spec);spec.loader.exec_module(caret)
CASES=['caret_only','size_change','manual_flag','unfocused_window','coalesced','disposed','unchanged']
ADAPTERS=r'''
final shellInteractionRegistryProvider=Object(),denialBridgeProvider=Object();
final nativeLayout=Layout();
class Bridge {
 final configured=<int>[];
 void configureWindow(Window window,Rect geometry,{required bool exact}) {
   require(exact,'configuration must remain exact');configured.add(window.objectId);
 }
}
class PublisherRef {
 PublisherRef(this.control);final Control control;final bridge=Bridge();
 Object? Function(State)? selection;Object? selected;
 dynamic watch(Object provider) {
   if(provider is Selector) {
     selection=(s)=>provider.read(s);selected=selection!(control.state);return selected;
   }
   require(identical(provider,shellInteractionRegistryProvider),'unexpected watched provider');
   return ShellInteractionSnapshot();
 }
 bool get changed=>selection!(control.state)!=selected;
 dynamic read(Object provider) {
   if(identical(provider,shellControllerProvider))return control.state;
   if(identical(provider,shellControllerProvider.notifier))return control;
   if(identical(provider,denialBridgeProvider))return bridge;
   if(identical(provider,shellInteractionRegistryProvider))return ShellInteractionSnapshot();
   throw StateError('unexpected read provider');
 }
}
class MediaQuery {static Size sizeOf(BuildContext context)=>const Size(540,1224);}
class WidgetsBinding {
 static final instance=WidgetsBinding();final callbacks=<void Function(Duration)>[];
 void addPostFrameCallback(void Function(Duration) callback)=>callbacks.add(callback);
 void pump(){final pending=List.of(callbacks);callbacks.clear();for(final callback in pending){callback(Duration.zero);}}
}
class PublisherWidget {final child=Widget();}
class Publisher {
 Publisher(this.ref);final PublisherRef ref;bool mounted=true;final widget=PublisherWidget();
 bool _scheduled=false;final _configureTracker=MobileWindowConfigureTracker();
 @PUBLISHER@
}
@TRACKER@
'''
MAIN=r'''
void main(List<String> args) {
 final mode=args.single;final c=Control();final window=Window();
 c.state=State.initial().copyWith(windows:[window],foregroundObjectId:7,
   edgePanelVisible:true,edgePanelAnimationProgress:1);
 DenialTextInputCaret makeCaret(double y)=>DenialTextInputCaret(windowId:7,surfaceId:70,
   rect:Rect.fromLTWH(0,y,0,20));
 void deliver(double y)=>c._handleTextInputState(DenialTextInputState(active:true,
   inputPanelVisible:true,legacy:false,contentHint:0,contentPurpose:0,
   activationSerial:1,caret:makeCaret(y)));
 deliver(mode=='size_change'?1100:80);
 final ref=PublisherRef(c);final publisher=Publisher(ref);
 void buildIfChanged(){if(ref.changed)publisher.build(BuildContext());}
 double paint(){final v=MobileKeyboardViewport(child:Widget());
   return -((v.build(BuildContext(),Ref(c))as LayoutBuilder).result as Transform).offset.dy;}
 double input(){final region=nativeLayout.windows.single;
   return 48-region.rect.top+region.sourceRect.top;}
 publisher.build(BuildContext());WidgetsBinding.instance.pump();
 near(input(),paint(),'initial publication');require(c.publications==1,'initial publishes once');
 if(mode=='caret_only'){
   deliver(1100);buildIfChanged();WidgetsBinding.instance.pump();
   near(paint(),319.2,'new caret moves painted window');
   near(input(),paint(),'caret-only change republishes matching input');
 }else if(mode=='size_change'){
   c.state=c.state.copyWith(windows:[Window(contentHeight:2352)]);
   buildIfChanged();WidgetsBinding.instance.pump();
   near(paint(),0,'new logical content size changes projection');
   near(input(),paint(),'same-owner metadata republishes matching input');
 }else if(mode=='manual_flag'){
   c.state=c.state.copyWith(edgePanelViewportManual:true);
   near(c.state.edgePanelViewportScroll,0,'scroll value unchanged');
   buildIfChanged();WidgetsBinding.instance.pump();
   near(paint(),367.2,'manual policy changes painted offset');
   near(input(),paint(),'manual-only change republishes matching input');
 }else if(mode=='unfocused_window'){
   c.state=c.state.copyWith(windows:[window,Window(objectId:8,surfaceId:80,surfaces:[80])]);
   buildIfChanged();WidgetsBinding.instance.pump();
   require(ref.bridge.configured.length==2 && ref.bridge.configured.last==8,
     'new unfocused window receives its initial exact configure');
 }else if(mode=='coalesced'){
   deliver(1000);buildIfChanged();deliver(1100);buildIfChanged();
   require(WidgetsBinding.instance.callbacks.length==1,'one pending post-frame callback');
   near(input(),0,'input unchanged before callback');WidgetsBinding.instance.pump();
   near(input(),paint(),'callback uses latest state');require(c.publications==2,'one final publication');
 }else if(mode=='disposed'){
   deliver(1100);buildIfChanged();publisher.mounted=false;WidgetsBinding.instance.pump();
   require(c.publications==1,'disposed publisher never writes native geometry');
 }else if(mode=='unchanged'){
   require(!ref.changed,'unchanged immutable state leaves record equal');
   buildIfChanged();WidgetsBinding.instance.pump();require(c.publications==1,'no redundant publication');
 }else{throw StateError('unknown case');}
 print('PASS $mode');
}
'''


def unit_for(root,publisher):
    unit,_,paths=caret.unit_for(root)
    unit=unit[:unit.index('void main(List<String> args)')]
    unit=unit.replace("class AppLaunchRequest {static", "class AppLaunchRequest {final requestId=1;static")
    unit=unit.replace("final isUserApp=true;final appId=", "final isUserApp=true,isLocalFlutter=false;final appId=")
    unit=unit.replace('class Control {','''class Control {
 int publications=0;
 void publishInputLayout(Size size,ShellInteractionSnapshot interactions) {
   nativeLayout.publish(state:state,viewSize:size,interactions:interactions);publications++;
 }
''',1)
    text=publisher.read_text();m=caret.animation.method
    methods='\n'.join(m(text,marker) for marker in ['  Widget build(', '  void _schedulePublish(', '  void _configureMobileWindows('])
    tracker=text[text.index('class MobileWindowConfigureTracker {'):]
    return unit+ADAPTERS.replace('@PUBLISHER@',methods).replace('@TRACKER@',tracker)+MAIN,paths


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--publisher-file',type=Path,required=True)
    p.add_argument('--dart',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--case',choices=CASES,action='append',dest='selected_cases')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    root=a.source/'dart_shell/lib/src';unit,paths=unit_for(root,a.publisher_file)
    script=a.output/'test.dart';script.write_text(unit)
    result={'scope':__doc__,'source_hashes':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in paths},
      'publisher':{'path':str(a.publisher_file),'sha256':hashlib.sha256(a.publisher_file.read_bytes()).hexdigest()},
      'unit_sha256':hashlib.sha256(unit.encode()).hexdigest(),'runs':[],'VM':'NOT RUN','phone':'NOT RUN'}
    compilation_failed=False
    for mode in a.selected_cases or CASES:
        command=[a.dart,str(script),mode]
        if compilation_failed:
            result['runs'].append({'case':mode,'command':command,'status':'BLOCKED','reason':'shared unit failed compilation'})
            continue
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

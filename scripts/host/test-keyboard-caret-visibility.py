#!/usr/bin/env python3
"""Execute exact Dart caret/state/controller and paint/input geometry methods.

Geometry, widget and scheduler adapters are not Flutter rasterization, Wayland
protocol delivery, VM or phone proof. An uncorrected source runs the top-caret
counterexample against its actual MobileKeyboardViewport implementation.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('animation', HERE/'test-keyboard-animation-geometry.py')
animation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(animation)

WINDOW = r'''
class AppLaunchRequest {static String normalizeAppId(String v)=>v;}
class Window {
 Window({this.objectId=7,this.surfaceId=70,this.contentX=0,this.contentY=0,
 this.contentWidth=540,this.contentHeight=1176,this.surfaces=const [70,71]});
 final int objectId,surfaceId;int get windowId=>objectId;
 final double contentX,contentY,contentWidth,contentHeight;
 final List<int> surfaces;final isUserApp=true;final appId='mousepad';
 final List<dynamic> popupRoots=[];
 List<int> get visibleSurfaceIds=>surfaces;
 Rect get contentCoordinateRect=>Rect.fromLTWH(contentX,contentY,contentWidth,contentHeight);
 dynamic mapSurfaceRect(dynamic popup,Rect rect)=>throw StateError('unexpected popup');
}
'''
CONTROL = r'''
class Control {
 State state=State.initial();Offset _rawGestureDrag=Offset.zero,_gestureLockOrigin=Offset.zero;
 _GestureAxis _gestureAxis=_GestureAxis.undecided;
 bool _edgePanelDragStartedOpen=false,_edgePanelDragMoved=false;
 static const _edgePanelFlickVelocity=520.0;
 bool _automaticSoftwareKeyboard=false;
 final Set<String> _legacyTextInputAppIds={};
 Timer? _automaticSoftwareKeyboardCloseTimer;
 static const _automaticSoftwareKeyboardCloseGrace=Duration(milliseconds:1);
 int _buildGeneration=1;bool isBuildGenerationActive(int generation)=>generation==1;
 @CONTROL@
}
'''
CASES = ['top', 'bottom', 'scaled', 'zero_width', 'owner', 'pending', 'clear',
         'activation', 'manual', 'manual_missing', 'closing', 'partial', 'invalid']
MAIN = r'''
void main(List<String> args) {
 final mode=args.single;final c=Control();final layout=Layout();const size=Size(540,1224);
 Window window=Window();
 c.state=State.initial().copyWith(windows:[window],foregroundObjectId:7,
   edgePanelVisible:true,edgePanelAnimationProgress:1);
 DenialTextInputCaret caret({int owner=7,int surface=70,double y=80,double width=0,double height=20})=>
   DenialTextInputCaret(windowId:owner,surfaceId:surface,rect:Rect.fromLTWH(0,y,width,height));
 void deliver(DenialTextInputCaret? value,{int serial=1,bool active=true,bool legacy=false})=>
   c._handleTextInputState(DenialTextInputState(active:active,inputPanelVisible:active,
     legacy:legacy,contentHint:0,contentPurpose:0,activationSerial:serial,caret:value));
 double paint() {
   final viewport=MobileKeyboardViewport(child:Widget());
   return -((viewport.build(BuildContext(),Ref(c)) as LayoutBuilder).result as Transform).offset.dy;
 }
 void agree(double offset) {
   near(paint(),offset,'paint translation');
   layout.publish(state:c.state,viewSize:size,interactions:ShellInteractionSnapshot());
   final region=layout.windows.single;
   near(48-region.rect.top+region.sourceRect.top,offset,'input translation agrees');
   near(layout.keyboard.first.top,1224-367.2*c.state.edgePanelAnimationProgress,'keyboard boundary');
 }
 if(mode=='top'){
   deliver(caret());agree(0);
 }else if(mode=='bottom'){
   deliver(caret(y:1100));agree(319.2);
 }else if(mode=='scaled'){
   window=Window(contentX:100,contentY:200,contentWidth:1080,contentHeight:2352);
   c.state=c.state.copyWith(windows:[window]);deliver(caret(y:2200,height:40));agree(319.2);
 }else if(mode=='zero_width'){
   final value=caret(y:1100,width:0);require(value.isValid,'zero width is valid');
   deliver(value);agree(319.2);
 }else if(mode=='owner'){
   deliver(caret(owner:8));agree(367.2);
   deliver(caret(surface:99));agree(367.2);
   deliver(caret(surface:71));agree(0);
 }else if(mode=='pending'){
   deliver(caret(owner:8,surface:80));agree(367.2);
   final next=Window(objectId:8,surfaceId:80,surfaces:[80]);
   c.state=c.state.copyWith(windows:[window,next]);
   require(c.state.textInputCaret?.windowId==8,'metadata must retain future owner');
   agree(367.2);
   c.state=c.state.copyWith(foregroundObjectId:8);agree(0);
   c.state=c.state.copyWith(foregroundObjectId:7);
   require(c.state.textInputCaret==null,'focus away retires caret');
   c.state=c.state.copyWith(foregroundObjectId:8);agree(367.2);
 }else if(mode=='clear'){
   deliver(caret());deliver(null,active:false);
   require(c.state.textInputCaret==null,'disable retires caret');agree(367.2);
   deliver(caret());c.state=c.state.copyWith(locked:true,lockLayerVisible:true);
   require(c.state.textInputCaret==null,'lock retires caret');
   c.state=c.state.copyWith(locked:false,lockLayerVisible:false);
   deliver(caret(surface:71));c.state=c.state.copyWith(windows:[Window(surfaces:[70])]);
   require(c.state.textInputCaret==null,'subsurface removal retires caret');
   deliver(caret());c.state=c.state.copyWith(windows:[]);
   require(c.state.textInputCaret==null,'window destruction retires caret');
 }else if(mode=='activation'){
   deliver(caret(y:1100),serial:100);
   c.updateEdgePanelViewportScroll(20,367.2,currentOffset:paint());agree(299.2);
   deliver(caret(y:1100),serial:1);
   require(!c.state.edgePanelViewportManual,'changed lower serial resets override');agree(319.2);
 }else if(mode=='manual'){
   deliver(caret(y:1100));final before=paint();
   c.updateEdgePanelViewportScroll(20,367.2,currentOffset:before);agree(before-20);
   require(c.state.edgePanelViewportManual,'pan records override');
   deliver(caret(y:80));agree(before-20);
   c.updateEdgePanelViewportScroll(1000,367.2,currentOffset:paint());agree(0);
   c.updateEdgePanelViewportScroll(-1000,367.2,currentOffset:paint());agree(367.2);
 }else if(mode=='manual_missing'){
   deliver(caret(y:1100));c.updateEdgePanelViewportScroll(20,367.2,currentOffset:paint());
   deliver(null);require(c.state.edgePanelViewportManual,'same activation missing caret preserves manual override');
   agree(299.2);
 }else if(mode=='closing'){
   deliver(caret(y:1100));c.updateEdgePanelViewportScroll(20,367.2,currentOffset:paint());
   c.closeEdgePanel();agree(299.2);
   c.updateEdgePanelAnimationProgress(.5);agree(115.6);
   c.updateEdgePanelAnimationProgress(0);
   require(!c.state.edgePanelViewportManual,'closed resets override');near(paint(),0,'closed offset');
   c.openEdgePanel();c.updateEdgePanelAnimationProgress(1);agree(319.2);
 }else if(mode=='partial'){
   deliver(caret(y:1100));c.updateEdgePanelAnimationProgress(.5);agree(135.6);
   c.updateEdgePanelAnimationProgress(.1);agree(0);
 }else if(mode=='invalid'){
   deliver(caret(height:0));agree(367.2);
   deliver(caret(width:-1));agree(367.2);
   deliver(caret(y:double.nan));agree(367.2);
   c.updateEdgePanelViewportScroll(double.nan,367.2,currentOffset:0);
   require(!c.state.edgePanelViewportManual,'invalid manual motion refused');
 }else {throw StateError('unknown case');}
 print('PASS $mode');
}
'''


def unit_for(root):
    paths = ['input/input_layout.dart', 'state/shell_controller.dart',
             'state/shell_input_layout_coordinator.dart', 'widgets/edge_panel_layer.dart']
    metrics, control, layout, layer = [(root/n).read_text() for n in paths]
    m = animation.method
    names = ['edgePanelHeight','edgePanelRect','edgePanelScrollStripRect','softwareKeyboardRegions','statusRect','gestureRect','edgePanelGestureRect']
    pieces = {
        'METRICS': '\n'.join(m(metrics, '  static '+('double' if n=='edgePanelHeight' else 'List<Rect>' if n=='softwareKeyboardRegions' else 'Rect')+' '+n+'(') for n in names),
        'CONTROL': '\n'.join(m(control,'  void '+n+'(') for n in ['openEdgePanel','closeEdgePanel','startEdgePanelDrag','updateEdgePanelDrag','endEdgePanelDrag','updateEdgePanelAnimationProgress']),
        'PUBLISH': m(layout,'  void publish(').replace('required ShellState state','required State state'),
        'REGIONS': m(layout,'  List<InputWindowRegion> _inputRegionsForWindow(').replace('required DenialWindow window','required Window window'),
        'VIEWPORT': layer[layer.index('class MobileKeyboardViewport '):layer.index('class EdgePanelLayer ')],
        'LAYER': '\n'.join(m(layer,'  void '+n+'(') for n in ['initState','dispose','_onPanelChanged','_scheduleProgress']),
        'CARET':'', 'VIEWPORT_OFFSET':'',
    }
    unit = animation.ADAPTERS
    # The complete production State getter references these aliases as well.
    constants = '\n'.join(re.findall(
        r'  static const double (?:quickSettingsPanelHeight|quickSettingsDragDistance) = [^;]+;', metrics))
    if len(constants.splitlines()) != 2:
        raise ValueError('exact quick-settings metric declarations unavailable')
    pieces['METRICS'] += '\n'+constants
    if not (root/'input/keyboard_viewport.dart').exists():
        # Execute the old viewport with a top-line scenario; lack of caret
        # transport is precisely why this current implementation loses it.
        unit = unit[:unit.index('void main(List<String> args)')]+r'''
void main(List<String> args) {
 final c=Control();c.state.edgePanelVisible=true;c.state.edgePanelAnimationProgress=1;
 final viewport=MobileKeyboardViewport(child:Widget());
 final transform=(viewport.build(BuildContext(),Ref(c)) as LayoutBuilder).result as Transform;
 near(transform.offset.dy,0,'opening keyboard must preserve visible top-line caret');
}
'''
        cases=['top']
    else:
        extra = ['state/shell_state.dart','models/denial_text_input_caret.dart',
                 'input/keyboard_viewport.dart','platform/denial_bridge.dart']
        paths += extra
        state, caret, helper, bridge = [(root/n).read_text() for n in extra]
        strip = lambda text: re.sub(r"^import .*?;\n",'',text,flags=re.M)
        state = strip(state).replace('ShellState','State').replace('DenialWindow','Window')
        caret = strip(caret).replace('DenialWindow','Window')
        helper = strip(helper).replace('DenialWindow','Window')
        input_state=bridge[bridge.index('class DenialTextInputState {'):bridge.index('class DenialSettingsDocument {')]
        unit=unit.replace("import 'dart:math' as math;", "import 'dart:math' as math;\nimport 'dart:async';")
        a,b=unit.index('class Window {'),unit.index('enum _GestureAxis ')
        unit=unit[:a]+WINDOW+state+caret+helper+input_state+unit[b:]
        a,b=unit.index('class Control {'),unit.index('class ShellInteractionSnapshot ')
        unit=unit[:a]+CONTROL+unit[b:]
        pieces['CONTROL']+='\n'+m(control,'  void _handleTextInputState(')+'\n'+m(control,'  void updateEdgePanelViewportScroll(')
        unit=unit[:unit.index('void main(List<String> args)')]+MAIN
        cases=CASES
    for key,value in pieces.items(): unit=unit.replace('@'+key+'@',value)
    return unit,cases,paths


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--dart',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--case',action='append',choices=CASES,dest='selected_cases')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    root=a.source/'dart_shell/lib/src';unit,cases,paths=unit_for(root)
    if a.selected_cases:
        if any(case not in cases for case in a.selected_cases):
            raise ValueError('requested case is unavailable on this source revision')
        cases=a.selected_cases
    script=a.output/'test.dart';script.write_text(unit)
    result={'scope':__doc__,'source_hashes':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in paths},
            'unit_sha256':hashlib.sha256(unit.encode()).hexdigest(),'runs':[],'VM':'NOT RUN','phone':'NOT RUN'}
    compilation_failed = False
    for mode in cases:
        command=[a.dart,str(script),mode];start=time.monotonic()
        if compilation_failed:
            result['runs'].append({'case':mode,'command':command,'status':'BLOCKED',
                                  'reason':'shared Dart unit failed compilation; semantic case not executed'})
            continue
        r=subprocess.run(command,capture_output=True,text=True,timeout=45)
        (a.output/(mode+'.log')).write_text(r.stdout+r.stderr)
        result['runs'].append({'case':mode,'command':command,'exit_status':r.returncode,
                              'seconds':time.monotonic()-start,'status':'PASS' if r.returncode==0 else 'FAIL'})
        if r.returncode and ': Error:' in r.stdout+r.stderr:
            result['runs'][-1]['failure_kind']='compilation'
            compilation_failed=True
    result['counts']={s:sum(r['status']==s for r in result['runs']) for s in ['PASS','FAIL','BLOCKED']}
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['counts']))
    return int(bool(result['counts']['FAIL']))


if __name__=='__main__':raise SystemExit(main())

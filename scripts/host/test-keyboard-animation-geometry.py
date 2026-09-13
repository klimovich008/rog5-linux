#!/usr/bin/env python3
"""Execute Denial's keyboard control and input-layout methods with Dart adapters.

No Flutter rasterization, native Wayland delivery, VM or phone proof is inferred.
The supplied source may be the prior revision to demonstrate the regressions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time


def method(text, marker):
    start = text.index(marker)
    body = text.index(') {', start) + 2
    end, depth = body + 1, 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


ADAPTERS = r'''
import 'dart:math' as math;
import 'dart:async';
class Offset {
 const Offset(this.dx,this.dy); final double dx,dy;
 static const zero=Offset(0,0);
 bool operator ==(Object o)=>o is Offset && o.dx==dx && o.dy==dy;
 int get hashCode=>Object.hash(dx,dy);
}
class Size { const Size(this.width,this.height);final double width,height; }
class Rect {
 const Rect.fromLTWH(this.left,this.top,this.width,this.height);
 factory Rect.fromLTRB(double l,double t,double r,double b)=>Rect.fromLTWH(l,t,r-l,b-t);
 final double left,top,width,height;
 double get right=>left+width;double get bottom=>top+height;
 bool get isEmpty=>width<=0 || height<=0;
 Rect intersect(Rect r)=>Rect.fromLTRB(math.max(left,r.left),math.max(top,r.top),math.min(right,r.right),math.min(bottom,r.bottom));
}
extension Canvas on Offset { Rect operator &(Size s)=>Rect.fromLTWH(dx,dy,s.width,s.height); }
class ShellMetrics {
 static const edgePanelMaxHeight=368.0,edgePanelDragDistance=368.0,
  edgePanelScrollStripWidth=18.0,appStatusBarHeight=48.0,statusDragHeight=48.0,
  gestureHitWidth=176.0,gestureHitHeight=72.0,gestureBottomInset=-8.0,
  edgePanelGestureWidth=220.0,edgePanelGestureHeight=18.0,edgePanelOpenDistance=86.0;
 @METRICS@
}
class Window {
 final isUserApp=true,objectId=7,surfaceId=7;final List<dynamic> popupRoots=[];
 Rect get contentCoordinateRect=>const Rect.fromLTWH(0,0,540,1176);
 List<int> get visibleSurfaceIds=>[7];
 dynamic mapSurfaceRect(dynamic popup,Rect rect)=>throw StateError('unexpected popup');
}
class State {
 bool edgePanelVisible=false,edgePanelDragActive=false,overviewVisible=false,
  quickSettingsVisible=false,quickSettingsDragActive=false,lockLayerVisible=false,
  launchTransitionActive=false;
 double edgePanelAnimationProgress=0,edgePanelViewportScroll=0;
 bool edgePanelViewportManual=false;dynamic textInputCaret;
 Offset edgePanelDrag=Offset.zero,gestureDrag=Offset.zero,quickSettingsDrag=Offset.zero;
 double get edgePanelDragProgress=>edgePanelVisible?1:(edgePanelDrag.dy/368).clamp(0,1).toDouble();
 double get quickSettingsDragProgress=>0;
 Window? inputWindow=Window(),primaryWindow;
 State copyWith({bool? edgePanelVisible,bool? edgePanelDragActive,Offset? edgePanelDrag,
   double? edgePanelAnimationProgress,double? edgePanelViewportScroll,
   bool? edgePanelViewportManual,
   bool? overviewVisible,Offset? gestureDrag,bool? quickSettingsVisible,
   Offset? quickSettingsDrag,bool? quickSettingsDragActive}) {
  final s=State();s.edgePanelVisible=edgePanelVisible??this.edgePanelVisible;
  s.edgePanelDragActive=edgePanelDragActive??this.edgePanelDragActive;
  s.edgePanelDrag=edgePanelDrag??this.edgePanelDrag;
  s.edgePanelAnimationProgress=edgePanelAnimationProgress??this.edgePanelAnimationProgress;
  s.edgePanelViewportScroll=edgePanelViewportScroll??this.edgePanelViewportScroll;
  s.edgePanelViewportManual=edgePanelViewportManual??this.edgePanelViewportManual;
  s.textInputCaret=textInputCaret;
  s.lockLayerVisible=lockLayerVisible;s.inputWindow=inputWindow;s.primaryWindow=primaryWindow;
  return s;
 }
}
enum _GestureAxis {undecided}
class Control {
 State state=State();Offset _rawGestureDrag=Offset.zero,_gestureLockOrigin=Offset.zero;
 Timer? _automaticSoftwareKeyboardCloseTimer;
 _GestureAxis _gestureAxis=_GestureAxis.undecided;
 bool _edgePanelDragStartedOpen=false,_edgePanelDragMoved=false;
 static const _edgePanelFlickVelocity=520.0;
 @CONTROL@
}
class ShellInteractionSnapshot {
 final capturesFullScene=false,capturesKeyboard=false,compositorExclusive=false;
 final List<Rect> childRegions=[];
}
class InputWindowRegion {
 InputWindowRegion({required this.window,required this.rect,required this.sourceRect,
 required this.z,this.surfaceId,this.hitTest=true,this.geometryLocked=false});
 final Window window;final Rect rect,sourceRect;final int z;final int? surfaceId;
 final bool hitTest,geometryLocked;
}
class Layout {
 List<Rect> keyboard=[],shell=[];List<InputWindowRegion> windows=[];
 bool exclusive=false,capture=false;
 @PUBLISH@
 @REGIONS@
 void _publishInputLayout({required Size viewSize,required List<Rect> shellRegions,
 required List<InputWindowRegion> windows,List<Rect> softwareKeyboardRegions=const [],
 bool keyboardCapture=false,bool exclusiveShellMode=false}) {
  keyboard=softwareKeyboardRegions;shell=shellRegions;this.windows=windows;
  capture=keyboardCapture;exclusive=exclusiveShellMode;
 }
}
class Selector<T> { Selector(this.read);final T Function(State) read; }
class Provider {final notifier=Object();Selector<T> select<T>(T Function(State) read)=>Selector(read);}
final shellControllerProvider=Provider(),hapticsServiceProvider=Object();
class Haptics {void prewarm(){}}
class Ref {
 Ref(this.control);final Control control;
 T watch<T>(Selector<T> selector)=>selector.read(control.state);
 dynamic read(Object key)=>key==shellControllerProvider?control.state:
  key==shellControllerProvider.notifier?control:Haptics();
}
class Widget {const Widget({Object? key});}
class ConsumerWidget extends Widget {const ConsumerWidget({super.key});}
typedef WidgetRef=Ref;
class BuildContext {}
class Constraints {final biggest=const Size(540,1224);}
class LayoutBuilder extends Widget {
 LayoutBuilder({required Widget Function(BuildContext,Constraints) builder}) {
  result=builder(BuildContext(),Constraints());
 }
 late final Widget result;
}
class Transform extends Widget {
 Transform.translate({required this.offset,required this.child});
 final Offset offset;final Widget child;
}
@VIEWPORT@
@CARET@
@VIEWPORT_OFFSET@
class SchedulerBinding {
 static final instance=SchedulerBinding();int next=0;final callbacks=<int,void Function(Duration)>{};
 int scheduleFrameCallback(void Function(Duration) cb){callbacks[++next]=cb;return next;}
 void cancelFrameCallbackWithId(int id){callbacks.remove(id);}
 void pump(){final pending=Map.of(callbacks);callbacks.clear();for(final cb in pending.values){cb(Duration.zero);}}
}
class AnimationController {
 AnimationController.unbounded({required Object vsync,required double value}):_value=value;
 double _value;bool disposed=false;double? target;final listeners=<void Function()>[];
 double get value=>_value;set value(double v){_value=v;for(final f in List.of(listeners)){f();}}
 void addListener(void Function() f)=>listeners.add(f);
 void removeListener(void Function() f)=>listeners.remove(f);
 void stop(){}void dispose(){disposed=true;listeners.clear();}
}
class Motion {static const gentle=0;}
void springTo(AnimationController c,double target,{Object? spring,String? telemetryLabel}){c.target=target;}
double unit(double v)=>v.clamp(0,1).toDouble();
class Base {void initState(){}void dispose(){}}
class Layer extends Base {
 Layer(this.ref);final Ref ref;bool mounted=true;late final AnimationController _controller;
 int? _progressFrameCallback;
 @LAYER@
}
void require(bool value,String message){if(!value)throw StateError(message);}
void near(double a,double b,String label)=>require((a-b).abs()<0.00001,'$label: $a != $b');
void main(List<String> args) {
 final mode=args.single;final c=Control();final layout=Layout();const size=Size(540,1224);
 void publish()=>layout.publish(state:c.state,viewSize:size,interactions:ShellInteractionSnapshot());
 if(mode=='viewport'){
  c.state.edgePanelVisible=true;c.state.edgePanelAnimationProgress=.5;
  final viewport=MobileKeyboardViewport(child:Widget());
  Transform draw()=>(viewport.build(BuildContext(),Ref(c)) as LayoutBuilder).result as Transform;
  near(draw().offset.dy,-183.6,'viewport uses actual sheet progress');
  c.state.edgePanelViewportScroll=100;near(draw().offset.dy,-83.6,'viewport pan agrees');
  c.state.edgePanelVisible=false;near(draw().offset.dy,-83.6,'closing target does not jump viewport');
 }else if(mode=='closing'||mode=='opening'||mode=='panned'||mode=='locked'||mode=='strip'){
  c.state.edgePanelVisible=mode!='closing';c.state.edgePanelAnimationProgress=0.5;
  if(mode=='panned')c.state.edgePanelViewportScroll=100;
  if(mode=='locked')c.state.lockLayerVisible=true;
  publish();require(layout.keyboard.isNotEmpty,'visible sheet must reserve native keyboard region');
  near(layout.keyboard.first.top,1040.4,'sheet/input top');
  near(layout.keyboard.first.height,183.6,'sheet/input height');
  if(mode=='locked'){require(layout.exclusive && layout.capture,'lock remains exclusive');return;}
  require(layout.keyboard.length==1,'invisible strip must not reserve input');
  final w=layout.windows.single;
  near(w.rect.top,0,'visible client starts at clipped top');
  near(w.sourceRect.top,mode=='panned'?35.6:135.6,'native source follows actual visual translation');
  if(mode=='strip'){
   c.state.edgePanelAnimationProgress=.979;publish();require(layout.keyboard.length==1,'strip hidden below threshold');
   c.state.edgePanelAnimationProgress=.98;publish();require(layout.keyboard.length==2,'strip visible at threshold');
   c.state.edgePanelVisible=false;publish();require(layout.keyboard.length==1,'closing strip absent');
  }
 }else if(mode=='closed'){
  c.state.edgePanelAnimationProgress=0;publish();require(layout.keyboard.isEmpty,'closed keyboard removed');
  near(layout.windows.single.rect.top,48,'closed status inset');near(layout.windows.single.sourceRect.top,0,'closed source reset');
 }else if(mode=='drag'){
  c.state.edgePanelVisible=true;c.state.edgePanelAnimationProgress=.4;c.startEdgePanelDrag();
  near(c.state.edgePanelDragProgress,.4,'interruption starts at displayed position');
  c.updateEdgePanelDrag(const Offset(0,20));near(c.state.edgePanelDragProgress,(147.2-20)/368,'drag stays continuous');
  c.endEdgePanelDrag(600);require(!c.state.edgePanelVisible,'downward flick closes');
 }else if(mode=='ticks'){
  c.state.edgePanelVisible=true;final layer=Layer(Ref(c));layer.initState();
  layer._controller.value=.2;layer._controller.value=.4;
  require(SchedulerBinding.instance.callbacks.length==1,'coalesced progress publication');
  near(c.state.edgePanelAnimationProgress,0,'no synchronous provider write');
  SchedulerBinding.instance.pump();near(c.state.edgePanelAnimationProgress,.4,'frame gets latest controller value');
  layer._onPanelChanged((false,0.0,false));near(c.state.edgePanelAnimationProgress,.4,'target change does not jump');
  require(layer._controller.target==0,'spring targets closed');
  layer._controller.value=.1;layer.dispose();layer.mounted=false;
  require(SchedulerBinding.instance.callbacks.isEmpty,'dispose cancels scheduled callback');
  SchedulerBinding.instance.pump();near(c.state.edgePanelAnimationProgress,.4,'no post-dispose write');
 }else if(mode=='invalid'){
  c.updateEdgePanelAnimationProgress(.4);final same=c.state;
  c.updateEdgePanelAnimationProgress(.4);require(identical(same,c.state),'duplicate progress does not notify');
  c.updateEdgePanelAnimationProgress(double.nan);c.updateEdgePanelAnimationProgress(double.infinity);
  near(c.state.edgePanelAnimationProgress,.4,'invalid progress ignored');
  c.updateEdgePanelAnimationProgress(2);near(c.state.edgePanelAnimationProgress,1,'upper clamp');
  c.updateEdgePanelAnimationProgress(-1);near(c.state.edgePanelAnimationProgress,0,'lower clamp');
  c.updateEdgePanelAnimationProgress(.0005);near(c.state.edgePanelAnimationProgress,0,'spring terminal residue removed');
  c.updateEdgePanelAnimationProgress(.9995);near(c.state.edgePanelAnimationProgress,1,'open endpoint normalized');
 }else{throw StateError('unknown test');}
 print('PASS $mode');
}
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--dart',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    root=a.source/'dart_shell/lib/src'
    paths=['input/input_layout.dart','state/shell_controller.dart','state/shell_input_layout_coordinator.dart','widgets/edge_panel_layer.dart']
    metrics,control,layout,layer=[(root/n).read_text() for n in paths]
    metric_names=['edgePanelHeight','edgePanelRect','edgePanelScrollStripRect','softwareKeyboardRegions','statusRect','gestureRect','edgePanelGestureRect']
    pieces={'VIEWPORT':layer[layer.index('class MobileKeyboardViewport '):layer.index('class EdgePanelLayer ')],
        'METRICS':'\n'.join(method(metrics,'  static '+ ('double' if n=='edgePanelHeight' else 'List<Rect>' if n=='softwareKeyboardRegions' else 'Rect')+' '+n+'(') for n in metric_names),
        'CONTROL':'\n'.join(method(control,'  void '+n+'(') for n in ['openEdgePanel','closeEdgePanel','startEdgePanelDrag','updateEdgePanelDrag','endEdgePanelDrag']),
        'PUBLISH':method(layout,'  void publish(').replace('required ShellState state','required State state'),
        'REGIONS':method(layout,'  List<InputWindowRegion> _inputRegionsForWindow(').replace('required DenialWindow window','required Window window'),
        'LAYER':'\n'.join(method(layer,'  void '+n+'(') for n in ['initState','dispose','_onPanelChanged']),
        'CARET':'','VIEWPORT_OFFSET':''}
    for key,name in [('CARET','models/denial_text_input_caret.dart'),
                     ('VIEWPORT_OFFSET','input/keyboard_viewport.dart')]:
        path=root/name
        if path.exists():
            paths.append(name)
            pieces[key]='\n'.join(line for line in path.read_text().splitlines()
                                  if not line.startswith('import ')).replace('DenialWindow','Window')
    if '  void updateEdgePanelAnimationProgress(' in control:
        pieces['CONTROL']+='\n'+method(control,'  void updateEdgePanelAnimationProgress(')
    else:
        # Absent on the old source: retain the unupdated initial visual sample.
        pieces['CONTROL']+='\nvoid updateEdgePanelAnimationProgress(double value) {}'
    if '  void _scheduleProgress(' in layer:pieces['LAYER']+='\n'+method(layer,'  void _scheduleProgress(')
    unit=ADAPTERS
    for key,value in pieces.items():unit=unit.replace('@'+key+'@',value)
    script=a.output/'test.dart';script.write_text(unit)
    result={'scope':__doc__,'source_hashes':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in paths},'unit_sha256':hashlib.sha256(unit.encode()).hexdigest(),'runs':[],'VM':'NOT RUN','phone':'NOT RUN'}
    for mode in ['viewport','opening','closing','panned','locked','strip','closed','drag','ticks','invalid']:
        command=[a.dart,str(script),mode];start=time.monotonic()
        r=subprocess.run(command,capture_output=True,text=True,timeout=45)
        (a.output/(mode+'.log')).write_text(r.stdout+r.stderr)
        result['runs'].append({'case':mode,'command':command,'exit_status':r.returncode,'seconds':time.monotonic()-start,'status':'PASS' if r.returncode==0 else 'FAIL'})
    result['counts']={s:sum(r['status']==s for r in result['runs']) for s in ['PASS','FAIL']}
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['counts']))
    return int(bool(result['counts']['FAIL']))


if __name__=='__main__':raise SystemExit(main())

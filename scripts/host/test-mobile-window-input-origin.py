#!/usr/bin/env python3
"""Round-trip painted mobile points through the actual input-region publisher.

Executes extracted _buildTexture, contentCoordinateRect, mapSurfaceRect,
_inputRegionsForWindow and matching Flutter applyBoxFit with Dart value/widget
adapters. Cases cover only 1:1 logical content, with geometry origin (26,23) or
(0,0), and upward translation 0 or 367.2. This is not native Smithay delivery,
Flutter rasterization, VM, touch or phone proof. Non-1:1 native pointer scaling
remains outside this correction and these tests.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('sizing', HERE/'test-mobile-content-sizing.py')
sizing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sizing)
spec = importlib.util.spec_from_file_location('animation', HERE/'test-keyboard-animation-geometry.py')
animation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(animation)
LAYOUT = 'dart_shell/lib/src/state/shell_input_layout_coordinator.dart'
FILES = sizing.FILES + [LAYOUT]

RECT = r'''
class Rect {
 const Rect.fromLTWH(this.left,this.top,this.width,this.height);
 const Rect.fromLTRB(double left,double top,double right,double bottom):
   this.fromLTWH(left,top,right-left,bottom-top);
 static const zero=Rect.fromLTWH(0,0,0,0);
 final double left,top,width,height;
 double get right=>left+width;
 double get bottom=>top+height;
 bool get isEmpty=>width<=0 || height<=0;
 Size get size=>Size(width,height);
 Rect intersect(Rect other)=>Rect.fromLTRB(math.max(left,other.left),
   math.max(top,other.top),math.min(right,other.right),math.min(bottom,other.bottom));
 bool contains(double x,double y)=>x>=left&&x<right&&y>=top&&y<bottom;
}
class InputWindowRegion {
 InputWindowRegion({required this.window,required this.surfaceId,
   required this.rect,required this.sourceRect,required this.z,
   required this.geometryLocked});
 final DenialWindow window;
 final int surfaceId,z;
 final Rect rect,sourceRect;
 final bool geometryLocked;
}
'''

TESTS = r'''
final outcomes=<String,bool>{};
final observations=<String,Object>{};
bool near(double a,double b)=>(a-b).abs()<0.000001;
void check(String name,bool value) { outcomes[name]=value; }
void main() {
 const target=Size(540,1224);
 for(final origin in [true,false]) {
  final w=DenialWindow(contentX:origin?26:0,contentY:origin?23:0);
  final content=w.contentCoordinateRect;
  final wrapper=Harness(w)._buildTexture(BuildContext(),target) as ShellBackdropBlur;
  final fitted=wrapper.child as FittedBox;
  final frame=fitted.child as SizedBox;
  final children=(frame.child as Column).children;
  final body=children.last as SizedBox;
  final bar=children.first as SizedBox;
  final fit=applyBoxFit(fitted.fit,Size(frame.width!,frame.height!),target);
  final scaleX=fit.destination.width/fit.source.width;
  final scaleY=fit.destination.height/fit.source.height;
  // Actual Alignment.topCenter cover-fit: centered x crop, top-aligned y.
  final sourceLeft=(frame.width!-fit.source.width)/2;
  final base=origin?'cropped':'zero_origin';
  check('${base}_actual_paint_is_one_to_one',near(scaleX,1)&&near(scaleY,1)
    &&near(sourceLeft,0)&&near(bar.height!,48));
  for(final pan in [0.0,367.2]) {
   final name='${base}_${pan==0?'untranslated':'panned'}';
   // The first nonzero-origin point reconstructs the retained protocol sample:
   // scene (270.4921875,200.13671875) must address surface
   // (296.4921875,175.13671875), not (270.4921875,152.13671875).
   final surfaceX=content.left+270.4921875;
   final surfaceY=content.top+152.13671875+pan;
   final painted=w.mapSurfaceRect(DenialSurfaceLayer(surfaceX,surfaceY,1,1),
     Rect.fromLTWH(0,0,body.width!,body.height!));
   final screenX=(painted.left-sourceLeft)*scaleX;
   final screenY=(painted.top+bar.height!)*scaleY-pan;
   final regions=InputHarness()._inputRegionsForWindow(window:w,viewSize:target,
     contentOffset:pan,inputBottom:pan==0?1224:856.8);
   final region=regions.single;
   check('${name}_root_identity',region.surfaceId==w.objectId&&region.geometryLocked);
   check('${name}_point_is_visible',region.rect.contains(screenX,screenY));
   final routedX=region.sourceRect.left+
     (screenX-region.rect.left)*region.sourceRect.width/region.rect.width;
   final routedY=region.sourceRect.top+
     (screenY-region.rect.top)*region.sourceRect.height/region.rect.height;
   check('${name}_paint_input_roundtrip',near(routedX,surfaceX)&&near(routedY,surfaceY));
   observations[name]={
    'surface':[surfaceX,surfaceY],'screen':[screenX,screenY],
    'mapped_input':[routedX,routedY],
    'error':[routedX-surfaceX,routedY-surfaceY],
    'input_rect':[region.rect.left,region.rect.top,region.rect.width,region.rect.height],
    'source_rect':[region.sourceRect.left,region.sourceRect.top,
      region.sourceRect.width,region.sourceRect.height],
   };
  }
 }
 print(jsonEncode({'cases':outcomes,'observations':observations}));
 exit(outcomes.values.every((value)=>value)?0:1);
}
'''


def unit(files, flutter):
    # Reuse the established exact presentation extraction/value adapters, but
    # substitute this test's independent paint-to-input assertions.
    source = sizing.unit(files, flutter)
    source = source[:source.index('final outcomes=<String,bool>{};')]
    start, end = source.index('class Rect {'), source.index('class DenialSurfaceLayer {')
    source = source[:start] + RECT + source[end:]
    marker = ' bool get isOpaque=>true;'
    assert source.count(marker) == 1
    source = source.replace(marker,
        ' int get objectId=>7;\n List<dynamic> get popupRoots=>const [];\n'+marker)
    region = animation.method(files[LAYOUT], '  List<InputWindowRegion> _inputRegionsForWindow')
    return source + '\nclass InputHarness {\n' + region + '\n}\n' + TESTS


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--flutter-box-fit', type=Path, required=True)
    p.add_argument('--dart', required=True, help='Dart executable; bounded wrapper supported')
    p.add_argument('--output', type=Path, required=True, help='fresh disk-backed output')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    files = {name:(a.source/name).read_text() for name in FILES}
    flutter = a.flutter_box_fit.read_text()
    script = a.output/'test.dart'
    script.write_text(unit(files, flutter))
    command = [a.dart, str(script.absolute())]
    start = time.monotonic()
    run = subprocess.run(command, capture_output=True, text=True, timeout=45)
    (a.output/'test.log').write_text(run.stdout+run.stderr)
    result = {'scope':__doc__, 'source_hashes':{
        n:hashlib.sha256(v.encode()).hexdigest() for n,v in files.items()},
        'flutter_box_fit_sha256':hashlib.sha256(flutter.encode()).hexdigest(),
        'unit_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),
        'command':command, 'duration_seconds':time.monotonic()-start,
        'exit_status':run.returncode, 'VM':'NOT RUN', 'phone':'NOT RUN'}
    if run.returncode in (0,1) and run.stdout.strip():
        try:
            result.update(json.loads(run.stdout))
        except json.JSONDecodeError:
            result['failure_kind'] = 'non-JSON Dart output'
    cases = result.get('cases', {})
    result['status'] = 'PASS' if run.returncode == 0 and len(cases) == 14 and all(cases.values()) else 'FAIL'
    if ': Error:' in run.stdout+run.stderr:
        result['failure_kind'] = 'compilation'
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return int(result['status'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())

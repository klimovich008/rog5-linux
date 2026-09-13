#!/usr/bin/env python3
"""Execute extracted Denial presentation code and Flutter's real applyBoxFit.

This manual exact-source test uses Dart VM value/widget-construction adapters;
it does not run a Flutter renderer, event routing, a VM guest or the phone.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

FILES = ['dart_shell/lib/src/widgets/window_texture_rect.dart',
         'dart_shell/lib/src/input/input_layout.dart',
         'dart_shell/lib/src/widgets/window_geometry.dart',
         'dart_shell/lib/src/widgets/window_content_rect.dart',
         'dart_shell/lib/src/models/denial_window.dart']
PATCH = 'patches/denial-85b2303e/0008-use-logical-window-content-size.patch'


def block(source, marker):
    start = source.index(marker)
    # Signatures can have named-argument braces; use the body following ')'.
    if marker.startswith(('Widget ', 'double ', 'Size ', '  static double')):
        pos = source.index(') {', start) + 2
    else:
        pos = source.index('{', start)
    end, depth = pos + 1, 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


ADAPTERS = r'''
import 'dart:math' as math;
import 'dart:convert';
import 'dart:io' show exit;
class Size {
 const Size(this.width,this.height); final double width,height;
 static const zero=Size(0,0);
}
class Rect {
 const Rect.fromLTWH(this.left,this.top,this.width,this.height);
 static const zero=Rect.fromLTWH(0,0,0,0);
 final double left,top,width,height;
 Size get size=>Size(width,height);
}
class DenialSurfaceLayer {
 const DenialSurfaceLayer(this.surfaceX,this.surfaceY,this.surfaceWidth,this.surfaceHeight);
 final double surfaceX,surfaceY,surfaceWidth,surfaceHeight;
}
class DenialWindow {
 const DenialWindow({this.width=592,this.height=1228,this.surfaceX=0,this.surfaceY=0,
 this.surfaceWidth=592,this.surfaceHeight=1228,this.contentX=26,this.contentY=23,
 this.contentWidth=540,this.contentHeight=1176,this.scale120=120,this.isUserApp=true,
 this.geometryWidth=540,this.geometryHeight=1176});
 final int width,height,scale120; final bool isUserApp;
 final double geometryWidth,geometryHeight;
 final double surfaceX,surfaceY,surfaceWidth,surfaceHeight,contentX,contentY,contentWidth,contentHeight;
 bool get isOpaque=>true; int? get statusColorArgb=>null;
 @GETTER@
 @MAP@
}
class Widget {}
class BuildContext { Colors get shellColors=>Colors(); }
class Colors { Color get background=>Color(0); }
class Color { Color(int value); }
class Padding { double get top=>0; }
class MediaQuery { static Padding paddingOf(BuildContext context)=>Padding(); }
class Motion { static int cardSettle=0, standard=0; }
class SizedBox extends Widget {
 SizedBox({this.width,this.height,this.child}); final double? width,height; final Widget? child;
}
class Column extends Widget { Column({required this.children}); final List<Widget> children; }
class AnimatedContainer extends Widget { AnimatedContainer({required int duration, required int curve, required Color color}); }
class WindowSurfaceTree extends Widget { WindowSurfaceTree({required DenialWindow window, required bool includePopups}); }
class Alignment { static int topCenter=0; }
class FittedBox extends Widget {
 FittedBox({required this.fit,required int alignment,required this.child});
 final BoxFit fit; final Widget child;
}
class ShellBackdropBlur extends Widget {
 ShellBackdropBlur({required bool blur,required int borderRadius,required this.child}); final Widget child;
}
enum BoxFit {fill,contain,cover,fitWidth,fitHeight,none,scaleDown}
class FittedSizes { const FittedSizes(this.source,this.destination); final Size source,destination; }
'''
TESTS = r'''
final outcomes=<String,bool>{};
bool near(double a,double b)=>(a-b).abs()<0.000001;
void check(String name,bool value) { outcomes[name]=value; }
void main() {
 const target=Size(540,1224);
 const w=DenialWindow();
 final wrapper=Harness(w)._buildTexture(BuildContext(),target) as ShellBackdropBlur;
 final fitted=wrapper.child as FittedBox;
 final frame=fitted.child as SizedBox;
 final children=(frame.child as Column).children;
 final body=children.last as SizedBox;
 final bar=children.first as SizedBox;
 final fit=applyBoxFit(fitted.fit,Size(frame.width!,frame.height!),target);
 // Alignment.topCenter crops symmetrically in x. A logical glyph at x=4
 // must survive the complete source-tree sizing and cover-fit transform.
 final sourceLeft=(frame.width!-fit.source.width)/2;
 final glyphTargetX=(4*body.width!/w.contentCoordinateRect.width-sourceLeft)*fit.destination.width/fit.source.width;
 check('logical_body_dimensions',near(body.width!,540)&&near(body.height!,1176));
 check('no_horizontal_cover_crop',near(fit.source.width,frame.width!));
 check('leading_glyph_remains_visible',glyphTargetX>=0 && near(glyphTargetX,4));
 check('visual_status_bar_48',near(bar.height!*fit.destination.height/fit.source.height,48));
 check('logical_preview_aspect',near(windowAspect(w),540/1224));
 const scaled=DenialWindow(width:1080,height:2352,surfaceWidth:540,surfaceHeight:1176,contentX:0,contentY:0,scale120:240);
 check('buffer_scale_does_not_change_preview',near(windowAspect(scaled),540/1224));
 check('logical_fallback_status_bar',near(ShellMetrics.appStatusBarTextureHeight(scaled),48));
 check('local_layout_status_bar',near(localStatus(w,target),48));
 const fallback=DenialWindow(width:540,height:1176,surfaceWidth:540,surfaceHeight:1176,contentWidth:0,contentHeight:0);
 check('surface_fallback_aspect',near(windowAspect(fallback),540/1224));
 const legacy=DenialWindow(width:540,height:1176,surfaceWidth:0,surfaceHeight:0,contentWidth:0,contentHeight:0);
 check('legacy_pixel_fallback',near(windowAspect(legacy),540/1224));
 const system=DenialWindow(isUserApp:false,width:540,height:1176,surfaceWidth:540,surfaceHeight:1176,contentWidth:540,contentHeight:1176);
 check('system_window_no_bar',near(ShellMetrics.appStatusBarTextureHeight(system,targetSize:target),0));
 const empty=DenialWindow(width:0,height:0,surfaceWidth:0,surfaceHeight:0,contentWidth:0,contentHeight:0);
 check('empty_preview_fallback',near(windowAspect(empty),kPreviewAspect));
 // Production mapping method is unchanged: geometry origin and scale are
 // applied once. This also covers desktop's direct logical target path.
 final mapped=w.mapSurfaceRect(const DenialSurfaceLayer(0,0,592,1228),const Rect.fromLTWH(10,20,540,1176));
 check('surface_mapping_keeps_origin',near(mapped.left,-16)&&near(mapped.top,-3)&&near(mapped.width,592)&&near(mapped.height,1228));
 print(jsonEncode({'cases':outcomes,'glyph_target_x':glyphTargetX,'body':[body.width,body.height],'cover_source':[fit.source.width,fit.source.height]}));
 exit(outcomes.values.every((value)=>value) ? 0 : 1);
}
'''


def unit(files, flutter):
    model = files[FILES[4]]
    adapters = ADAPTERS.replace('@GETTER@', block(model, 'Rect get contentCoordinateRect')).replace(
        '@MAP@', block(model, 'Rect mapSurfaceRect'))
    metrics = block(files[FILES[1]], 'class ShellMetrics')
    # The remaining ShellMetrics geometry methods only need these Size/Rect
    # value adapters; the three presentation methods run verbatim.
    method = block(files[FILES[0]], 'Widget _buildTexture')
    geometry = files[FILES[2]]
    constants = '\n'.join(x for x in geometry.splitlines() if x.startswith('const double'))
    local = files[FILES[3]]
    call_start = local.index('final statusBarHeight = ShellMetrics.appStatusBarTextureHeight(')
    call_end = local.index(';', call_start) + 1
    local_unit = block(local, 'Size _localLayoutSize') + '\ndouble localStatus(DenialWindow window, Size targetSize) { final layoutSize=_localLayoutSize(window); final visualStatusBarHeight=48.0; ' + local[call_start:call_end] + ' return statusBarHeight; }\n'
    return adapters + metrics + local_unit + constants + block(geometry, 'double windowAspect') + '\n' + block(
        flutter, 'FittedSizes applyBoxFit') + '\nclass Harness { Harness(this.window); final DenialWindow window; int borderRadius=0;\n' + method + '\n}\n' + TESTS


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True, help='retained Denial tree; source hashes are recorded')
    p.add_argument('--flutter-box-fit', type=Path, required=True, help='exact matching Flutter painting/box_fit.dart')
    p.add_argument('--dart', required=True, help='Dart executable (a bounded wrapper is supported)')
    p.add_argument('--output', type=Path, required=True, help='fresh disk-backed output')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    original = {name:(a.source/name).read_text() for name in FILES}
    flutter = a.flutter_box_fit.read_text()
    stage = a.output/'source'
    for name, value in original.items():
        dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(value)
    patch = Path(__file__).resolve().parents[2]/PATCH
    subprocess.run(['git','apply','--check',str(patch)],cwd=stage,check=True,timeout=10)
    subprocess.run(['git','apply',str(patch)],cwd=stage,check=True,timeout=10)
    patched = {name:(stage/name).read_text() for name in FILES}
    result={'scope':__doc__,'physical':'NOT RUN','source_hashes':{n:hashlib.sha256(v.encode()).hexdigest() for n,v in original.items()},
            'flutter_box_fit_sha256':hashlib.sha256(flutter.encode()).hexdigest(),'patch_sha256':hashlib.sha256(patch.read_bytes()).hexdigest(),'runs':{}}
    for label,files in [('before',original),('after',patched)]:
        path=a.output/(label+'.dart');path.write_text(unit(files,flutter));command=[a.dart,str(path.absolute())]
        start=time.monotonic();run=subprocess.run(command,text=True,capture_output=True,timeout=45)
        (a.output/(label+'.log')).write_text(run.stdout+run.stderr)
        entry={'command':command,'duration_seconds':time.monotonic()-start,'exit_status':run.returncode,'unit_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        if run.returncode in (0,1) and run.stdout.strip(): entry.update(json.loads(run.stdout))
        result['runs'][label]=entry
    before=result['runs']['before'].get('cases',{});after=result['runs']['after'].get('cases',{})
    expected_fail={'logical_body_dimensions','no_horizontal_cover_crop','leading_glyph_remains_visible','logical_preview_aspect','logical_fallback_status_bar','local_layout_status_bar'}
    result['status']='PASS' if result['runs']['before']['exit_status']==1 and result['runs']['after']['exit_status']==0 and len(before)==13 and {n for n,v in before.items() if not v}==expected_fail and len(after)==13 and all(after.values()) else 'FAIL'
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));return 0 if result['status']=='PASS' else 1

if __name__=='__main__': raise SystemExit(main())

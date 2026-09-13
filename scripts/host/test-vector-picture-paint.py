#!/usr/bin/env python3
"""Execute extracted vector picture paint and its diagnostic with Dart adapters.

Exercises the production paint body and diagnostic helper against a recording
canvas, not a duplicated paint model. Optional baseline comparison executes the
previous package's paint body against the same adapters. This does not establish
Flutter layout, rasterization, GPU output, VM presentation, or phone behavior.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

PAINT = 'lib/src/render_vector_graphic.dart'
HELPER = 'lib/src/rog5_picture_diagnostic.dart'


def paint_method(source):
    owner = source.index('class RenderPictureVectorGraphic ')
    match = re.search(r'void paint\(PaintingContext context, ui\.Offset offset\)\s*\{',
                      source[owner:])
    if match is None:
        raise ValueError('actual picture paint method is absent')
    start = owner + match.start()
    opening = owner + match.end() - 1
    depth = 1
    for end in range(opening + 1, len(source)):
        depth += (source[end] == '{') - (source[end] == '}')
        if depth == 0:
            return source[start:end + 1].replace('ui.Offset', 'Offset')
    raise ValueError('unterminated picture paint method')


ADAPTERS = r'''
class SchedulerBinding {
  static final instance=SchedulerBinding();
  Duration currentFrameTimeStamp=const Duration(microseconds:123456);
}
class Size {
  const Size(this.width,this.height);
  final double width,height;
}
class Offset {
  const Offset(this.dx,this.dy);
  static const zero=Offset(0,0);
  final double dx,dy;
  Rect operator &(Size size)=>Rect(dx,dy,size.width,size.height);
  @override bool operator ==(Object other)=>other is Offset&&dx==other.dx&&dy==other.dy;
  @override int get hashCode=>Object.hash(dx,dy);
}
class Rect {
  Rect(this.x,this.y,this.width,this.height);
  final double x,y,width,height;
  List<double> get values=>[x,y,width,height];
}
class Color {
  Color.fromRGBO(this.r,this.g,this.b,this.opacity);
  final int r,g,b;
  final double opacity;
}
class ColorFilter {}
class Paint {
  ColorFilter? colorFilter;
  Color? color;
}
class PictureInfo {
  PictureInfo(this.picture,this.size);
  final Object picture;
  final Size size;
}
class Canvas {
  final operations=<Object>[];
  final Object? error;
  Canvas({this.error});
  int getSaveCount(){operations.add(['getSaveCount']);return 3;}
  void save(){operations.add(['save']);}
  void translate(double x,double y){operations.add(['translate',x,y]);}
  void clipRect(Rect rect){operations.add(['clipRect',rect.values]);}
  void saveLayer(Rect rect,Paint paint){operations.add([
    'saveLayer',rect.values,paint.color?.opacity,paint.colorFilter!=null]);}
  void drawPicture(Object picture){
    operations.add(['drawPicture',identityHashCode(picture)]);
    if(error!=null)throw error!;
  }
  void restoreToCount(int count){operations.add(['restoreToCount',count]);}
}
class PaintingContext {
  PaintingContext(this.canvas);
  final Canvas canvas;
}
'''

FIELDS = r'''
  Harness(this.pictureInfo,this._opacityValue,this.colorFilter);
  final PictureInfo pictureInfo;
  final double _opacityValue;
  final ColorFilter? colorFilter;
  Size get size=>pictureInfo.size;
'''

TESTS = r'''
final checks=<String,bool>{};
final observations=<String,Object>{};
final records=<String>[];
void check(String name,bool value){checks[name]=value;}
Map<String,String> fields(String record)=>{
  for(final match in RegExp(r'([a-zA-Z_]+)=([^ ]+)').allMatches(record))
    match[1]!:match[2]!
};
String stage(String record)=>fields(record)['stage']??'';
void main(){
  final picture=Object();
  final info=PictureInfo(picture,const Size(48,32));
  final error=StateError('original-draw-failure');
  final definitions=<String,(Offset,double,ColorFilter?,Object?)>{
    'ordinary':(Offset.zero,1,null,null),
    'translated':(const Offset(7,11),1,null,null),
    'opacity_zero':(Offset.zero,0,null,null),
    'opacity_filter':(const Offset(7,11),0.5,ColorFilter(),null),
    'draw_throws':(Offset.zero,1,null,error),
  };
  runZoned((){
    for(final entry in definitions.entries){
      final (offset,opacity,filter,exception)=entry.value;
      final canvas=Canvas(error:exception);
      final begin=records.length;
      Object? caught;
      try{Harness(info,opacity,filter).paint(PaintingContext(canvas),offset);}
      catch(value){caught=value;}
      final trace=records.sublist(begin);
      final stages=trace.map(stage).toList();
      final expected=opacity<=0?['paintEnter','opacitySkip']:
        exception!=null?['paintEnter','drawBegin']:
        ['paintEnter','drawBegin','drawEnd','paintEnd'];
      check('${entry.key}_diagnostic_order',jsonEncode(stages)==jsonEncode(expected));
      check('${entry.key}_exception_identity',identical(caught,exception));
      check('${entry.key}_metadata_values',trace.map(fields).every((r)=>
        double.tryParse(r['width']??'')==48&&double.tryParse(r['height']??'')==32&&
        double.tryParse(r['picture_width']??'')==48&&
        double.tryParse(r['picture_height']??'')==32&&
        double.tryParse(r['x']??'')==offset.dx&&double.tryParse(r['y']??'')==offset.dy&&
        double.tryParse(r['opacity']??'')==opacity&&r['filter']=='${filter!=null}'));
      if(opacity<=0){
        check('opacity_zero_no_canvas_operations',canvas.operations.isEmpty);
      }else{
        final names=canvas.operations.map((v)=>(v as List).first).toList();
        final expectedOps=<String>['getSaveCount',
          if(offset!=Offset.zero)...['save','translate'],
          if(opacity!=1||filter!=null)...['save','clipRect','saveLayer'],
          'drawPicture',if(exception==null)'restoreToCount'];
        check('${entry.key}_canvas_order',jsonEncode(names)==jsonEncode(expectedOps));
      }
      // Execute baseline production code with the identical picture and values.
      BASELINE_CHECK
      observations[entry.key]={'operations':canvas.operations,'records':trace};
    }
    for(var i=0;i<120;i++){
      rog5PictureStage(Rog5PictureStage.build,picture,width:48,height:32,
        pictureWidth:48,pictureHeight:32);
    }
  },zoneSpecification:ZoneSpecification(print:(self,parent,zone,line){records.add(line);}));
  final rows=records.map(fields).toList();
  check('record_cap_96',records.length==96);
  check('sequence_contiguous',List.generate(rows.length,(i)=>
    rows[i]['seq']=='${i+1}').every((v)=>v));
  CORRELATION_CHECK
  check('no_multiline_records',records.every((r)=>!r.contains('\n')&&!r.contains('\r')));
  check('fixed_record_prefix',records.every((r)=>r.startsWith('ROG5_PICTURE seq=')));
  print(jsonEncode({'cases':checks,'observations':observations,
    'diagnostic_records':records,'baseline_compared':BASELINE_ENABLED}));
  exit(checks.values.every((v)=>v)?0:1);
}
'''


def unit(source, helper, baseline=None):
    # Preserve helper code; only its Flutter import gets a value-only adapter.
    helper = re.sub(r"^import ['\"]package:flutter/[^'\"]+['\"];\s*$", '',
                    helper, flags=re.M)
    if re.search(r'^\s*(import|export|part)\s', helper, re.M):
        raise ValueError('unexpected helper directive; adapter must be reviewed')
    baseline_class = ''
    baseline_check = ''
    if baseline is not None:
        baseline_class = '\nclass BaselineHarness {\n' + FIELDS.replace(
            'Harness(', 'BaselineHarness(') + paint_method(baseline) + '\n}\n'
        baseline_check = r'''
      final original=Canvas(error:exception);
      Object? baselineError;
      try{BaselineHarness(info,opacity,filter).paint(PaintingContext(original),offset);}
      catch(value){baselineError=value;}
      check('${entry.key}_baseline_operations',
        jsonEncode(original.operations)==jsonEncode(canvas.operations));
      check('${entry.key}_baseline_exception',identical(baselineError,caught));
'''
    tests = TESTS.replace('BASELINE_CHECK', baseline_check).replace(
        'BASELINE_ENABLED', str(baseline is not None).lower())
    # Filled against the actual helper's fixed numeric field names below.
    tests = tests.replace('CORRELATION_CHECK', correlation_checks(helper))
    return ("import 'dart:async';\nimport 'dart:convert';\nimport 'dart:io';\n" +
            ADAPTERS + helper + '\nclass Harness {\n' + FIELDS +
            paint_method(source) + '\n}\n' + baseline_class + tests)


def correlation_checks(helper):
    # This explicit schema is kept separate from fake canvas implementation.
    # Review alongside the helper if its output contract changes.
    return r'''
  check('picture_identity',rows.every((r)=>r['picture']=='${identityHashCode(picture)}'));
  check('frame_timestamp',rows.every((r)=>r['frame_us']=='123456'));
  check('elapsed_numeric_monotonic',rows.every((r)=>int.tryParse(r['mono_us']??'')!=null)
    && List.generate(rows.length-1,(i)=>int.parse(rows[i+1]['mono_us']!)>=
      int.parse(rows[i]['mono_us']!)).every((v)=>v));
  check('fixed_numeric_metadata',rows.every((r)=>[
    'width','height','picture_width','picture_height','x','y','opacity'
  ].every((key)=>double.tryParse(r[key]??'')!=null)));
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--baseline-package', type=Path)
    parser.add_argument('--dart', required=True, help='Dart executable or bounded wrapper')
    parser.add_argument('--output', type=Path, required=True, help='fresh output directory')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    files = {name: (args.package/name).read_text() for name in (PAINT, HELPER)}
    baseline = ((args.baseline_package/PAINT).read_text()
                if args.baseline_package is not None else None)
    script = args.output/'test.dart'
    script.write_text(unit(files[PAINT], files[HELPER], baseline))
    command = [args.dart, str(script.absolute())]
    result = {'scope': __doc__, 'command': command,
              'source_hashes': {name: hashlib.sha256(value.encode()).hexdigest()
                                for name, value in files.items()},
              'unit_sha256': hashlib.sha256(script.read_bytes()).hexdigest(),
              'baseline_sha256': hashlib.sha256(baseline.encode()).hexdigest()
              if baseline is not None else None, 'VM': 'NOT RUN', 'phone': 'NOT RUN'}
    start = time.monotonic()
    try:
        run = subprocess.run(command, capture_output=True, text=True, timeout=45)
        (args.output/'test.log').write_text(run.stdout + run.stderr)
        result['exit_status'] = run.returncode
        try:
            result.update(json.loads(run.stdout))
        except json.JSONDecodeError:
            result['failure_kind'] = 'non-JSON Dart output or compilation failure'
    except subprocess.TimeoutExpired as error:
        def decode(value):
            return value.decode(errors='replace') if isinstance(value, bytes) else value or ''
        (args.output/'test.log').write_text(decode(error.stdout) + decode(error.stderr))
        result.update(exit_status=None, failure_kind='Dart wrapper exceeded 45 seconds')
    result['duration_seconds'] = time.monotonic() - start
    cases = result.get('cases', {})
    expected_cases = 28 + (10 if baseline is not None else 0)
    result['expected_cases'] = expected_cases
    result['status'] = 'PASS' if (result['exit_status'] == 0 and
        len(cases) == expected_cases and all(value is True for value in cases.values())) else 'FAIL'
    (args.output/'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return int(result['status'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())

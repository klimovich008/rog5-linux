#!/usr/bin/env python3
"""Execute copied SvgLoader._load with real Dart isolates and compiler adapters.

Proves diagnostic cap and byte/error propagation, not SVG compilation, Flutter
image decoding, frame delivery, VM behavior or phone operation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

FIXTURE = r'''
import 'dart:async';
import 'dart:isolate';
import 'dart:typed_data';
class BuildContext {}
class SvgTheme {Object toVgTheme()=>Object();}
class _DelegateVgColorMapper { _DelegateVgColorMapper(Object value); }
class vg {
 static Uint8List encodeSvg({required String xml, required Object theme,
 Object? colorMapper,required String debugName,required bool enableClippingOptimizer,
 required bool enableMaskingOptimizer,required bool enableOverdrawOptimizer}) {
  if(xml=='bad') throw FormatException('DO_NOT_LOG_PAYLOAD');
  return Uint8List.fromList([0,1,255]);
 }
}
Future<R> compute<Q,R>(FutureOr<R> Function(Q) fn,Q value,{String? debugLabel}) => Isolate.run(()=>fn(value));
class Loader<T> {
 Loader(this.mode);
 final String mode; final Object? colorMapper=null;
 SvgTheme getTheme(BuildContext? context)=>SvgTheme();
 Future<T?> prepareMessage(BuildContext? context) => mode=='prepare-error'
   ? Future.error(StateError('DO_NOT_LOG_PREPARE')) : Future.value(null);
 String provideSvg(T? message)=>mode;
 @METHOD@
}
@HELPER@
Future<void> main(List<String> args) async {
 final mode=args.single;
 if(mode=='cap') {
  for(var i=0;i<1000;i++) _rog5IconStage('cap', '\nFORGED'+('x'*1000));
  return;
 }
 try {
  final data=await Loader<void>(mode)._load(null);
  if(mode!='good'||data.lengthInBytes!=3||data.getUint8(2)!=255) throw StateError('bytes changed');
 } on FormatException catch(e) {
  if(mode!='bad'||e.message!='DO_NOT_LOG_PAYLOAD') rethrow;
 } on StateError catch(e) {
  if(mode!='prepare-error'||e.message!='DO_NOT_LOG_PREPARE') rethrow;
 }
 print('PASS $mode');
}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True,help='copied flutter_svg lib/src/loaders.dart')
    p.add_argument('--dart',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    source=a.source.read_text();start=source.index('  Future<ByteData> _load(')
    end=source.index('\n  /// This method intentionally',start)
    helper=source[source.index('// ROG5 diagnostic only:'):]
    unit=FIXTURE.replace('@METHOD@',source[start:end]).replace('@HELPER@',helper)
    f=a.output/'fixture.dart';f.write_text(unit)
    result={'scope':__doc__,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
            'fixture_sha256':hashlib.sha256(unit.encode()).hexdigest(),'runs':[]}
    for mode in ['good','bad','prepare-error','cap']:
        cmd=[a.dart,str(f),mode];t=time.monotonic()
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=45)
        (a.output/(mode+'.log')).write_text(r.stdout+r.stderr)
        lines=[x for x in r.stdout.splitlines() if x.startswith('ROG5_ICON_STAGE ')]
        stages=[x.split('stage=',1)[1].split(' ',1)[0] for x in lines]
        expected={'good':['prepare-begin','prepare-end','encode-begin','encode-end'],
                  'bad':['prepare-begin','prepare-end','encode-begin','encode-error'],
                  'prepare-error':['prepare-begin'],'cap':['cap']*64}[mode]
        good=r.returncode==0 and stages==expected and 'DO_NOT_LOG_' not in r.stdout+r.stderr
        if mode=='cap':good &= all(len(x)<200 for x in lines) and len(r.stdout.splitlines())==64
        result['runs'].append(dict(command=cmd,status='PASS' if good else 'FAIL',exit_status=r.returncode,seconds=time.monotonic()-t,stages=stages))
    result['status']='PASS' if all(x['status']=='PASS' for x in result['runs']) else 'FAIL'
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));return int(result['status']!='PASS')
if __name__=='__main__':raise SystemExit(main())

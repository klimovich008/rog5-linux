#!/usr/bin/env python3
"""Execute patched Dart focus diagnostics and callback/send methods with adapters."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def block(text, marker):
    start = text.index(marker)
    body = text.index(') {', start) + 2
    end, depth = body + 1, 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


FIXTURE = r'''
class DenialWindow { DenialWindow(this.windowId); final int windowId; }
class Codec {
 Uint8List encodeWindowRequest(wire.WindowRequestKind kind,{required int windowId}) => Uint8List.fromList([windowId]);
}
class Messenger {
 String mode='reply'; int calls=0; ByteData? last;
 Future<ByteData?>? send(String channel, ByteData bytes) {
  if(channel != wire.denialWireToNativeChannel) throw StateError('channel changed');
  calls++;last=bytes;
  if(mode=='sync') throw StateError('sync failure');
  if(mode=='error') return Future.error(StateError('DO_NOT_LOG_SECRET'));
  if(mode=='none') return null;
  return Future.value(null);
 }
}
class ServicesBinding {
 static final instance=ServicesBinding(); final defaultBinaryMessenger=Messenger();
}
class Bridge {
 final _wireCodec=Codec();
 @FOCUS@
 @SEND@
}
enum AnimationStatus { dismissed,forward,reverse,completed }
class Controller { final directions=<int>[];void completeAdjacentWindowSwitch(int d){directions.add(d);} }
class Provider { final notifier=0; }
final shellControllerProvider=Provider();
class Ref { final controller=Controller(); Controller read(Object key)=>controller; }
class Handle {
 int _switchDirection=-1; Object? _switchAnimation=Object();final ref=Ref();
 @STATUS@
}
void check(bool value,String name) { if(!value) throw StateError(name); }
Future<void> main(List<String> args) async {
 if(args.single=='cap') {
  for(var i=0;i<100;i++) traceFocus(FocusTraceStage.send,windowId:i,status:'x'*1000);
  return;
 }
 final h=Handle();h._handleSwitchStatus(AnimationStatus.forward);
 check(h.ref.controller.directions.isEmpty,'forward must not commit');
 h._handleSwitchStatus(AnimationStatus.completed);
 check(h.ref.controller.directions.single==-1 && h._switchDirection==0 && h._switchAnimation==null,'completion must commit once and clear animation');
 h._handleSwitchStatus(AnimationStatus.completed);
 check(h.ref.controller.directions.length==1,'completed callback cannot duplicate commit');
 final b=Bridge(); final m=ServicesBinding.instance.defaultBinaryMessenger;
 b.focusWindow(DenialWindow(0));check(m.calls==0,'invalid ID refused');
 b.focusWindow(DenialWindow(7));await Future<void>.delayed(Duration.zero);
 check(m.calls==1 && m.last!.getUint8(0)==7,'focus payload preserved');
 m.mode='error';b.focusWindow(DenialWindow(8));await Future<void>.delayed(Duration.zero);
 m.mode='none';b.focusWindow(DenialWindow(9));
 m.mode='sync';var threw=false;try{b.focusWindow(DenialWindow(10));}on StateError{threw=true;}
 check(threw,'synchronous transport failure still propagates');
 m.mode='error';b._sendWire(Uint8List.fromList([11]));await Future<void>.delayed(Duration.zero);
 check(m.calls==5,'nonfocus send preserved');
 print('PASS shell focus method semantics');
}
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True,help='source with patch 0010 applied')
    parser.add_argument('--dart',required=True)
    parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    root=a.source/'dart_shell/lib/src'
    logger=(root/'platform/focus_trace.dart').read_text()
    bridge=(root/'platform/denial_bridge.dart').read_text()
    handle=(root/'widgets/bottom_gesture_handle.dart').read_text()
    methods={'FOCUS':block(bridge,'  void focusWindow('),'SEND':block(bridge,'  void _sendWire('),'STATUS':block(handle,'  void _handleSwitchStatus(')}
    unit="import 'dart:typed_data';\nimport 'fixture-wire.dart' as wire;\n"+logger+FIXTURE
    for key,value in methods.items():unit=unit.replace('@'+key+'@',value)
    p=a.output/'test.dart';p.write_text(unit)
    (a.output/'fixture-wire.dart').write_text("enum WindowRequestKind {FocusWindow}\nconst denialWireToNativeChannel='denial/wire/to_native';\n")
    result={'scope':__doc__,'source_hashes':{str(x.relative_to(a.source)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [root/'platform/focus_trace.dart',root/'platform/denial_bridge.dart',root/'widgets/bottom_gesture_handle.dart']},'unit_sha256':hashlib.sha256(unit.encode()).hexdigest(),'runs':[],'vm':'NOT RUN','phone':'NOT RUN'}
    for label,setting,mode in [('disabled','0','methods'),('enabled','1','methods'),('cap','1','cap')]:
        command=[a.dart,str(p),mode];start=time.monotonic()
        r=subprocess.run(command,env=dict(os.environ,DENIA_FOCUS_TRACE=setting),capture_output=True,text=True,timeout=45)
        (a.output/(label+'.log')).write_text(r.stdout+r.stderr)
        rows=[json.loads(line.split('FOCUS_TRACE dart ',1)[1]) for line in r.stdout.splitlines() if line.startswith('FOCUS_TRACE dart ')]
        good=r.returncode==0 and 'DO_NOT_LOG_SECRET' not in r.stdout+r.stderr
        if label=='disabled':good &= not rows and 'PASS shell focus method semantics' in r.stdout
        elif label=='cap':good &= len(rows)==64 and [x['sequence'] for x in rows]==list(range(1,65)) and all(len(x['status'])<=48 for x in rows)
        else:
            good &= [(x['stage'],x.get('window_id')) for x in rows]==[('animationStatus',None),('animationStatus',None),('animationStatus',None),('invalidTarget',0),('send',7),('reply',7),('send',8),('error',8),('send',9),('noReply',9),('send',10)]
        result['runs'].append({'label':label,'command':command,'exit_status':r.returncode,'duration_seconds':time.monotonic()-start,'status':'PASS' if good else 'FAIL','trace_records':len(rows)})
    result['status']='PASS' if all(x['status']=='PASS' for x in result['runs']) else 'FAIL'
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0 if result['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())

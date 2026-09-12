#!/usr/bin/env python3
"""Strict log and installed-module closure checks for unsigned board builds."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

REPO=Path(__file__).resolve().parents[2]
POLICY=REPO/'configs/kernel/rog5-production-warning-policy.json'
INITIALIZER='warning: initializer overrides prior initialization of this subobject [-Winitializer-overrides]'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
    return h.hexdigest()

def safe(root,relative):
    path=(root/relative).resolve(strict=True)
    if not path.is_relative_to(root.resolve()):raise ValueError('path escapes build tree')
    return path

def diagnostics(text,stage,source,objects,policy):
    """Never treat dt-validate or depmod's zero exit status as silent success."""
    results=[];counts=Counter()
    pins=policy.get('initializer_overrides',[])
    config_path=objects/'.config'
    config=dict(line.split('=',1) for line in config_path.read_text().splitlines()
                if line.startswith('CONFIG_')) if config_path.is_file() else {}
    for line in text.splitlines():
        if not line.strip():continue
        if stage=='depmod':
            results.append(dict(line=line,allowed=False,kind='depmod'));continue
        schema=bool(re.search(r'\.(?:dtb|dtbo|yaml)(?::|\s+\()',line))
        if not schema and not re.search(r'\b(?:warning|error|fatal error)(?::|\s+\()',line,re.I):continue
        allowed=False
        match=re.match(r'(.+?):\d+:\d+: '+re.escape(INITIALIZER)+r'$',line)
        if match and not schema:
            for pin in pins:
                root=source if pin['root']=='source' else objects
                path=(root/pin['path']).resolve()
                reported=Path(match[1])
                if not reported.is_absolute():reported=objects/reported
                if reported.resolve()!=path:continue
                counts[str(path)]+=1
                site=match[0].split(str(match[1])+':',1)[1].split(': warning:',1)[0]
                counts[(str(path),site)]+=1
                identity=sha(safe(root,pin['path']))==pin['sha256']
                for dependency in pin['dependencies']:
                    dep_root=source if dependency['root']=='source' else objects
                    identity &= sha(safe(dep_root,dependency['path']))==dependency['sha256']
                allowed=identity and counts[str(path)]<=pin['maximum_count']
                if 'sites' in pin:
                    allowed &= site in pin['sites'] and counts[(str(path),site)]<=pin['sites'].get(site,0)
                break
        # Explicit reviewed site/message records are separate from schema validation.
        # A future DT schema error is never accepted through this warning policy.
        normalized=line.replace(str(source.resolve())+'/', '')
        if not allowed and not schema:
            for pin in policy.get('reviewed_messages',[]):
                limit=pin['messages'].get(normalized)
                if limit is None:continue
                counts[('reviewed',normalized)]+=1
                identity=sha(safe(source,pin['path']))==pin['sha256']
                for dep in pin['dependencies']:
                    identity &= sha(safe(source,dep['path']))==dep['sha256']
                guards=all(config.get(key,'n')==value for key,value in pin['config_guards'].items())
                allowed=identity and guards and counts[('reviewed',normalized)]<=limit
                break
        results.append(dict(line=line,allowed=allowed,kind='schema' if schema else 'compiler-or-tool'))
    return results

def module_closure(entries,builtin_text,dep_text,release):
    names={};paths={};errors=[]
    for entry in entries:
        name=entry['name'].replace('-','_');path=entry['path'].split('/lib/modules/'+release+'/',1)[-1]
        if name in names:errors.append('duplicate module name '+name)
        if path in paths:errors.append('duplicate module path '+path)
        names[name]=entry;paths[path]=name
        if not entry['vermagic'].split() or entry['vermagic'].split()[0]!=release:errors.append('vermagic '+name)
    builtin={Path(line).stem.replace('-','_') for line in builtin_text.splitlines() if line}
    dependencies={}
    for line in dep_text.splitlines():
        if line.count(':')!=1:errors.append('malformed modules.dep');continue
        path,raw=line.split(':',1)
        if path in dependencies:errors.append('duplicate modules.dep path '+path)
        dependencies[path]=raw.split()
        for target in [path]+raw.split():
            if target not in paths:errors.append('unknown modules.dep path '+target)
    if set(dependencies)!=set(paths):errors.append('modules.dep coverage')
    for path,name in paths.items():
        declared={x.replace('-','_') for x in names[name]['depends'].split(',') if x}
        missing=declared-set(names)-builtin
        if missing:errors.append('missing dependencies for '+name+': '+','.join(sorted(missing)))
        resolved={paths[x] for x in dependencies.get(path,[]) if x in paths}
        if declared-builtin-resolved:errors.append('modules.dep omits declared dependency for '+name)
    # A closed name set alone would admit an unloadable dependency cycle.
    pending={path:set(deps) for path,deps in dependencies.items()}
    while pending:
        leaves={path for path,deps in pending.items() if not deps}
        if not leaves:
            errors.append('modules.dep cycle or unresolved dependency');break
        pending={path:deps-leaves for path,deps in pending.items() if path not in leaves}
    return errors

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();build=args.build.resolve()
    result=dict(format='rog5-production-diagnostics-v1',status='FAIL',physical_validation='NOT RUN',
                scope='Compiler/DT diagnostics and installed-module dependency closure only',errors=[])
    try:
        raw=json.loads((build/'result.json').read_text());policy=json.loads(POLICY.read_text())
        result['raw_result_sha256']=sha(build/'result.json');result['policy_sha256']=sha(POLICY)
        result['checker_sha256']=sha(Path(__file__).resolve());result['diagnostics']=[]
        if raw['linux_base']!=policy['base_commit']:result['errors'].append('exact base identity mismatch')
        for relative,expected in raw.get('outputs',{}).items():
            if sha(safe(build,relative))!=expected:result['errors'].append('recorded output changed '+relative)
        for stage in ('kernel-build','modules-install','depmod','dtbs-check'):
            if raw['stages'].get(stage,{}).get('status')!='PASS':result['errors'].append(stage+' did not complete successfully')
            log=build/(stage+'.log')
            if not log.is_file():result['errors'].append('missing '+log.name);continue
            if sha(log)!=raw['stages'].get(stage,{}).get('log_sha256'):
                result['errors'].append('recorded log changed '+log.name)
            result['diagnostics']+=diagnostics(log.read_text(errors='replace'),stage,build/'source',build/'objects',policy)
        entries=json.loads((build/'module-provenance.json').read_text())
        for entry in entries:
            if sha(safe(build,entry['path']))!=entry['sha256']:result['errors'].append('module bytes changed '+entry['name'])
        modroot=build/'modules/lib/modules'/raw['release']
        result['errors']+=module_closure(entries,(modroot/'modules.builtin').read_text(),(modroot/'modules.dep').read_text(),raw['release'])
        if any(not entry['allowed'] for entry in result['diagnostics']):result['errors'].append('unreviewed diagnostic output')
        result['status']='PASS' if not result['errors'] else 'FAIL'
    except (OSError,ValueError,KeyError,TypeError,IndexError) as error:result['errors'].append(str(error))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.output.exists():parser.error('output already exists; preserve previous evidence')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['status']=='PASS' else 1
if __name__=='__main__':sys.exit(main())

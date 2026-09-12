#!/usr/bin/env python3
"""Validate the mobile contract and maintain only the generated current-state header."""
import argparse
import hashlib
import json
from pathlib import Path
import re

START='<!-- generated mobile status: begin -->'
END='<!-- generated mobile status: end -->'


def validate(repo):
    status=json.loads((repo/'configs/project-status.json').read_text())
    contract=json.loads((repo/status['mobile_contract']).read_text())
    baseline=contract['headless_baseline']
    if hashlib.sha256((repo/baseline['path']).read_bytes()).hexdigest()!=baseline['sha256']:
        raise ValueError('headless baseline changed')
    if contract['cellular']!='excluded': raise ValueError('cellular scope changed')
    if set(status['open_headless_results']) != {'S06', 'R01'} or any(value not in ('FAIL', 'BLOCKED', 'NOT RUN') for value in status['open_headless_results'].values()):
        raise ValueError('headless PASS requires an adapter to existing qualified acceptance evidence; cannot promote through this status file')
    required={'board-build','panel-scanout','brightness','panel-lifecycle','touch-identity','touch-coordinates','touch-wake','gpu-gles','gpu-vulkan','buttons-led','mobile-shell','audio','bluetooth','sensors','cameras','suspend-idle','charging','shutdown-startup','networking','update-rollback','recovery','daily-security','data-at-rest','boot-threat','lock-security','secret-handling','lost-device','remote-defaults'}
    if {row['id'] for row in contract['rows']}!=required or len(contract['rows'])!=len(required):
        raise ValueError('mobile acceptance rows missing or duplicated')
    for row in contract['rows']:
        for kind in ('software','physical'):
            proof=row[kind]
            if proof['status'] not in ('PASS','FAIL','BLOCKED','NOT RUN'): raise ValueError('invalid status')
            if proof['status']=='PASS':
                ref=proof['evidence']
                if not isinstance(ref,dict) or set(ref)!={'path','sha256'}: raise ValueError('PASS needs evidence bytes')
                path=(repo/ref['path']).resolve()
                path.relative_to(repo.resolve())
                if hashlib.sha256(path.read_bytes()).hexdigest()!=ref['sha256']: raise ValueError('evidence hash mismatch')
                if kind=='software':
                    observed=json.loads(path.read_text())
                    if observed.get('status')!='PASS' or observed.get('row')!=row['id'] or observed.get('scope')!='software' or not re.fullmatch('[0-9a-f]{40}',str(observed.get('source_tree',''))):
                        raise ValueError('software receipt does not prove row/source tree')
                if kind=='physical':
                    candidate=contract['candidate_sha256']
                    if not isinstance(candidate,str) or not re.fullmatch('[0-9a-f]{64}',candidate) or proof['candidate_sha256']!=candidate:
                        raise ValueError('physical proof needs exact candidate')
                    observed=json.loads(path.read_text())
                    if observed.get('status')!='PASS' or observed.get('scope')!='physical' or observed.get('candidate_sha256')!=candidate or observed.get('row')!=row['id']:
                        raise ValueError('physical receipt does not match candidate/row')
    physical={row['physical']['status'] for row in contract['rows']}
    aggregate='PASS' if physical=={'PASS'} else 'FAIL' if 'FAIL' in physical else 'BLOCKED' if 'BLOCKED' in physical else 'NOT RUN'
    if status['physical_tests']!=aggregate: raise ValueError('physical summary disagrees with acceptance rows')
    if not (repo/status['artifact_pointer']).is_file(): raise ValueError('artifact pointer missing')
    if not (repo/status['evidence']).is_file(): raise ValueError('current evidence missing')
    header=(START+'\n'+f"Current structured status: **{status['phase']}**. Mobile physical tests: **{status['physical_tests']}**. "
            +f"Headless S06: **{status['open_headless_results']['S06']}**; R01: **{status['open_headless_results']['R01']}**.\n\n"
            +status['next']+' See [current repair evidence](../'+status['evidence']+') and '
            +'[artifact pointer](../'+status['artifact_pointer']+'). Historical checkpoints below remain unchanged.\n'+END+'\n\n')
    return header


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true')
    args=parser.parse_args();repo=Path(__file__).resolve().parents[2];header=validate(repo)
    path=repo/'docs/current-state.md';old=path.read_text()
    if START in old:
        begin=old.index(START);end=old.index(END,begin)+len(END)
        new=old[:begin]+header+old[end:].lstrip('\n')
    else:
        first,rest=old.split('\n',1);new=first+'\n\n'+header+rest.lstrip('\n')
    if args.write: path.write_text(new)
    elif old!=new: raise SystemExit('FAIL generated current-state header is stale')
    print('PASS mobile acceptance and generated current-state status; physical evidence not inferred')

if __name__=='__main__': main()

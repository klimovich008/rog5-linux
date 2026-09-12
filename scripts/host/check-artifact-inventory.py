#!/usr/bin/env python3
"""Check the recorded inventory; never open large images or admit a candidate."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess

def need(condition, message):
    if not condition:
        raise ValueError(message)

def validate(root, database_dir=None):
    inventory = json.loads((root / 'manifests/artifact-sets.json').read_text())
    current = json.loads((root / 'manifests/current-artifact.json').read_text())
    registered = {r['name']: r for r in csv.DictReader((root / 'manifests/artifacts.tsv').open(), delimiter='\t')}
    tracked = set(subprocess.check_output(['git', '-C', str(root), 'ls-files', '--', 'artifacts'], text=True).splitlines())
    required = {'status', 'source_commit', 'linux_commit', 'production_series_sha256', 'config_sha256', 'toolchain_hashes', 'exact_command', 'release_vermagic', 'module_dependencies', 'input_hashes', 'outputs', 'admission', 'physical_qualification', 'superseded_by'}
    statuses = {'active', 'historical', 'retired', 'superseded', 'fixture'}
    sets, outputs = ({}, {})
    verified = 0
    for entry in inventory['sets']:
        need(required <= set(entry), entry['id'])
        need(entry['id'] not in sets, 'duplicate set')
        need(entry['status'] in statuses, 'invalid recorded metadata')
        sets[entry['id']] = entry
        for artifact in entry['outputs']:
            path = artifact['path']
            need(path not in outputs, path)
            outputs[path] = artifact
            need(artifact['status'] in statuses, 'invalid recorded metadata')
            if path in registered:
                need(artifact['sha256'] == registered[path]['sha256'], path)
                need(artifact['size'] == int(registered[path]['size']), path)
            if path in tracked and artifact['size'] <= 1024 * 1024:
                data = (root / path).read_bytes()
                need(len(data) == artifact['size'], path)
                need(hashlib.sha256(data).hexdigest() == artifact['sha256'], path)
                verified += 1
    need(set(registered) | tracked <= set(outputs), 'unclassified retained artifact')
    need(len(sets) == inventory['coverage']['set_count'], 'invalid recorded metadata')
    target = sets[current['prepared_signed_candidate']['set_id']]
    need(target['status'] == 'active', 'invalid recorded metadata')
    need(target['physical_qualification'] == 'NOT RUN', 'invalid recorded metadata')
    need(current['review_source_changes']['status'] == 'NOT INSTALLED', 'invalid recorded metadata')
    need(outputs['artifacts/buttons-indicator-v1/leds-qcom-lpg.ko']['status'] == 'fixture', 'invalid recorded metadata')
    print(f'PASS {len(sets)} sets; {len(registered)} registered and {len(tracked)} tracked files covered; {verified} small tracked hashes checked')
    print('NOT RUN large/private byte verification, admission or physical qualification')
if __name__ == '__main__':
    validate(Path(__file__).resolve().parents[2])

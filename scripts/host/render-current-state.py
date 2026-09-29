#!/usr/bin/env python3
"""Write the generated status block of docs/current-state.md from docs/status/components.json.

The block sits between the BEGIN/END markers below; the rest of the file is
hand-written. components.json is the single status source: its "bundles"
object names the installed default and fallback, its "areas" list every
component with ready/partial/missing/untested (the same data
tools/status-map/render.py draws).

    python3 scripts/host/render-current-state.py           # rewrite the block
    python3 scripts/host/render-current-state.py --check   # fail if it is stale
"""
import argparse
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
COMPONENTS = REPO / 'docs/status/components.json'
STATE = REPO / 'docs/current-state.md'
BEGIN = '<!-- BEGIN GENERATED: scripts/host/render-current-state.py from docs/status/components.json -->'
END = '<!-- END GENERATED -->'
ORDER = ('ready', 'partial', 'untested', 'missing')
LABEL = {'ready': 'ready', 'partial': 'partial', 'untested': 'needs a test', 'missing': 'missing'}


def render(data):
    bundles = data['bundles']
    default, fallback = bundles['default'], bundles['fallback']
    counts = {status: 0 for status in ORDER}
    open_items = {status: [] for status in ORDER[1:]}
    for area in data['areas']:
        for component in area['components']:
            status = component['status']
            if status not in counts:
                raise ValueError(f"unknown status {status!r} for {component['name']}")
            counts[status] += 1
            if status != 'ready':
                open_items[status].append((area['name'], component['name'], component.get('note', '')))
    lines = [BEGIN,
             f"Status as of {data['as_of']} (source: `docs/status/components.json`).",
             '',
             '| | Bundle | Kernel build | DTB | Installed |',
             '|---|---|---|---|---|',
             f"| Default | `{default['bundle']}` | {default['kernel']} | {default['dtb']} | {default['installed']} |",
             f"| Fallback | `{fallback['bundle']}` | {fallback['kernel']} | {fallback['dtb']} | {fallback['installed']} |",
             '',
             'Components: ' + ', '.join(f"{counts[s]} {LABEL[s]}" for s in ORDER) + '.',
             '']
    for status in ORDER[1:]:
        if not open_items[status]:
            continue
        lines.append(f"{LABEL[status].capitalize()}:")
        lines.append('')
        for area, name, note in open_items[status]:
            lines.append(f"- {area} / {name}" + (f": {note}" if note else ''))
        lines.append('')
    lines.append(END)
    return '\n'.join(lines) + '\n'


def splice(text, block):
    if text.count(BEGIN) != 1 or text.count(END) != 1 or text.index(BEGIN) > text.index(END):
        raise ValueError('docs/current-state.md must contain exactly one generated block')
    start = text.index(BEGIN)
    end = text.index(END) + len(END)
    if text[end:end + 1] == '\n':
        end += 1
    return text[:start] + block + text[end:]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', help='exit 1 if the block differs from components.json')
    parser.add_argument('--components', type=Path, default=COMPONENTS)
    parser.add_argument('--state', type=Path, default=STATE)
    args = parser.parse_args()
    text = args.state.read_text()
    updated = splice(text, render(json.loads(args.components.read_text())))
    if args.check:
        if updated != text:
            print('FAIL docs/current-state.md is stale: run scripts/host/render-current-state.py', file=sys.stderr)
            return 1
        print('PASS docs/current-state.md matches docs/status/components.json')
        return 0
    if updated != text:
        args.state.write_text(updated)
    return 0


if __name__ == '__main__':
    sys.exit(main())

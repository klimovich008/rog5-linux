#!/usr/bin/env python3
"""Render docs/status/components.json as a treemap SVG (docs/images/status-map.svg).

Each area is a block; each component inside it is a tile sized by its weight
and coloured by status: ready (green), partial (yellow), missing (red),
untested (blue). No dependencies beyond the Python standard library.

Usage: render.py [components.json] [output.svg]
"""
import html, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
COLORS = {'ready': '#4cc417', 'partial': '#e0b91b', 'missing': '#d9534f', 'untested': '#3b8fd9'}
LABELS = {'ready': 'ready', 'partial': 'partial / not fully integrated', 'missing': 'missing',
          'untested': 'needs a test'}


def worst(ratios):
    return max(ratios) if ratios else float('inf')


def squarify(values, x, y, w, h):
    """Squarified treemap (Bruls et al.): returns one (x, y, w, h) per value."""
    total = sum(values)
    if not values or total <= 0:
        return []
    scale = w * h / total
    areas = [v * scale for v in values]
    rects, row, i = [], [], 0

    def layout(row, x, y, w, h):
        s = sum(row)
        out = []
        if w >= h:  # column on the left
            cw = s / h
            yy = y
            for a in row:
                out.append((x, yy, cw, a / cw))
                yy += a / cw
            return out, (x + cw, y, w - cw, h)
        rh = s / w
        xx = x
        for a in row:
            out.append((xx, y, a / rh, rh))
            xx += a / rh
        return out, (x, y + rh, w, h - rh)

    def ratios(row, side):
        s = sum(row)
        return [max(side * side * a / (s * s), (s * s) / (side * side * a)) for a in row]

    while i < len(areas):
        side = min(w, h)
        a = areas[i]
        if not row or worst(ratios(row + [a], side)) <= worst(ratios(row, side)):
            row.append(a)
            i += 1
            continue
        out, (x, y, w, h) = layout(row, x, y, w, h)
        rects += out
        row = []
    if row:
        out, _ = layout(row, x, y, w, h)
        rects += out
    return rects


def text(x, y, s, size, weight='normal', fill='#10200a'):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="DejaVu Sans, Arial, sans-serif" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}">{html.escape(s)}</text>')


def render(data, width=960, height=620):
    areas = sorted(data['areas'], key=lambda a: -sum(c.get('weight', 1) for c in a['components']))
    legend_h = 34
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height + legend_h}" '
             f'viewBox="0 0 {width} {height + legend_h}">',
             f'<rect width="{width}" height="{height + legend_h}" fill="#1f2229"/>']
    sums = [sum(c.get('weight', 1) for c in a['components']) for a in areas]
    for area, (ax, ay, aw, ah) in zip(areas, squarify(sums, 2, 2, width - 4, height - 4)):
        comps = sorted(area['components'], key=lambda c: -c.get('weight', 1))
        head = 16 if ah > 40 and aw > 60 else 0
        parts.append(f'<rect x="{ax:.1f}" y="{ay:.1f}" width="{aw:.1f}" height="{ah:.1f}" '
                     f'fill="#2b2f38" stroke="#1f2229" stroke-width="2"/>')
        if head:
            parts.append(text(ax + 4, ay + 12, area['name'], 11, 'bold', '#e8e8e8'))
        rects = squarify([c.get('weight', 1) for c in comps], ax + 1, ay + head + 1, aw - 2, ah - head - 2)
        for c, (x, y, w, h) in zip(comps, rects):
            fill = COLORS.get(c['status'], '#888')
            note = f"{area['name']} / {c['name']}: {LABELS.get(c['status'], c['status'])}"
            if c.get('note'):
                note += f" - {c['note']}"
            parts.append(f'<g><title>{html.escape(note)}</title><rect x="{x:.1f}" y="{y:.1f}" '
                         f'width="{w:.1f}" height="{h:.1f}" fill="{fill}" stroke="#e6e6e6" stroke-width="1"/>')
            size = 10 if w > 70 else 8
            if w > 34 and h > 13:
                max_chars = int((w - 6) / (size * 0.6))
                name = c['name'] if len(c['name']) <= max_chars else c['name'][:max(max_chars - 1, 1)] + '…'
                parts.append(text(x + 3, y + size + 2, name, size))
            parts.append('</g>')
    x = 8
    for key in ('ready', 'partial', 'untested', 'missing'):
        n = sum(1 for a in areas for c in a['components'] if c['status'] == key)
        parts.append(f'<rect x="{x}" y="{height + 10}" width="14" height="14" fill="{COLORS[key]}"/>')
        label = f'{LABELS[key]} ({n})'
        parts.append(text(x + 20, height + 22, label, 12, fill='#e8e8e8'))
        x += 30 + len(label) * 7
    parts.append(text(width - 150, height + 22, data.get('as_of', ''), 12, fill='#9aa0a6'))
    parts.append('</svg>')
    return '\n'.join(parts) + '\n'


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, 'docs/status/components.json')
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPO, 'docs/images/status-map.svg')
    with open(src) as f:
        data = json.load(f)
    for a in data['areas']:
        for c in a['components']:
            if c['status'] not in COLORS:
                sys.exit(f"{a['name']}/{c['name']}: unknown status {c['status']!r}")
    with open(out, 'w') as f:
        f.write(render(data))
    print(out)


if __name__ == '__main__':
    main()

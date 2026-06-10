#!/usr/bin/env python3
"""
svg_part_tool — outil déterministe d'extraction de pièces depuis les SVG BikeCAD.

Les SVG exportés par BikeCAD (Batik) dessinent le vélo dans des groupes dont le
transform est EXACTEMENT la matrice de base `matrix(a,0,0,d,0,H)` (a≈1, d≈-1).
Les coordonnées des paths AVANT cette matrice sont déjà en **mm, y vers le haut**
— c'est exactement le repère qu'attend `io/svg_export.py`. La matrice de base ne
sert qu'à projeter vers les pixels écran (y vers le bas).

Les COTES (dimensions) sont dans des groupes `fill="red"` ou dont le transform
ajoute un `translate(...)`/`rotate(...)` après la matrice de base, et sont faits
de `line` + petites flèches + `text`. On les exclut des pièces.

Sous-commandes :
  paths   <svg>                       → JSON: une ligne par path candidat (pièce)
  render  <svg> <idx,idx,..> <out>    → SVG autonome avec SEULEMENT ces paths (vérif visuelle)
  context <svg> <idx,idx,..> <out>    → vélo entier en gris + paths sélectionnés en rouge plein
  extract <svg> <idx,idx,..> <out>    → sprite normalisé (anchor→origine), + manifest .json

Les index `idx` sont ceux renvoyés par `paths` (numérotation globale stable).
"""
import sys, re, json, math
import xml.etree.ElementTree as ET

NS = 'http://www.w3.org/2000/svg'
ETNS = '{%s}' % NS
ET.register_namespace('', NS)

_NUM = re.compile(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?')


def _style_get(style, key):
    m = re.search(r'(?:^|;)\s*%s\s*:\s*([^;]+)' % re.escape(key), style or '')
    return m.group(1).strip() if m else ''


def _fill_of(el):
    """Couleur de remplissage effective d'un élément (attr fill ou style fill)."""
    f = el.get('fill')
    if f:
        return f.strip()
    return _style_get(el.get('style', ''), 'fill')


def _stroke_of(el):
    s = el.get('stroke')
    if s:
        return s.strip()
    return _style_get(el.get('style', ''), 'stroke')


def _base_matrix(transform):
    """Renvoie (a,b,c,d,e,f) si transform est exactement une matrix(...), sinon None."""
    if not transform:
        return None
    t = transform.strip()
    m = re.fullmatch(r'matrix\(([^)]*)\)', t)
    if not m:
        return None
    nums = [float(x) for x in _NUM.findall(m.group(1))]
    if len(nums) != 6:
        return None
    return tuple(nums)


def _path_points(d):
    """Liste de (x,y) approx (points de contrôle inclus) pour bbox. Coords pré-matrice."""
    pts = []
    i = 0
    n = len(d)
    cmd = None
    while i < n:
        c = d[i]
        if c.isalpha():
            cmd = c
            i += 1
            continue
        # lire un bloc de nombres jusqu'à la prochaine lettre
        m = _NUM.match(d, i)
        if not m:
            i += 1
            continue
        # rassembler tous les nombres de ce segment
        nums = []
        j = i
        while j < n and not d[j].isalpha():
            mm = _NUM.match(d, j)
            if mm:
                nums.append(float(mm.group()))
                j = mm.end()
                # sauter séparateurs
                while j < n and d[j] in ' ,\t\n\r':
                    j += 1
            else:
                j += 1
        i = j
        if cmd in ('M', 'L', 'T'):
            for k in range(0, len(nums) - 1, 2):
                pts.append((nums[k], nums[k + 1]))
        elif cmd in ('C',):
            for k in range(0, len(nums) - 5, 6):
                pts.append((nums[k + 4], nums[k + 5]))
                pts.append((nums[k], nums[k + 1]))
                pts.append((nums[k + 2], nums[k + 3]))
        elif cmd in ('S', 'Q'):
            for k in range(0, len(nums) - 3, 4):
                pts.append((nums[k], nums[k + 1]))
                pts.append((nums[k + 2], nums[k + 3]))
        elif cmd in ('A',):
            for k in range(0, len(nums) - 6, 7):
                pts.append((nums[k + 5], nums[k + 6]))
        elif cmd in ('H',):
            pass
        elif cmd in ('V',):
            pass
    return pts


def _bbox(pts):
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]


def _canvas(root):
    return float(root.get('width', '0')), float(root.get('height', '0'))


def _collect(root):
    """Renvoie (base, items) ; items = list de dict pour chaque path candidat-pièce.

    base = matrice de base (a,b,c,d,e,f) la plus fréquente parmi les groupes dessin.
    Un path est candidat-pièce ssi : parent <g> a transform == matrice de base,
    le path lui-même n'a pas de transform, et le groupe n'est pas une cote (fill red).
    """
    # 1) trouver la matrice de base : matrix la plus fréquente sur les <g>
    from collections import Counter
    matcount = Counter()
    for g in root.iter(ETNS + 'g'):
        bm = _base_matrix(g.get('transform', ''))
        if bm:
            matcount[bm] += 1
    base = matcount.most_common(1)[0][0] if matcount else (1, 0, 0, -1, 0, 0)

    items = []
    gi = 0
    for g in root.iter(ETNS + 'g'):
        bm = _base_matrix(g.get('transform', ''))
        if bm != base:
            continue
        gfill = _fill_of(g)
        gi += 1
        for ch in g:
            if ch.tag != ETNS + 'path':
                continue
            if ch.get('transform'):  # paths avec transform propre = flèches de cote
                continue
            d = ch.get('d', '')
            pts = _path_points(d)
            bb = _bbox(pts)
            if not bb:
                continue
            fill = _fill_of(ch) or gfill
            items.append({
                'grp': gi,
                'gfill': gfill,
                'fill': fill,
                'stroke': _stroke_of(ch),
                'bbox': bb,
                'npts': len(pts),
                'dlen': len(d),
                '_d': d,
            })
    # index global stable
    for i, it in enumerate(items):
        it['i'] = i
    return base, items


def _is_dim(it):
    """Heuristique : path de cote (rouge, ou pur trait noir fin de cote)."""
    f = (it['fill'] or '').replace(' ', '')
    return f in ('red', 'rgb(204,0,0)')


def cmd_paths(svg, show_dims=False):
    root = ET.parse(svg).getroot()
    W, H = _canvas(root)
    base, items = _collect(root)
    out = {'svg': svg, 'canvas': [W, H], 'base_matrix': base, 'count': len(items), 'paths': []}
    for it in items:
        if not show_dims and _is_dim(it):
            continue
        out['paths'].append({k: it[k] for k in ('i', 'grp', 'gfill', 'fill', 'stroke', 'bbox', 'npts', 'dlen')})
    print(json.dumps(out))


def _selected(items, idxstr):
    want = set()
    for tok in idxstr.split(','):
        tok = tok.strip()
        if not tok:
            continue
        if '-' in tok and not tok.startswith('-'):
            a, b = tok.split('-')
            want.update(range(int(a), int(b) + 1))
        else:
            want.add(int(tok))
    return [it for it in items if it['i'] in want]


def _svg_header(W, H, style="stroke:none"):
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="{NS}" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{W:.1f}" height="{H:.1f}" viewBox="0 0 {W:.1f} {H:.1f}" '
            f'style="{style}">\n')


def _rasterize(svg_path, png_path, width=1100):
    """Rasterise un SVG en PNG via cairosvg (respecte exactement le viewBox)."""
    try:
        import cairosvg
    except Exception as e:
        return {'png': None, 'error': f'cairosvg indisponible: {e}'}
    cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=width)
    return {'png': png_path}


def cmd_raster(svg, out, width=1100):
    print(json.dumps(_rasterize(svg, out, width)))


def cmd_render(svg, idxstr, out, pad=20.0):
    """SVG autonome avec seulement les paths choisis, dans le repère écran (matrice de base)."""
    root = ET.parse(svg).getroot()
    base, items = _collect(root)
    sel = _selected(items, idxstr)
    if not sel:
        sys.exit('aucun path sélectionné')
    a, b, c, d, e, f = base
    # bbox écran
    xs, ys = [], []
    for it in sel:
        x0, y0, x1, y1 = it['bbox']
        for (px, py) in [(x0, y0), (x1, y1), (x0, y1), (x1, y0)]:
            xs.append(a * px + c * py + e)
            ys.append(b * px + d * py + f)
    minx, maxx = min(xs) - pad, max(xs) + pad
    miny, maxy = min(ys) - pad, max(ys) + pad
    W, H = maxx - minx, maxy - miny
    parts = [f'<?xml version="1.0" encoding="UTF-8"?>',
             f'<svg xmlns="{NS}" width="{W:.1f}" height="{H:.1f}" viewBox="{minx:.2f} {miny:.2f} {W:.2f} {H:.2f}">',
             f'<rect x="{minx:.1f}" y="{miny:.1f}" width="{W:.1f}" height="{H:.1f}" fill="white"/>',
             f'<g transform="matrix({a},{b},{c},{d},{e},{f})">']
    for it in sel:
        fill = it['fill'] if it['fill'] and it['fill'] != 'none' else 'rgb(120,120,120)'
        parts.append(f'<path d="{it["_d"]}" fill="{fill}" stroke="black" stroke-width="0.5"/>')
    parts.append('</g></svg>')
    open(out, 'w').write('\n'.join(parts))
    r = _rasterize(out, out.replace('.svg', '.png'), width=min(1200, int(W) + 40))
    print(json.dumps({'out': out, 'png': r.get('png'), 'selected': [it['i'] for it in sel], 'screen_bbox': [minx, miny, maxx, maxy]}))


def cmd_context(svg, idxstr, out):
    """Vélo entier en gris clair, paths sélectionnés en rouge plein → confirme la région."""
    root = ET.parse(svg).getroot()
    W, H = _canvas(root)
    base, items = _collect(root)
    selset = set(it['i'] for it in _selected(items, idxstr))
    a, b, c, d, e, f = base
    parts = [_svg_header(W, H),
             f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>',
             f'<g transform="matrix({a},{b},{c},{d},{e},{f})">']
    for it in items:
        if _is_dim(it):
            continue
        if it['i'] in selset:
            parts.append(f'<path d="{it["_d"]}" fill="red" stroke="red" stroke-width="1"/>')
        else:
            parts.append(f'<path d="{it["_d"]}" fill="rgb(225,225,225)" stroke="rgb(180,180,180)" stroke-width="0.4"/>')
    parts.append('</g></svg>')
    open(out, 'w').write('\n'.join(parts))
    r = _rasterize(out, out.replace('.svg', '.png'), width=1200)
    print(json.dumps({'out': out, 'png': r.get('png'), 'selected': sorted(selset)}))


def cmd_extract(svg, idxstr, out, anchor=None):
    """Sprite normalisé : paths en mm y-up, translatés pour que l'ancre soit l'origine.

    anchor = "cx,cy" en coords pré-matrice (mm y-up). Défaut = coin bas-gauche de la bbox.
    Écrit aussi out.replace('.svg','.json') = {paths:[{d,fill}], bbox_local, anchor}.
    """
    root = ET.parse(svg).getroot()
    base, items = _collect(root)
    sel = _selected(items, idxstr)
    if not sel:
        sys.exit('aucun path sélectionné')
    xs, ys = [], []
    for it in sel:
        x0, y0, x1, y1 = it['bbox']
        xs += [x0, x1]
        ys += [y0, y1]
    minx, miny, maxx, maxy = min(xs), min(ys), max(xs), max(ys)
    if anchor:
        ax, ay = [float(v) for v in anchor.split(',')]
    else:
        ax, ay = minx, miny
    # translater chaque path : on réécrit les nombres = soustraction de l'ancre.
    def shift(d):
        # réécrit en consommant commande par commande (mêmes règles que _path_points)
        res = []
        i, n, cmd = 0, len(d), None
        while i < n:
            ch = d[i]
            if ch.isalpha():
                cmd = ch
                res.append(ch)
                i += 1
                continue
            mm = _NUM.match(d, i)
            if not mm:
                res.append(ch); i += 1; continue
            nums = []
            j = i
            while j < n and not d[j].isalpha():
                m2 = _NUM.match(d, j)
                if m2:
                    nums.append(float(m2.group())); j = m2.end()
                    while j < n and d[j] in ' ,\t\n\r': j += 1
                else:
                    j += 1
            i = j
            res.append(_shift_nums(cmd, nums, ax, ay))
        return ' '.join(x for x in res)
    sprite_paths = [{'d': shift(it['_d']).strip(), 'fill': it['fill'], 'stroke': it['stroke']} for it in sel]
    bbox_local = [round(minx - ax, 3), round(miny - ay, 3), round(maxx - ax, 3), round(maxy - ay, 3)]
    manifest = {'source': svg, 'selected': [it['i'] for it in sel],
                'anchor_world': [ax, ay], 'bbox_local': bbox_local,
                'size': [round(maxx - minx, 3), round(maxy - miny, 3)], 'paths': sprite_paths}
    open(out.replace('.svg', '.json'), 'w').write(json.dumps(manifest, indent=1))
    # SVG de prévisualisation (y-up → on flippe pour affichage)
    w, h = maxx - minx, maxy - miny
    pv = [f'<?xml version="1.0" encoding="UTF-8"?>',
          f'<svg xmlns="{NS}" width="{w:.1f}" height="{h:.1f}" viewBox="0 0 {w:.1f} {h:.1f}">',
          f'<rect width="{w:.1f}" height="{h:.1f}" fill="white"/>',
          f'<g transform="matrix(1,0,0,-1,{-bbox_local[0]:.3f},{bbox_local[3]:.3f})">']
    for sp in sprite_paths:
        fill = sp['fill'] if sp['fill'] and sp['fill'] != 'none' else 'rgb(120,120,120)'
        pv.append(f'<path d="{sp["d"]}" fill="{fill}" stroke="black" stroke-width="0.4"/>')
    pv.append('</g></svg>')
    open(out, 'w').write('\n'.join(pv))
    _rasterize(out, out.replace('.svg', '.png'), width=min(900, int(w) + 40))
    print(json.dumps({'out': out, 'png': out.replace('.svg', '.png'), 'manifest': out.replace('.svg', '.json'),
                      'size': manifest['size'], 'bbox_local': bbox_local, 'npaths': len(sprite_paths) if False else len(sprite_paths)}))


def _shift_nums(cmd, nums, ax, ay):
    """Réécrit les nombres d'une commande absolue en soustrayant l'ancre aux coords."""
    out = []
    if cmd in ('M', 'L', 'T'):
        for k in range(0, len(nums), 2):
            out += [nums[k] - ax, nums[k + 1] - ay]
    elif cmd == 'C':
        for k in range(0, len(nums) - 5, 6):
            out += [nums[k] - ax, nums[k + 1] - ay, nums[k + 2] - ax, nums[k + 3] - ay, nums[k + 4] - ax, nums[k + 5] - ay]
    elif cmd in ('S', 'Q'):
        for k in range(0, len(nums) - 3, 4):
            out += [nums[k] - ax, nums[k + 1] - ay, nums[k + 2] - ax, nums[k + 3] - ay]
    elif cmd == 'A':
        for k in range(0, len(nums) - 6, 7):
            out += nums[k:k + 5] + [nums[k + 5] - ax, nums[k + 6] - ay]
    elif cmd == 'H':
        out += [v - ax for v in nums]
    elif cmd == 'V':
        out += [v - ay for v in nums]
    else:
        out += nums
    return ' '.join(f'{v:.3f}' for v in out)


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1]
    if cmd == 'paths':
        cmd_paths(sys.argv[2], show_dims=('--dims' in sys.argv))
    elif cmd == 'raster':
        width = 1100
        if '--w' in sys.argv:
            width = int(sys.argv[sys.argv.index('--w') + 1])
        cmd_raster(sys.argv[2], sys.argv[3], width)
    elif cmd == 'render':
        pad = 20.0
        if '--pad' in sys.argv:
            pad = float(sys.argv[sys.argv.index('--pad') + 1])
        cmd_render(sys.argv[2], sys.argv[3], sys.argv[4], pad)
    elif cmd == 'context':
        cmd_context(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == 'extract':
        anchor = None
        if '--anchor' in sys.argv:
            anchor = sys.argv[sys.argv.index('--anchor') + 1]
        cmd_extract(sys.argv[2], sys.argv[3], sys.argv[4], anchor)
    else:
        print(__doc__); sys.exit(1)


if __name__ == '__main__':
    main()

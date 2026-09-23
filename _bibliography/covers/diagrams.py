"""Generate consistent 600x400 schematic SVG thumbnails for publications.

Each spec: tag (short method name), stages (left-to-right pipeline),
optional loop (feedback arrow from last stage back to a given stage),
optional below (a node under a stage, arrow direction up/down),
caption (one-line key idea), motif (small illustrative glyph in the corner).
"""
import math, random, html, os, sys

W, H = 480, 320
INK = "#1f2a37"
MUTED = "#5b6b7b"
PAL = {
    "blue":  ("#2f6f9f", "#e6f0f7"),
    "teal":  ("#2a8c82", "#e4f3f1"),
    "amber": ("#b7791f", "#fbf1df"),
    "plum":  ("#7a4f9a", "#f1eaf6"),
    "slate": ("#4a5a6a", "#eef1f4"),
    "red":   ("#b04a3c", "#f8e9e6"),
}
FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"


def esc(s):
    return html.escape(s, quote=True)


def text_block(cx, cy, label, size=14, color=INK, weight="500"):
    lines = label.split("\n")
    lh = size * 1.22
    y0 = cy - (len(lines) - 1) * lh / 2 + size * 0.35
    out = []
    for i, ln in enumerate(lines):
        out.append(f'<text x="{cx:.1f}" y="{y0 + i*lh:.1f}" text-anchor="middle" '
                   f'font-family="{FONT}" font-size="{size}" font-weight="{weight}" fill="{color}">{esc(ln)}</text>')
    return "\n".join(out)


CW = 0.54  # approx glyph width / font size


def wrap(words, n):
    """Greedy wrap into at most n lines balancing length."""
    total = sum(len(w) for w in words) + len(words) - 1
    target = max(max(len(w) for w in words), total / n)
    lines, cur = [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > target + 1:
            lines.append(cur); cur = w
        else:
            cur = (cur + ("" if cur.endswith("-") else " ") + w).strip()
    lines.append(cur)
    return lines


def fit(label, w, h, maxsize):
    import re as _re
    words = [w for w in _re.split(r"(?<=-)|\s+", label.replace("\n", " ")) if w]
    best = (0, [label])
    for n in range(1, 6):
        lines = wrap(words, n)
        longest = max(len(l) for l in lines)
        size = min(maxsize, (w - 10) / (CW * longest), (h - 12) / (1.22 * len(lines)))
        if size > best[0] + 0.3:
            best = (size, lines)
    return best


def box(x, y, w, h, label, color, size=14):
    stroke, fill = PAL[color]
    size, lines = fit(label, w, h, size)
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="10" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>\n' + text_block(x + w/2, y + h/2, "\n".join(lines), size))


def arrow(x1, y1, x2, y2, color=MUTED, dashed=False):
    d = ' stroke-dasharray="6 5"' if dashed else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
            f'stroke-width="2.2" marker-end="url(#ah)"{d}/>')


def motif_svg(kind, seed):
    rnd = random.Random(seed)
    g = []
    ox, oy = 350, 22  # top-right corner region ~110x70
    if kind == "dots":
        for _ in range(70):
            a = rnd.random() * 2 * math.pi; r = rnd.random() ** 0.6 * 30
            g.append(f'<circle cx="{ox+55+r*math.cos(a)*1.4:.1f}" cy="{oy+35+r*math.sin(a):.1f}" r="2" fill="{PAL[rnd.choice(["blue","teal","plum"])][0]}" opacity="0.8"/>')
    elif kind == "curve":
        pts = [(ox + i*11, oy + 35 + 22*math.sin(i*0.7 + 0.5)) for i in range(11)]
        g.append('<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f'" fill="none" stroke="{PAL["teal"][0]}" stroke-width="3" stroke-linecap="round"/>')
        for x, y in pts[::3]:
            g.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#fff" stroke="{PAL["teal"][0]}" stroke-width="2"/>')
    elif kind == "tree":
        levels = [[(ox+55, oy+8)], [(ox+25, oy+35), (ox+85, oy+35)], [(ox+10, oy+62), (ox+40, oy+62), (ox+70, oy+62), (ox+100, oy+62)]]
        for l in range(2):
            for i, (x, y) in enumerate(levels[l]):
                for (x2, y2) in levels[l+1][i*2:i*2+2]:
                    g.append(f'<line x1="{x}" y1="{y}" x2="{x2}" y2="{y2}" stroke="{MUTED}" stroke-width="1.5"/>')
        for lv in levels:
            for x, y in lv:
                g.append(f'<circle cx="{x}" cy="{y}" r="6" fill="{PAL["amber"][1]}" stroke="{PAL["amber"][0]}" stroke-width="2"/>')
    elif kind == "graph":
        nodes = [(ox+rnd.randint(8, 102), oy+rnd.randint(6, 66)) for _ in range(9)]
        for i in range(len(nodes)):
            for j in range(i+1, len(nodes)):
                if math.dist(nodes[i], nodes[j]) < 42:
                    g.append(f'<line x1="{nodes[i][0]}" y1="{nodes[i][1]}" x2="{nodes[j][0]}" y2="{nodes[j][1]}" stroke="{MUTED}" stroke-width="1.4"/>')
        for x, y in nodes:
            g.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{PAL["blue"][1]}" stroke="{PAL["blue"][0]}" stroke-width="2"/>')
    elif kind == "gauss":
        pts = [(ox + i*2.2, oy + 66 - 56*math.exp(-((i-25)/9.0)**2)) for i in range(51)]
        g.append('<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f'" fill="{PAL["plum"][1]}" stroke="{PAL["plum"][0]}" stroke-width="2.5"/>')
    elif kind == "bars":
        for i, hgt in enumerate([50, 38, 44, 20, 32, 14, 26]):
            c = PAL["slate"][0] if i % 3 else PAL["red"][0]
            g.append(f'<rect x="{ox+6+i*15}" y="{oy+68-hgt}" width="10" height="{hgt}" rx="2" fill="{c}" opacity="0.8"/>')
    elif kind == "grid":
        for i in range(5):
            for j in range(4):
                keep = rnd.random() > 0.45
                g.append(f'<rect x="{ox+8+i*20}" y="{oy+4+j*17}" width="16" height="13" rx="2" fill="{PAL["teal"][0] if keep else "#dfe5ea"}" opacity="{0.85 if keep else 1}"/>')
    elif kind == "rotate":
        cx, cy = ox+55, oy+36
        g.append(f'<circle cx="{cx}" cy="{cy}" r="28" fill="none" stroke="{PAL["plum"][0]}" stroke-width="2.5" stroke-dasharray="120 60"/>')
        g.append(f'<polygon points="{cx+22},{cy-22} {cx+32},{cy-14} {cx+20},{cy-10}" fill="{PAL["plum"][0]}"/>')
        g.append(f'<rect x="{cx-10}" y="{cy-10}" width="20" height="20" fill="{PAL["plum"][1]}" stroke="{PAL["plum"][0]}" stroke-width="2" transform="rotate(25 {cx} {cy})"/>')
    elif kind == "layers":
        for i in range(8):
            keep = i not in (2, 4, 5)
            g.append(f'<rect x="{ox+6}" y="{oy+2+i*8.5}" width="98" height="6" rx="2" fill="{PAL["blue"][0] if keep else "#dfe5ea"}"/>')
    elif kind == "gripper":
        c = PAL["slate"][0]
        g.append(f'<rect x="{ox+30}" y="{oy+4}" width="50" height="12" rx="3" fill="{c}"/>')
        g.append(f'<rect x="{ox+30}" y="{oy+16}" width="10" height="36" rx="3" fill="{c}"/>')
        g.append(f'<rect x="{ox+70}" y="{oy+16}" width="10" height="36" rx="3" fill="{c}"/>')
        g.append(f'<rect x="{ox+45}" y="{oy+42}" width="20" height="20" rx="3" fill="{PAL["amber"][0]}"/>')
    elif kind == "suction":
        c = PAL["slate"][0]
        g.append(f'<rect x="{ox+15}" y="{oy+6}" width="80" height="12" rx="3" fill="{c}"/>')
        for i in range(4):
            x = ox + 22 + i*20
            g.append(f'<rect x="{x}" y="{oy+18}" width="6" height="22" fill="{c}"/>')
            g.append(f'<path d="M{x-5},{oy+46} L{x+11},{oy+46} L{x+7},{oy+40} L{x-1},{oy+40} Z" fill="{PAL["teal"][0]}"/>')
        g.append(f'<rect x="{ox+10}" y="{oy+50}" width="90" height="16" rx="3" fill="{PAL["amber"][1]}" stroke="{PAL["amber"][0]}"/>')
    elif kind == "skeleton":
        c = PAL["blue"][0]
        J = {"h": (55, 8), "n": (55, 20), "p": (55, 44), "la": (38, 34), "ra": (72, 34), "ll": (44, 66), "rl": (66, 66)}
        for a, b in [("h", "n"), ("n", "p"), ("n", "la"), ("n", "ra"), ("p", "ll"), ("p", "rl")]:
            g.append(f'<line x1="{ox+J[a][0]}" y1="{oy+J[a][1]}" x2="{ox+J[b][0]}" y2="{oy+J[b][1]}" stroke="{c}" stroke-width="3" stroke-linecap="round"/>')
        for x, y in J.values():
            g.append(f'<circle cx="{ox+x}" cy="{oy+y}" r="3.5" fill="#fff" stroke="{c}" stroke-width="2"/>')
    return "\n".join(g)


def render(spec):
    stages = spec["stages"]
    n = len(stages)
    margin, gap = 16, 22
    bw = (W - 2*margin - gap*(n-1)) / n
    bh = spec.get("box_h", 128)
    by = spec.get("row_y", 112 if spec.get("loop") else 128)
    size = spec.get("font", 16)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
             f'<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
             f'<path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/></marker></defs>',
             f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
             f'<rect x="0" y="0" width="{W}" height="6" fill="{PAL[spec.get("accent","blue")][0]}"/>']
    # tag + subtitle
    tsize = min(34, 318 / (0.6 * len(spec["tag"])))
    parts.append(f'<text x="{margin}" y="54" font-family="{FONT}" font-size="{tsize:.1f}" font-weight="700" letter-spacing="-0.5" fill="{INK}">{esc(spec["tag"])}</text>')
    if spec.get("sub"):
        parts.append(f'<text x="{margin}" y="80" font-family="{FONT}" font-size="15.5" fill="{MUTED}">{esc(spec["sub"])}</text>')
    if spec.get("motif"):
        parts.append(motif_svg(spec["motif"], spec["tag"]))
    xs = []
    for i, (label, color) in enumerate(stages):
        x = margin + i*(bw + gap)
        xs.append(x)
        parts.append(box(x, by, bw, bh, label, color, size))
        if i:
            parts.append(arrow(x - gap + 3, by + bh/2, x - 3, by + bh/2))
    if spec.get("loop"):
        a, b, lbl = spec["loop"]
        x1 = xs[a] + bw/2; x2 = xs[b] + bw/2; yb = by + bh; yl = by + bh + 30
        parts.append(f'<path d="M{x1:.1f},{yb:.1f} L{x1:.1f},{yl} L{x2:.1f},{yl} L{x2:.1f},{yb+4:.1f}" fill="none" stroke="{MUTED}" '
                     f'stroke-width="2.2" stroke-dasharray="6 5" marker-end="url(#ah)"/>')
        if lbl:
            parts.append(f'<rect x="{(x1+x2)/2-70:.1f}" y="{yl-11}" width="140" height="22" fill="#fff"/>')
            parts.append(text_block((x1+x2)/2, yl, lbl, 13, MUTED, "400"))
    for (idx, label, color, direction) in spec.get("below", []):
        x = xs[idx]; y = by + bh + 44; h2 = 58
        parts.append(box(x, y, bw, h2, label, color, size - 1))
        if direction == "down":
            parts.append(arrow(x + bw/2, by + bh + 3, x + bw/2, y - 3))
        else:
            parts.append(arrow(x + bw/2, y - 3, x + bw/2, by + bh + 3))
    if spec.get("caption"):
        parts.insert(1, f'<title>{esc(spec["tag"] + ": " + spec["caption"])}</title>')
    parts.append("</svg>")
    return "\n".join(parts)


if __name__ == "__main__":
    from specs import SPECS
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for key, spec in SPECS.items():
        with open(os.path.join(out, key + ".svg"), "w") as f:
            f.write(render(spec))
    print(len(SPECS), "diagrams")

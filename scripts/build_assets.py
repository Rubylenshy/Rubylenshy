#!/usr/bin/env python3
"""Generate the SVG artwork used by the profile README.

Every visual in README.md is produced here from the data below, in a dark and a
light variant, using the same design tokens as usereuben.com (near-black canvas,
hairline borders, one acid-lime signal colour, Inter + JetBrains Mono).

Fonts are subset to the glyphs each file uses and embedded as WOFF2, so the
artwork renders identically for every visitor without loading web fonts.

    python3 -m pip install fonttools brotli
    python3 scripts/build_assets.py

Font lookup: $FONT_DIR, then scripts/fonts/, then common system folders. It
needs Inter (Regular, Medium, SemiBold) and JetBrains Mono (Regular, Medium),
both free under the SIL Open Font License.
"""

from __future__ import annotations

import base64
import io
import os
import re
from html import escape
from pathlib import Path

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"

# --------------------------------------------------------------------------
# Content
# --------------------------------------------------------------------------

NAME_FIRST, NAME_LAST = "Reuben", "Oluwafemi"
ROLE = "Frontend & Plugin Engineer"
TAGLINE = [
    ("Bridging the gap between ", 0), ("engineering logic", 1), (" and ", 0),
    ("creative design", 1), (". I build React interfaces and high-performance "
     "WordPress plugins that solve real productivity problems.", 0),
]
NOW = [
    ("Now · Frontend Developer", "SeamlessTechnologies"),
    ("Based", "Nigeria · Remote-friendly"),
    ("Web", "usereuben.com"),
]

CAPABILITIES = [
    ("Plugin Developer",
     "Custom WordPress plugins built for performance, security, and scalability.",
     ["Custom plugins", "WooCommerce", "SEO & automation"]),
    ("Frontend Engineer",
     "Translating designs into production-ready React interfaces with modern frontend techniques.",
     ["Web app UI", "E-commerce", "AI-driven UI"]),
    ("API Integration",
     "Seamless third-party integrations that create automated workflows and data flows.",
     ["CRM & marketing APIs", "App-to-app automation", "HubSpot"]),
    ("Performance Optimizer",
     "Code audits and refactoring that target 90+ Lighthouse scores and healthy Core Web Vitals.",
     ["Core Web Vitals", "Site speed", "Refactoring"]),
]

EXPERIENCE = [
    ("Apr 2026 — Present", "Frontend Developer", "SeamlessTechnologies", "formerly SeamlessHR",
     "Delivering scalable HR solutions to African businesses."),
    ("Aug 2023 — Apr 2026", "CMS Plugin Developer", "Plugli LLC", None,
     "Refactored custom plugins onto new frameworks, cutting save/load times by 30% and "
     "speeding up runtime processes by 20%. Created SEO-enhancing add-ons that drove revenue growth."),
    ("Aug 2022 — Oct 2022", "Frontend Intern", "SideHustle Nigeria", None,
     "Built React web apps that reduced checkout steps by 40%, and streamlined the team's Git "
     "workflow to cut merge conflicts by 50%."),
    ("Jan 2022 — Jul 2022", "IT Intern", "NISER", None,
     "Appointed Head of Interns, leading a team of 8 to a 20% reduction in project timelines."),
]

# slug, tag, title, subtitle, description, stack, url
PROJECTS = [
    ("linksy", "Plugin", "Linksy", "AI internal linking",
     "Builds the internal links search engines love, using AI keyword extraction and NLP "
     "content analysis, with silo-network visualisation and link analytics.",
     ["WordPress", "Vue", "PHP", "Gemini"], "https://linksyai.com"),
    ("wp-alchemist", "Open source", "wp-alchemist", "WordPress plugin framework",
     "A scaffolder and runtime for modern WordPress plugins: lifecycle, feature modules, "
     "permissioned REST routes, schema-driven settings, migrations and Vite assets.",
     ["PHP 8.1", "Composer", "Vite", "MIT"], "https://github.com/Rubylenshy/wp-alchemist-framework"),
    ("alttexty", "Plugin", "AltTexty", "Image accessibility",
     "Uses AI to analyse a media library and write descriptive alt text in bulk, for WCAG "
     "compliance and better SEO, with credit tracking and gap detection.",
     ["WordPress", "React", "PHP", "AI vision"], "https://plugli.com"),
    ("datey-ai", "Plugin", "Datey AI", "Content freshness manager",
     "An auditing dashboard that finds outdated years and terms across blog posts and "
     "queues them for review, keeping evergreen content current.",
     ["WordPress", "React", "Tailwind", "Gemini"], "https://plugli.com"),
    ("spiritwise", "Full stack", "SpiritWise", "Sermons & daily Bible app",
     "A sermon library and daily Bible engagement app, with a React frontend over a "
     "Python API, JWT auth and cached server state.",
     ["React", "TanStack Query", "Zustand", "Python"], "https://github.com/Rubylenshy/spiritwise"),
    ("agile-system", "Frontend", "Agile System", "Project management tool",
     "A productivity dashboard with a Kanban workflow: track progress, move tasks across "
     "columns, assign teammates and visualise team velocity.",
     ["React", "Redux", "Firebase"], "https://agile-system.vercel.app"),
]

STACK = [
    ("Languages", ["JavaScript", "TypeScript", "PHP", "Python", "HTML", "SCSS"], {"JavaScript", "PHP"}),
    ("Frontend", ["React", "Next.js", "Vue", "Vite", "Tailwind CSS", "GSAP", "Redux", "Zustand"], {"React", "Vue"}),
    ("CMS & data", ["WordPress", "WooCommerce", "MySQL", "Firebase", "REST APIs"], {"WordPress"}),
    ("Tooling", ["Git", "GitHub", "Bitbucket", "Vercel", "Figma", "Notion"], set()),
]

LINKS = [
    ("web", "usereuben.com", True),
    ("linkedin", "LinkedIn", False),
    ("x", "X / Twitter", False),
    ("email", "Email", False),
    ("wordpress", "WordPress.org", False),
]

SECTIONS = [
    ("capabilities", "01", "What I do", "Capabilities",
     "From plugin architecture to pixel-level UI: the full surface of a modern web product."),
    ("experience", "02", "Career path", "Experience",
     "Four roles, one thread: shipping software people rely on every day."),
    ("work", "03", "Selected work", "Projects",
     "Plugins in production, open-source tooling and product builds."),
    ("stack", "04", "Toolkit", "Stack",
     "What I reach for daily. Highlighted: where I spend most of my time."),
]

# --------------------------------------------------------------------------
# Design tokens (mirrors usereuben.com)
# --------------------------------------------------------------------------

THEMES = {
    "dark": dict(
        bg="#0A0A0A", surface="#121212", surface2="#171717",
        border="rgba(255,255,255,0.08)", border_strong="rgba(255,255,255,0.16)",
        text="#FFFFFF", text2="#B4B4B4", muted="#8A8A8A",
        ghost="rgba(255,255,255,0.06)", signal="#D6F84C", signal_ink="#0A0A0A",
        signal_text="#D6F84C", signal_tint="rgba(214,248,76,0.08)",
        grid="rgba(255,255,255,0.05)", aurora="#D6F84C", aurora_op=0.13,
        beam="#D6F84C", beam_op=0.75,
    ),
    "light": dict(
        bg="#F5F5F2", surface="#FFFFFF", surface2="#EDEDEA",
        border="rgba(10,10,10,0.09)", border_strong="rgba(10,10,10,0.20)",
        text="#0A0A0A", text2="#3F3F3F", muted="#5E5E5E",
        ghost="rgba(10,10,10,0.05)", signal="#D6F84C", signal_ink="#0A0A0A",
        signal_text="#5B6B00", signal_tint="rgba(91,107,0,0.07)",
        grid="rgba(10,10,10,0.06)", aurora="#BEE628", aurora_op=0.22,
        beam="#6E8200", beam_op=0.5,
    ),
}

# --------------------------------------------------------------------------
# Fonts: measuring and embedding
# --------------------------------------------------------------------------

FONT_FILES = {
    "sans": ("Inter-Regular", "RO Sans", 400),
    "sans-md": ("Inter-Medium", "RO Sans", 500),
    "sans-sb": ("Inter-SemiBold", "RO Sans", 600),
    "mono": ("JetBrainsMono-Regular", "RO Mono", 400),
    "mono-md": ("JetBrainsMono-Medium", "RO Mono", 500),
}
FALLBACK = {
    "RO Sans": "Inter,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif",
    "RO Mono": "'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace",
}
SEARCH_DIRS = [
    os.environ.get("FONT_DIR"), ROOT / "scripts" / "fonts",
    "/usr/share/fonts", "/usr/local/share/fonts", Path.home() / ".local/share/fonts",
    Path.home() / "Library/Fonts", "/Library/Fonts", "C:/Windows/Fonts",
]


def find_font(stem: str) -> Path:
    for d in SEARCH_DIRS:
        if not d or not Path(d).exists():
            continue
        for ext in ("ttf", "otf"):
            hit = next(Path(d).rglob(f"{stem}.{ext}"), None)
            if hit:
                return hit
    raise SystemExit(f"Font {stem} not found. Put it in scripts/fonts/ or set FONT_DIR.")


class Font:
    def __init__(self, key: str):
        stem, self.family, self.weight = FONT_FILES[key]
        self.path = find_font(stem)
        tt = TTFont(self.path)
        self.cmap = tt.getBestCmap()
        self.hmtx = tt["hmtx"]
        self.upm = tt["head"].unitsPerEm

    def width(self, text: str, size: float, tracking: float = 0.0) -> float:
        units = 0
        for ch in text:
            glyph = self.cmap.get(ord(ch)) or self.cmap.get(ord("?"))
            units += self.hmtx[glyph][0]
        return units / self.upm * size + tracking * size * len(text)


FONTS = {k: Font(k) for k in FONT_FILES}


def embed_fonts(svg_body: str) -> str:
    """Subset each font to the glyphs used in `svg_body` and return @font-face CSS."""
    css = []
    for key, font in FONTS.items():
        chars = set()
        for m in re.finditer(r'<text[^>]*class="(?:[^"]*\s)?f-' + re.escape(key) + r'(?=[\s"])[^"]*"[^>]*>(.*?)</text>',
                             svg_body, re.S):
            chars |= set(re.sub(r"<[^>]+>", "", m.group(1)))
        if not chars:
            continue
        text = "".join(sorted(chars)).replace("&amp;", "&")
        text = re.sub(r"&\w+;", "", text) + "&<>"
        opts = Options()
        opts.flavor = "woff2"
        opts.hinting = False
        opts.desubroutinize = True
        opts.layout_features = ["kern", "calt", "tnum"]
        opts.name_IDs = []
        tt = TTFont(font.path)
        sub = Subsetter(opts)
        sub.populate(text=text)
        sub.subset(tt)
        buf = io.BytesIO()
        tt.flavor = "woff2"
        tt.save(buf)
        data = base64.b64encode(buf.getvalue()).decode()
        css.append(
            f"@font-face{{font-family:'{font.family}';font-weight:{font.weight};"
            f"src:url(data:font/woff2;base64,{data}) format('woff2')}}"
        )
        css.append(
            f".f-{key}{{font-family:'{font.family}',{FALLBACK[font.family]};font-weight:{font.weight}}}"
        )
    return "".join(css)


# --------------------------------------------------------------------------
# SVG helpers
# --------------------------------------------------------------------------


def text(x, y, s, font, size, fill, tracking=0.0, anchor="start", extra=""):
    ls = f' letter-spacing="{tracking * size:.2f}"' if tracking else ""
    an = f' text-anchor="{anchor}"' if anchor != "start" else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="f-{font}" font-size="{size}" fill="{fill}"'
            f'{ls}{an}{extra}>{escape(s, quote=False)}</text>')


def wrap(s, font, size, max_w, tracking=0.0):
    lines, cur = [], ""
    for word in s.split():
        trial = f"{cur} {word}".strip()
        if cur and FONTS[font].width(trial, size, tracking) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + ([cur] if cur else [])


def wrap_rich(segments, font, size, max_w):
    """Wrap [(text, style)] into lines of [(word, style, glued_to_previous)]."""
    words, prev_space = [], True
    for s, style in segments:
        for i, part in enumerate(s.split(" ")):
            if part:
                glued = i == 0 and bool(words) and not prev_space
                words.append((part, style, glued))
        prev_space = s.endswith(" ")
    lines, cur, cur_w = [], [], 0.0
    space = FONTS[font].width(" ", size)
    for word, style, glued in words:
        w = FONTS[font].width(word, size)
        add = w if (glued or not cur) else w + space
        if cur and not glued and cur_w + add > max_w:
            lines.append(cur)
            cur, cur_w, add = [], 0.0, w
        cur.append((word, style, glued and bool(cur)))
        cur_w += add
    if cur:
        lines.append(cur)
    return lines


def pill(x, y, label, t, filled=False, h=30, size=11.5, font="mono-md", tracking=0.06, upper=True):
    label = label.upper() if upper else label
    w = FONTS[font].width(label, size, tracking) + 28
    if filled:
        bg, stroke, fg = t["signal"], t["signal"], t["signal_ink"]
    else:
        bg, stroke, fg = t["surface2"], t["border_strong"], t["text2"]
    out = (f'<rect x="{x + 0.5:.1f}" y="{y + 0.5:.1f}" width="{w - 1:.1f}" height="{h - 1}" rx="{h / 2}" '
           f'fill="{bg}" stroke="{stroke}"/>'
           + text(x + w / 2, y + h / 2 + size * 0.36, label, font, size, fg, tracking, "middle"))
    return out, w


def arrow(cx, cy, r, color, stroke_w=1.8):
    """A '↗' drawn as a path so it never depends on a glyph."""
    a = r * 0.42
    return (f'<path d="M{cx - a:.1f} {cy + a:.1f}L{cx + a:.1f} {cy - a:.1f}M{cx - a * 0.55:.1f} {cy - a:.1f}'
            f'H{cx + a:.1f}V{cy + a * 0.55:.1f}" fill="none" stroke="{color}" stroke-width="{stroke_w}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def backdrop(w, h, t, uid, focus=(0.82, 0.0), beams=True, grid=True, rx=24):
    """Rounded panel with grid, lime aurora and animated beams (the portfolio's hero)."""
    fx, fy = focus
    parts = [
        f'<clipPath id="{uid}c"><rect width="{w}" height="{h}" rx="{rx}"/></clipPath>',
        f'<radialGradient id="{uid}a" gradientUnits="userSpaceOnUse" cx="{fx * w:.0f}" cy="{fy * h:.0f}" '
        f'r="{0.55 * w:.0f}">'
        f'<stop offset="0" stop-color="{t["aurora"]}" stop-opacity="{t["aurora_op"]}"/>'
        f'<stop offset="1" stop-color="{t["aurora"]}" stop-opacity="0"/></radialGradient>',
        f'<radialGradient id="{uid}m" gradientUnits="userSpaceOnUse" cx="{fx * w:.0f}" cy="{fy * h:.0f}" r="{0.8 * w:.0f}"><stop offset="0" stop-color="#fff"/>'
        f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>',
        f'<mask id="{uid}k"><rect width="{w}" height="{h}" fill="url(#{uid}m)"/></mask>',
        f'<pattern id="{uid}g" width="48" height="48" patternUnits="userSpaceOnUse">'
        f'<path d="M48 0H0V48" fill="none" stroke="{t["grid"]}"/></pattern>',
        f'<linearGradient id="{uid}v" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["beam"]}" '
        f'stop-opacity="0"/><stop offset="1" stop-color="{t["beam"]}"/></linearGradient>',
        f'<linearGradient id="{uid}h" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t["beam"]}" '
        f'stop-opacity="0"/><stop offset="1" stop-color="{t["beam"]}"/></linearGradient>',
    ]
    defs = "<defs>" + "".join(parts) + "</defs>"
    body = [f'<g clip-path="url(#{uid}c)"><rect width="{w}" height="{h}" fill="{t["bg"]}"/>']
    if grid:
        body.append(f'<rect width="{w}" height="{h}" fill="url(#{uid}g)" mask="url(#{uid}k)"/>')
    body.append(f'<rect width="{w}" height="{h}" fill="url(#{uid}a)"/>')
    if beams:
        cols = [c for c in range(48 * 2, w, 48)]
        picks = [cols[int(len(cols) * p)] for p in (0.55, 0.72, 0.9)]
        for i, x in enumerate(picks):
            body.append(f'<rect class="bv" style="animation-delay:{i * 2.3:.1f}s" x="{x - 0.75}" y="-140" '
                        f'width="1.5" height="140" fill="url(#{uid}v)" opacity="{t["beam_op"]}"/>')
        rows = [r for r in range(48, h, 48)]
        for i, y in enumerate([rows[1], rows[-2]] if len(rows) > 3 else rows[:1]):
            body.append(f'<rect class="bh" style="animation-delay:{1.2 + i * 3.1:.1f}s" x="-200" y="{y - 0.75}" '
                        f'width="200" height="1.5" fill="url(#{uid}h)" opacity="{t["beam_op"]}"/>')
    body.append("</g>")
    body.append(f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="{rx - 0.5}" fill="none" '
                f'stroke="{t["border"]}"/>')
    css = (f".bv{{animation:bv 7s cubic-bezier(.16,1,.3,1) infinite;opacity:0}}"
           f".bh{{animation:bh 8s cubic-bezier(.16,1,.3,1) infinite;opacity:0}}"
           f"@keyframes bv{{0%{{transform:translateY(0);opacity:0}}8%{{opacity:{t['beam_op']}}}"
           f"55%,100%{{transform:translateY({h + 160}px);opacity:0}}}}"
           f"@keyframes bh{{0%{{transform:translateX(0);opacity:0}}8%{{opacity:{t['beam_op']}}}"
           f"55%,100%{{transform:translateX({w + 240}px);opacity:0}}}}")
    return defs + "".join(body), css


PULSE_CSS = (".pulse{transform-box:fill-box;transform-origin:center;animation:pulse 2s ease-out infinite}"
             "@keyframes pulse{0%{transform:scale(1);opacity:.7}100%{transform:scale(3.2);opacity:0}}")
REDUCED = "@media (prefers-reduced-motion:reduce){*{animation:none!important}.bv,.bh{display:none}}"


def svg(w, h, body, title, css="", t=None):
    style = embed_fonts(body) + css + REDUCED
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{escape(title)}"><title>{escape(title)}</title>'
            f"<style>{style}</style>{body}</svg>\n")


def eyebrow(x, y, num, label, t, size=12.5):
    s = text(x, y, num, "mono-md", size, t["signal_text"], 0.12)
    dx = FONTS["mono-md"].width(num, size, 0.12) + 8
    s += text(x + dx, y, "—", "mono", size, t["muted"])
    dx += FONTS["mono"].width("—", size) + 8
    s += text(x + dx, y, label.upper(), "mono", size, t["muted"], 0.12)
    return s


# --------------------------------------------------------------------------
# Artwork
# --------------------------------------------------------------------------


def header(t):
    W, H, P = 1200, 520, 64
    deco, css = backdrop(W, H, t, "hd", focus=(0.85, 0.05))
    b = [deco]
    b.append(eyebrow(P, 80, "00", ROLE, t, 16))
    # status pill, top right
    label = "AVAILABLE FOR PROJECTS"
    tw = FONTS["mono-md"].width(label, 14.5, 0.1)
    pw = tw + 62
    px = W - P - pw
    b.append(f'<rect x="{px + .5}" y="52.5" width="{pw - 1}" height="41" rx="20.5" fill="{t["signal_tint"]}" '
             f'stroke="{t["border_strong"]}"/>')
    b.append(f'<circle class="pulse" cx="{px + 24}" cy="73" r="4.5" fill="{t["signal_text"]}"/>'
             f'<circle cx="{px + 24}" cy="73" r="4.5" fill="{t["signal_text"]}"/>')
    b.append(text(px + 40, 78.2, label, "mono-md", 14.5, t["text"], 0.1))
    # name
    size, track = 128, -0.045
    b.append(text(P - 6, 232, NAME_FIRST, "sans-sb", size, t["text"], track))
    b.append(text(P - 6, 372, NAME_LAST, "sans-sb", size, t["ghost"], track,
                  extra=f' stroke="{t["border_strong"]}" stroke-width="1.5"'))
    name_w = FONTS["sans-sb"].width(NAME_LAST, size, track) + P
    # tagline, right column, bottom aligned with surname
    cx = max(name_w + 44, 740)
    lines = wrap_rich(TAGLINE, "sans", 21, W - P - cx)
    lh = 31
    y0 = 372 - lh * (len(lines) - 1)
    b.append(f'<rect x="{cx}" y="{y0 - 54}" width="24" height="2" fill="{t["signal_text"]}"/>')
    for i, line in enumerate(lines):
        spans = []
        for j, (word, style, glued) in enumerate(line):
            sep = "" if glued or j == 0 else " "
            col = t["text"] if style else t["muted"]
            cls = "f-sans-md" if style else "f-sans"
            spans.append(f'{sep}<tspan class="{cls}" fill="{col}">{escape(word, quote=False)}</tspan>')
        b.append(f'<text x="{cx}" y="{y0 + i * lh}" class="f-sans f-sans-md" font-size="21" '
                 f'xml:space="preserve">{"".join(spans)}</text>')
    # bottom bar
    b.append(f'<rect x="{P}" y="428" width="{W - 2 * P}" height="1" fill="{t["border"]}"/>')
    col_w = (W - 2 * P) / len(NOW)
    for i, (k, v) in enumerate(NOW):
        x = P + i * col_w
        b.append(text(x, 462, k.upper(), "mono-md", 14, t["signal_text"], 0.14))
        b.append(text(x, 494, v, "sans-md", 20, t["text"], -0.01))
        if i:
            b.append(f'<rect x="{x - 24}" y="446" width="1" height="52" fill="{t["border"]}"/>')
    title = f"{NAME_FIRST} {NAME_LAST}, {ROLE}"
    return W, H, b, title, css + PULSE_CSS


def section_heading(sec, t):
    _, num, eyebrow_label, title, note = sec
    W, H = 1200, 148
    b = [eyebrow(4, 36, num, eyebrow_label, t, 15)]
    b.append(text(0, 116, title, "sans-sb", 68, t["text"], -0.035))
    lines = wrap(note, "sans", 20, 460)
    for i, ln in enumerate(lines):
        b.append(text(W - 2, 114 - (len(lines) - 1 - i) * 28, ln, "sans", 20, t["muted"], anchor="end"))
    b.append(f'<rect x="0" y="{H - 1}" width="{W}" height="1" fill="{t["border"]}"/>')
    return W, H, b, f"{num} — {eyebrow_label}: {title}", ""


def capabilities(t):
    W, gap, pad = 1200, 24, 36
    cw = (W - gap) / 2
    cards, heights = [], []
    for i, (role, desc, pills) in enumerate(CAPABILITIES):
        lines = wrap(desc, "sans", 20, cw - pad * 2 - 20)
        heights.append(160 + len(lines) * 30 + 84)
        cards.append((role, lines, pills))
    ch = max(heights)
    rows = (len(cards) + 1) // 2
    H = rows * ch + (rows - 1) * gap
    b = []
    for i, (role, lines, pills) in enumerate(cards):
        x, y = (i % 2) * (cw + gap), (i // 2) * (ch + gap)
        b.append(f'<rect x="{x + .5}" y="{y + .5}" width="{cw - 1}" height="{ch - 1}" rx="20" fill="{t["surface"]}" '
                 f'stroke="{t["border"]}"/>')
        b.append(text(x + pad, y + pad + 15, f"/{i + 1:02d}", "mono-md", 16, t["signal_text"], 0.08))
        # corner mark
        b.append(f'<rect x="{x + cw - pad - 36.5}" y="{y + pad - 9.5}" width="36" height="36" rx="18" '
                 f'fill="none" stroke="{t["border_strong"]}"/>' + arrow(x + cw - pad - 18.5, y + pad + 8.5, 18, t["text2"], 1.6))
        b.append(text(x + pad, y + 118, role, "sans-sb", 32, t["text"], -0.025))
        for j, ln in enumerate(lines):
            b.append(text(x + pad, y + 160 + j * 30, ln, "sans", 20, t["muted"]))
        px = x + pad
        for p in pills:
            s, w = pill(px, y + ch - pad - 36, p, t, h=36, size=13.5)
            b.append(s)
            px += w + 8
    return W, H, b, "Capabilities: " + "; ".join(f"{r}: {d}" for r, d, _ in CAPABILITIES), ""


def experience(t):
    W, P = 1200, 48
    date_x, rail_x, body_x = P, 310, 350
    body_w = W - body_x - P
    rows, y = [], 48
    for i, (dates, title, company, note, desc) in enumerate(EXPERIENCE):
        lines = wrap(desc, "sans", 20, body_w)
        h = 44 + (28 if note else 0) + 20 + len(lines) * 30
        rows.append((y, dates, title, company, note, lines, h))
        y += h + 56
    H = y - 56 + 48
    deco, css = backdrop(W, H, t, "ex", focus=(0.95, 0.0), beams=False)
    b = [deco]
    first_y, last_y = rows[0][0] + 22, rows[-1][0] + 22
    b.append(f'<rect x="{rail_x - .5}" y="{first_y}" width="1" height="{last_y - first_y}" fill="{t["border_strong"]}"/>')
    for i, (ry, dates, title, company, note, lines, h) in enumerate(rows):
        cy = ry + 22
        if i == 0:
            b.append(f'<circle class="pulse" cx="{rail_x}" cy="{cy}" r="5" fill="{t["signal_text"]}"/>'
                     f'<circle cx="{rail_x}" cy="{cy}" r="5" fill="{t["signal_text"]}"/>')
        else:
            b.append(f'<circle cx="{rail_x}" cy="{cy}" r="5" fill="{t["bg"]}" stroke="{t["signal_text"]}" stroke-width="1.5"/>')
        b.append(text(date_x, cy + 4.5, dates.upper(), "mono-md", 14.5, t["signal_text"] if i == 0 else t["muted"], 0.08))
        tw = FONTS["sans-sb"].width(title, 28, -0.02)
        b.append(text(body_x, ry + 32, title, "sans-sb", 28, t["text"], -0.02))
        b.append(text(body_x + tw + 10, ry + 32, f"· {company}", "sans", 28, t["text2"], -0.02))
        yy = ry + 32
        if note:
            yy += 28
            b.append(text(body_x, yy, note, "mono", 15, t["muted"], 0.04))
        yy += 20
        for j, ln in enumerate(lines):
            b.append(text(body_x, yy + 20 + j * 30, ln, "sans", 20, t["muted"]))
        if i < len(rows) - 1:
            b.append(f'<rect x="{body_x}" y="{ry + h + 28}" width="{body_w}" height="1" fill="{t["border"]}"/>')
    alt = "Experience: " + "; ".join(f"{ti}, {co} ({d})" for d, ti, co, _, _ in EXPERIENCE)
    return W, H, b, alt, css + PULSE_CSS


def project_cards():
    W, pad = 520, 32
    max_lines = max(len(wrap(p[4], "sans", 19, W - pad * 2)) for p in PROJECTS)
    H = 206 + max_lines * 28 + 82
    return W, H, pad


def project(idx, t):
    slug, tag, title, subtitle, desc, stack, url = PROJECTS[idx]
    W, H, pad = project_cards()
    deco, css = backdrop(W, H, t, f"p{idx}", focus=(1.0, 0.0), beams=False)
    b = [deco]
    host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
    if "github.com" in url:
        host = "github.com"
    s, w = pill(pad, pad + 4, tag, t, filled=(tag == "Open source"), h=36, size=13.5)
    b.append(s)
    b.append(text(pad + w + 12, pad + 27, host, "mono", 14, t["muted"], 0.02))
    b.append(f'<circle cx="{W - pad - 22}" cy="{pad + 22}" r="22" fill="{t["signal"]}"/>'
             + arrow(W - pad - 22, pad + 22, 22, t["signal_ink"], 2))
    b.append(text(pad - 2, 140, title, "sans-sb", 46, t["text"], -0.035))
    b.append(text(pad, 174, subtitle.upper(), "mono-md", 14.5, t["signal_text"], 0.08))
    for j, ln in enumerate(wrap(desc, "sans", 19, W - pad * 2)):
        b.append(text(pad, 216 + j * 28, ln, "sans", 19, t["muted"]))
    px = pad
    for item in stack:
        s, w = pill(px, H - pad - 36, item, t, upper=False, font="mono", size=14.5, tracking=0.0, h=36)
        b.append(s)
        px += w + 8
    return W, H, b, f"{title}: {subtitle}. {desc} Built with {', '.join(stack)}.", css


def stack(t):
    W, P = 1200, 48
    label_w = 260
    row_h, pill_h, gap = 30, 42, 10
    rows, y = [], 40
    for label, items, core in STACK:
        placed, px, py = [], P + label_w, y
        for it in items:
            w = FONTS["mono-md"].width(it, 16, 0.02) + 36
            if px + w > W - P:
                px, py = P + label_w, py + pill_h + gap
            placed.append((px, py, it, it in core))
            px += w + gap
        rows.append((y, label, placed))
        y = py + pill_h + 40
    H = y
    deco, css = backdrop(W, H, t, "st", focus=(0.0, 1.0), beams=False)
    b = [deco]
    for i, (ry, label, placed) in enumerate(rows):
        b.append(text(P, ry + 26.5, f"{i + 1:02d}", "mono-md", 15, t["signal_text"], 0.1))
        b.append(text(P + 40, ry + 26.5, label.upper(), "mono", 15, t["muted"], 0.12))
        for px, py, it, is_core in placed:
            s, _ = pill(px, py, it, t, filled=is_core, h=pill_h, size=16, font="mono-md", tracking=0.02, upper=False)
            b.append(s)
        if i < len(rows) - 1:
            b.append(f'<rect x="{P}" y="{placed[-1][1] + pill_h + 20}" width="{W - 2 * P}" height="1" fill="{t["border"]}"/>')
    alt = "Stack: " + "; ".join(f"{label}: {', '.join(items)}" for label, items, _ in STACK)
    return W, H, b, alt, ""


def footer(t):
    W, H, P = 1200, 380, 64
    deco, css = backdrop(W, H, t, "ft", focus=(0.1, 1.0))
    b = [deco, eyebrow(P, 82, "05", "Contact", t, 16)]
    size, track = 100, -0.045
    b.append(text(P - 4, 188, "Let's build", "sans-sb", size, t["text"], track))
    b.append(text(P - 4, 284, "something.", "sans-sb", size, t["ghost"], track,
                  extra=f' stroke="{t["border_strong"]}" stroke-width="1.5"'))
    rx = 760
    b.append(text(rx, 146, "HAVE AN IDEA?", "mono-md", 14.5, t["signal_text"], 0.14))
    for i, ln in enumerate(wrap("Plugins, product UI or a performance rescue. Tell me what you're building.",
                                "sans", 21, W - P - rx)):
        b.append(text(rx, 184 + i * 31, ln, "sans", 21, t["muted"]))
    label = "Start a project"
    tw = FONTS["sans-md"].width(label, 20)
    bw = tw + 90
    b.append(f'<rect x="{rx}" y="240" width="{bw}" height="60" rx="30" fill="{t["signal"]}"/>')
    b.append(text(rx + 30, 277, label, "sans-md", 20, t["signal_ink"]))
    b.append(f'<circle cx="{rx + bw - 30}" cy="270" r="17" fill="{t["signal_ink"]}"/>'
             + arrow(rx + bw - 30, 270, 17, t["signal"], 1.8))
    b.append(f'<rect x="{P}" y="{H - 58}" width="{W - 2 * P}" height="1" fill="{t["border"]}"/>')
    b.append(text(P, H - 20, "REZTOMOLOJU@GMAIL.COM", "mono", 14, t["muted"], 0.1))
    b.append(text(W - P, H - 20, "ENGINEERED WITH PRECISION", "mono", 14, t["muted"], 0.1, "end"))
    return W, H, b, "Let's build something. Start a project with Reuben: reztomoloju@gmail.com", css


ICONS = {
    # 24px line icons, drawn with stroke
    "web": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z"/>',
    "linkedin": '<rect x="3" y="3" width="18" height="18" rx="4"/><path d="M8 10.5V17M8 7.2v.1M12 17v-6.5M12 13.2c0-1.6 1-2.7 2.4-2.7S16.5 11.4 16.5 13v4"/>',
    "x": '<path d="M4 4l16 16M20 4L4 20"/>',
    "email": '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M4 7l8 6 8-6"/>',
    "wordpress": '<circle cx="12" cy="12" r="9"/><path d="M5.5 8.5L9.5 19M9 8.5h4M10.5 8.5l4 10.5M17.8 8c1 2 .9 4.2-.6 7.6L15.5 19"/>',
}


def link_pill(i, t):
    key, label, primary = LINKS[i]
    h, size = 48, 17
    tw = FONTS["sans-md"].width(label, size)
    w = 20 + 20 + 10 + tw + 22 + 20
    fill = t["signal"] if primary else t["surface"]
    stroke = t["signal"] if primary else t["border_strong"]
    fg = t["signal_ink"] if primary else t["text"]
    icon_c = t["signal_ink"] if primary else t["signal_text"]
    b = [f'<rect x=".5" y=".5" width="{w - 1:.1f}" height="{h - 1}" rx="{(h - 1) / 2}" fill="{fill}" stroke="{stroke}"/>',
         f'<g transform="translate(18 14) scale(0.8333)" fill="none" stroke="{icon_c}" stroke-width="2" '
         f'stroke-linecap="round" stroke-linejoin="round">{ICONS[key]}</g>',
         text(48, 29.5, label, "sans-md", size, fg),
         arrow(w - 26, 24, 12, fg if primary else t["muted"], 1.6)]
    return w, h, b, label, ""


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------


def build():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
    jobs = {"header": header, "capabilities": capabilities, "experience": experience,
            "stack": stack, "footer": footer}
    for sec in SECTIONS:
        jobs[f"heading-{sec[0]}"] = lambda t, s=sec: section_heading(s, t)
    for i, p in enumerate(PROJECTS):
        jobs[f"project-{p[0]}"] = lambda t, i=i: project(i, t)
    for i, lk in enumerate(LINKS):
        jobs[f"link-{lk[0]}"] = lambda t, i=i: link_pill(i, t)
    total = 0
    for name, fn in jobs.items():
        for theme, tokens in THEMES.items():
            w, h, body, title, css = fn(tokens)
            data = svg(round(w), round(h), "".join(body), title, css)
            path = OUT / f"{name}-{theme}.svg"
            path.write_text(data, encoding="utf-8")
            total += len(data)
    print(f"wrote {len(jobs) * len(THEMES)} files to {OUT.relative_to(ROOT)}/ ({total / 1024:.0f} KB)")


if __name__ == "__main__":
    build()

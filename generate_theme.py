#!/usr/bin/env python3
"""
generate_theme.py  ·  Identidade visual do README (estilo mission control)

Gera os elementos estáticos que dão ao README inteiro o mesmo visual do painel
de telemetria:

  assets/hero.svg              faixa de abertura (nome, cargos, station ID)
  assets/sec-<nome>.svg        faixas de título de cada seção
  assets/panel-profile.svg     interesses de pesquisa + perfil de operador
  assets/panel-stack.svg       tech stack em pastilhas
  assets/panel-contact.svg     rodapé com contatos
  assets/card-<slug>.svg       cartões clicáveis (estações e espaços)

As cores, fontes e helpers vêm de generate_stats.py, então mudar a paleta lá
muda tudo aqui junto. Só usa a biblioteca padrão do Python (3.9+).

Uso:
  python generate_theme.py          gera/atualiza todos os arquivos em assets/

O conteúdo fica no bloco CONTEÚDO abaixo: é ali que se edita texto, links e
cartões, sem mexer no resto do código.
"""

import os

from generate_stats import C, SANS, Svg, esc, font_css, svg_open

W = 900          # mesma largura do painel de telemetria
PAD = 22
ASSETS = "assets"

# =============================================================================
# CONTEÚDO (edite aqui)
# =============================================================================
NAME = "RAMON MAYOR MARTINS"
DEGREE = "Ph.D."
ROLES = [
    "Associate Professor · Telecommunications Engineering · IFSC São José",
    "Research & Innovation Coordinator · IFSC São José",
    "Postdoctoral research in Educational Games · UFSC, 2025",
]
HERO_CHIPS = ["MACHINE LEARNING", "SATELLITE COMMS", "RF & TELECOM", "CS EDUCATION"]
STATION = [
    ("CALLSIGN", "PU4MAY"),
    ("GROUND STN", "SatNOGS IFSC-389"),
    ("LOCATION", "São José / SC / BR"),
    ("ON AIR", "since 1996"),
]

SECTIONS = [  # (arquivo, índice, título, legenda à direita)
    ("about", "01", "ABOUT", "who is on the other side"),
    ("honors", "02", "HONORS & QUALIFICATION", "badges and certifications"),
    ("profile", "03", "MISSION PROFILE", "research interests · operator profile"),
    ("stations", "04", "LIVE STATIONS", "tools running on GitHub Pages"),
    ("spaces", "05", "TOOLBOXES & SPACES", "labs, models and datasets"),
    ("telemetry", "06", "GITHUB TELEMETRY", "auto-updated daily by GitHub Actions"),
    ("stack", "07", "TECH STACK", "languages, libraries and rigs"),
    ("extras", "08", "EXTRA PANELS", "third party cards"),
    ("city", "09", "GITHUB CITY", "commits rendered as a city"),
    ("topics", "10", "TOPIC PURSUIT", "what is on the bench right now"),
    ("memorial", "11", "MEMORIAL 1988-1998", "the machines that started it"),
    ("statements", "12", "STATEMENTS & CONTACT", "for the record"),
]

INTERESTS = [
    ("ai", "Strategies for Teaching Machine Learning"),
    ("sat", "Radiofrequency and satellite communication systems"),
    ("ai", "Artificial Intelligence and Machine/Deep Learning projects"),
    ("chart", "Computational and Critical Thinking in Computing Education"),
]
OPERATOR = [
    ("tools", "Programmer since 1998", "Basic, Pascal, C, CBuilder, Visual Basic, C++,"
                                       " Shell, Matlab, R, Python, Java"),
    ("radar", "Ham radio operator since 1996", "callsign PU4MAY, licensed by ANATEL"),
    ("sat", "Satellite radio operator", "callsign PU4MAY · ground station IFSC-389"),
]

STACK = ["R", "Python", "C++", "C (ANSI)", "MATLAB", "Basic (MSX)", "LOLCODE", "Fast.ai",
         "GNU Radio", "OpenCV", "TensorFlow.js", "LaTeX", "Bash", "Shell Script",
         "Markdown", "HF Spaces", "HF Transformers", "Colab"]
REVOLTZ = ["JAVA global variables rules", "C GOTO rules", "Python against ident rules"]

# Cartões clicáveis: (arquivo, ícone, título, legenda, texto do link)
STATIONS = [
    ("starlink", "sat", "Starlink Commander", "Constellation tracker with CelesTrak TLE",
     "rmayormartins.github.io/starlink-commander"),
    ("iss", "sat", "ISS Commander", "Live telemetry, space weather and schematics",
     "rmayormartins.github.io/iss-commander"),
    ("satcmd", "globe", "SAT Commander", "3D globe, SGP4 propagation and passes",
     "rmayormartins.github.io/sat-commander"),
    ("funcube", "radar", "FUNcube-1 Commander", "BPSK/CW detection and FEC chain",
     "rmayormartins.github.io/funcube1-commander"),
    ("telenews", "radar", "Telecom News Radar", "RSS aggregation for telecom news",
     "rmayormartins.github.io/telecom-news-radar"),
    ("ainews", "ai", "AI News Radar", "RSS aggregation for AI news",
     "rmayormartins.github.io/ai-news-radar"),
]
SPACES = [
    ("telecomtools", "tools", "Telecom Tools", "Interactive labs for telecom teaching",
     "rmayormartins.github.io/telecom-tools"),
    ("iatools", "ai", "IA Tools", "Machine learning tools and cheat sheets",
     "rmayormartins.github.io/ia-tools"),
    ("hf", "chart", "Hugging Face Spaces", "Deployed AI demos and models",
     "huggingface.co/rmayormartins"),
    ("kaggle", "chart", "Kaggle", "Notebooks and datasets",
     "kaggle.com/rmayormartins"),
]

CONTACT = [("INSTITUTIONAL", "ramon.mayor at ifsc.edu.br"),
           ("PERSONAL", "mayor at linuxmail.org"),
           ("PROFILE", "rmayormartins.github.io")]
FOOTER_NOTE = "73 de PU4MAY · built with Python + GitHub Actions"


# =============================================================================
# Ícones (desenhados, nada de fonte de emoji)
# =============================================================================
def icon(kind, x, y, color=None, s=1.0):
    """Ícone 20x20 desenhado em vetor, ancorado no canto superior esquerdo."""
    col = color or C["accent"]
    g = [f'<g transform="translate({x:.1f},{y:.1f}) scale({s})" fill="none" '
         f'stroke="{col}" stroke-width="1.6" stroke-linecap="round" '
         f'stroke-linejoin="round">']
    if kind == "sat":       # satélite: corpo + dois painéis + antena
        g.append('<rect x="7.5" y="7.5" width="5" height="5" rx="1"/>'
                 '<path d="M2 6.5h4.5v7H2zM13.5 6.5H18v7h-4.5z"/>'
                 '<path d="M10 7.5V4M10 12.5V16"/>')
    elif kind == "radar":   # radar: arcos + ponto
        g.append('<path d="M3 14a7 7 0 0 1 14 0"/><path d="M6.5 14a3.5 3.5 0 0 1 7 0"/>'
                 f'<circle cx="10" cy="14" r="1.2" fill="{col}" stroke="none"/>'
                 '<path d="M10 14 16 6"/>')
    elif kind == "globe":   # globo: círculo + meridianos
        g.append('<circle cx="10" cy="10" r="7"/><path d="M3 10h14"/>'
                 '<path d="M10 3a11 11 0 0 1 0 14a11 11 0 0 1 0-14z"/>')
    elif kind == "ai":      # rede neural simplificada
        g.append('<circle cx="4.5" cy="10" r="1.8"/><circle cx="15.5" cy="5.5" r="1.8"/>'
                 '<circle cx="15.5" cy="14.5" r="1.8"/><path d="M6.2 9.2 13.8 6.2"/>'
                 '<path d="M6.2 10.8 13.8 13.8"/>')
    elif kind == "tools":   # chave + terminal
        g.append('<path d="M4 16 10 10"/><path d="M11.5 8.5a3.5 3.5 0 1 0 4-4l-2 2 '
                 '-1.9-.1-.1-1.9z"/><path d="M3 4h5"/>')
    elif kind == "chart":   # colunas
        g.append('<path d="M3 16.5h14"/><path d="M6 16.5V9M10 16.5V4.5M14 16.5V12"/>')
    elif kind == "mail":
        g.append('<rect x="2.5" y="5" width="15" height="10" rx="1.5"/>'
                 '<path d="m3.5 6.5 6.5 5 6.5-5"/>')
    g.append("</g>")
    return "".join(g)


# =============================================================================
# Estilo e moldura
# =============================================================================
EXTRA_CSS = f"""
.name{{font-family:{SANS};font-size:40px;font-weight:700;letter-spacing:.5px;fill:{C["ink"]};}}
.deg{{font-family:{SANS};font-size:18px;font-weight:500;fill:{C["accent"]};}}
.role{{font-size:13px;fill:{C["ink2"]};}}
.tiny{{font-size:11px;letter-spacing:1px;fill:{C["muted"]};}}
.sec{{font-size:15px;font-weight:700;letter-spacing:3px;fill:{C["ink"]};}}
.secn{{font-size:15px;font-weight:700;letter-spacing:1px;fill:{C["accent"]};}}
.secs{{font-size:11.5px;letter-spacing:.5px;fill:{C["muted"]};}}
.ct{{font-size:14.5px;font-weight:700;letter-spacing:.6px;fill:{C["ink"]};}}
.cs{{font-size:11.5px;fill:{C["ink2"]};}}
.cu{{font-size:11.5px;fill:{C["accent"]};}}
.it{{font-size:12.5px;fill:{C["ink2"]};}}
.ib{{font-size:12.5px;font-weight:700;fill:{C["ink"]};}}
.kt{{font-size:11.5px;font-weight:600;letter-spacing:1px;fill:{C["muted"]};}}
.kv2{{font-size:12.5px;font-weight:700;fill:{C["ink"]};}}
.pill{{font-size:11.5px;letter-spacing:.8px;fill:{C["ink2"]};}}
.pilld{{font-size:11.5px;letter-spacing:.8px;fill:{C["muted"]};}}
.orbiter{{fill:{C["accent"]};}}
@media (prefers-reduced-motion:reduce){{.orbiter{{display:none}}}}
"""


def head(w, h, title, desc, part=None):
    """Abertura do SVG com o estilo comum, a fonte embutida e os defs."""
    return svg_open(w, h, title, desc, EXTRA_CSS, part)


def font_embedded(part):
    return bool(font_css(part))


def card_bg(w, h, rx=12, fill=None):
    f = fill or C["card"]
    return (f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1:.0f}" rx="{rx}" '
            f'fill="{f}" stroke="{C["stroke"]}"/>'
            f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1:.0f}" rx="{rx}" fill="url(#dots)"/>')


def brackets(s, x, y, w, h, t=9, op=".7"):
    d = (f"M{x:.1f},{y + t:.1f}V{y:.1f}H{x + t:.1f}"
         f"M{x + w - t:.1f},{y:.1f}H{x + w:.1f}V{y + t:.1f}"
         f"M{x + w:.1f},{y + h - t:.1f}V{y + h:.1f}H{x + w - t:.1f}"
         f"M{x + t:.1f},{y + h:.1f}H{x:.1f}V{y + h - t:.1f}")
    s.add(f'<path d="{d}" fill="none" stroke="{C["bracket"]}" stroke-width="1.5" '
          f'stroke-opacity="{op}"/>')


def mono_w(text, size, spacing=0.0):
    """Largura aproximada de texto monoespaçado (fontes variam por sistema)."""
    return len(text) * (size * 0.62 + spacing)


def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# =============================================================================
# Peças
# =============================================================================
def hero():
    h = 256
    s = Svg()
    s.add(card_bg(W, h))
    # barra superior
    s.text(PAD, 26, 'PROFILE.README<tspan dx="8">//</tspan><tspan dx="8">'
                    'GITHUB.COM/RMAYORMARTINS</tspan>', "tiny")
    s.text(W - PAD - 16, 26, "STATION ONLINE", "tiny", "end")
    s.add(f'<circle cx="{W - PAD - 5}" cy="22" r="7.5" fill="{C["good"]}" fill-opacity=".18" class="led"/>')
    s.add(f'<circle cx="{W - PAD - 5}" cy="22" r="3.6" fill="{C["good"]}" class="led"/>')
    s.add(f'<path d="M{PAD},40.5H{W - PAD}" stroke="{C["stroke"]}"/>')

    # órbita decorativa cruzando o cartão (o ponto some atrás do painel da direita)
    cx, cy = 430, 150
    s.add(f'<g opacity=".55"><ellipse cx="{cx}" cy="{cy}" rx="430" ry="86" fill="none" '
          f'stroke="{C["stroke"]}" stroke-width="1.2"/>'
          f'<ellipse cx="{cx}" cy="{cy}" rx="300" ry="54" fill="none" stroke="{C["stroke"]}" '
          f'stroke-width="1.2"/></g>')
    s.add(f'<path id="orbit" d="M{cx - 430},{cy}a430,86 0 1,0 860,0a430,86 0 1,0 -860,0" '
          f'fill="none" stroke="none"/>')
    s.add('<circle r="3.4" class="orbiter"><animateMotion dur="18s" repeatCount="indefinite">'
          '<mpath href="#orbit"/></animateMotion></circle>')

    # bloco STATION ID (desenhado antes do nome para ficar por cima da órbita)
    bx, by, bw, bh = W - PAD - 258, 56, 258, 148
    s.add(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="3" fill="{C["panel"]}" '
          f'stroke="{C["stroke"]}"/>')
    brackets(s, bx, by, bw, bh)
    s.text(bx + 16, by + 26, "STATION ID", "pt")
    s.add(f'<path d="M{bx + 16},{by + 38.5}H{bx + bw - 16}" stroke="{C["stroke"]}"/>')
    for i, (k, v) in enumerate(STATION):
        yy = by + 62 + i * 23
        s.text(bx + 16, yy, esc(k), "kt")
        s.text(bx + bw - 16, yy, esc(v), "kv2", "end")

    # nome e cargos (corpo ajustado para nunca invadir o bloco da direita)
    # Source Code Pro é monoespaçada: avanço fixo de 0.6 em por caractere.
    ratio, cap = (0.6, 42) if font_embedded("hero") else (0.78, 38)
    room = bx - PAD - 90                      # 90 reservados para o "Ph.D."
    size = min(cap, room / max(len(NAME) * ratio, 1))
    s.add(f'<text x="{PAD}" y="102" class="name" style="font-size:{size:.1f}px">{esc(NAME)}'
          f'<tspan class="deg" dx="12">{esc(DEGREE)}</tspan></text>')
    s.add(f'<path d="M{PAD},118.5H{PAD + 250}" stroke="url(#fade)" stroke-width="2"/>')
    for i, role in enumerate(ROLES):
        s.text(PAD, 144 + i * 21, esc(role), "role")
    # pastilhas de área (linha inteira, abaixo do bloco de identificação)
    x = PAD
    for chip in HERO_CHIPS:
        cw = mono_w(chip, 11.5, 0.8) + 26
        s.add(f'<rect x="{x:.1f}" y="214" width="{cw:.1f}" height="24" rx="12" fill="none" '
              f'stroke="{C["chip"]}"/>')
        s.text(x + 13, 230, esc(chip), "pill")
        x += cw + 8

    desc = f"{NAME}, {DEGREE} " + ". ".join(ROLES) + ". Callsign PU4MAY."
    return head(W, h, f"{NAME} profile banner", desc, "hero") + "".join(s.parts) + "</svg>\n"


def section(index, title, note):
    h = 46
    s = Svg()
    s.add(f'<rect x=".5" y=".5" width="{W - 1}" height="{h - 1}" rx="6" fill="{C["card"]}" '
          f'stroke="{C["stroke"]}"/>')
    s.add(f'<rect x="1" y="1" width="4" height="{h - 2}" rx="2" fill="{C["accent"]}"/>')
    s.text(PAD, 30, esc(index), "secn")
    s.text(PAD + 34, 30, esc(title), "sec")
    tw = mono_w(title, 15, 3) + PAD + 34
    hatch_x = W - PAD - 26          # bloco de hachuras no canto direito
    s.text(hatch_x - 14, 30, esc(note), "secs", "end")
    nw = mono_w(note, 11.5, 0.5)
    x0, x1 = tw + 18, hatch_x - 26 - nw
    if x1 > x0 + 20:
        s.add(f'<path d="M{x0:.1f},23.5H{x1:.1f}" stroke="{C["stroke"]}"/>')
    s.add('<g opacity=".65">' + "".join(
        f'<path d="M{hatch_x + i * 6},16 l-7,14" stroke="{C["accent"]}" stroke-width="1.4"/>'
        for i in range(3)) + "</g>")
    return (head(W, h, f"{title} section", f"Section {index}: {title}. {note}.", "section")
            + "".join(s.parts) + "</svg>\n")


def wrap_lines(text, width_px, size):
    """Quebra o texto em linhas que cabem na largura dada (fonte monoespaçada)."""
    maxc = max(int(width_px / (size * 0.62)), 8)
    words, lines, cur = text.split(), [], ""
    for word in words:
        cand = f"{cur} {word}".strip()
        if len(cand) > maxc and cur:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def panel_profile():
    gap = 14
    pw = (W - 2 * PAD - gap) / 2
    left = [(k, wrap_lines(t, pw - 70, 12.5)) for k, t in INTERESTS]
    right = [(k, t, wrap_lines(u, pw - 70, 11.5)) for k, t, u in OPERATOR]
    hl = 58 + sum(14 + 17 * len(ls) for _, ls in left)
    hr = 58 + sum(14 + 20 + 16 * len(ls) for _, _, ls in right)
    ph = max(hl, hr) + 16
    h = ph + 32
    s = Svg()
    s.add(card_bg(W, h))

    s.panel(PAD, 16, pw, ph, "RESEARCH INTERESTS", "what I work on")
    y = 70
    for kind, lines in left:
        s.add(icon(kind, PAD + 16, y - 13, C["accent"], 0.95))
        for j, line in enumerate(lines):
            s.text(PAD + 46, y + j * 17, esc(line), "it")
        y += 14 + 17 * len(lines)

    x2 = PAD + pw + gap
    s.panel(x2, 16, pw, ph, "OPERATOR PROFILE", "since the last century")
    y = 70
    for kind, title, lines in right:
        s.add(icon(kind, x2 + 16, y - 13, C["accent"], 0.95))
        s.text(x2 + 46, y, esc(title), "ib")
        for j, line in enumerate(lines):
            s.text(x2 + 46, y + 18 + j * 16, esc(line), "cs")
        y += 14 + 20 + 16 * len(lines)

    desc = ("Research interests: " + "; ".join(t for _, t in INTERESTS)
            + ". Operator profile: " + "; ".join(f"{t} ({u})" for _, t, u in OPERATOR) + ".")
    return head(W, h, "Mission profile", desc, "panel") + "".join(s.parts) + "</svg>\n"


def chips_rows(items, x0, width, size=11.5, spacing=0.8, pad=26, gap=8):
    """Distribui pastilhas em linhas, respeitando a largura disponível."""
    rows, row, used = [], [], 0.0
    for it in items:
        cw = mono_w(it, size, spacing) + pad
        if used + cw > width and row:
            rows.append(row)
            row, used = [], 0.0
        row.append((it, cw))
        used += cw + gap
    if row:
        rows.append(row)
    return rows


def panel_stack():
    inner = W - 2 * PAD - 32
    rows = chips_rows(STACK, PAD + 16, inner)
    rows2 = chips_rows(REVOLTZ, PAD + 16, inner)
    h = 96 + len(rows) * 32 + 54 + len(rows2) * 32
    s = Svg()
    s.add(card_bg(W, h))
    s.panel(PAD, 16, W - 2 * PAD, len(rows) * 32 + 62, "TECH STACK",
            "languages, libraries and rigs")
    y = 74
    for row in rows:
        x = PAD + 16
        for label, cw in row:
            s.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="24" rx="4" '
                  f'fill="{C["panel"]}" stroke="{C["chip"]}"/>')
            s.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="3" height="24" rx="1.5" '
                  f'fill="{C["accent"]}"/>')
            s.text(x + 14, y + 16, esc(label), "pill")
            x += cw + 8
        y += 32
    y2 = 16 + len(rows) * 32 + 62 + 16
    s.panel(PAD, y2, W - 2 * PAD, len(rows2) * 32 + 62, "REVOLTZ STACK",
            "rules were made to be broken")
    y = y2 + 58
    for row in rows2:
        x = PAD + 16
        for label, cw in row:
            s.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="24" rx="4" '
                  f'fill="none" stroke="{C["chip"]}" stroke-dasharray="4 3"/>')
            s.text(x + 14, y + 16, esc(label), "pilld")
            x += cw + 8
        y += 32
    desc = "Tech stack: " + ", ".join(STACK) + ". Revoltz stack: " + ", ".join(REVOLTZ) + "."
    return head(W, h, "Tech stack", desc, "panel") + "".join(s.parts) + "</svg>\n"


def link_card(kind, title, sub, url, w=430, h=92):
    s = Svg()
    s.add(f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="8" fill="{C["panel"]}" '
          f'stroke="{C["stroke"]}"/>')
    s.add(f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="8" fill="url(#dots)"/>')
    s.add(f'<rect x="1" y="1" width="4" height="{h - 2}" rx="2" fill="{C["accent"]}"/>')
    brackets(s, 12, 10, w - 24, h - 20, 8, ".45")
    s.add(icon(kind, 24, 22, C["accent"], 1.05))
    s.text(56, 38, esc(title), "ct")
    s.text(56, 58, esc(sub), "cs")
    s.text(56, 78, esc(url), "cu")
    s.add(f'<path d="M{w - 34},{h / 2 - 6} l7,6 l-7,6" fill="none" stroke="{C["accent"]}" '
          f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>')
    return head(w, h, title, f"{title}: {sub}. Link: {url}", "card") + "".join(s.parts) + "</svg>\n"


def panel_contact():
    h = 128
    s = Svg()
    s.add(card_bg(W, h))
    s.panel(PAD, 16, W - 2 * PAD, h - 32, "CONTACT", "open channels")
    x = PAD + 16
    colw = (W - 2 * PAD - 32) / len(CONTACT)
    for i, (label, value) in enumerate(CONTACT):
        s.add(icon("mail" if i < 2 else "globe", x + i * colw, 58, C["accent"], 0.9))
        s.text(x + i * colw + 28, 66, esc(label), "kt")
        s.text(x + i * colw + 28, 84, esc(value), "kv2")
    s.text(W / 2, h - 22, esc(FOOTER_NOTE), "tiny", "middle")
    desc = "Contact: " + "; ".join(f"{k}: {v}" for k, v in CONTACT)
    return head(W, h, "Contact", desc, "panel") + "".join(s.parts) + "</svg>\n"


def main():
    os.makedirs(ASSETS, exist_ok=True)
    made = [write(f"{ASSETS}/hero.svg", hero())]
    for key, index, title, note in SECTIONS:
        made.append(write(f"{ASSETS}/sec-{key}.svg", section(index, title, note)))
    made.append(write(f"{ASSETS}/panel-profile.svg", panel_profile()))
    made.append(write(f"{ASSETS}/panel-stack.svg", panel_stack()))
    made.append(write(f"{ASSETS}/panel-contact.svg", panel_contact()))
    for slug, kind, title, sub, url in STATIONS + SPACES:
        made.append(write(f"{ASSETS}/card-{slug}.svg", link_card(kind, title, sub, url)))
    print(f"OK: {len(made)} arquivos de estilo gerados em {ASSETS}/")


if __name__ == "__main__":
    main()

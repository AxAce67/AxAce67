"""Renders the profile README banner (assets/banner-dark.png, assets/banner-light.png).

The banner is drawn as HTML and captured with Playwright so the Geist fonts and
the dotted world map look exactly like aki.sh. Backgrounds are transparent so the
image sits on GitHub's own page colour; only the ink colours differ per theme.

    cp ~/portfolio/node_modules/@fontsource-variable/geist/files/geist-latin-wght-normal.woff2 \
       ~/portfolio/node_modules/@fontsource-variable/geist-mono/files/geist-mono-latin-wght-normal.woff2 tools/
    ~/.local/share/stack-diagram/venv/bin/python tools/banner.py
"""
import json
import pathlib

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
OUT = HERE.parent / "assets"
W, H = 1280, 400

# where the servers are (same coordinates as aki.sh/servers)
CITIES = [
    ("Tokyo", 35.68, 139.69, 3, "left-up"),
    ("Osaka", 34.69, 135.5, 1, "left"),
    ("Singapore", 1.35, 103.82, 1, "right"),
    ("Bishkek", 42.87, 74.59, 1, "right"),
    ("Stockholm", 59.33, 18.07, 1, "right"),
    ("Phoenix", 33.45, -112.07, 1, "right"),
]

THEMES = {
    "dark": {"ink": "#f0f6fc", "muted": "#9198a1", "faint": "#3d444d", "dot": "#2a3038", "pin": "#3fb950", "ring": "rgba(63,185,80,.28)"},
    "light": {"ink": "#1f2328", "muted": "#59636e", "faint": "#d1d9e0", "dot": "#d6dbe1", "pin": "#1a7f37", "ring": "rgba(26,127,55,.2)"},
}


def map_svg(t: dict) -> str:
    g = json.loads((HERE / "worlddots.json").read_text())
    cols, rows, lat_top = g["cols"], g["rows"], g["latTop"]
    cell = 5.9
    deg = 360 / cols
    dots = []
    for r, row in enumerate(g["data"]):
        bits = "".join(bin(int(h, 16))[2:].zfill(4) for h in row)
        for c in range(cols):
            if bits[c] == "1":
                dots.append(f'<circle cx="{c * cell + cell / 2:.1f}" cy="{r * cell + cell / 2:.1f}" r="1.3"/>')
    pins = []
    for name, lat, lon, n, side in CITIES:
        x = (lon + 180) / deg * cell
        y = (lat_top - lat) / deg * cell
        nudge = {"Tokyo": 6, "Osaka": -6}.get(name, 0)
        x += nudge
        label = f"{name}" + (f" ×{n}" if n > 1 else "")
        if side == "left-up":  # above the pin (Tokyo sits at the map's right edge)
            tx, ty, anchor = x + 4, y - 15, "middle"
        else:
            anchor, dx = ("start", 12) if side == "right" else ("end", -12)
            tx, ty = x + dx, y + 5
        pins.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="{t["ring"]}"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.6" fill="{t["pin"]}"/>'
            f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="{anchor}" class="lbl">{label}</text>'
        )
    w, h = cols * cell, rows * cell
    return (
        f'<svg viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}">'
        f'<g fill="{t["dot"]}">{"".join(dots)}</g>{"".join(pins)}</svg>'
    )


def page(t: dict) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family: Geist; src: url(geist-latin-wght-normal.woff2); font-weight: 100 900; }}
@font-face {{ font-family: GeistMono; src: url(geist-mono-latin-wght-normal.woff2); font-weight: 100 900; }}
html, body {{ margin: 0; background: transparent; }}
.b {{ position: relative; width: {W}px; height: {H}px; overflow: hidden;
      font-family: Geist, 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', sans-serif; color: {t["ink"]}; }}
.map {{ position: absolute; right: 70px; top: 40px; }}
.map .lbl {{ font: 500 15px GeistMono, monospace; fill: {t["muted"]}; letter-spacing: .02em; }}
.text {{ position: absolute; left: 56px; top: 118px; }}
.name {{ font-size: 108px; font-weight: 700; letter-spacing: -.045em; line-height: 1; margin: 0 0 22px; }}
.tag {{ font-size: 27px; font-weight: 500; letter-spacing: .02em; }}
</style></head><body><div class="b">
  <div class="map">{map_svg(t)}</div>
  <div class="text">
    <div class="name">Aki</div>
    <div class="tag">好きなものを作る。それだけ。</div>
  </div>
</div></body></html>"""


def main() -> None:
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, t in THEMES.items():
            html = HERE / f"_banner-{name}.html"
            html.write_text(page(t))
            pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
            pg.goto(html.as_uri())
            pg.wait_for_timeout(400)
            pg.locator(".b").screenshot(path=str(OUT / f"banner-{name}.png"), omit_background=True)
            html.unlink()
            pg.close()
        b.close()
    for name in THEMES:
        f = OUT / f"banner-{name}.png"
        print(f.name, f.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()

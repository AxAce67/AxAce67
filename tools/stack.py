"""Builds the stack card (assets/stack-{dark,light}.svg): what I use, grouped,
with each brand logo embedded so the image needs nothing from outside.

Logos come from the portfolio repo (public/brands/stack, the same ones aki.sh
shows); a "-dark" file is used on the dark card when it exists.

    python3 tools/stack.py            # PORTFOLIO=~/portfolio by default

Edit GROUPS to change what is listed.
"""
import base64
import os
import pathlib
from xml.sax.saxutils import escape

OUT = pathlib.Path(__file__).resolve().parent.parent / "assets"
LOGOS = pathlib.Path(os.environ.get("PORTFOLIO", pathlib.Path.home() / "portfolio")) / "public/brands/stack"
W = 840
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"

# (label, [(name, logo file slug)])
GROUPS = [
    ("LANGUAGES", [("TypeScript", "typescript"), ("JavaScript", "javascript"), ("Python", "python"), ("Java", "java"), ("Bash", "bash"), ("SQL", "sql")]),
    ("WEB", [("React", "react"), ("Next.js", "nextjs"), ("Tailwind CSS", "tailwindcss"), ("Node.js", "nodejs"), ("Astro", "astro"), ("Three.js", "threejs")]),
    ("DATA", [("Appwrite", "appwrite"), ("Supabase", "supabase"), ("PostgreSQL", "postgresql"), ("MongoDB", "mongodb"), ("Redis", "redis"), ("SQLite", "sqlite")]),
    ("INFRA", [("Linux", "linux"), ("Docker", "docker"), ("Dokploy", "dokploy"), ("Cloudflare", "cloudflare"), ("Tailscale", "tailscale"), ("WireGuard", "wireguard"), ("BIRD", "bird"), ("chrony", "chrony")]),
]

THEMES = {
    "dark": {"ink": "#f0f6fc", "muted": "#9198a1", "line": "#3d444d", "chip": "#161b22", "chipline": "#30363d"},
    "light": {"ink": "#1f2328", "muted": "#59636e", "line": "#d1d9e0", "chip": "#f6f8fa", "chipline": "#d1d9e0"},
}


def logo_uri(slug: str, theme: str) -> str:
    f = LOGOS / f"{slug}-dark.svg" if theme == "dark" and (LOGOS / f"{slug}-dark.svg").exists() else LOGOS / f"{slug}.svg"
    return "data:image/svg+xml;base64," + base64.b64encode(f.read_bytes()).decode()


def text_width(s: str, size: float) -> float:
    # rough width of the system sans at this size (no font metrics available here)
    narrow = sum(1 for c in s if c in "iljtfr.' ")
    wide = sum(1 for c in s if c in "mwMW")
    return (len(s) - narrow - wide) * size * 0.56 + narrow * size * 0.3 + wide * size * 0.82


def build(theme: str) -> str:
    t = THEMES[theme]
    x0, label_w, chip_h, gap, row_gap = 28, 116, 32, 8, 12
    y = 68
    parts = []
    for label, items in GROUPS:
        x = x0 + label_w
        row_y = y
        parts.append(f'<text x="{x0}" y="{row_y + 21}" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{t["muted"]}">{label}</text>')
        for name, slug in items:
            w = 12 + 18 + 8 + text_width(name, 13.5) + 14
            if x + w > W - x0:  # wrap
                x = x0 + label_w
                row_y += chip_h + gap
            parts.append(
                f'<rect x="{x:.1f}" y="{row_y}" width="{w:.1f}" height="{chip_h}" rx="8" fill="{t["chip"]}" stroke="{t["chipline"]}"/>'
                f'<image href="{logo_uri(slug, theme)}" x="{x + 12:.1f}" y="{row_y + 7}" width="18" height="18"/>'
                f'<text x="{x + 38:.1f}" y="{row_y + 21}" font-family="{SANS}" font-size="13.5" fill="{t["ink"]}">{escape(name)}</text>'
            )
            x += w + gap
        y = row_y + chip_h + row_gap
    height = y + 16
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}">'
        f'<rect x=".5" y=".5" width="{W - 1}" height="{height - 1}" rx="12" fill="none" stroke="{t["line"]}"/>'
        f'<text x="28" y="40" font-family="{MONO}" font-size="13" letter-spacing="1.2" fill="{t["muted"]}">STACK</text>'
        + "".join(parts) + "</svg>"
    )


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for theme in THEMES:
        f = OUT / f"stack-{theme}.svg"
        f.write_text(build(theme))
        print(f.name, f.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()

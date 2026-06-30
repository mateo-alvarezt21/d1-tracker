#!/usr/bin/env python3
"""
Genera los assets de marca para producción:
  - favicon.svg          (icono escalable, logo "d1")
  - apple-touch-icon.png (180x180)
  - icon-192.png, icon-512.png (PWA / Android)
  - og-image.png         (1200x630, preview para WhatsApp / redes)

Uso:  python scripts/make_assets.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RED = (227, 6, 19)
DARK = (26, 26, 26)
BG = (250, 248, 247)
GRAY = (110, 110, 110)
YELLOW = (255, 209, 0)
WHITE = (255, 255, 255)

# Fuentes del sistema (Windows). Fallback a la default si no están.
def font(size, bold=True):
    for name in (("arialbd.ttf" if bold else "arial.ttf"), "Arialbd.ttf"):
        p = os.path.join("C:/Windows/Fonts", name)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def d1_badge(size):
    """Devuelve una imagen RGBA con el logo 'd1' (cuadro rojo redondeado)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = int(size * 0.24)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=RED)
    f = font(int(size * 0.56))
    text = "d1"
    bbox = d.textbbox((0, 0), text, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]), text, font=f, fill=WHITE)
    return img


def save_icon(size, name):
    d1_badge(size).save(os.path.join(ROOT, name))
    print("  ->", name)


def make_og():
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # franja superior de marca
    d.rectangle([0, 0, W, 12], fill=RED)
    # badge
    badge = d1_badge(150)
    img.paste(badge, (90, 96), badge)
    # marca textual al lado del badge
    d.text((262, 116), "Mi Canasta", font=font(56), fill=DARK)
    d.text((262, 178), "Tiendas D1", font=font(30), fill=GRAY)
    # titular
    d.text((90, 300), "Planea tu mercado", font=font(82), fill=DARK)
    t = "a tu presupuesto."
    d.text((90, 392), t, font=font(82), fill=RED)
    # subrayado amarillo
    bbox = d.textbbox((90, 392), t, font=font(82))
    d.rectangle([90, bbox[3] + 6, bbox[2], bbox[3] + 16], fill=YELLOW)
    # subtítulo
    d.text((92, 506), "Lista de compras y plan de comidas con productos y precios reales.",
           font=font(30, bold=False), fill=GRAY)
    # disclaimer
    d.text((92, 560), "Proyecto personal · Sin relación con Tiendas D1 · No vendemos nada",
           font=font(22, bold=False), fill=(150, 150, 150))
    img.save(os.path.join(ROOT, "og-image.png"))
    print("  -> og-image.png")


def make_favicon_svg():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 46 46">\n'
        '  <rect width="46" height="46" rx="11" fill="#E30613"/>\n'
        '  <text x="23" y="33" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" '
        'font-weight="900" font-size="26" fill="#ffffff">d1</text>\n'
        '</svg>\n'
    )
    with open(os.path.join(ROOT, "favicon.svg"), "w", encoding="utf-8") as f:
        f.write(svg)
    print("  -> favicon.svg")


if __name__ == "__main__":
    make_favicon_svg()
    save_icon(180, "apple-touch-icon.png")
    save_icon(192, "icon-192.png")
    save_icon(512, "icon-512.png")
    make_og()
    print("Assets generados.")

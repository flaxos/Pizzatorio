#!/usr/bin/env python3
"""Generate placeholder sprite PNGs for Pizzatorio Godot project.

Tiles are 48x48 with a 1px dark border and centered label.
Items are 16x16 with a 1px dark border, no text.

Usage:
    python tools/generate_placeholders.py
"""

import os
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites")

TILES = {
    # filename: (r, g, b, label)
    "conveyor":       (199, 209, 219, "\u2192"),   # arrow right
    "processor":      (153, 199, 230, "P"),
    "oven":           (242, 166, 115, "O"),
    "bot_dock":       (140, 204, 166, "B"),
    "assembly_table": (179, 166, 224, "A"),
    "source":         (115, 191, 115, "\u25b6"),   # right-pointing triangle
    "sink":           (217, 115, 115, "\u25a0"),   # filled square
}

ITEMS = {
    # relative path: (r, g, b)
    "raw/default":       (242, 217, 153),
    "processed/default": (153, 217, 153),
    "baked/default":     (217, 140, 89),
}


def make_tile(name: str, r: int, g: int, b: int, label: str) -> None:
    size = 48
    img = Image.new("RGBA", (size, size), (r, g, b, 255))
    draw = ImageDraw.Draw(img)

    # 1px dark border
    border = (max(r - 60, 0), max(g - 60, 0), max(b - 60, 0), 255)
    draw.rectangle([0, 0, size - 1, size - 1], outline=border)

    # Centered label — try to load a font, fall back to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except (OSError, IOError):
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (size - tw) // 2 - bbox[0]
    ty = (size - th) // 2 - bbox[1]
    draw.text((tx, ty), label, fill=border, font=font)

    path = os.path.join(BASE, "tiles", f"{name}.png")
    img.save(path)
    print(f"  {path}")


def make_item(rel_path: str, r: int, g: int, b: int) -> None:
    size = 16
    img = Image.new("RGBA", (size, size), (r, g, b, 255))
    draw = ImageDraw.Draw(img)

    border = (max(r - 60, 0), max(g - 60, 0), max(b - 60, 0), 255)
    draw.rectangle([0, 0, size - 1, size - 1], outline=border)

    path = os.path.join(BASE, "items", f"{rel_path}.png")
    img.save(path)
    print(f"  {path}")


def main() -> None:
    print("Generating tile sprites (48x48):")
    for name, (r, g, b, label) in TILES.items():
        make_tile(name, r, g, b, label)

    print("Generating item sprites (16x16):")
    for rel, (r, g, b) in ITEMS.items():
        make_item(rel, r, g, b)

    print("Done.")


if __name__ == "__main__":
    main()

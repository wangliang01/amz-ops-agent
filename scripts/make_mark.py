"""Render the flat gate mark used as favicon.

The inline SVG in `app/streamlit_app.py` is the source of truth for the shape;
this script renders the same geometry to `app/assets/mark.png` so Streamlit's
`page_icon` works without an SVG renderer.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "assets" / "mark.png"

SIZE = 1024
PAPER = "#F7F4ED"
INK = "#1F1D1A"
BRASS = "#9C631C"


def unit(value: float) -> int:
    return round(value * SIZE / 24)


def main() -> None:
    img = Image.new("RGBA", (SIZE, SIZE), PAPER)
    draw = ImageDraw.Draw(img)

    # Gate frame: a flat doorframe, the place where a run waits for approval.
    stroke = 2.4
    draw.rectangle([unit(4 - stroke / 2), unit(4 - stroke / 2), unit(4 + stroke / 2), unit(22)], fill=INK)
    draw.rectangle([unit(4 - stroke / 2), unit(4 - stroke / 2), unit(20 + stroke / 2), unit(4 + stroke / 2)], fill=INK)
    draw.rectangle([unit(20 - stroke / 2), unit(4 - stroke / 2), unit(20 + stroke / 2), unit(22)], fill=INK)
    # Brass node: the human decision that opens the gate.
    draw.ellipse(
        [unit(12 - 2.2), unit(13.5 - 2.2), unit(12 + 2.2), unit(13.5 + 2.2)],
        fill=BRASS,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.resize((256, 256), Image.LANCZOS).save(OUT, format="PNG", optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)} (256x256)")


if __name__ == "__main__":
    main()

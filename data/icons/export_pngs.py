#!/usr/bin/env python3
"""Rasterize data/icons/svgs/*.svg to data/icons/pngs/*.png via CairoSVG.

ImageMagick's SVG renderer ignores opacity; CairoSVG preserves it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import cairosvg
except ImportError:
    sys.stderr.write(
        "cairosvg is required for correct SVG opacity.\n"
        "Install with: .venv/bin/pip install cairosvg\n"
    )
    sys.exit(1)

ICONS_DIR = Path(__file__).resolve().parent
SVG_DIR = ICONS_DIR / "svgs"
PNG_DIR = ICONS_DIR / "pngs"


def export_svgs(*, size: int, svg_dir: Path = SVG_DIR, png_dir: Path = PNG_DIR) -> int:
    svgs = sorted(svg_dir.glob("*.svg"))
    if not svgs:
        sys.stderr.write(f"No SVGs found in {svg_dir}\n")
        return 1

    png_dir.mkdir(parents=True, exist_ok=True)
    for svg in svgs:
        out = png_dir / f"{svg.stem}.png"
        cairosvg.svg2png(
            url=str(svg),
            write_to=str(out),
            output_width=size,
            output_height=size,
            background_color="rgba(0,0,0,0)",
        )
        print(f"Wrote {out}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--size",
        type=int,
        default=128,
        help="Output width/height in pixels (default: 128)",
    )
    args = parser.parse_args()
    return export_svgs(size=args.size)


if __name__ == "__main__":
    raise SystemExit(main())

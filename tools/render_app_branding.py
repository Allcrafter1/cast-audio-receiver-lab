#!/usr/bin/env python3
"""Render HA's PNG assets from the existing project SVG, outside runtime.

Developer-only renderer: CairoSVG 2.8.2 in an isolated environment. Generated
files are reviewed and hash-allowlisted by create_public_source_export.py.
"""
from pathlib import Path


def main():
    import cairosvg
    root = Path(__file__).resolve().parents[1]
    svg = root / "src/cast_audio_lab/web/favicon.svg"
    for name, size in (("icon.png", 128), ("logo.png", 256)):
        cairosvg.svg2png(url=str(svg), write_to=str(root / "cast-audio-receiver" / name),
                        output_width=size, output_height=size)


if __name__ == "__main__":
    main()

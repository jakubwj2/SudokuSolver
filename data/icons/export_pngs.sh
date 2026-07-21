#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SVG_DIR="${SCRIPT_DIR}/svgs"
PNG_DIR="${SCRIPT_DIR}/pngs"

mkdir -p "${PNG_DIR}"

shopt -s nullglob
svgs=("${SVG_DIR}"/*.svg)
if ((${#svgs[@]} == 0)); then
  echo "No SVGs found in ${SVG_DIR}" >&2
  exit 1
fi

for svg in "${svgs[@]}"; do
  name="$(basename "${svg}" .svg)"
  out="${PNG_DIR}/${name}.png"
  # PNG32 + TrueColorAlpha keeps SVG opacity / anti-aliased alpha
  # (plain .png output can collapse to Gray/Bilevel and crush it).
  convert \
    -background none \
    -density 384 \
    "${svg}" \
    -resize 128x128 \
    -colorspace sRGB \
    -type TrueColorAlpha \
    "PNG32:${out}"
  echo "Wrote ${out}"
done

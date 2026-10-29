#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

import starfile

p = argparse.ArgumentParser(description="Collapse all optics groups in a particles STAR file into opticsGroup1.")
p.add_argument("input", type=Path, help="input particles STAR file")
p.add_argument("-o", "--output", type=Path, help="output STAR file (default: <input>_1og.star)")
args = p.parse_args()

out = args.output or args.input.with_name(args.input.stem + "_1og.star")
if out.exists():
    sys.exit(f"Error: {out} exists, not overwriting.")

d = starfile.read(args.input)
optics, parts = d["optics"], d["particles"]

print(optics[["rlnOpticsGroup", "rlnImagePixelSize", "rlnImageSize"]].to_string(index=False))
if optics[["rlnImagePixelSize", "rlnImageSize"]].nunique().max() > 1:
    sys.exit("Error: optics groups differ in pixel size or box size; cannot merge.")

optics = optics.iloc[[0]].copy()
optics["rlnOpticsGroup"] = 1
optics["rlnOpticsGroupName"] = "opticsGroup1"

parts["rlnOpticsGroup"] = 1
if "rlnOpticsGroupName" in parts.columns:
    parts["rlnOpticsGroupName"] = "opticsGroup1"

starfile.write({"optics": optics, "particles": parts}, out)
print(f"Wrote {len(parts)} particles to {out}")
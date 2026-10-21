#!/usr/bin/env python3
"""Remap rlnTomoName in a RELION 5 particle STAR file so ArtiaX can parse it,
and convert it back afterwards using the saved mapping table.

Forward (RELION -> ArtiaX), writes <output>.tsv (with information about which new tomo name
corresponds to which original tomogram name) next to the output STAR:
    artiax_tomoname.py to-artiax -i particles.star -o particles_artiax.star

Reverse (ArtiaX export -> RELION names):
    artiax_tomoname.py to-relion -i artiax_export.star -o particles_restored.star \
        -t particles_artiax.tsv
"""
import argparse
import os
import re
import sys

import pandas as pd
import starfile


def refuse_overwrite(*paths):
    existing = [p for p in paths if os.path.exists(p)]
    if existing:
        sys.exit(f"Refusing to overwrite existing file(s): {', '.join(existing)}")


def particle_block(d):
    for k, v in d.items():
        if isinstance(v, pd.DataFrame) and "rlnTomoName" in v.columns:
            return k
    sys.exit("No data block with rlnTomoName found")


def to_artiax(args):
    table = os.path.splitext(args.output)[0] + ".tsv"
    refuse_overwrite(args.output, table)

    d = starfile.read(args.input, always_dict=True)
    df = d[particle_block(d)]

    names = sorted(df["rlnTomoName"].astype(str).unique())
    mapping = pd.DataFrame({
        "tomo_number": range(1, len(names) + 1),
        "artiax_name": [f"{args.prefix}{i}" for i in range(1, len(names) + 1)],
        "original_name": names,
    })
    df["rlnTomoName"] = df["rlnTomoName"].astype(str).map(
        dict(zip(mapping.original_name, mapping.artiax_name)))

    starfile.write(d, args.output)
    mapping.to_csv(table, sep="\t", index=False)
    print(f"Wrote {args.output} and {table} ({len(names)} tomograms)")
    print(f"Open in ArtiaX with prefix '{args.prefix}'")


def to_relion(args):
    refuse_overwrite(args.output)

    mapping = pd.read_csv(args.table, sep="\t")
    num_to_name = dict(zip(mapping.tomo_number.astype(int), mapping.original_name))

    d = starfile.read(args.input, always_dict=True)
    df = d[particle_block(d)]

    # Match on the number, not the string, so zero-padding or "1.0" from ArtiaX still works
    pat = re.compile(rf"^{re.escape(args.prefix)}(\d+(?:\.0+)?)$")

    def restore(n):
        m = pat.match(str(n))
        return num_to_name.get(int(float(m.group(1)))) if m else None

    restored = df["rlnTomoName"].map(restore)
    bad = sorted(df.loc[restored.isna(), "rlnTomoName"].astype(str).unique())
    if bad:
        sys.exit(f"Could not map these rlnTomoName values: {bad[:10]}"
                 f"{' ...' if len(bad) > 10 else ''}")
    df["rlnTomoName"] = restored

    starfile.write(d, args.output)
    print(f"Wrote {args.output}")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="mode", required=True)

    f = sub.add_parser("to-artiax", help="rename tomograms to <prefix><N> and save table")
    f.add_argument("-i", "--input", required=True, help="input RELION STAR file")
    f.add_argument("-o", "--output", required=True, help="output STAR file; table is <output>.tsv")
    f.add_argument("--prefix", default="tomo_", help="name prefix (default: tomo_)")
    f.set_defaults(func=to_artiax)

    r = sub.add_parser("to-relion", help="restore original names using the table")
    r.add_argument("-i", "--input", required=True, help="STAR file exported from ArtiaX")
    r.add_argument("-o", "--output", required=True, help="output STAR file")
    r.add_argument("-t", "--table", required=True, help="mapping .tsv from to-artiax")
    r.add_argument("--prefix", default="tomo_", help="prefix used in to-artiax (default: tomo_)")
    r.set_defaults(func=to_relion)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

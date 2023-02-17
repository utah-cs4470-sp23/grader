#!/usr/bin/env python3
import argparse

def go(file, split, outdir):
    s = file.read()
    parts = s.split(split)
    for i, part in enumerate(parts):
        with open(outdir / f"{i:03}.jpl", "w") as f:
            f.write(part + split)

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Split a file into pieces")
    argparser.add_argument("file", type=argparse.FileType("r"))
    argparser.add_argument("outdir", type=str)
    argparser.add_argument("--on", type=str)
    args = argparser.parse_args()

    out = Path(args.outdir)
    out.mkdir(parents=True, exists_ok=True)

    split = split.replace("\\n", "\n")
    go(args, split, out)
    

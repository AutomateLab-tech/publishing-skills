#!/usr/bin/env python3
"""
audit-corpus.py - corpus-level non-ASCII and prose-banlist sweep.

The per-post scrub inside seo-blog-writer covers the common LLM-tell characters
(em-dash, smart quotes, ellipsis, non-breaking space, zero-width space) and the
default prose banlist. Run this script periodically across your whole corpus to
catch:

  1. Non-ASCII characters that slipped past the per-post scrub.
  2. Prose-level LLM tells ("delve into", "leverage", "robust", etc.) that
     re-appeared because an edit pass re-introduced them.

Default targets every *.html, *.draft.html, and *.md in the given directory tree.

Usage:
    python3 scripts/audit-corpus.py <dir>                # default sweep
    python3 scripts/audit-corpus.py <dir> --no-banlist   # only non-ASCII
    python3 scripts/audit-corpus.py <dir> --extra "term1,term2"

Exit codes:
    0  clean
    1  hits found (CI-friendly; pipe to a notifier or fail the build)
    2  bad invocation
"""

from __future__ import annotations

import argparse
import io
import pathlib
import re
import sys
import unicodedata
from collections import defaultdict

# Force UTF-8 stdout so the script doesn't crash on Windows cp1252 terminals
# when reporting characters like U+2014 or U+FE0F.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="backslashreplace", line_buffering=True)

DEFAULT_GLOBS = ("**/*.html", "**/*.md")

# These match the per-post scrub in seo-blog-writer Step 4b. Keep in sync.
DEFAULT_BANLIST = (
    "delve into", "delving",
    "in today's fast-paced world", "in the ever-evolving",
    "robust", "seamless", "powerful", "cutting-edge",
    "harness the power of",
    "it's worth noting that", "it's important to note",
    "navigate the landscape", "navigating the complexities",
    "unlock the potential of", "unleash",
    "game-changer", "revolutionize",
    "leverage",  # as a verb; review hits manually
)


def iter_files(root: pathlib.Path, globs: tuple[str, ...]) -> list[pathlib.Path]:
    seen: set[pathlib.Path] = set()
    for g in globs:
        for p in root.glob(g):
            if p.is_file():
                seen.add(p.resolve())
    return sorted(seen)


def scan_non_ascii(files: list[pathlib.Path]) -> dict:
    """Return {(char, codepoint, name): [filenames...]}."""
    hits: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for ch in text:
            if ord(ch) < 128:
                continue
            cat = unicodedata.category(ch)
            # Skip pictographic symbols (emoji etc) - those are usually deliberate.
            if cat.startswith("So"):
                continue
            key = (ch, f"U+{ord(ch):04X}", unicodedata.name(ch, "?"))
            if str(path) not in hits[key]:
                hits[key].append(str(path))
    return hits


def scan_banlist(files: list[pathlib.Path], banlist: tuple[str, ...]) -> dict:
    """Return {term: [(filename, line_number, line_text), ...]}."""
    hits: dict[str, list[tuple[str, int, str]]] = defaultdict(list)
    patterns = [(t, re.compile(r"\b" + re.escape(t) + r"\b", re.I)) for t in banlist]
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for n, line in enumerate(lines, 1):
            for term, pat in patterns:
                if pat.search(line):
                    hits[term].append((str(path), n, line.strip()[:160]))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description="Corpus-level non-ASCII + LLM-tell sweep.")
    ap.add_argument("root", type=pathlib.Path, help="Directory to scan")
    ap.add_argument("--no-banlist", action="store_true",
                    help="Skip prose-banlist scan; only inventory non-ASCII")
    ap.add_argument("--no-ascii", action="store_true",
                    help="Skip non-ASCII scan; only run prose banlist")
    ap.add_argument("--extra", default="",
                    help="Comma-separated extra banlist terms to add")
    ap.add_argument("--glob", action="append", default=None,
                    help="Override default file globs (repeatable). "
                         f"Defaults to {DEFAULT_GLOBS!r}.")
    args = ap.parse_args()

    if not args.root.exists():
        print(f"error: {args.root} does not exist", file=sys.stderr)
        return 2

    globs = tuple(args.glob) if args.glob else DEFAULT_GLOBS
    files = iter_files(args.root, globs)
    if not files:
        print(f"no files matched {globs} under {args.root}", file=sys.stderr)
        return 2

    print(f"scanning {len(files)} file(s) under {args.root}")
    total_hits = 0

    if not args.no_ascii:
        non_ascii = scan_non_ascii(files)
        if non_ascii:
            print(f"\n=== non-ASCII characters ({len(non_ascii)} distinct) ===")
            for (ch, cp, name), paths in sorted(non_ascii.items(), key=lambda kv: kv[0][1]):
                print(f"  {cp}  {ch!r}  {name}  ({len(paths)} file(s))")
                for p in paths[:5]:
                    print(f"      - {p}")
                if len(paths) > 5:
                    print(f"      ... and {len(paths) - 5} more")
            total_hits += sum(len(v) for v in non_ascii.values())
        else:
            print("\nnon-ASCII: clean")

    if not args.no_banlist:
        extra = tuple(t.strip() for t in args.extra.split(",") if t.strip())
        banlist = DEFAULT_BANLIST + extra
        bl = scan_banlist(files, banlist)
        if bl:
            print(f"\n=== prose banlist ({len(bl)} terms hit) ===")
            for term, occurrences in sorted(bl.items(), key=lambda kv: -len(kv[1])):
                print(f"  '{term}' ({len(occurrences)} occurrence(s))")
                for path, ln, snippet in occurrences[:3]:
                    print(f"      {path}:{ln}: {snippet}")
                if len(occurrences) > 3:
                    print(f"      ... and {len(occurrences) - 3} more")
            total_hits += sum(len(v) for v in bl.values())
        else:
            print("\nprose banlist: clean")

    print(f"\ntotal hits: {total_hits}")
    return 1 if total_hits else 0


if __name__ == "__main__":
    raise SystemExit(main())

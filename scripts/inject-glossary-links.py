#!/usr/bin/env python3
"""
inject-glossary-links.py - turn the first mention of each glossary term in an
HTML document into an auto-linked, tooltip-ready anchor.

Pure function: HTML string in -> HTML string out. No CMS coupling, no network
calls, no file writes unless you use the CLI form. Works against any HTML the
seo-blog-writer skill produces (or any other source).

Rules:
  - First occurrence per post only (Wikipedia rule).
  - Hard cap MAX_LINKS_PER_POST (default 6), sorted by term priority ascending.
  - Longest aliases tried first (so "Model Context Protocol" beats "MCP").
  - Word-boundary match, case-insensitive, original casing preserved in link text.
  - Skip inside <a>, <code>, <pre>, <h1-h6>, <script>, <style>, tables, blockquotes,
    asides, and the TL;DR opening paragraph.
  - Skip candidates embedded in identifier-like compounds (e.g. "user-agent"
    won't match "agent"; "@scope/ai-seo-mcp" won't match "mcp").

Usage as library:
    from inject_glossary_links import inject, load_terms
    terms = load_terms("path/to/glossary.json")
    new_html = inject(html, terms, base_url="/glossary/")

Usage as CLI:
    python3 inject-glossary-links.py post.html --glossary glossary.json
    python3 inject-glossary-links.py - --glossary glossary.json < post.html
    python3 inject-glossary-links.py post.html --glossary glossary.json \\
        --base-url /glossary/ --max-links 6 > linked.html

Glossary schema: see references/glossary-schema.md. A minimum entry is:
    {"slug": "mcp", "term": "MCP", "aliases": ["mcp", "model context protocol"],
     "short": "<one-line definition for the hover tooltip>"}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

DEFAULT_BASE_URL = "/glossary/"
DEFAULT_MAX_LINKS = 6
SKIP_TAGS = {
    "a", "code", "pre", "h1", "h2", "h3", "h4", "h5", "h6",
    "script", "style", "dfn", "title", "textarea", "option",
    "button", "noscript",
    # No-link zones: table cells, blockquotes/asides
    "table", "thead", "tbody", "tfoot", "tr", "td", "th",
    "caption", "colgroup", "col",
    "blockquote", "aside",
}

# Chars that, if adjacent to a candidate match, mean the match is part of an
# identifier / package name / URL / compound token rather than a standalone
# term. \b treats all of these as boundaries, so the regex alone gives false
# positives like "mcp" inside "@scope/ai-seo-mcp" or "agent" inside
# "user-agent". We post-filter on raw neighbouring chars.
# Note: "-" is bad PRECEDING only - that blocks "user-agent" on "agent" but
# still allows "MCP-compatible" to match on "MCP".
_BAD_PREV = set("/_@:.-")
_BAD_NEXT = set("/_@:")


def _build_patterns(terms: list[dict]) -> list[tuple[re.Pattern, dict]]:
    """One regex per (alias, term). Sorted by alias length desc so longer matches win."""
    rows = []
    for term in terms:
        aliases = term.get("aliases") or [term["term"]]
        for alias in aliases:
            rows.append((alias, term))
    rows.sort(key=lambda r: len(r[0]), reverse=True)
    return [(re.compile(rf"\b{re.escape(a)}\b", re.IGNORECASE), t) for a, t in rows]


class _Rewriter(HTMLParser):
    def __init__(self, terms: list[dict], base_url: str, max_links: int):
        super().__init__(convert_charrefs=False)
        self.terms = sorted(terms, key=lambda t: t.get("priority", 99))
        self.patterns = _build_patterns(self.terms)
        self.base_url = base_url.rstrip("/") + "/"
        self.max_links = max_links
        self.out: list[str] = []
        self.skip_depth = 0
        self.used_slugs: set[str] = set()
        self.link_count = 0
        # TL;DR paragraph tracking. When we open a <p>, we don't yet know if
        # it's a TL;DR. We hold a "pending" flag until we see text data - if
        # that text starts with "TL;DR" (optionally inside <strong>), we flip
        # the paragraph into skip mode until its </p>.
        self._p_depth = 0
        self._p_pending = False
        self._tldr_p_depth = 0

    def _attrs_str(self, attrs):
        parts = []
        for k, v in attrs:
            if v is None:
                parts.append(k)
            else:
                parts.append(f'{k}="{v}"')
        return (" " + " ".join(parts)) if parts else ""

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip_depth += 1
        if tag == "p":
            self._p_depth += 1
            self._p_pending = True
        self.out.append(f"<{tag}{self._attrs_str(attrs)}>")

    def handle_startendtag(self, tag, attrs):
        self.out.append(f"<{tag}{self._attrs_str(attrs)}/>")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self.skip_depth > 0:
            self.skip_depth -= 1
        if tag == "p" and self._p_depth > 0:
            self._p_depth -= 1
            self._p_pending = False
            if self._tldr_p_depth > 0:
                self._tldr_p_depth -= 1
        self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if self._p_pending and data.strip():
            if data.lstrip().upper().startswith("TL;DR"):
                self._tldr_p_depth = self._p_depth
            self._p_pending = False
        if (self.skip_depth > 0
                or self._tldr_p_depth > 0
                or self.link_count >= self.max_links):
            self.out.append(data)
            return
        self.out.append(self._inject(data))

    def handle_entityref(self, name):
        self.out.append(f"&{name};")

    def handle_charref(self, name):
        self.out.append(f"&#{name};")

    def handle_comment(self, data):
        self.out.append(f"<!--{data}-->")

    def handle_decl(self, decl):
        self.out.append(f"<!{decl}>")

    def _inject(self, text: str) -> str:
        if not text.strip():
            return text
        result = text
        protected: list[tuple[int, int]] = []
        for pattern, term in self.patterns:
            if self.link_count >= self.max_links:
                break
            slug = term["slug"]
            if slug in self.used_slugs:
                continue
            m = None
            pos = 0
            while True:
                cand = pattern.search(result, pos)
                if not cand:
                    break
                in_protected = any(s <= cand.start() < e for s, e in protected)
                prev_char = result[cand.start() - 1] if cand.start() > 0 else ""
                next_char = result[cand.end()] if cand.end() < len(result) else ""
                bad_neighbour = prev_char in _BAD_PREV or next_char in _BAD_NEXT
                if not in_protected and not bad_neighbour:
                    m = cand
                    break
                pos = cand.end()
            if not m:
                continue
            matched_text = m.group(0)
            short = (term.get("short") or "").replace('"', "&quot;")
            href = f"{self.base_url}{slug}/"
            replacement = (
                f'<a class="glossary-term" href="{href}" '
                f'target="_blank" rel="noopener" '
                f'data-definition="{short}" title="{short}">{matched_text}</a>'
            )
            result = result[: m.start()] + replacement + result[m.end():]
            shift = len(replacement) - (m.end() - m.start())
            protected = [
                (s + shift if s >= m.end() else s,
                 e + shift if e > m.end() else e)
                for s, e in protected
            ]
            protected.append((m.start(), m.start() + len(replacement)))
            self.used_slugs.add(slug)
            self.link_count += 1
        return result


def inject(html: str, terms: list[dict],
           base_url: str = DEFAULT_BASE_URL,
           max_links: int = DEFAULT_MAX_LINKS) -> str:
    rw = _Rewriter(terms, base_url, max_links)
    rw.feed(html)
    rw.close()
    return "".join(rw.out)


def load_terms(path: Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data["terms"]


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Inject glossary links into post HTML.")
    ap.add_argument("input", type=Path,
                    help="Input HTML file (use - for stdin).")
    ap.add_argument("--glossary", type=Path, required=True,
                    help="Path to glossary.json (see references/glossary-schema.md).")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL,
                    help=f"URL prefix for term pages (default: {DEFAULT_BASE_URL!r}).")
    ap.add_argument("--max-links", type=int, default=DEFAULT_MAX_LINKS,
                    help=f"Cap auto-links per document (default: {DEFAULT_MAX_LINKS}).")
    args = ap.parse_args(list(argv) if argv is not None else None)

    html = sys.stdin.read() if str(args.input) == "-" else args.input.read_text(encoding="utf-8")
    terms = load_terms(args.glossary)
    sys.stdout.write(inject(html, terms, args.base_url, args.max_links))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

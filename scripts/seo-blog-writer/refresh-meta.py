#!/usr/bin/env python3
import json, pathlib, datetime, re, sys
slug, fmt = sys.argv[1], sys.argv[2]
html = pathlib.Path(f"tmp/blog-drafts/{slug}.draft.html").read_text(encoding='utf-8')

# Version detector: requires a leading "v" OR a preceding tool/runtime keyword
# to avoid swallowing IPv4 octets ("127.0.0.1" -> "127.0.0") on networking posts.
# Add your own keywords to the second alternation for project-specific tools.
versions = sorted(set(
    re.findall(r'\bv\d+\.\d+(?:\.\d+)?\b', html) +
    [m.group(2) for m in re.finditer(
        r'\b(version|node|n8n|python|ubuntu|debian|docker|nginx|caddy|postgres|sqlite|claude|cursor|wordpress|ghost)\b[^\n<]{0,15}?(\d+\.\d+(?:\.\d+)?)',
        html, flags=re.I)]
))

record = {
    "slug": slug,
    "published_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "format": fmt,
    "versions_cited": versions,
    "prices_cited": sorted(set(re.findall(r'\$\d+(?:\.\d+)?(?:/\w+)?', html))),
    "years_cited": sorted(set(re.findall(r'\b20\d{2}\b', html))),
    "external_sources": sorted(set(
        m.group(1) for m in re.finditer(r'href="(https?://[^"]+)"', html))),
}
pathlib.Path(f"tmp/blog-drafts/{slug}.refresh.json").write_text(
    json.dumps(record, indent=2), encoding='utf-8')
print(f"refresh snapshot written: {len(versions)} versions, "
      f"{len(record['years_cited'])} years, {len(record['external_sources'])} external sources")

#!/usr/bin/env python3
import json, re, pathlib, sys
slug, headline, fmt, primary_tag, base = sys.argv[1:6]
base = base.rstrip('/')
draft = pathlib.Path(f"tmp/blog-drafts/{slug}.draft.html")
html = draft.read_text(encoding='utf-8')

def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

blocks = []

# 1. BreadcrumbList — always
blocks.append(("BreadcrumbList", {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
        {"@type":"ListItem","position":1,"name":"Home","item":f"{base}/"},
        {"@type":"ListItem","position":2,"name":primary_tag,
         "item":f"{base}/tag/{slugify(primary_tag)}/"},
        {"@type":"ListItem","position":3,"name":headline,
         "item":f"{base}/{slug}/"},
    ],
}))

# 2. FAQPage — extracted from the FAQ block
m = re.search(r'<h2[^>]*>\s*FAQ\s*</h2>(.*)$', html, flags=re.S|re.I)
qa = []
if m:
    pairs = re.findall(r'<h3[^>]*>(.*?)</h3>\s*<p[^>]*>(.*?)</p>', m.group(1), flags=re.S|re.I)
    qa = [{"@type":"Question",
           "name": re.sub(r'<[^>]+>','',q).strip(),
           "acceptedAnswer":{"@type":"Answer","text": re.sub(r'<[^>]+>','',a).strip()}}
          for q, a in pairs]
if qa:
    blocks.append(("FAQPage", {"@context":"https://schema.org","@type":"FAQPage","mainEntity":qa}))
else:
    print("WARN: no FAQ Q/A pairs found — Step 3 requires an FAQ block", file=sys.stderr)

# 3. HowTo — procedural formats with >=3 step-shaped H2s
if fmt in {"how-to-fix", "how-to-connect", "how-to-automate", "use-case", "migration"}:
    h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', html)
    proc = [re.sub(r'<[^>]+>','',h).strip() for h in h2s
            if re.match(r'^\s*(Step|How to|Fix|Configure|Set up|Install|Create|Add|Enable)',
                        re.sub(r'<[^>]+>','',h).strip(), flags=re.I)]
    if len(proc) >= 3:
        blocks.append(("HowTo", {"@context":"https://schema.org","@type":"HowTo",
                                 "name": headline,
                                 "step":[{"@type":"HowToStep","name":s,"position":i+1}
                                         for i,s in enumerate(proc)]}))

ci = "\n".join(f'<script type="application/ld+json">{json.dumps(b, ensure_ascii=False)}</script>'
               for _, b in blocks)
pathlib.Path(f"tmp/blog-drafts/{slug}.schema.html").write_text(ci, encoding='utf-8')
print(f"wrote {len(blocks)} JSON-LD block(s): {[t for t,_ in blocks]}")

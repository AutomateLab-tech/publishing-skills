#!/usr/bin/env python3
import json, pathlib, re, sys
slug = sys.argv[1]
meta = json.loads(pathlib.Path(f"tmp/blog-drafts/{slug}.metadata.json").read_text())
html = pathlib.Path(f"tmp/blog-drafts/{slug}.draft.html").read_text(encoding='utf-8')
schema = pathlib.Path(f"tmp/blog-drafts/{slug}.schema.html").read_text(encoding='utf-8')

assert meta.get("author", {}).get("slug"), "author.slug missing"
assert meta.get("tags"), "tags list empty"

# Feature image: if set, alt text is required and capped at 191
if meta.get("feature_image"):
    alt = meta.get("feature_image_alt") or ""
    assert alt.strip(), "feature_image_alt required when feature_image is set"
    assert len(alt) <= 191, \
        f"feature_image_alt is {len(alt)} chars; cap at 191 (Ghost varchar(191))"

# JSON-LD in schema.html
assert '"@type": "FAQPage"' in schema or '"@type":"FAQPage"' in schema, \
       "FAQPage JSON-LD missing in schema.html - re-run 7b"
assert '"@type": "BreadcrumbList"' in schema or '"@type":"BreadcrumbList"' in schema, \
       "BreadcrumbList JSON-LD missing in schema.html - re-run 7b"

# TL;DR block check
m_first_p = re.search(r'<p\b[^>]*>(.*?)</p>', html, flags=re.S|re.I)
assert m_first_p, "no <p> in body - TL;DR check cannot run"
first_p_inner = m_first_p.group(1)
assert re.search(r'^\s*<strong>\s*TL;DR\s*:?\s*</strong>', first_p_inner, flags=re.I), \
       "first <p> must open with <strong>TL;DR:</strong>"
_t = re.sub(r'<code\b[^>]*>.*?</code>', '', first_p_inner, flags=re.S|re.I)
_t = re.sub(r'<pre\b[^>]*>.*?</pre>', '', _t, flags=re.S|re.I)
tldr_text = re.sub(r'<[^>]+>', '', _t)
tldr_text = re.sub(r'^\s*TL;DR\s*:?\s*', '', tldr_text, flags=re.I).strip()
tldr_words = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", tldr_text))
assert 8 <= tldr_words <= 40, f"TL;DR must be 8-40 words, got {tldr_words}: {tldr_text!r}"
mid_sentence_ends = len(re.findall(r'(?<!\.)[.!?]\s+[A-Z(]', tldr_text))
assert mid_sentence_ends == 0, \
       f"TL;DR must be a single sentence; got: {tldr_text!r}"

# Scheduled posts need a future timestamp
if meta.get("status") == "scheduled":
    import datetime
    pa = meta.get("published_at") or ""
    assert pa, "scheduled posts require published_at"
    ts = datetime.datetime.fromisoformat(pa.replace("Z","+00:00"))
    assert ts > datetime.datetime.now(datetime.timezone.utc), \
           f"scheduled published_at must be in the future, got {pa}"

# H2 question-shape gate (Step 3 voice rule)
# Every H2 ends with '?' OR is in the operational-label allowlist.
H2_QUESTION_ALLOWLIST = {
    "install", "prerequisites", "links", "tl;dr", "tldr",
    "faq", "frequently asked questions", "summary", "references",
    "further reading", "sources", "bottom line",
}
_h2_inner = re.findall(r'<h2\b[^>]*>(.*?)</h2>', html, flags=re.S|re.I)
_h2_text = [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', h)).strip() for h in _h2_inner]
_bad_h2 = [h for h in _h2_text
           if h and not h.endswith('?')
           and h.lower().strip(':?. ') not in H2_QUESTION_ALLOWLIST]
assert not _bad_h2, \
    "H2s must end with '?' or be in the allowlist (Step 3). Bad H2s: " + \
    "; ".join(repr(h) for h in _bad_h2) + \
    ". Rewrite as natural-language questions, e.g. 'How do you ...?', 'Why does ...?', 'When should you ...?'."

# Body word count (same recipe as Step 5)
_no_code = re.sub(r'<pre\b[^>]*>.*?</pre>', ' ', html, flags=re.S|re.I)
_no_table = re.sub(r'<table\b[^>]*>.*?</table>', ' ', _no_code, flags=re.S|re.I)
_no_fig = re.sub(r'<figure\b[^>]*>.*?</figure>', ' ', _no_table, flags=re.S|re.I)
_no_script = re.sub(r'<script\b[^>]*>.*?</script>', ' ', _no_fig, flags=re.S|re.I)
_text_only = re.sub(r'<[^>]+>', ' ', _no_script)
_words = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", _text_only))

# Figure-count gate (Step 6 rule): max(1, words // 500) when body >= 800 words
fig_count = len(re.findall(r'<figure\b', html, flags=re.I))
_required = max(1, _words // 500) if _words >= 800 else 0
assert fig_count >= _required, \
    f"figure shortfall: {fig_count} present, {_required} required for {_words}-word body. Step 6."

# Bullet discipline gate (Step 3 voice rule)
# Reject any <ul>/<ol> with fewer than 3 items or more than 9 items.
# Recap-checklist <ol> after the last H2 question is exempt from the upper bound;
# common practice ships a 5-7 step recap that should not be split.
_lists = re.findall(r'<(ul|ol)\b[^>]*>(.*?)</\1>', html, flags=re.S|re.I)
_bad_lists = []
for kind, body in _lists:
    items = re.findall(r'<li\b', body, flags=re.I)
    n = len(items)
    if n < 3:
        _bad_lists.append(f"<{kind}> with {n} items (min 3; convert to prose)")
    elif n > 9:
        _bad_lists.append(f"<{kind}> with {n} items (max 9; split or use a <table>)")
assert not _bad_lists, \
    "bullet discipline (Step 3): " + "; ".join(_bad_lists)

# Currency check (Step 3 / Step 5 rule)
# Flag any cited year that is > 1 year stale relative to the current year
# unless an explicit 'as of <YYYY>' or 'as of <YYYY-MM>' qualifier sits within 80 chars.
import datetime as _dt
_now_year = _dt.datetime.now(_dt.timezone.utc).year
_text_for_dates = re.sub(r'<(pre|code|script|style)\b[^>]*>.*?</\1>', ' ', html, flags=re.S|re.I)
_stale = []
for m in re.finditer(r'\b(20\d{2})\b', _text_for_dates):
    y = int(m.group(1))
    if y > _now_year:
        continue
    if _now_year - y <= 1:
        continue
    window_start = max(0, m.start() - 80)
    window = _text_for_dates[window_start:m.end() + 80]
    if re.search(r'as of\s+20\d{2}', window, flags=re.I):
        continue
    _stale.append(m.group(1))
assert not _stale, \
    "currency check (Step 5): stale year(s) cited without 'as of <YYYY>' qualifier: " + \
    ", ".join(sorted(set(_stale))) + \
    f". Either update to {_now_year - 1}-{_now_year} or add 'as of <YYYY-MM>' within 80 chars of the year."

# Figure caption gate: every <figure> must contain a non-empty <figcaption>
figures = re.findall(r'<figure\b[^>]*>.*?</figure>', html, flags=re.S|re.I)
uncaptioned = []
for i, fig in enumerate(figures, 1):
    cap = re.search(r'<figcaption\b[^>]*>(.*?)</figcaption>', fig, flags=re.S|re.I)
    if not cap or not re.sub(r'<[^>]+>', '', cap.group(1)).strip():
        src = re.search(r'<img[^>]*src="([^"]+)"', fig)
        uncaptioned.append(f"figure {i} ({src.group(1) if src else 'no src'})")
assert not uncaptioned, \
    "missing/empty <figcaption> on: " + ", ".join(uncaptioned)

# Outbound interlink survival (Step 1f rule): every planned URL appears in the draft
_il_path = pathlib.Path(f"tmp/blog-drafts/{slug}.interlinks.json")
if _il_path.exists():
    _il = json.loads(_il_path.read_text(encoding='utf-8'))
    _missing = [t["url"] for t in _il.get("outbound", [])
                if t.get("url") and f'href="{t["url"]}"' not in html]
    assert not _missing, \
        "outbound interlinks planned in Step 1f but missing from draft: " + \
        ", ".join(_missing) + ". Splice them into Step 3 prose or remove from interlinks.json."

print(f"bundle OK ({_words} words, {fig_count} figures, all captioned, {len(_h2_text)} H2s)")

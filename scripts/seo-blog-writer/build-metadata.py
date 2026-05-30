#!/usr/bin/env python3
"""Build the publish-bundle metadata file (Step 7f).

Reads per-post fields from tmp/blog-drafts/<slug>.params.json and writes
tmp/blog-drafts/<slug>.metadata.json in the shape every Step 8 adapter consumes.

Usage:  build-metadata.py <slug>

params.json shape (see SKILL.md Step 7f):
  {
    "title": "...",                       # headline (Step 7a)
    "tags": ["How To", "n8n"],            # first entry is the primary tag passed to 7b
    "author": {"slug": "...", "name": "..."},
    "meta_title": "...",                  # SEO title under 60 chars
    "meta_description": "...",            # SEO description, 140-160 chars
    "custom_excerpt": "...",              # dek shown on index page
    "feature_image": "" ,                 # URL, relative path, or "" / null
    "feature_image_alt": "...",          # required when feature_image is set, <=191 chars
    "feature_image_caption": "...",
    "publish": false,                     # --publish      -> true
    "publish_at": null                    # --publish-at <ISO-UTC> -> "2026-..Z"
  }
"""
import json, pathlib, sys

if len(sys.argv) < 2:
    sys.exit("usage: build-metadata.py <slug>")
SLUG = sys.argv[1]
DRAFTS = pathlib.Path("tmp/blog-drafts")

params_path = DRAFTS / f"{SLUG}.params.json"
if not params_path.exists():
    sys.exit(f"missing {params_path} — write the per-post fields first (see SKILL.md Step 7f)")
p = json.loads(params_path.read_text(encoding="utf-8"))

for field in ("title", "tags", "author", "meta_title", "meta_description", "custom_excerpt"):
    if not p.get(field):
        sys.exit(f"params.json missing required field: {field!r}")
if not p["author"].get("slug"):
    sys.exit("params.json author.slug is required")

# status semantics map cleanly to every adapter:
#   default              -> "draft"
#   publish=true         -> "published"
#   publish_at <iso>     -> "scheduled" + published_at
status, published_at = "draft", None
if p.get("publish_at"):
    status, published_at = "scheduled", p["publish_at"]
elif p.get("publish"):
    status = "published"

feature = p.get("feature_image") or None
meta = {
    "slug": SLUG,
    "title": p["title"],
    "tags": p["tags"],
    "author": {"slug": p["author"]["slug"], "name": p["author"].get("name", "")},
    "meta_title": p["meta_title"],
    "meta_description": p["meta_description"],
    "custom_excerpt": p["custom_excerpt"],
    "feature_image": feature,
    "feature_image_alt": p.get("feature_image_alt") if feature else None,
    "feature_image_caption": p.get("feature_image_caption") if feature else None,
    "status": status,
    "published_at": published_at,
}

(DRAFTS / f"{SLUG}.metadata.json").write_text(
    json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"metadata written: {SLUG}.metadata.json  status={status}  tags={p['tags']}")

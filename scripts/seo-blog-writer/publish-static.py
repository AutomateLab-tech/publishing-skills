#!/usr/bin/env python3
import json, pathlib, sys

slug, out_dir = sys.argv[1], pathlib.Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)

meta = json.loads(pathlib.Path(f"tmp/blog-drafts/{slug}.metadata.json").read_text())
html = pathlib.Path(f"tmp/blog-drafts/{slug}.draft.html").read_text(encoding='utf-8')
schema = pathlib.Path(f"tmp/blog-drafts/{slug}.schema.html").read_text(encoding='utf-8')

# Hugo / Jekyll-style YAML front matter; tweak the field names for your SSG.
fm_lines = [
    "---",
    f'title: {json.dumps(meta["title"])}',
    f'slug: {meta["slug"]}',
    f'date: {meta.get("published_at") or ""}',
    f'draft: {str(meta["status"] == "draft").lower()}',
    f'author: {meta["author"]["slug"]}',
    f'tags: {json.dumps(meta["tags"])}',
    f'description: {json.dumps(meta["meta_description"])}',
]
if meta.get("feature_image"):
    fm_lines.append(f'feature_image: {meta["feature_image"]}')
    fm_lines.append(f'feature_image_alt: {json.dumps(meta["feature_image_alt"])}')
fm_lines.append("---\n")

post_path = out_dir / f"{slug}.html"
post_path.write_text("\n".join(fm_lines) + html, encoding='utf-8')
(out_dir / f"{slug}.schema.html").write_text(schema, encoding='utf-8')

print(f"wrote {post_path}")
print(f"wrote {out_dir / f'{slug}.schema.html'}  (include in <head> via your SSG template)")

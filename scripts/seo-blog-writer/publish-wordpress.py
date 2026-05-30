#!/usr/bin/env python3
import os, sys, json, pathlib, requests
from requests.auth import HTTPBasicAuth

slug = sys.argv[1]
wp = os.environ['WP_URL'].rstrip('/')
auth = HTTPBasicAuth(os.environ['WP_USER'], os.environ['WP_APP_PASSWORD'])

meta = json.loads(pathlib.Path(f"tmp/blog-drafts/{slug}.metadata.json").read_text())
html = pathlib.Path(f"tmp/blog-drafts/{slug}.draft.html").read_text(encoding='utf-8')
schema = pathlib.Path(f"tmp/blog-drafts/{slug}.schema.html").read_text(encoding='utf-8')

# Resolve tag names -> term ids (create if missing)
def ensure_tag(name):
    g = requests.get(f"{wp}/wp-json/wp/v2/tags",
                     auth=auth, params={"search": name}).json()
    for t in g:
        if t['name'].lower() == name.lower(): return t['id']
    return requests.post(f"{wp}/wp-json/wp/v2/tags",
                         auth=auth, json={"name": name}).json()['id']

# Resolve author slug -> user id
def author_id(slug):
    u = requests.get(f"{wp}/wp-json/wp/v2/users",
                     auth=auth, params={"slug": slug}).json()
    if not u: sys.exit(f"no WP user with slug {slug!r}")
    return u[0]['id']

status_map = {"draft": "draft", "published": "publish", "scheduled": "future"}

# WordPress doesn't have a clean "codeinjection_head" slot. Two options:
#   1. Schema goes into a custom field (`meta`) and a theme hook reads it into <head>.
#   2. Schema is appended to the body (works because WP doesn't strip <script> on save
#      *if the user has unfiltered_html — see notes below).
# Option 2 is the path of least resistance for a vanilla WP; we use that here.
body = html + "\n" + schema

post = {
    "title": meta["title"],
    "slug": meta["slug"],
    "content": body,
    "status": status_map[meta["status"]],
    "tags": [ensure_tag(t) for t in meta["tags"]],
    "author": author_id(meta["author"]["slug"]),
    "excerpt": meta["custom_excerpt"],
    # Yoast / Rank Math read these via their own meta keys; vanilla WP ignores them.
    "meta": {"_yoast_wpseo_title": meta["meta_title"],
             "_yoast_wpseo_metadesc": meta["meta_description"]},
}
if meta.get("published_at"):
    post["date_gmt"] = meta["published_at"].replace("Z", "")

r = requests.post(f"{wp}/wp-json/wp/v2/posts", auth=auth, json=post)
if not r.ok: print(r.status_code, r.text, file=sys.stderr); sys.exit(1)
j = r.json()
print(json.dumps({'id': j['id'], 'url': j['link'], 'status': j['status']}, indent=2))

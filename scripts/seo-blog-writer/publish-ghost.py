#!/usr/bin/env python3
import os, sys, json, pathlib, datetime, requests, jwt

slug = sys.argv[1]
ghost_url = os.environ['GHOST_URL'].rstrip('/')
key = os.environ['GHOST_ADMIN_KEY']
kid, secret = key.split(':', 1)

meta = json.loads(pathlib.Path(f"tmp/blog-drafts/{slug}.metadata.json").read_text())
html = pathlib.Path(f"tmp/blog-drafts/{slug}.draft.html").read_text(encoding='utf-8')
schema = pathlib.Path(f"tmp/blog-drafts/{slug}.schema.html").read_text(encoding='utf-8')

post = {
    "title": meta["title"],
    "slug": meta["slug"],
    "html": html,
    "status": meta["status"],
    "tags": [{"name": t} for t in meta["tags"]],
    "authors": [{"slug": meta["author"]["slug"]}],
    "meta_title": meta["meta_title"],
    "meta_description": meta["meta_description"],
    "custom_excerpt": meta["custom_excerpt"],
    "codeinjection_head": schema,
}
if meta.get("feature_image"):
    post["feature_image"] = meta["feature_image"]
    post["feature_image_alt"] = meta["feature_image_alt"]
    post["feature_image_caption"] = meta["feature_image_caption"]
if meta.get("published_at"):
    post["published_at"] = meta["published_at"]

iat = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
token = jwt.encode(
    {'iat': iat, 'exp': iat + 5 * 60, 'aud': '/admin/'},
    bytes.fromhex(secret),
    algorithm='HS256',
    headers={'kid': kid, 'alg': 'HS256', 'typ': 'JWT'},
)

r = requests.post(
    f"{ghost_url}/ghost/api/admin/posts/?source=html",
    headers={'Authorization': f'Ghost {token}',
             'Content-Type': 'application/json',
             'Accept-Version': 'v5.0'},
    json={"posts": [post]},
)
if not r.ok:
    print(f"FAILED {r.status_code}: {r.text}", file=sys.stderr); sys.exit(1)
created = r.json()['posts'][0]
print(json.dumps({'id': created['id'], 'url': created.get('url'),
                  'slug': created.get('slug'), 'status': created.get('status')}, indent=2))

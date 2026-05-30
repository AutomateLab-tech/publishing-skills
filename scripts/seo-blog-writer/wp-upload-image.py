#!/usr/bin/env python3
import os, sys, pathlib, requests
from requests.auth import HTTPBasicAuth

img = pathlib.Path(sys.argv[1])
r = requests.post(
    f"{os.environ['WP_URL'].rstrip('/')}/wp-json/wp/v2/media",
    auth=HTTPBasicAuth(os.environ['WP_USER'], os.environ['WP_APP_PASSWORD']),
    headers={"Content-Disposition": f'attachment; filename="{img.name}"',
             "Content-Type": "image/png"},
    data=img.read_bytes(),
)
r.raise_for_status()
j = r.json(); print(j['id'], j['source_url'])

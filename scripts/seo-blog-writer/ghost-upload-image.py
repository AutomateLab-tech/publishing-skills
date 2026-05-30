#!/usr/bin/env python3
import os, sys, pathlib, datetime, requests, jwt

GHOST_URL = os.environ['GHOST_URL'].rstrip('/')
key = os.environ['GHOST_ADMIN_KEY']
kid, secret = key.split(':', 1)

iat = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
token = jwt.encode(
    {'iat': iat, 'exp': iat + 5 * 60, 'aud': '/admin/'},
    bytes.fromhex(secret),
    algorithm='HS256',
    headers={'kid': kid, 'alg': 'HS256', 'typ': 'JWT'},
)

img_path = pathlib.Path(sys.argv[1])
with img_path.open('rb') as f:
    r = requests.post(
        f"{GHOST_URL}/ghost/api/admin/images/upload/",
        headers={'Authorization': f'Ghost {token}'},
        files={'file': (img_path.name, f, 'image/png')},
        data={'purpose': 'image'},
    )
r.raise_for_status()
print(r.json()['images'][0]['url'])

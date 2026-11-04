import json
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError

key = sys.stdin.readline(4097).strip()
try:
    request = Request('https://human.marulee.dev/api/admin/status', headers={
        'x-admin-key': key, 'User-Agent': 'AlphaCaptchaDeploymentAudit/1.0', 'Accept': 'application/json'})
    with urlopen(request, timeout=15) as response:
        data = json.load(response)
        print(json.dumps({'http': response.status, 'ready': data.get('ready'),
                          'photoCount': data.get('photoCount'), 'topics': data.get('topics')}))
except HTTPError as error:
    print(json.dumps({'http': error.code}))
    raise SystemExit(1)

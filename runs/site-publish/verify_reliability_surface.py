"""Read-only production health/SSR/asset verification, never room credentials."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import time
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

class Assets(HTMLParser):
    def __init__(self):
        super().__init__(); self.paths = set()
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        candidate = values.get('src') if tag == 'script' else values.get('href') if tag == 'link' else None
        if candidate and candidate.startswith('/') and urlsplit(candidate).path.endswith(('.js', '.css')):
            self.paths.add(candidate)

def fetch(url):
    started = time.monotonic()
    with urlopen(Request(url, headers={'User-Agent': 'AlphaReliabilitySurfaceQA/1.0'}), timeout=20) as response:
        content = response.read(4 * 1024 * 1024 + 1)
        if len(content) > 4 * 1024 * 1024: raise RuntimeError('oversized_asset')
        return content, {'status': response.status, 'seconds': round(time.monotonic()-started, 4),
                         'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest(),
                         'content_type': response.headers.get('Content-Type', '')}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists(): parser.error('Use a new output report')
    hosts = []
    for host in ['https://human.marulee.dev', 'https://bot.marulee.dev']:
        html, page = fetch(host + '/?lane=A')
        health_bytes, health_request = fetch(host + '/api/health')
        health = json.loads(health_bytes)
        assets = Assets(); assets.feed(html.decode('utf-8'))
        assert 0 < len(assets.paths) <= 32
        with ThreadPoolExecutor(max_workers=3) as pool:
            rows = list(pool.map(lambda path: {'path': path, **fetch(urljoin(host, path))[1]}, sorted(assets.paths)))
        checks = {'html_ok': page['status'] == 200, 'all_initial_assets_ok': all(v['status'] == 200 for v in rows),
                  'no_doubled_chunk_path': all('/_next/static/chunks/_next/' not in v['path'] for v in rows),
                  'schema_and_protocol_ready': health.get('ok') is True and health.get('protocolVersion') == 3
                    and health.get('imageReadinessBarrier') is True and health.get('minimumTileIntervalMs') == 250}
        hosts.append({'host': host, 'page': page, 'health': health, 'health_request': health_request,
                      'initial_assets': rows, 'checks': checks})
    result = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'hosts': hosts,
              'passed': all(all(v['checks'].values()) for v in hosts),
              'limits': 'SSR, initial asset bytes and health API only; browser rendering and actual ML are separate checks.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['passed'] else 1

if __name__ == '__main__': raise SystemExit(main())

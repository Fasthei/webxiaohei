"""Notify participating search engines after a successful production deployment."""
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
# Official IndexNow participant; accepted URLs are shared across the network.
ENDPOINT = 'https://yandex.com/indexnow'
ERROR_BODY_LIMIT = 1024


def response_detail(response):
    """Keep server diagnostics useful without copying an unbounded response into CI."""
    body = response.read(ERROR_BODY_LIMIT + 1)
    detail = ' '.join(body[:ERROR_BODY_LIMIT].decode('utf-8', errors='replace').split())
    if len(body) > ERROR_BODY_LIMIT:
        detail += ' [truncated]'
    return detail


def submit(root=ROOT):
    """Print each host's outcome and return a process exit code."""
    config = json.loads((root / 'config/marketing.json').read_text())
    urls = []
    for sitemap in [root / 'site/sitemap.xml', root / 'site/zh/sitemap.xml']:
        if sitemap.exists():
            urls.extend(node.text for node in ET.parse(sitemap).iter(
                '{http://www.sitemaps.org/schemas/sitemap/0.9}loc') if node.text)

    results = []
    failed = False
    for host, key in config['indexNow'].items():
        selected = sorted(set(url for url in urls if urlparse(url).netloc == host))
        if not selected:
            results.append(f'{host}: SKIPPED — no sitemap URLs for this host')
            continue
        key_url = f'https://{host}/{key}.txt'
        try:
            with urllib.request.urlopen(key_url, timeout=12) as response:
                final_url = urlparse(response.geturl())
                if final_url.scheme != 'https' or final_url.netloc != host:
                    raise ValueError('Published ownership file redirected away from its HTTPS host')
                body = response.read(257)
                if response.status != 200 or len(body) > 256 or body.decode().strip() != key:
                    raise ValueError('Published ownership file does not match')
            payload = json.dumps({
                'host': host,
                'key': key,
                'keyLocation': key_url,
                'urlList': selected,
            }).encode()
            request = urllib.request.Request(
                ENDPOINT,
                data=payload,
                headers={'Content-Type': 'application/json; charset=utf-8'},
                method='POST',
            )
            with urllib.request.urlopen(request, timeout=18) as response:
                status = response.status
                if status not in (200, 202):
                    detail = response_detail(response)
                    raise ValueError(f'Unexpected IndexNow HTTP {status}: {detail}')
            outcome = ('received; ownership validation pending' if status == 202
                       else 'received (not a guarantee of indexing)')
            results.append(f'{host}: {len(selected)} URLs; HTTP {status} — {outcome}')
        except urllib.error.HTTPError as exc:
            failed = True
            try:
                detail = response_detail(exc)
            except (OSError, ValueError) as read_error:
                detail = f'Could not read error response: {read_error}'
            finally:
                exc.close()
            results.append(f'{host}: NOT submitted — HTTP {exc.code} {exc.reason}: {detail}')
        except Exception as exc:
            failed = True
            results.append(f'{host}: NOT submitted — {type(exc).__name__}: {exc}')

    for line in results:
        print(line)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
            summary.write('## IndexNow submission\n\n'
                          + '\n'.join('- ' + line for line in results) + '\n')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(submit())

"""Notify IndexNow after deployment; a successful receipt does not mean indexing."""
import json
import os
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
# A supported IndexNow participant; accepted URLs are shared across the network.
ENDPOINT = 'https://yandex.com/indexnow'
MAX_ATTEMPTS = 3
BODY_LIMIT = 1024


class SubmissionError(Exception):
    """An ownership check or submission could not be completed."""


def response_detail(body):
    """Keep remote diagnostics bounded and on one line in logs and summaries."""
    text = body[:BODY_LIMIT].decode('utf-8', errors='replace')
    text = ''.join(c if c.isprintable() else ' ' for c in text)
    return ' '.join(text.split()) + (' [truncated]' if len(body) > BODY_LIMIT else '')


def request_with_retry(request, stage, timeout):
    """Retry network/5xx errors only, with at most three attempts and 1s/2s waits."""
    for attempt in range(MAX_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = response.status
                retry_after = response.headers.get('Retry-After') if status == 429 else None
                body = response.read(BODY_LIMIT + 1)
        except urllib.error.HTTPError as exc:
            status = exc.code
            retry_after = exc.headers.get('Retry-After') if exc.headers else None
            try:
                body = exc.read(BODY_LIMIT + 1)
            except OSError:
                body = b'(response body unavailable)'
            finally:
                exc.close()
        except (urllib.error.URLError, OSError) as exc:
            if attempt + 1 < MAX_ATTEMPTS:
                time.sleep(2 ** attempt)
                continue
            raise SubmissionError(
                f'{stage}: network error after {MAX_ATTEMPTS} attempts '
                f'({type(exc).__name__}); check connectivity and retry'
            ) from exc
        if status == 429:
            detail = response_detail(body) or '(empty response body)'
            hint = ('; Retry-After: ' + response_detail(retry_after.encode())
                    if retry_after else '')
            raise SubmissionError(f'{stage}: HTTP 429: rate limited; retry later{hint}; {detail}')
        if 500 <= status <= 599:
            if attempt + 1 < MAX_ATTEMPTS:
                time.sleep(2 ** attempt)
                continue
        return status, body


def require_status(status, body, allowed, stage):
    if status not in allowed:
        detail = response_detail(body) or '(empty response body)'
        hint = ('; verify the public ownership file and IndexNow host/keyLocation; '
                '403 is not retried' if status == 403 else '')
        raise SubmissionError(f'{stage}: HTTP {status}: {detail}{hint}')


def submit():
    """Report every configured host and return a process exit code."""
    results = []
    failed = False
    try:
        config = json.loads((ROOT / 'config/marketing.json').read_text())
        urls = []
        for sitemap in [ROOT / 'site/sitemap.xml', ROOT / 'site/zh/sitemap.xml']:
            if sitemap.exists():
                urls.extend(n.text for n in ET.parse(sitemap).iter(
                    '{http://www.sitemaps.org/schemas/sitemap/0.9}loc') if n.text)
        if not config['indexNow']:
            raise ValueError('No IndexNow hosts configured')
        for host, key in config['indexNow'].items():
            try:
                key_url = f'https://{host}/{key}.txt'
                selected = sorted(set(u for u in urls if urlparse(u).netloc == host))
                if not selected:
                    raise SubmissionError('sitemap selection: no URLs for configured host')
                status, body = request_with_retry(key_url, 'ownership file GET', 12)
                require_status(status, body, {200}, 'ownership file GET')
                if body.decode('utf-8', errors='replace').strip() != key:
                    raise SubmissionError('ownership file GET: HTTP 200 but file content '
                                          'does not match the configured public key')
                payload = json.dumps({'host': host, 'key': key, 'keyLocation': key_url,
                                      'urlList': selected}).encode()
                request = urllib.request.Request(
                    ENDPOINT, data=payload,
                    headers={'Content-Type': 'application/json; charset=utf-8'}, method='POST')
                status, body = request_with_retry(request, 'IndexNow POST', 18)
                require_status(status, body, {200, 202}, 'IndexNow POST')
                outcome = ('submission confirmed (not a guarantee of indexing)' if status == 200
                           else 'accepted; ownership validation pending; indexing not confirmed')
                results.append(f'{host}: {len(selected)} URLs; HTTP {status} — {outcome}')
            except SubmissionError as exc:
                failed = True
                results.append(f'{host}: NOT confirmed — {exc}')
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as exc:
        failed = True
        results.append(f'IndexNow configuration/sitemap error: {type(exc).__name__}: {exc}')
    for line in results:
        print(line)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
            summary.write('## IndexNow submission\n\n' + '\n'.join('- ' + x for x in results) + '\n')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(submit())

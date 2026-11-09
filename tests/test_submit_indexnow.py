"""IndexNow tests use mocked HTTP only, never external submissions."""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import submit_indexnow as indexnow


class Response(io.BytesIO):
    def __init__(self, status=200, body=b''):
        super().__init__(body)
        self.status = status
        self.headers = {}


class IndexNowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'config').mkdir()
        (self.root / 'site/zh').mkdir(parents=True)
        (self.root / 'config/marketing.json').write_text(json.dumps(
            {'indexNow': {'example.com': 'public-key'}}))
        xml = ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
               '<url><loc>https://example.com/</loc></url>'
               '<url><loc>https://other.example/</loc></url></urlset>')
        (self.root / 'site/sitemap.xml').write_text(xml)
        (self.root / 'site/zh/sitemap.xml').write_text(xml)
        self.output = io.StringIO()
        self.enterContext(contextlib.redirect_stdout(self.output))
        self.enterContext(patch.object(indexnow, 'ROOT', self.root))
        self.http = self.enterContext(patch.object(indexnow.urllib.request, 'urlopen'))
        self.sleep = self.enterContext(patch.object(indexnow.time, 'sleep'))
        self.summary = self.root / 'summary.md'
        self.enterContext(patch.dict(indexnow.os.environ, {'GITHUB_STEP_SUMMARY': str(self.summary)}))

    def error(self, code, body=b'error'):
        return urllib.error.HTTPError(indexnow.ENDPOINT, code, 'failed', {}, io.BytesIO(body))

    def test_confirmed_submission_filters_deduplicates_and_summarizes(self):
        self.http.side_effect = [Response(body=b'public-key\n'), Response()]
        self.assertEqual(indexnow.submit(), 0)
        request = self.http.call_args_list[1].args[0]
        self.assertEqual(request.full_url, indexnow.ENDPOINT)
        self.assertEqual(request.get_method(), 'POST')
        self.assertEqual(json.loads(request.data), {
            'host': 'example.com', 'key': 'public-key',
            'keyLocation': 'https://example.com/public-key.txt',
            'urlList': ['https://example.com/']})
        self.assertIn('submission confirmed', self.output.getvalue())
        self.assertIn('not a guarantee of indexing', self.summary.read_text())

    def test_202_is_pending_not_confirmed(self):
        self.http.side_effect = [Response(body=b'public-key'), Response(202)]
        self.assertEqual(indexnow.submit(), 0)
        self.assertIn('ownership validation pending', self.output.getvalue())
        self.assertIn('indexing not confirmed', self.output.getvalue())
        self.assertNotIn('submission confirmed', self.output.getvalue())

    def test_ownership_403_does_not_post_or_retry(self):
        self.http.side_effect = self.error(403, b'forbidden')
        self.assertEqual(indexnow.submit(), 1)
        self.assertEqual(self.http.call_count, 1)
        self.sleep.assert_not_called()
        self.assertIn('ownership file GET: HTTP 403: forbidden', self.output.getvalue())

    def test_post_403_reports_diagnostic_without_retry(self):
        self.http.side_effect = [Response(body=b'public-key'), self.error(
            403, b'{"code":"UserForbiddedToAccessSite","message":"verify ownership"}')]
        self.assertEqual(indexnow.submit(), 1)
        self.assertEqual(self.http.call_count, 2)
        self.sleep.assert_not_called()
        self.assertIn('IndexNow POST: HTTP 403', self.summary.read_text())
        self.assertIn('UserForbiddedToAccessSite', self.summary.read_text())

    def test_mismatched_ownership_does_not_post(self):
        self.http.return_value = Response(body=b'<html>fallback</html>')
        self.assertEqual(indexnow.submit(), 1)
        self.assertEqual(self.http.call_count, 1)
        self.assertIn('does not match', self.output.getvalue())

    def test_unexpected_success_status_is_not_confirmed(self):
        self.http.side_effect = [Response(body=b'public-key'), Response(204)]
        self.assertEqual(indexnow.submit(), 1)
        self.assertIn('IndexNow POST: HTTP 204', self.output.getvalue())

    def test_transient_post_errors_retry_with_bound(self):
        self.http.side_effect = [Response(body=b'public-key'), self.error(502),
                                 self.error(503), Response()]
        self.assertEqual(indexnow.submit(), 0)
        self.assertEqual(self.http.call_count, 4)
        self.assertEqual([c.args[0] for c in self.sleep.call_args_list], [1, 2])

    def test_rate_limit_reports_retry_after_without_retry(self):
        error = self.error(429, b'too many requests')
        error.headers['Retry-After'] = '120'
        self.http.side_effect = [Response(body=b'public-key'), error]
        self.assertEqual(indexnow.submit(), 1)
        self.assertEqual(self.http.call_count, 2)
        self.sleep.assert_not_called()
        self.assertIn('HTTP 429: rate limited; retry later; Retry-After: 120',
                      self.output.getvalue())

    def test_rate_limit_without_retry_after_does_not_retry(self):
        self.http.side_effect = self.error(429)
        self.assertEqual(indexnow.submit(), 1)
        self.assertEqual(self.http.call_count, 1)
        self.sleep.assert_not_called()
        self.assertIn('ownership file GET: HTTP 429: rate limited; retry later',
                      self.output.getvalue())

    def test_exhausted_transient_errors_fail(self):
        self.http.side_effect = [Response(body=b'public-key')] + [self.error(503) for _ in range(3)]
        self.assertEqual(indexnow.submit(), 1)
        self.assertEqual(self.http.call_count, 4)
        self.assertIn('IndexNow POST: HTTP 503', self.output.getvalue())

    def test_network_error_exhaustion_reports_stage(self):
        self.http.side_effect = urllib.error.URLError('network down')
        self.assertEqual(indexnow.submit(), 1)
        self.assertEqual(self.http.call_count, 3)
        self.assertIn('ownership file GET: network error after 3 attempts', self.output.getvalue())

    def test_network_retry_can_recover(self):
        self.http.side_effect = [TimeoutError(), Response(body=b'public-key'), Response()]
        self.assertEqual(indexnow.submit(), 0)
        self.assertEqual(self.http.call_count, 3)

    def test_response_body_is_bounded_and_single_line(self):
        self.http.side_effect = [Response(body=b'public-key'), self.error(400, b'bad\n' + b'x' * 5000)]
        self.assertEqual(indexnow.submit(), 1)
        self.assertIn('bad xxx', self.output.getvalue())
        self.assertIn('[truncated]', self.output.getvalue())
        self.assertLess(len(self.output.getvalue()), 1200)
        self.assertEqual(len(self.output.getvalue().splitlines()), 1)

    def test_missing_sitemap_urls_fail_without_network(self):
        (self.root / 'site/sitemap.xml').unlink()
        (self.root / 'site/zh/sitemap.xml').unlink()
        self.assertEqual(indexnow.submit(), 1)
        self.http.assert_not_called()

    def test_invalid_configuration_fails(self):
        (self.root / 'config/marketing.json').write_text('{')
        self.assertEqual(indexnow.submit(), 1)
        self.http.assert_not_called()
        self.assertIn('configuration/sitemap error', self.summary.read_text())

    def test_cli_exits_nonzero_on_failure_without_network(self):
        scripts = self.root / 'scripts'
        scripts.mkdir()
        script = scripts / 'submit_indexnow.py'
        script.write_text(Path(indexnow.__file__).read_text())
        (self.root / 'config/marketing.json').write_text('{')
        result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('configuration/sitemap error', result.stdout)

    def test_one_failed_host_does_not_hide_other_host(self):
        (self.root / 'config/marketing.json').write_text(json.dumps({'indexNow': {
            'missing.example': 'public-key', 'example.com': 'public-key'}}))
        self.http.side_effect = [Response(body=b'public-key'), Response()]
        self.assertEqual(indexnow.submit(), 1)
        self.assertIn('missing.example: NOT confirmed', self.output.getvalue())
        self.assertIn('example.com: 1 URLs; HTTP 200', self.output.getvalue())


if __name__ == '__main__':
    unittest.main()

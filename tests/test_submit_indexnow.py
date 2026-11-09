import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import submit_indexnow


class Response(io.BytesIO):
    def __init__(self, status=200, body=b'', url='https://www.example.com/test-key.txt'):
        super().__init__(body)
        self.status = status
        self.url = url

    def geturl(self):
        return self.url


class IndexNowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / 'config').mkdir()
        (self.root / 'site/zh').mkdir(parents=True)
        self.summary = self.root / 'summary.md'
        self.configure({'www.example.com': 'test-key'})
        self.sitemap('site/sitemap.xml', ['https://www.example.com/', 'https://www.example.com/'])
        self.sitemap('site/zh/sitemap.xml', ['https://www.example.com/zh/'])

    def configure(self, keys):
        (self.root / 'config/marketing.json').write_text(json.dumps({'indexNow': keys}))

    def sitemap(self, path, urls):
        (self.root / path).write_text(
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + ''.join(f'<url><loc>{url}</loc></url>' for url in urls) + '</urlset>'
        )

    def invoke(self, responses):
        output = io.StringIO()
        with patch.object(submit_indexnow.urllib.request, 'urlopen', side_effect=responses) as request:
            with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(self.summary)}):
                with contextlib.redirect_stdout(output):
                    result = submit_indexnow.submit(self.root)
        return result, output.getvalue(), request

    def test_200_groups_and_deduplicates_both_sitemaps(self):
        result, output, request = self.invoke([Response(body=b'test-key'), Response(200)])
        self.assertEqual(result, 0)
        self.assertIn('2 URLs; HTTP 200', output)
        self.assertIn('not a guarantee of indexing', output)
        self.assertEqual(request.call_args_list[1].args[0].full_url,
                         'https://yandex.com/indexnow')
        payload = json.loads(request.call_args_list[1].args[0].data)
        self.assertEqual(payload['urlList'], ['https://www.example.com/', 'https://www.example.com/zh/'])
        self.assertEqual(payload['keyLocation'], 'https://www.example.com/test-key.txt')
        self.assertIn(output.strip(), self.summary.read_text())

    def test_202_is_pending_not_verified(self):
        result, output, _ = self.invoke([Response(body=b'test-key'), Response(202)])
        self.assertEqual(result, 0)
        self.assertIn('ownership validation pending', output)

    def test_403_body_is_reported_and_fails(self):
        error = HTTPError(submit_indexnow.ENDPOINT, 403, 'Forbidden', {},
                          io.BytesIO(b'{"code":"InvalidKey","message":"Site ownership is not verified"}'))
        result, output, _ = self.invoke([Response(body=b'test-key'), error])
        self.assertEqual(result, 1)
        self.assertIn('HTTP 403', output)
        self.assertIn('Site ownership is not verified', output)
        self.assertIn('NOT submitted', self.summary.read_text())

    def test_error_body_is_bounded(self):
        error = HTTPError(submit_indexnow.ENDPOINT, 403, 'Forbidden', {},
                          io.BytesIO(b'x' * 10000))
        result, output, _ = self.invoke([Response(body=b'test-key'), error])
        self.assertEqual(result, 1)
        self.assertLess(len(output), 1500)
        self.assertIn('truncated', output)

    def test_preflight_timeout_fails_without_post(self):
        result, output, request = self.invoke([URLError('timed out')])
        self.assertEqual(result, 1)
        self.assertEqual(request.call_count, 1)
        self.assertIn('timed out', output)

    def test_post_timeout_fails(self):
        result, output, _ = self.invoke([Response(body=b'test-key'), TimeoutError('timed out')])
        self.assertEqual(result, 1)
        self.assertIn('NOT submitted', output)

    def test_invalid_ownership_file_stops_before_post(self):
        for response in [Response(body=b'wrong-key'), Response(203, b'test-key'),
                         Response(body=b'test-key' + b' ' * 300)]:
            with self.subTest(response=response):
                result, output, request = self.invoke([response])
                self.assertEqual(result, 1)
                self.assertEqual(request.call_count, 1)
                self.assertIn('ownership file', output)

    def test_cross_host_or_insecure_key_redirect_is_rejected(self):
        for url in ['https://other.example.com/test-key.txt', 'http://www.example.com/test-key.txt']:
            with self.subTest(url=url):
                result, output, request = self.invoke([Response(body=b'test-key', url=url)])
                self.assertEqual(result, 1)
                self.assertEqual(request.call_count, 1)
                self.assertIn('ownership file', output)

    def test_unexpected_success_status_is_failure(self):
        result, output, _ = self.invoke([Response(body=b'test-key'), Response(204, b'unexpected')])
        self.assertEqual(result, 1)
        self.assertIn('HTTP 204', output)
        self.assertNotIn('received (', output)

    def test_partial_failure_keeps_other_hosts_but_fails_overall(self):
        self.configure({'www.example.com': 'test-key', 'other.example.com': 'other-key'})
        self.sitemap('site/zh/sitemap.xml', ['https://other.example.com/zh/'])
        result, output, request = self.invoke([
            Response(body=b'test-key'), Response(200),
            Response(body=b'other-key', url='https://other.example.com/other-key.txt'),
            URLError('network unavailable'),
        ])
        self.assertEqual(result, 1)
        self.assertEqual(request.call_count, 4)
        self.assertIn('www.example.com: 1 URLs; HTTP 200', output)
        self.assertIn('other.example.com: NOT submitted', output)
        payloads = [json.loads(request.call_args_list[i].args[0].data) for i in (1, 3)]
        self.assertEqual(payloads[0]['urlList'], ['https://www.example.com/'])
        self.assertEqual(payloads[1]['urlList'], ['https://other.example.com/zh/'])

    def test_no_urls_is_explicit_skip_without_network(self):
        self.configure({'unused.example.com': 'unused-key'})
        result, output, request = self.invoke([])
        self.assertEqual(result, 0)
        request.assert_not_called()
        self.assertIn('SKIPPED', output)
        self.assertIn('no sitemap URLs', output)

    def test_cli_propagates_failed_submission_exit_code(self):
        (self.root / 'scripts').mkdir()
        script = self.root / 'scripts/submit_indexnow.py'
        shutil.copyfile(submit_indexnow.__file__, script)
        with patch('urllib.request.urlopen', side_effect=URLError('offline')):
            with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(self.summary)}):
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(SystemExit) as stopped:
                        runpy.run_path(str(script), run_name='__main__')
        self.assertEqual(stopped.exception.code, 1)


if __name__ == '__main__':
    unittest.main()

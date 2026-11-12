"""Regression coverage for the public-page SEO audit fixes."""
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import build_seo
from growth_pages import topic_of


class AuditFixTests(unittest.TestCase):
    def test_static_inline_citations(self):
        self.assertEqual(build_seo.inline('[source](https://example.com/?a=1&b=2)'),
                         '<a href="https://example.com/?a=1&amp;b=2">source</a>')
        self.assertEqual(build_seo.inline('`[source](https://example.com)`'),
                         '<code>[source](https://example.com)</code>')
        self.assertNotIn('<a', build_seo.inline('[bad](javascript:alert(1))'))
        self.assertIn('&lt;img', build_seo.inline('[<img>](https://example.com)'))
        self.assertIn('<strong>source</strong>', build_seo.inline('[**source**](https://example.com)'))


    def test_identity_related_links_and_concise_search_descriptions(self):
        root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            for folder in ('site', 'content', 'config'):
                shutil.copytree(root / folder, dest / folder)
            build_seo.build(dest)
            build_seo.build(dest)
            data = json.loads((dest / 'content/site.json').read_text())
            posts = {p['id']: p for p in data['posts']}
            related = json.loads((dest / 'config/topic-related.json').read_text())['identity']
            for prefix in ('', 'zh/'):
                hub = (dest / 'site' / prefix / 'topics/identity/index.html').read_text()
                self.assertEqual(hub.count('class="topic-related"'), 1)
                for slug in related:
                    self.assertIn('href="/' + prefix + 'articles/' + slug + '/"', hub)
                    self.assertTrue((dest / 'site' / prefix / 'articles' / slug / 'index.html').exists())
                    # Cross-topic links should not move the cloud articles out of their primary topic.
                    self.assertEqual(topic_of(posts[slug]), 'cloud')
            for prefix in ('', 'zh/'):
                for slug, post in posts.items():
                    article = (dest / 'site' / prefix / 'articles' / slug / 'index.html').read_text()
                    schemas = [json.loads(raw) for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', article)]
                    posting = next(item for item in schemas if item.get('@type') == 'BlogPosting')
                    self.assertEqual(posting['author'], {'@type': 'Person', 'name': 'xiaohei', 'url': 'https://www.xiaohei.co/' + prefix + 'about.html'})
                    self.assertEqual(posting['datePublished'], post['date'])
                    self.assertNotIn('dateModified', posting)
            for slug in ('mcp-stdio-configuration-trust-boundary', 'embedding-inversion-environment-and-ai-errors'):
                article = (dest / 'site/articles' / slug / 'index.html').read_text()
                description = re.search(r'<meta name="description" content="([^"]+)"', article)[1]
                self.assertLessEqual(len(description), 160)
                # The short search snippet must not replace the complete article deck.
                self.assertIn(posts[slug]['summary']['en'], article)

    def test_invalid_related_article_fails_build(self):
        root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            for folder in ('site', 'content', 'config'):
                shutil.copytree(root / folder, dest / folder)
            (dest / 'config/topic-related.json').write_text('{"identity": ["missing-article"]}')
            with self.assertRaisesRegex(ValueError, 'Invalid related topic'):
                build_seo.build(dest)


if __name__ == '__main__':
    unittest.main()

import unittest,json,tempfile,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import build_seo
class SEOTests(unittest.TestCase):
 def test_static_content_locale_and_metadata_survive_rebuild(self):
  root=Path(__file__).parents[1]
  with tempfile.TemporaryDirectory() as tmp:
   dest=Path(tmp);shutil.copytree(root/'site',dest/'site');shutil.copytree(root/'content',dest/'content')
   build_seo.build(dest);build_seo.build(dest)
   data=json.loads((dest/'content/site.json').read_text())
   for lang in ['en','zh']:
    for post in data['posts']:
     path=dest/'site'/('zh' if lang=='zh' else '')/'articles'/post['id']/'index.html';s=path.read_text()
     self.assertNotIn('noindex',s);self.assertEqual(s.count('rel="canonical"'),1)
     self.assertIn(post['title'][lang],s)
     self.assertIn(build_seo.HOST[lang],s)
     self.assertIn('hreflang="zh-Hans"',s);self.assertIn('application/ld+json',s)
     self.assertIn('article-body',s)
   self.assertIn('noindex,follow',(dest/'site/post.html').read_text())
   self.assertIn('sitemap.xml',(dest/'site/robots.txt').read_text())

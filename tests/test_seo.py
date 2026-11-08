import unittest,json,tempfile,shutil,sys
from pathlib import Path
import xml.etree.ElementTree as ET
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
   for lang,prefix in [('en',''),('zh','zh/')]:
    sitemap=ET.parse(dest/'site'/prefix/'sitemap.xml')
    urls=[item.text for item in sitemap.iter() if item.tag.endswith('loc')]
    self.assertTrue(urls)
    self.assertTrue(all(u.startswith('https://www.xiaohei.co/') for u in urls))
    self.assertTrue(all(u.startswith('https://www.xiaohei.co/zh/')==(lang=='zh') for u in urls))
   chinese=(dest/'site/zh/index.html').read_text()
   self.assertIn('rel="canonical" href="https://www.xiaohei.co/zh/"',chinese)
   self.assertIn('hreflang="zh-Hans" href="https://www.xiaohei.co/zh/"',chinese)
   self.assertNotIn('cn.xiaohei.co',chinese)

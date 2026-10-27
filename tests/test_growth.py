import json,tempfile,shutil,sys,unittest
from pathlib import Path
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import build_seo
from growth_pages import topic_of
class GrowthTests(unittest.TestCase):
 def test_hubs_feeds_and_analytics_are_idempotent(self):
  root=Path(__file__).parents[1]
  with tempfile.TemporaryDirectory() as tmp:
   r=Path(tmp)
   for folder in ['site','content','config']:shutil.copytree(root/folder,r/folder)
   build_seo.build(r);build_seo.build(r)
   for lang,prefix in [('en',''),('zh','zh/')]:
    index=(r/'site'/prefix/'index.html').read_text()
    self.assertEqual(index.count('src="/analytics-loader.js?v=1"'),1)
    self.assertNotIn('src="https://analytics.ahrefs.com/analytics.js"',index)
    self.assertIn('data-key="',index)
    sitemap=(r/'site/sitemap.xml').read_text()
    ET.parse(r/'site'/prefix/'feed.xml')
    hub=(r/'site'/prefix/'topics/cloud/index.html').read_text()
    self.assertIn('Cloud &amp; Hybrid' if lang=='en' else '云与混合云',hub)
    data=json.loads((r/'content/site.json').read_text())
    for topic in data['topics']:
     if not any(topic_of(p)==topic['id'] for p in data['posts']):
      empty=(r/'site'/prefix/'topics'/topic['id']/'index.html').read_text()
      self.assertIn('noindex,follow',empty)
      self.assertNotIn('/topics/'+topic['id']+'/',sitemap)
    article=(r/'site'/prefix/'articles'/data['posts'][0]['id']/'index.html').read_text()
    self.assertEqual(article.count('class="related-reading"'),int(len(data['posts'])>1))
    self.assertEqual(article.count('src="/analytics-loader.js?v=1"'),1)
    self.assertEqual(article.count('property="og:image"'),1)
    self.assertIn('<!--email_off-->',index)

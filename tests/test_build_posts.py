import importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('build_posts',Path(__file__).parents[1]/'scripts/build_posts.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'posts').mkdir();(self.root/'content').mkdir();(self.root/'content/site.json').write_text(json.dumps({'version':1,'posts':[],'contactEmail':'xiaohei@xiaohei.co'}))
 def tearDown(self):self.tmp.cleanup()
 def write(self,name,text):
  p=self.root/'posts'/name;p.write_text(text);return p
 def test_plain_markdown(self):
  p=self.write('2026-10-19-note.md','# 标题\n\n正文\n\n## 小标题\n\n- 一\n- 二\n\n```python\nprint(1)\n```\n')
  post=m.parse(p,self.root);self.assertEqual(post['title']['zh'],'标题');self.assertEqual([b['type'] for b in post['body']],['paragraph','heading','list','code']);self.assertEqual(len(post['body'][2]['items']),2)
 def test_frontmatter_and_chinese_filename(self):
  post=m.parse(self.write('中文.md','---\ntitle: 中文\ndate: 2026-10-19\n---\n正文'),self.root);self.assertTrue(post['id'].startswith('post-'));self.assertEqual(post['date'],'2026-10-19')
 def test_draft_excluded(self):self.assertIsNone(m.parse(self.write('draft.md','---\ndraft: true\n---\n# 草稿'),self.root))
 def test_invalid_date(self):
  with self.assertRaises(ValueError):m.parse(self.write('2026-99-99-test.md','# Test'),self.root)
 def test_duplicate_slug(self):
  for name in ['one.md','two.md']:self.write(name,'---\ndate: 2026-10-19\nslug: same\n---\n# Test')
  with self.assertRaises(ValueError):m.build(self.root)
 def test_removed_articles_removed_from_index(self):
  p=self.write('2026-10-19-test.md','# Test');m.build(self.root);self.assertEqual(len(json.loads((self.root/'content/site.json').read_text())['posts']),1);p.unlink();m.build(self.root);self.assertEqual(json.loads((self.root/'content/site.json').read_text())['posts'],[])
 def test_code_is_preserved(self):self.assertEqual(m.blocks('```html\n<script>alert(1)</script>\n```')[0]['text']['zh'],'<script>alert(1)</script>')
 def test_unclosed_fence(self):
  with self.assertRaises(ValueError):m.blocks('```python\nprint(1)')
 def test_english_companion_merges_into_one_article(self):
  self.write('2026-10-19-note.md','# 中文\n\n中文正文')
  self.write('2026-10-19-note.en.md','# English\n\nEnglish body')
  m.build(self.root)
  posts=json.loads((self.root/'content/site.json').read_text())['posts']
  self.assertEqual(len(posts),1)
  self.assertEqual(posts[0]['title'],{'zh':'中文','en':'English'})
  self.assertEqual(posts[0]['body'][0]['text'],{'zh':'中文正文','en':'English body'})
 def test_misaligned_translation_fails(self):
  self.write('2026-10-19-note.md','# 中文\n\n正文')
  self.write('2026-10-19-note.en.md','# English\n\n## Heading\n\nBody')
  with self.assertRaises(ValueError):m.build(self.root)
if __name__=='__main__':unittest.main()

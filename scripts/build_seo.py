"""Generate crawlable bilingual pages from the same article source used by the UI."""
import html,json,re,shutil
from pathlib import Path
from html.parser import HTMLParser
from xml.sax.saxutils import escape as xml_escape
from growth_pages import topic_of
DATA=None
CONFIG={}
SEO={}
HOST={'en':'https://www.xiaohei.co','zh':'https://cn.xiaohei.co'}
def url(path,lang):return HOST[lang]+('/zh' if lang=='zh' else '')+path

def inline(s):
 s=html.escape(s)
 s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
 s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
 return s

def blocks(body,lang):
 out=[];i=0
 for b in body:
  kind=b.get('type','paragraph');text=b.get('text',b).get(lang,'')
  if kind=='heading':
   i+=1;out.append(f'<h{b["level"]} id="section-{i}">{inline(text)}</h{b["level"]}>')
  elif kind=='code':out.append('<pre><code>'+html.escape(text)+'</code></pre>')
  elif kind=='divider':out.append('<hr>')
  elif kind=='list':
   tag='ol' if b['ordered'] else 'ul';out.append('<'+tag+'>'+''.join('<li>'+inline(x[lang])+'</li>' for x in b['items'])+'</'+tag+'>')
  elif kind=='table':out.append('<div class="article-table"><table><thead><tr>'+''.join('<th scope="col">'+inline(x[lang])+'</th>' for x in b['headers'])+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+inline(x[lang])+'</td>' for x in row)+'</tr>' for row in b['rows'])+'</tbody></table></div>')
  else:
   tag='blockquote' if kind=='quote' else 'p';out.append('<'+tag+'>'+inline(text)+'</'+tag+'>')
 return ''.join(out)

class Localize(HTMLParser):
 def __init__(self,lang):super().__init__(convert_charrefs=False);self.lang=lang;self.out=[];self.skip=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='html':a['lang']='zh-CN' if self.lang=='zh' else 'en'
  if 'data-aria-en' in a:a['aria-label']=a['data-aria-'+self.lang]
  if 'data-placeholder-en' in a:a['placeholder']=a['data-placeholder-'+self.lang]
  if tag=='a' and a.get('href','').startswith('/') and not a['href'].startswith('//'):
   href=a['href']
   if self.lang=='zh' and not href.startswith(('/assets/','/zh/')):a['href']='/zh'+href
  self.out.append('<'+tag+''.join(' '+k+('="'+html.escape(v,quote=True)+'"' if v is not None else '') for k,v in a.items())+'>')
  if 'data-en' in a:self.out.append(html.escape(a['data-'+self.lang]));self.skip=tag
 def handle_endtag(self,tag):
  self.out.append('</'+tag+'>')
  if self.skip==tag:self.skip=None
 def handle_data(self,data):
  if not self.skip:self.out.append(data)
 def handle_entityref(self,name):
  if not self.skip:self.out.append('&'+name+';')
 def handle_charref(self,name):
  if not self.skip:self.out.append('&#'+name+';')
 def handle_decl(self,decl):self.out.append('<!'+decl+'>')

def build(root):
 site=root/'site'
 if not (site/'index.html').exists():return
 global DATA,CONFIG,SEO
 data=json.loads((root/'content/site.json').read_text());posts=data['posts'];DATA=data
 config_path=root/'config/marketing.json';CONFIG=json.loads(config_path.read_text()) if config_path.exists() else {}
 seo_path=root/'config/seo.json';SEO=json.loads(seo_path.read_text()) if seo_path.exists() else {}
 templates={name:re.sub(r'<meta name="robots"[^>]*>','',(site/name).read_text()) for name in ['index.html','topics.html','about.html','post.html']}
 # Rebuild generated directories to avoid retaining removed articles.
 for directory in [site/'articles',site/'zh',site/'topics']:
  if directory.exists():shutil.rmtree(directory)
 pages=[]
 for lang in ['en','zh']:
  for name,template in templates.items():
   if name=='post.html':continue
   path='/' if name=='index.html' else '/'+name
   title={'index.html':{'en':'AI, Cloud & Red Team Security Notes','zh':'AI、云与红队安全笔记'},'topics.html':{'en':'Security Topics & Article Index','zh':'安全主题与文章目录'},'about.html':{'en':'Background & Certifications','zh':'背景与专业认证'}}[name][lang]+' — TR Notes'
   desc={'en':'Practical notes and experiments on AI security, agents, RAG, cloud security and Active Directory.','zh':'整理 AI 安全、智能体、RAG、云安全与 Active Directory 的实践笔记和实验记录。'}[lang]
   s=re.sub(r'<!-- SEO START -->.*?<!-- SEO END -->','',template,flags=re.S)
   entries=''.join('<article class="post-preview"><time>'+p['date']+'</time><h2><a href="'+('/zh' if lang=='zh' else '')+'/articles/'+p['id']+'/">'+html.escape(p['title'][lang])+'</a></h2><p>'+html.escape(p['summary'][lang])+'</p></article>' for p in posts)
   if name=='index.html':s=re.sub(r'(<div id="github-posts">).*?(</div>)',lambda m:m[1]+entries+m[2],s,count=1,flags=re.S)
   if name=='topics.html':
    ids=['ai','agents','cloud','identity','notes'];topics={t['id']:t for t in data.get('topics',[])}
    entries=''.join('<section class="directory-card" id="'+tid+'"><h2>'+html.escape(topics[tid]['title'][lang])+'</h2><ul class="directory-links">'+''.join('<li><a href="'+('/zh' if lang=='zh' else '')+'/articles/'+p['id']+'/">'+html.escape(p['title'][lang])+'</a></li>' for p in posts if topic_of(p)==tid)+'</ul></section>' for tid in ids)
    s=re.sub(r'(<div id="topic-directory"[^>]*>).*?(</div>)',lambda m:m[1]+entries+m[2],s,count=1,flags=re.S)
   write_page(site,s,path,title,desc,lang,pages)
  for post in posts:
   path='/articles/'+post['id']+'/'
   title=post['title'][lang]+' — TR Notes';desc=post['summary'][lang]
   body='<header class="article-header"><p>'+post['date']+'</p><h1>'+html.escape(post['title'][lang])+'</h1><p class="article-deck">'+html.escape(desc)+'</p></header><div class="article-body">'+blocks(post['body'],lang)+'</div>'
   s=re.sub(r'(<article id="github-article">).*?(</article>)',lambda m:m[1]+body+m[2],templates['post.html'],flags=re.S)
   s=s.replace('<body ','<body data-post-id="'+post['id']+'" ',1)
   write_page(site,s,path,title,desc,lang,pages,post)
 from growth_pages import build as build_growth
 build_growth(root,data,templates,pages,write_page)
 for host,key in CONFIG.get('indexNow',{}).items():
  if re.fullmatch(r'[a-f0-9]{32}',key):(site/(key+'.txt')).write_text(key)
 (site/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+xml_escape(u)+'</loc></url>' for u in pages)+'</urlset>\n')
 (site/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: https://www.xiaohei.co/sitemap.xml\nSitemap: https://cn.xiaohei.co/sitemap.xml\n')
 # Generic query-based article shell should not compete with permanent article pages.
 legacy=templates['post.html'];legacy=re.sub(r'<!-- SEO START -->.*?<!-- SEO END -->','',legacy,flags=re.S)
 legacy=legacy.replace('</head>','<meta name="robots" content="noindex,follow"></head>')
 (site/'post.html').write_text(legacy)
 print(f'Generated {len(pages)} crawlable localized URLs')

def write_page(site,s,path,title,desc,lang,pages,post=None):
 # Editorial search snippets are separate from the full article headline and deck.
 overrides=SEO.get(path,{}).get(lang,{})
 title=overrides.get('title',title)
 desc=overrides.get('description',desc)
 s=re.sub(r'<!-- SEO START -->.*?<!-- SEO END -->','',s,flags=re.S)
 s=re.sub(r'<link rel="alternate" type="application/rss\+xml"[^>]*>','',s)
 s=s.replace('<script defer src="/growth.js"></script>','')
 s=re.sub(r'<a href="(?:/zh)?/feed.xml">RSS</a>','',s)
 s=re.sub(r'<title>.*?</title>','<title>'+html.escape(title)+'</title>',s,flags=re.S)
 s=re.sub(r'<meta name="description"[^>]*>','<meta name="description" content="'+html.escape(desc,quote=True)+'">',s)
 s=re.sub(r' data-(?:page-language|en-url|zh-url|seo-title)="[^"]*"','',s)
 s=s.replace('<body ','<body data-seo-title="'+html.escape(title,quote=True)+'" data-page-language="'+lang+'" data-en-url="'+path+'" data-zh-url="/zh'+path+'" ',1)
 s=re.sub(r'<aside class="ai-writing-note".*?</aside>','',s,flags=re.S)
 s=s.replace('<footer class="site-footer">',"<aside class=\"ai-writing-note\" aria-label=\"A note on the writing\" data-aria-en=\"A note on the writing\" data-aria-zh=\"内容说明\" style=\"margin-top:28px;padding:20px 0;border-top:1px solid #c9d3b72c;color:#b8c1ac;font-size:12px;line-height:1.9\"><p data-en=\"Written by AI and reviewed by the author before publication. Some AI flavor remains—the author is lazy and doesn't feel like polishing it away.\" data-zh=\"本站内容由 AI 代笔，发布前由作者审核。AI 味可能还在——作者比较懒，暂时不想调。\">Written by AI and reviewed by the author before publication. Some AI flavor remains—the author is lazy and doesn't feel like polishing it away.</p></aside>"+'<footer class="site-footer">')
 from growth_pages import enrich
 s=enrich(s,path,lang,post,DATA,CONFIG)
 parser=Localize(lang);parser.feed(s);s=''.join(parser.out)
 canonical=url(path,lang)
 structured={'@context':'https://schema.org','@type':'BlogPosting' if post else 'WebPage','name':title,'url':canonical,'inLanguage':'zh-CN' if lang=='zh' else 'en','description':desc,'isPartOf':{'@type':'WebSite','name':'TR Notes','url':HOST['en']}}
 if post:structured.update(headline=post['title'][lang],datePublished=post['date'],mainEntityOfPage=canonical)
 meta='<!-- SEO START --><link rel="canonical" href="'+canonical+'">'+''.join('<link rel="alternate" hreflang="'+code+'" href="'+url(path,l)+'">' for code,l in [('en','en'),('zh-Hans','zh'),('x-default','en')])+'<meta property="og:type" content="'+('article' if post else 'website')+'"><meta property="og:site_name" content="TR Notes"><meta property="og:title" content="'+html.escape(title,quote=True)+'"><meta property="og:description" content="'+html.escape(desc,quote=True)+'"><meta property="og:url" content="'+canonical+'"><meta name="twitter:card" content="summary"><script type="application/ld+json">'+json.dumps(structured,ensure_ascii=False).replace('<','\\u003c')+'</script><!-- SEO END -->'
 s=s.replace('</head>',meta+'</head>')
 output=site/(('zh/' if lang=='zh' else '')+('index.html' if path=='/' else path.lstrip('/')+('index.html' if path.endswith('/') else '')))
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(s);pages.append(canonical)

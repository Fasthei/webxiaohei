"""Topic hubs, related reading, RSS and optional verified marketing integrations."""
import html,json,re
from xml.sax.saxutils import escape
from email.utils import format_datetime
from datetime import datetime,timezone
HOST={'en':'https://www.xiaohei.co','zh':'https://cn.xiaohei.co'}
def topic_of(post):
 if post.get('topic') in {'ai','agents','cloud','identity','notes'}:return post['topic']
 label=' '.join(post['category'].values())
 for pattern,topic in [(r'agent|rag|智能体|检索','agents'),(r'cloud|aws|azure|gcp|云','cloud'),(r'identity|active directory|red team|身份|红队|域控','identity'),(r'\bai\b|llm|模型','ai')]:
  if re.search(pattern,label,re.I):return topic
 return 'notes' 
def canonical(path,lang):return HOST[lang]+('/zh' if lang=='zh' else '')+path

def enrich(s,path,lang,post,data,config):
 s=re.sub(r'<!-- GROWTH START -->.*?<!-- GROWTH END -->','',s,flags=re.S)
 s=re.sub(r'<script\b[^>]*src="https://analytics\.ahrefs\.com/analytics\.js"[^>]*>\s*</script>','',s,flags=re.S)
 for name in ['google-site-verification','msvalidate.01','ahrefs-site-verification']:
  provider={'google-site-verification':'google','msvalidate.01':'bing','ahrefs-site-verification':'ahrefs'}[name]
  if config.get('verification',{}).get(provider,{}).get(lang):s=re.sub(r'<meta name="'+re.escape(name)+r'"[^>]*>','',s)
 if post:
  topic=topic_of(post);label=next((t['title'][lang] for t in data['topics'] if t['id']==topic),topic)
  s=re.sub(r'<span\b[^>]*id="article-topic"[^>]*>.*?</span>', '<a id="article-topic" href="/topics/'+topic+'/">'+html.escape(label)+'</a>',s,flags=re.S)
  others=sorted((p for p in data['posts'] if p['id']!=post['id']),key=lambda p:(topic_of(p)==topic,p['date']),reverse=True)[:3]
  if others:
   related='<!-- GROWTH START --><nav class="related-reading" aria-label="'+('Related reading' if lang=='en' else '相关阅读')+'"><h2>'+('Related reading' if lang=='en' else '相关阅读')+'</h2><ul>'+''.join('<li><a href="/articles/'+p['id']+'/">'+html.escape(p['title'][lang])+'</a></li>' for p in others)+'</ul></nav><!-- GROWTH END -->'
   s=s.replace('<div class="article-end">',related+'<div class="article-end">',1)
 # These are public verification values, not credentials. Empty values emit no tags.
 for provider,meta in [('google','google-site-verification'),('bing','msvalidate.01'),('ahrefs','ahrefs-site-verification')]:
  value=config.get('verification',{}).get(provider,{}).get(lang,'')
  if value:s=s.replace('</head>','<meta name="'+meta+'" content="'+html.escape(value,quote=True)+'"></head>')
 key=config.get('ahrefsAnalytics',{}).get(lang,'')
 if key:s=s.replace('</head>','<script async src="https://analytics.ahrefs.com/analytics.js" data-key="'+html.escape(key,quote=True)+'"></script></head>')
 feed=canonical('/feed.xml',lang)
 s=s.replace('</head>','<link rel="alternate" type="application/rss+xml" title="TR Notes" href="'+feed+'"><script defer src="/growth.js"></script></head>')
 s=s.replace('<footer class="site-footer">','<footer class="site-footer"><a href="'+('/zh' if lang=='zh' else '')+'/feed.xml">RSS</a>')
 return s

def build(root,data,templates,pages,write_page):
 site=root/'site'
 for lang in ['en','zh']:
  prefix='/zh' if lang=='zh' else ''
  for topic in data['topics']:
   tid=topic['id'];posts=[p for p in data['posts'] if topic_of(p)==tid]
   title=topic['title'][lang];desc=topic['description'][lang]
   main='<main id="main" class="directory-page paper-main"><nav class="breadcrumbs"><a href="/topics.html">'+('All topics' if lang=='en' else '全部分类')+'</a></nav><header class="page-intro"><h1>'+html.escape(title)+'</h1><p>'+html.escape(desc)+'</p></header>'
   if posts:
    main+=''.join('<article class="post-preview"><time>'+p['date']+'</time><h2><a href="/articles/'+p['id']+'/">'+html.escape(p['title'][lang])+'</a></h2><p>'+html.escape(p['summary'][lang])+'</p></article>' for p in posts)
   else:main+='<p>'+('No articles published in this topic yet.' if lang=='en' else '此主题暂未发布文章。')+'</p>'
   main+='</main>'
   s=re.sub(r'<main\b.*?</main>',lambda _:main,templates['topics.html'],flags=re.S)
   path='/topics/'+tid+'/'
   s=s.replace('data-content-page="topics"','data-content-page="topic"')
   if not posts:s=s.replace('</head>','<meta name="robots" content="noindex,follow"></head>')
   write_page(site,s,path,title+' — TR Notes',desc,lang,pages)
   if not posts:pages.pop() # Do not invite crawlers to index empty hubs.
  items=''
  for p in data['posts']:
   link=canonical('/articles/'+p['id']+'/',lang)
   date=format_datetime(datetime.fromisoformat(p['date']).replace(tzinfo=timezone.utc))
   items+='<item><title>'+escape(p['title'][lang])+'</title><link>'+escape(link)+'</link><guid isPermaLink="true">'+escape(link)+'</guid><description>'+escape(p['summary'][lang])+'</description><pubDate>'+date+'</pubDate></item>'
  feed='<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>TR Notes</title><link>'+canonical('/',lang)+'</link><description>Security research and learning notes</description><language>'+('zh-CN' if lang=='zh' else 'en')+'</language>'+items+'</channel></rss>'
  out=site/('zh/feed.xml' if lang=='zh' else 'feed.xml');out.parent.mkdir(parents=True,exist_ok=True);out.write_text(feed)

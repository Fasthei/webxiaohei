"""Fail publishing on broken local links or incomplete indexable-page metadata."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import json, sys

class Page(HTMLParser):
 def __init__(self):
  super().__init__(); self.links=[]; self.meta=[]; self.canonical=[]; self.h1=0; self.titles=0
 def handle_starttag(self, tag, attrs):
  a=dict(attrs)
  if tag=='h1':self.h1+=1
  if tag=='title':self.titles+=1
  if tag=='meta':self.meta.append(a)
  if tag=='link' and a.get('rel')=='canonical':self.canonical.append(a.get('href',''))
  if tag in ['a','img','script','link']:
   value=a.get('src') if tag in ['img','script'] else a.get('href')
   if value:self.links.append(value)

def check(root):
 errors=[]; pages=0
 for file in sorted(root.rglob('*.html')):
  p=Page();p.feed(file.read_text());pages+=1
  for link in p.links:
   u=urlsplit(link)
   if u.scheme or u.netloc or not u.path:continue
   target=(root/unquote(u.path.lstrip('/'))) if u.path.startswith('/') else file.parent/unquote(u.path)
   if not target.is_file() and not (target/'index.html').is_file():errors.append(f'{file.relative_to(root)}: broken local link {link}')
  indexable=not any('noindex' in m.get('content','') for m in p.meta if m.get('name')=='robots')
  if indexable:
   for valid,label in [(p.h1==1,'one H1'),(p.titles==1,'one title'),(len(p.canonical)==1,'one canonical'),(sum(m.get('name')=='description' and bool(m.get('content')) for m in p.meta)==1,'one description'),(sum(m.get('property')=='og:image' for m in p.meta)==1,'one share image')]:
    if not valid:errors.append(f'{file.relative_to(root)}: expected {label}')
 if errors:raise SystemExit('\n'.join(errors))
 print(f'Checked {pages} HTML pages: local links and metadata pass')

if __name__=='__main__':check(Path(__file__).resolve().parents[1]/'site')

"""Notify participating search engines after a successful production deployment."""
import json,os,urllib.request,urllib.error,xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
def submit():
 config=json.loads((ROOT/'config/marketing.json').read_text())
 urls=[n.text for n in ET.parse(ROOT/'site/sitemap.xml').iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
 results=[]
 for host,key in config['indexNow'].items():
  key_url=f'https://{host}/{key}.txt'
  selected=sorted(set(u for u in urls if urlparse(u).netloc==host))
  try:
   with urllib.request.urlopen(key_url,timeout=12) as response:
    if response.status!=200 or response.read(256).decode().strip()!=key:raise ValueError('Published ownership file does not match')
   payload=json.dumps({'host':host,'key':key,'keyLocation':key_url,'urlList':selected}).encode()
   request=urllib.request.Request('https://api.indexnow.org/indexnow',data=payload,headers={'Content-Type':'application/json; charset=utf-8'},method='POST')
   with urllib.request.urlopen(request,timeout=18) as response:
    status=response.status
   results.append(f'{host}: {len(selected)} URLs; HTTP {status} — '+('received; ownership validation pending' if status==202 else 'received (not a guarantee of indexing)'))
  except Exception as exc:
   results.append(f'{host}: NOT submitted — {type(exc).__name__}: {exc}')
 for line in results:print(line)
 if os.environ.get('GITHUB_STEP_SUMMARY'):
  with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write('## IndexNow submission\n\n'+'\n'.join('- '+x for x in results)+'\n')
 return results
if __name__=='__main__':submit()

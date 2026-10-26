const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('site/app.js','utf8');
const baseline=JSON.parse(fs.readFileSync('site/content/site.json','utf8'));
async function run(remote, {page='home', fail=false}={}) {
 const nodes=[];
 function node(tagName='div'){ const n={tagName,dataset:{},children:[],attrs:{},textContent:'',append(...x){this.children.push(...x)},contains(target){return this.children.some(child=>child===target||child.contains(target))},replaceChildren(...x){this.children=x},setAttribute(k,v){this.attrs[k]=v},hasAttribute(k){return k==='data-en'&&'en' in this.dataset},addEventListener(k,f){this[k]=f}}; nodes.push(n); return n; }
 const text=node();text.dataset={contentKey:'text_01',en:'old',zh:'旧'};
 const mail=node(); const list=node(); const article=node();const count=node();const upcoming=node();const staticPost=node();staticPost.className='post-preview';
 const button=node(); button.dataset.language='zh';
 const document={documentElement:{dataset:{}},body:{dataset:{contentPage:page}},createElement:node,createTextNode(text){const n=node("#text");n.textContent=text;return n;},querySelectorAll(q){return q==='.post-preview'?nodes.filter(n=>n.className==='post-preview'):q==='[data-language]'?[button]:q==='[data-en]'?nodes.filter(n=>'en'in n.dataset):q==='[data-content-key]'?[text]:q.startsWith('a[')?[mail]:[]},querySelector(q){return q.startsWith('#writing')?count:upcoming},getElementById(id){return id==='github-posts'&&page==='home'?list:id==='github-article'&&page==='post'?article:null}};
 let calls=0;
 const fetch=async url=>{calls++;if(fail&&calls===1)throw Error('offline');return {ok:true,text:async()=>JSON.stringify(calls===1?remote:baseline)}};
 await vm.runInNewContext(source,{document,fetch,localStorage:{getItem(){},setItem(){}},AbortSignal,URLSearchParams,location:{search:'?id=test-note'}});
 await new Promise(resolve=>setImmediate(resolve));
 return {document,text,mail,list,article,button,calls,nodes,count,staticPost};
}
test('fresh deployed content updates text and email and preserves language switching',async()=>{const data=structuredClone(baseline);data.contactEmail='test@example.com';data.pages.home.text_01={en:'Changed',zh:'已更新'};const r=await run(data);assert.equal(r.text.textContent,'Changed');assert.equal(r.mail.href,'mailto:test@example.com');r.button.click();assert.equal(r.text.textContent,'已更新');assert.equal(r.document.documentElement.dataset.contentSource,'site')});
test('network failure falls back to published content',async()=>{const r=await run(null,{fail:true});assert.equal(r.document.documentElement.dataset.contentSource,'fallback');assert.equal(r.calls,2)});
test('invalid remote data falls back without partial updates',async()=>{const r=await run({version:2});assert.equal(r.document.documentElement.dataset.contentSource,'fallback');assert.equal(r.mail.href,'mailto:xiaohei@xiaohei.co')});
const post={id:'test-note',date:'2026-10-19',title:{en:'Test',zh:'测试'},summary:{en:'Summary',zh:'摘要'},category:{en:'Research',zh:'研究'},body:[{en:'<script>unsafe()</script>',zh:'中文正文'}]};
test('new posts generate links and article paragraphs as text',async()=>{const data=structuredClone(baseline);data.posts=[post];const home=await run(data);assert.equal(home.list.children.length,1);assert.equal(home.list.children[0].children[3].href,'/post.html?id=test-note');const page=await run(data,{page:'post'});assert.equal(page.article.children[1].children[0].textContent,'<script>unsafe()</script>');assert.equal(page.article.children[1].children[0].children.length,0)});
test('unknown article displays a recovery message',async()=>{const r=await run(baseline,{page:'post'});assert.equal(r.article.children[0].children[0].textContent,'Article unavailable')});
test('duplicate IDs reject the remote content',async()=>{const data=structuredClone(baseline);data.posts=[post,post];const r=await run(data);assert.equal(r.document.documentElement.dataset.contentSource,'fallback')});

const bilingual = text => ({en:text,zh:'中文 '+text});
test('structured Markdown blocks render semantic elements as inert text and switch language',async()=>{
 const data=structuredClone(baseline);
 data.posts=[{...post,body:[
  {type:'heading',level:2,text:bilingual('Section')},
  {type:'heading',level:3,text:bilingual('Subsection')},
  {type:'heading',level:4,text:bilingual('Details')},
  {type:'paragraph',text:bilingual('<img src=x onerror=alert(1)>')},
  {type:'code',language:'javascript',text:bilingual('const x = "<script>";\nalert(x);')},
  {type:'list',ordered:false,items:[bilingual('One'),bilingual('Two')]},
  {type:'list',ordered:true,items:[bilingual('First')]},
  {type:'quote',text:bilingual('A quote')},
  {en:'Legacy paragraph',zh:'旧段落'}
 ]}];
 const r=await run(data,{page:'post'});
 assert.equal(r.document.documentElement.dataset.contentSource,'site');
 const blocks=r.article.children[1].children;
 assert.deepEqual(blocks.map(n=>n.tagName),['h2','h3','h4','p','pre','ul','ol','blockquote','p']);
 assert.equal(blocks[3].textContent,'<img src=x onerror=alert(1)>');
 assert.equal(blocks[3].children.length,0);
 assert.equal(blocks[4].children[0].tagName,'code');
 assert.equal(blocks[4].children[0].textContent,'const x = "<script>";\nalert(x);');
 assert.equal(blocks[4].children[0].dataset.language,'javascript');
 assert.deepEqual(blocks[5].children.map(n=>[n.tagName,n.textContent]),[['li','One'],['li','Two']]);
 assert.equal(r.document.title,'Test — LISG');
 r.button.click();
 assert.equal(blocks[0].textContent,'中文 Section');
 assert.equal(blocks[5].children[0].textContent,'中文 One');
 assert.equal(blocks[8].textContent,'旧段落');
 assert.equal(r.document.title,'测试 — LISG');
});
test('invalid structured blocks reject the entire remote payload before application',async()=>{
 const invalid=[null,[],{type:'html',text:bilingual('<b>bad</b>')},
  {type:'heading',level:1,text:bilingual('Bad heading')},
  {type:'heading',level:'2',text:bilingual('Bad level')},
  {type:'paragraph',text:{en:'Missing translation'}},
  {type:'code',language:'js onload=bad',text:bilingual('bad')},
  {type:'list',items:[bilingual('Missing ordered')]},
  {type:'list',ordered:false,items:[{en:'Missing translation'}]},
  {type:'quote',text:'Not bilingual'},
  {type:null,en:'Not legacy',zh:'非旧格式'}];
 for(const block of invalid){
  const data=structuredClone(baseline);data.contactEmail='should-not-apply@example.com';
  data.posts=[{...post,body:[block]}];
  const r=await run(data);
  assert.equal(r.document.documentElement.dataset.contentSource,'fallback',JSON.stringify(block));
  assert.equal(r.mail.href,'mailto:'+baseline.contactEmail);
 }
});

test('GitHub introduction replaces the static preview without double counting',async()=>{
 const data=structuredClone(baseline);data.posts=[{...post,id:'hello-lisg'}];
 const r=await run(data);
 assert.equal(r.staticPost.hidden,true);
 assert.equal(r.list.children.length,1);
 assert.notEqual(r.list.children[0].hidden,true);
 assert.equal(r.count.textContent,'1 entry');
 r.button.click();assert.equal(r.count.textContent,'1 篇');
});
test('static introduction remains visible and counted when not supplied by GitHub',async()=>{
 const data=structuredClone(baseline);data.posts=[post];
 const r=await run(data);
 assert.equal(r.staticPost.hidden,false);
 assert.equal(r.count.textContent,'2 entries');
});

test('technical article tables and inline formatting render safely and switch languages',async()=>{
 const data=structuredClone(baseline);
 data.posts=[{...post,body:[
  {type:'paragraph',text:{en:'**Finding** with `cached_tokens` and [source](https://example.com). <img src=x onerror=bad()>',zh:'**结论** 与 `cached_tokens` 和 [来源](https://example.com)。'}},
  {type:'table',headers:[bilingual('Input'),bilingual('Result')],rows:[[bilingual('Unchanged'),bilingual('**HTTP 200**')]]},
  {type:'divider'},
  {type:'code',text:bilingual('**literal** <script>alert(1)</script>')}
 ]}];
 const r=await run(data,{page:'post'});
 assert.equal(r.document.documentElement.dataset.contentSource,'site');
 const b=r.article.children[1].children;
 assert.equal(b[0].children[0].tagName,'strong');assert.equal(b[0].children[0].textContent,'Finding');
 assert.equal(b[0].children.find(n=>n.tagName==='a').href,'https://example.com');
 assert.equal(r.nodes.some(n=>n.tagName==='img'||n.tagName==='script'),false);
 assert.equal(b[1].children[0].tagName,'table');
 assert.equal(b[1].children[0].children[0].children[0].children[0].attrs.scope,'col');
 assert.equal(b[2].tagName,'hr');
 assert.equal(b[3].children[0].textContent,'**literal** <script>alert(1)</script>');
 r.button.click();assert.equal(b[0].children[0].textContent,'结论');
});
test('malformed table rows are rejected before content is applied',async()=>{
 const data=structuredClone(baseline);data.posts=[{...post,body:[{type:'table',headers:[bilingual('A')],rows:[[bilingual('B'),bilingual('C')]]}]}];
 const r=await run(data);assert.equal(r.document.documentElement.dataset.contentSource,'fallback');
});

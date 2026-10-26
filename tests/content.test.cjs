const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('site/app.js','utf8');
const baseline=JSON.parse(fs.readFileSync('site/content/site.json','utf8'));
async function run(remote, {page='home', fail=false, search='?id=test-note'}={}) {
 const nodes=[];
 function node(tagName='div'){ const n={tagName,dataset:{},children:[],attrs:{},textContent:'',append(...x){this.children.push(...x)},contains(target){return this.children.some(child=>child===target||child.contains(target))},replaceChildren(...x){this.children=x},setAttribute(k,v){this.attrs[k]=v},removeAttribute(k){delete this.attrs[k]},focus(){this.focused=true},hasAttribute(k){return k==='data-en'&&'en' in this.dataset},addEventListener(k,f){this[k]=f}}; nodes.push(n); return n; }
 const text=node();text.dataset={contentKey:'text_01',en:'old',zh:'旧'};
 const mail=node(); const list=node(); const article=node();const count=node();const upcoming=node();const staticPost=node();staticPost.className='post-preview';
 const button=node(); button.dataset.language='zh';
 const ids={};if(page==='home')for(const id of ['article-search','article-sort','clear-search','reset-filters','article-count','total-notes','writing-heading','catalog-description','empty-results'])ids[id]=node();
 if(page==='post')for(const id of ['article-toc','article-topic'])ids[id]=node();
 if(page==='topics')ids['topic-directory']=node();
 const filters=['all','ai','agents','cloud','identity','notes'].map(id=>{const a=node('a');a.dataset.topic=id;return a;});
 const document={documentElement:{dataset:{}},body:{dataset:{contentPage:page}},createElement:node,createTextNode(text){const n=node("#text");n.textContent=text;return n;},querySelectorAll(q){return q==='[data-topic]'?(page==='home'?filters:[]):q==='.post-preview'?nodes.filter(n=>n.className==='post-preview'):q==='[data-language]'?[button]:q==='[data-en]'?nodes.filter(n=>'en'in n.dataset):q==='[data-content-key]'?[text]:q.startsWith('a[')?[mail]:[]},querySelector(q){return q.startsWith('#writing')?count:upcoming},getElementById(id){return ids[id]|| (id==='github-posts'&&page==='home'?list:id==='github-article'&&page==='post'?article:null)}};
 let calls=0;
 const fetch=async url=>{calls++;if(fail&&calls===1)throw Error('offline');return {ok:true,text:async()=>JSON.stringify(calls===1?remote:baseline)}};
 await vm.runInNewContext(source,{document,fetch,localStorage:{getItem(){},setItem(){}},AbortSignal,URLSearchParams,location:{search,pathname:'/'},history:{replaceState(){}}});
 await new Promise(resolve=>setImmediate(resolve));
 return {document,text,mail,list,article,button,calls,nodes,count,staticPost,ids,filters};
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
 assert.equal(r.document.title,'Test — TR Notes');
 r.button.click();
 assert.equal(blocks[0].textContent,'中文 Section');
 assert.equal(blocks[5].children[0].textContent,'中文 One');
 assert.equal(blocks[8].textContent,'旧段落');
 assert.equal(r.document.title,'测试 — TR Notes');
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

test('topic deep links filter articles, and empty topics show a recovery action',async()=>{
 const data=structuredClone(baseline);data.posts=[{...post,topic:'ai'},{...post,id:'cloud-note',topic:'cloud'}];
 const r=await run(data,{search:'?topic=ai'});
 assert.equal(r.list.children.length,1);assert.equal(r.list.children[0].children[3].href,'/post.html?id=test-note');
 assert.equal(r.ids['article-count'].textContent,'1 note');
 r.filters.find(n=>n.dataset.topic==='agents').click({preventDefault(){}});
 assert.equal(r.list.children.length,0);assert.equal(r.ids['empty-results'].hidden,false);
 r.ids['reset-filters'].click();assert.equal(r.list.children.length,2);assert.equal(r.ids['empty-results'].hidden,true);
});
test('bilingual full-text search, clearing and date sorting work together',async()=>{
 const data=structuredClone(baseline);data.posts=[{...post,topic:'ai',date:'2026-10-26'},{...post,id:'older',date:'2026-10-19',topic:'cloud',body:[{type:'paragraph',text:{en:'unique phrase',zh:'检索实验'}}]}];
 const r=await run(data);r.ids['article-search'].value='检索实验';r.ids['article-search'].input();
 assert.equal(r.list.children.length,1);assert.equal(r.list.children[0].children[3].href,'/post.html?id=older');
 r.button.click();assert.equal(r.ids['article-count'].textContent,'1 篇');
 r.ids['clear-search'].click();assert.equal(r.list.children.length,2);
 r.ids['article-sort'].value='oldest';r.ids['article-sort'].change();assert.equal(r.list.children[0].children[3].href,'/post.html?id=older');
});
test('topic directory shows real counts and explicitly empty categories',async()=>{
 const data=structuredClone(baseline);data.posts=[{...post,topic:'ai'}];const r=await run(data,{page:'topics'});
 const cards=r.ids['topic-directory'].children;assert.equal(cards.length,5);
 assert.equal(cards[0].children[0].children[1].textContent,'1 note');
 assert.equal(cards[1].children[3].textContent,'No entries yet.');
});
test('article table of contents targets stable headings in both languages',async()=>{
 const data=structuredClone(baseline);data.posts=[{...post,body:[{type:'heading',level:2,text:{en:'Overview',zh:'概览'}},{type:'heading',level:3,text:{en:'Evidence',zh:'证据'}}]}];
 const r=await run(data,{page:'post'});const links=r.ids['article-toc'].children;
 assert.equal(links[0].href,'#section-1');assert.equal(links[1].href,'#section-2');
 assert.equal(r.article.children[1].children[1].id,'section-2');r.button.click();assert.equal(links[0].textContent,'概览');assert.equal(links[0].href,'#section-1');
});

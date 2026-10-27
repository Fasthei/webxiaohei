const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const code=fs.readFileSync('site/analytics-loader.js','utf8');
function run(search='',cookie='',storage='',dnt='0',throws=false){
 const scripts=[],notices=[];let saved=storage;
 const document={cookie,currentScript:{dataset:{key:'test-public-key'}},documentElement:{lang:'en'},createElement:()=>({dataset:{},setAttribute(){}}),head:{appendChild:s=>scripts.push(s)},body:{prepend:n=>notices.push(n)}};
 const context={document,location:{search,hostname:'www.xiaohei.co'},navigator:{doNotTrack:dnt},window:{},URLSearchParams,localStorage:{getItem(){if(throws)throw Error();return saved},setItem(k,v){if(throws)throw Error();saved=v}}};
 vm.runInNewContext(code,context);return {scripts,notices,context};
}
test('ordinary visits load exactly one configured tracker',()=>{const r=run();assert.equal(r.scripts.length,1);assert.equal(r.scripts[0].dataset.key,'test-public-key');});
test('exclude URL prevents first pageview and sets shared-domain preference',()=>{const r=run('?analytics=off');assert.equal(r.scripts.length,0);assert.match(r.context.document.cookie,/Domain=xiaohei.co/);assert.equal(r.notices.length,1);});
test('saved exclusion prevents tracking on subsequent pages',()=>assert.equal(run('','tr_analytics_excluded=1').scripts.length,0));
test('shared on preference overrides stale local preference',()=>assert.equal(run('','tr_analytics_excluded=0','1').scripts.length,1));
test('DNT prevents provider loading',()=>assert.equal(run('','','','1').scripts.length,0));
test('explicit exclusion works when storage is unavailable',()=>assert.equal(run('?analytics=off','','','0',true).scripts.length,0));

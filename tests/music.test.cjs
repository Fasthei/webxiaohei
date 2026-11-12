const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const code=fs.readFileSync('site/music.js','utf8');
for(const lang of ['en','zh']) test(`music stays in header flow and controls playback (${lang})`,async()=>{
 const made=[];let placement;
 function element(tag){const el={tag,attrs:{},events:{},paused:true,setAttribute(k,v){this.attrs[k]=v},append(){},addEventListener(k,fn){this.events[k]=fn},async play(){this.paused=false;this.events.playing()},pause(){this.paused=true;this.events.pause()}};made.push(el);return el}
 const header={insertAdjacentElement(position,node){placement={position,node}}};
 vm.runInNewContext(code,{document:{documentElement:{lang},getElementById(){return null},querySelector(sel){assert.equal(sel,'.site-header');return header},createElement:element},localStorage:{getItem(){return 'false'},setItem(){}}});
 assert.equal(placement.position,'afterend');assert.equal(placement.node.id,'site-music');
 const button=made.find(x=>x.tag==='button');const audio=made.find(x=>x.tag==='audio');
 assert.equal(button.attrs['aria-pressed'],'false');button.events.click();await Promise.resolve();
 assert.equal(audio.paused,false);assert.equal(button.attrs['aria-pressed'],'true');
 button.events.click();assert.equal(audio.paused,true);assert.equal(button.attrs['aria-pressed'],'false');
});
test('mobile control has normal-flow positioning and readable summaries',()=>{
 const css=fs.readFileSync('site/music.css','utf8');
 assert.match(css,/@media\(max-width:760px\)\{\s*#site-music\{position:static/);
 assert.match(css,/#site-music button\{min-height:44px;min-width:44px\}/);
 assert.match(fs.readFileSync('site/style.css','utf8'),/\.page-home \.post-preview p\{font-size:16px;line-height:1\.75\}/);
});

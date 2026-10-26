(() => {
  const source = '/content/site.json';
  let language = 'en';
  let articleTitle = null;
  try { if (localStorage.getItem('lisg-language-choice') === 'zh') language = 'zh'; } catch {}
  const buttons = [...document.querySelectorAll('[data-language]')];
  function render() {
    document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
    if (articleTitle) document.title = articleTitle[language] + ' — 天秀之人 · TR';
    else if (document.body.dataset.titleEn) document.title = document.body.dataset[language === 'en' ? 'titleEn' : 'titleZh'];
    document.querySelectorAll('[data-en]').forEach(element => {
      if (element.dataset.markdown === 'true') renderInline(element, element.dataset[language]);
      else element.textContent = element.dataset[language];
    });
    document.querySelectorAll('[data-placeholder-en]').forEach(node => {node.placeholder = node.dataset[language === 'en' ? 'placeholderEn' : 'placeholderZh'];});
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.language === language)));
  }
  buttons.forEach(button => button.addEventListener('click', () => {
    language = button.dataset.language;
    try { localStorage.setItem('lisg-language-choice', language); } catch {}
    render();
  }));
  const record = value => value !== null && typeof value === 'object' && !Array.isArray(value);
  const bilingual = value => record(value) && typeof value.en === 'string' && typeof value.zh === 'string';
  function validBlock(block) {
    if (!record(block)) return false;
    if (!Object.prototype.hasOwnProperty.call(block, 'type')) return bilingual(block);
    if (block.type === 'divider') return true;
    if (block.type === 'table') return Array.isArray(block.headers) && block.headers.length > 0 && block.headers.every(bilingual) && Array.isArray(block.rows) && block.rows.every(row => Array.isArray(row) && row.length === block.headers.length && row.every(bilingual));
    if (block.type === 'list') return typeof block.ordered === 'boolean' && Array.isArray(block.items) && block.items.every(bilingual);
    if (!bilingual(block.text)) return false;
    if (block.type === 'heading') return [2, 3, 4].includes(block.level);
    if (block.type === 'code') return block.language === undefined || (typeof block.language === 'string' && /^[a-zA-Z0-9_+.-]{1,40}$/.test(block.language));
    return block.type === 'paragraph' || block.type === 'quote';
  }
  function validate(data) {
    if (!data || data.version !== 1 || !/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(data.contactEmail) || !data.pages || !Array.isArray(data.posts)) throw new Error('Invalid content format');
    for (const name of ['home', 'about', 'hello']) {
      if (!data.pages[name] || !Object.values(data.pages[name]).every(bilingual)) throw new Error('Invalid page content');
    }
    const ids = new Set();
    for (const post of data.posts) {
      if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(post.id) || ids.has(post.id) || !/^\d{4}-\d{2}-\d{2}$/.test(post.date) || ![post.title, post.summary, post.category].every(bilingual) || !Array.isArray(post.body) || !post.body.every(validBlock)) throw new Error('Invalid article');
      ids.add(post.id);
    }
    return data;
  }
  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (typeof text === 'string') node.textContent = text;
    else if (text) { node.dataset.en = text.en; node.dataset.zh = text.zh; }
    return node;
  }
  function renderInline(node, text) {
    // Only create known elements; article HTML is always rendered as text.
    const pattern = /(`[^`\n]+`|\*\*[^*\n]+\*\*|\*[^*\n]+\*|\[[^\]\n]+\]\(https?:\/\/[^\s)]+\)|https?:\/\/[^\s<>\u3000-\u303f]+)/g;
    const matches = [...text.matchAll(pattern)];
    if (!matches.length) { node.textContent = text; return; }
    node.replaceChildren();
    let cursor = 0;
    for (const match of matches) {
      if (match.index > cursor) node.append(document.createTextNode(text.slice(cursor, match.index)));
      const token = match[0];
      let child;
      if (token.startsWith('`')) child = element('code', '', token.slice(1, -1));
      else if (token.startsWith('**')) child = element('strong', '', token.slice(2, -2));
      else if (token.startsWith('*')) child = element('em', '', token.slice(1, -1));
      else {
        const link = token.match(/^\[([^\]]+)\]\((.+)\)$/);
        child = element('a', '', link ? link[1] : token);
        child.href = link ? link[2] : token;
        child.rel = 'noopener noreferrer';
      }
      node.append(child);
      cursor = match.index + token.length;
    }
    if (cursor < text.length) node.append(document.createTextNode(text.slice(cursor)));
  }
  function markdownElement(tag, text) {
    const node = element(tag, '', text);
    node.dataset.markdown = 'true';
    return node;
  }
  function renderBlock(block) {
    if (!Object.prototype.hasOwnProperty.call(block, 'type')) return element('p', '', block);
    if (block.type === 'list') {
      const list = element(block.ordered ? 'ol' : 'ul');
      block.items.forEach(item => list.append(markdownElement('li', item)));
      return list;
    }
    if (block.type === 'divider') return element('hr');
    if (block.type === 'table') {
      const wrapper = element('div', 'article-table');
      wrapper.setAttribute('tabindex', '0');
      wrapper.setAttribute('role', 'region');
      wrapper.setAttribute('aria-label', 'Data table / 数据表格');
      const table = element('table');
      const head = element('thead');
      const headings = element('tr');
      block.headers.forEach(value => {
        const cell = markdownElement('th', value);
        cell.setAttribute('scope', 'col');
        headings.append(cell);
      });
      head.append(headings);
      const body = element('tbody');
      block.rows.forEach(row => {
        const tr = element('tr');
        row.forEach(value => tr.append(markdownElement('td', value)));
        body.append(tr);
      });
      table.append(head, body);
      wrapper.append(table);
      return wrapper;
    }
    if (block.type === 'code') {
      const pre = element('pre');
      const code = element('code', '', block.text);
      if (block.language) code.dataset.language = block.language;
      pre.append(code);
      return pre;
    }
    const tag = block.type === 'heading' ? 'h' + block.level : block.type === 'quote' ? 'blockquote' : 'p';
    return markdownElement(tag, block.text);
  }
  const topics = [
    {id:'ai', title:{en:'AI & LLM Security',zh:'AI 与大模型'}, description:{en:'Models, reasoning states & infrastructure.',zh:'模型、推理状态与基础设施。'}},
    {id:'agents', title:{en:'Agents & RAG',zh:'Agent 与 RAG'}, description:{en:'Tools, retrieval & trust between agents.',zh:'工具调用、检索与智能体间的信任。'}},
    {id:'cloud', title:{en:'Cloud & Hybrid',zh:'云与混合云'}, description:{en:'AWS, Azure, GCP & connected environments.',zh:'AWS、Azure、GCP 与跨环境安全。'}},
    {id:'identity', title:{en:'Identity & Red Team',zh:'身份与红队'}, description:{en:'Active Directory, identity & lateral movement.',zh:'Active Directory、身份与横向移动。'}},
    {id:'notes', title:{en:'Study Notes',zh:'学习笔记'}, description:{en:'Methods, reflections & notes along the way.',zh:'方法、思考与学习过程中的记录。'}}
  ];
  let libraryData = null;
  const initialParams = new URLSearchParams(location.search);
  let selectedTopic = initialParams.get('topic') || 'all';
  let searchQuery = initialParams.get('q') || '';
  let sortOrder = initialParams.get('sort') === 'oldest' ? 'oldest' : 'newest';
  if (!topics.some(t => t.id === selectedTopic)) selectedTopic = 'all';
  const topicFor = post => {
    if (topics.some(t => t.id === post.topic)) return topics.find(t => t.id === post.topic);
    const label = post.category.en + ' ' + post.category.zh;
    const id = /agent|rag|智能体|检索/i.test(label) ? 'agents' : /cloud|aws|azure|gcp|云/i.test(label) ? 'cloud' : /identity|active directory|red team|身份|红队|域控/i.test(label) ? 'identity' : /\bai\b|llm|模型/i.test(label) ? 'ai' : 'notes';
    return topics.find(t => t.id === id);
  };
  function readingTime(post) {
    const values = {en:[],zh:[]};
    function collect(item) {
      if (bilingual(item)) {values.en.push(item.en); values.zh.push(item.zh);}
      else if (Array.isArray(item)) item.forEach(collect);
      else if (record(item)) Object.values(item).forEach(collect);
    }
    collect(post.body);
    const count = lang => Math.max(1, Math.ceil((values[lang].join(' ').match(/[\u3400-\u9fff]|[A-Za-z0-9_]+/g) || []).length / (lang === 'zh' ? 350 : 220)));
    return {en:count('en')+' min read',zh:'约 '+count('zh')+' 分钟'};
  }
  function setText(node, value) {
    if (!node) return;
    node.dataset.en=value.en; node.dataset.zh=value.zh;
  }
  function setFilterURL() {
    if (typeof history === 'undefined' || !history.replaceState) return;
    const p=new URLSearchParams();
    if(selectedTopic!=='all')p.set('topic',selectedTopic);
    if(searchQuery)p.set('q',searchQuery);
    if(sortOrder==='oldest')p.set('sort','oldest');
    history.replaceState(null,'',location.pathname+(p.toString()?'?'+p.toString():''));
  }
  function updateCatalog() {
    if(!libraryData)return;
    const list=document.getElementById('github-posts');
    if(!list)return;
    const query=searchQuery.trim().toLocaleLowerCase();
    function searchable(post){
      const values=[];
      function visit(x){if(bilingual(x)){values.push(x.en,x.zh);}else if(Array.isArray(x))x.forEach(visit);else if(record(x))Object.values(x).forEach(visit);}
      visit([post.title,post.summary,post.category,post.body,topicFor(post).title]);return values.join(' ').toLocaleLowerCase();
    }
    const posts=libraryData.posts.filter(post => (selectedTopic==='all'||topicFor(post).id===selectedTopic) && (!query||searchable(post).includes(query))).sort((a,b)=>(sortOrder==='oldest'?1:-1)*(a.date.localeCompare(b.date)||a.id.localeCompare(b.id)));
    list.replaceChildren();
    for(const post of posts){
      const card=element('article','post-preview');
      const meta=element('div','post-meta');
      const topic=element('a','topic-pill',topicFor(post).title);topic.href='/?topic='+topicFor(post).id;
      const date=element('time','',post.date);date.dateTime=post.date;
      meta.append(topic,date,element('span','',readingTime(post)));
      const title=element('h2');const titleLink=element('a','',post.title);titleLink.href='/post.html?id='+post.id;title.append(titleLink);
      const link=element('a','read-link',{en:'Continue reading →',zh:'继续阅读 →'});link.href='/post.html?id='+post.id;
      card.append(meta,title,element('p','',post.summary),link);list.append(card);
    }
    const active=topics.find(t=>t.id===selectedTopic);
    setText(document.getElementById('writing-heading'),active?active.title:{en:'All notes',zh:'全部文章'});
    setText(document.getElementById('catalog-description'),active?active.description:(sortOrder==='oldest'?{en:'Oldest entries first.',zh:'从最早的文章开始。'}:{en:'Newest entries first.',zh:'从最近的文章开始。'}));
    setText(document.getElementById('article-count'),{en:posts.length+' '+(posts.length===1?'note':'notes'),zh:posts.length+' 篇'});
    const empty=document.getElementById('empty-results');if(empty)empty.hidden=posts.length>0;
    const clear=document.getElementById('clear-search');if(clear)clear.hidden=!searchQuery;
    document.querySelectorAll('[data-topic]').forEach(a=>{
      if(a.dataset.topic===selectedTopic)a.setAttribute('aria-current','page');
      else a.removeAttribute('aria-current');
    });
    render();
  }
  function setupLibrary(data) {
    libraryData=data;
    const total=document.getElementById('total-notes');setText(total,{en:data.posts.length+' entries',zh:data.posts.length+' 篇'});
    document.querySelectorAll('[data-topic]').forEach(a=>{
      const count=a.dataset.topic==='all'?data.posts.length:data.posts.filter(p=>topicFor(p).id===a.dataset.topic).length;
      a.append(element('span','topic-count',String(count)));
      a.addEventListener('click',event=>{
        if(event.metaKey||event.ctrlKey||event.shiftKey||event.altKey||event.button>0)return;
        event.preventDefault();selectedTopic=a.dataset.topic;setFilterURL();updateCatalog();
      });
    });
    const input=document.getElementById('article-search');if(input){input.value=searchQuery;input.addEventListener('input',()=>{searchQuery=input.value;setFilterURL();updateCatalog();});}
    const sort=document.getElementById('article-sort');if(sort){sort.value=sortOrder;sort.addEventListener('change',()=>{sortOrder=sort.value;setFilterURL();updateCatalog();});}
    const clear=document.getElementById('clear-search');if(clear)clear.addEventListener('click',()=>{searchQuery='';if(input){input.value='';input.focus();}setFilterURL();updateCatalog();});
    const reset=document.getElementById('reset-filters');if(reset)reset.addEventListener('click',()=>{searchQuery='';selectedTopic='all';if(input)input.value='';setFilterURL();updateCatalog();});
    const directory=document.getElementById('topic-directory');
    if(directory){directory.replaceChildren();topics.forEach((t,index)=>{
      const posts=data.posts.filter(p=>topicFor(p).id===t.id).sort((a,b)=>b.date.localeCompare(a.date));
      const card=element('section','directory-card');card.id=t.id;
      const meta=element('div','directory-meta');meta.append(element('span','',String(index+1).padStart(2,'0')),element('span','',{en:posts.length+' '+(posts.length===1?'note':'notes'),zh:posts.length+' 篇'}));
      card.append(meta,element('h2','',t.title),element('p','',t.description));
      if(posts.length){const list=element('ul','directory-links');posts.forEach(p=>{const li=element('li');const a=element('a','',p.title);a.href='/post.html?id='+p.id;li.append(a);list.append(li);});card.append(list);}
      else card.append(element('p','directory-empty',{en:'No entries yet.',zh:'暂无文章。'}));
      const link=element('a','directory-link',{en:'View notes →',zh:'查看文章 →'});link.href='/?topic='+t.id;card.append(link);directory.append(card);
    });}
    updateCatalog();
  }
  function apply(data) {
    const page = data.pages[document.body.dataset.contentPage] || {};
    document.querySelectorAll('[data-content-key]').forEach(node => {
      const value = page[node.dataset.contentKey];
      if (value) { node.dataset.en = value.en; node.dataset.zh = value.zh; }
    });
    document.querySelectorAll('a[href^="mailto:"]').forEach(node => {
      node.href = 'mailto:' + data.contactEmail;
      if (!node.hasAttribute('data-en')) node.textContent = data.contactEmail + ' ↗';
    });
    setupLibrary(data);
    const article = document.getElementById('github-article');
    if (article) {
      article.replaceChildren();
      const post = data.posts.find(post => post.id === new URLSearchParams(location.search).get('id'));
      const header = element('header', 'article-header');
      if (post) {
        const meta=element('div','post-meta');meta.append(element('time','',post.date),element('span','',readingTime(post)),element('span','',{en:'By LISG',zh:'作者 LISG'}));
        header.append(meta, element('h1', '', post.title), element('p', 'article-deck', post.summary));
        setText(document.getElementById('article-topic'),topicFor(post).title);
        const body = element('div', 'article-body');
        const toc=document.getElementById('article-toc');if(toc)toc.replaceChildren();
        let headingIndex=0;
        post.body.forEach(block => {
          const node=renderBlock(block);
          if(block.type==='heading'){
            node.id='section-'+(++headingIndex);
            if(toc){const a=element('a',block.level>2?'toc-sub':'',block.text);a.href='#'+node.id;toc.append(a);}
          }
          body.append(node);
        });
        if(toc&&!headingIndex)toc.append(element('p','',{en:'This note has no sections.',zh:'这篇笔记暂无章节。'}));
        article.append(header, body);
        articleTitle = post.title;
      } else {
        header.append(element('h1', '', {en:'Article unavailable', zh:'暂时无法读取这篇文章'}), element('p', '', {en:'Return to the library or try refreshing later.', zh:'请返回知识库，或稍后刷新重试。'}));
        article.append(header);
      }
    }
    render();
  }
  async function read(url) {
    const response = await fetch(url, {cache:'no-store', headers: {Accept: 'application/vnd.github.raw+json'}, signal:AbortSignal.timeout(8000)});
    if (!response.ok) throw new Error('Content request failed');
    const text = await response.text();
    if (text.length > 1000000) throw new Error('Content too large');
    return validate(JSON.parse(text));
  }
  document.querySelectorAll('[data-nav]').forEach(a=>{if(a.dataset.nav===document.body.dataset.contentPage)a.setAttribute('aria-current','page');});
  render();
  (async () => {
    try {
      const data = await read(source);
      apply(data);
      document.documentElement.dataset.contentSource = 'site';
    } catch {
      try {
        apply(await read('/content/site.json'));
        document.documentElement.dataset.contentSource = 'fallback';
      } catch {
        const article = document.getElementById('github-article');
        const list=document.getElementById('github-posts')||document.getElementById('topic-directory');
        if(list)list.replaceChildren(element('p','empty-state',{en:'Notes could not be loaded. Please refresh to try again.',zh:'文章暂时无法加载，请刷新后重试。'}));
        if (article) { article.replaceChildren(element('p', '', {en:'Content unavailable. Please try again later.', zh:'暂时无法读取内容，请稍后重试。'})); render(); }
      }
    }
  })();
})();

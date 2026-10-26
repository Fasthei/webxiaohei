(() => {
  const source = '/content/site.json';
  let language = 'en';
  let articleTitle = null;
  try { if (localStorage.getItem('lisg-language-choice') === 'zh') language = 'zh'; } catch {}
  const buttons = [...document.querySelectorAll('[data-language]')];
  function render() {
    document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
    if (articleTitle) document.title = articleTitle[language] + ' — LISG';
    document.querySelectorAll('[data-en]').forEach(element => {
      if (element.dataset.markdown === 'true') renderInline(element, element.dataset[language]);
      else element.textContent = element.dataset[language];
    });
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
    const list = document.getElementById('github-posts');
    if (list) {
      list.replaceChildren();
      for (const post of [...data.posts].sort((a, b) => b.date.localeCompare(a.date))) {
        const card = element('article', 'post-preview');
        const meta = element('div', 'post-meta');
        const date = element('time', '', post.date); date.dateTime = post.date;
        meta.append(date, element('span', '', '·'), element('span', '', post.category));
        const link = element('a', 'read-link', {en:'Read the article →', zh:'阅读全文 →'});
        link.href = '/post.html?id=' + encodeURIComponent(post.id);
        card.append(meta, element('h2', '', post.title), element('p', '', post.summary), link);
        list.append(card);
      }
      const hasIntroduction = data.posts.some(post => post.id === 'hello-lisg');
      document.querySelectorAll('.post-preview').forEach(card => {
        if (!list.contains(card)) card.hidden = hasIntroduction;
      });
      const entryCount = data.posts.length + (hasIntroduction ? 0 : 1);
      const count = document.querySelector('#writing-heading + span');
      if (count) { count.dataset.en = `${entryCount} ${entryCount === 1 ? 'entry' : 'entries'}`; count.dataset.zh = `${entryCount} 篇`; }
      const upcoming = document.querySelector('.upcoming');
      if (upcoming) upcoming.hidden = data.posts.length > 0;
    }
    const article = document.getElementById('github-article');
    if (article) {
      article.replaceChildren();
      const post = data.posts.find(post => post.id === new URLSearchParams(location.search).get('id'));
      const header = element('header', 'article-header');
      if (post) {
        header.append(element('p', 'post-meta', post.date), element('h1', '', post.title), element('p', 'article-deck', post.summary));
        const body = element('div', 'article-body');
        post.body.forEach(block => body.append(renderBlock(block)));
        article.append(header, body);
        articleTitle = post.title;
      } else {
        header.append(element('h1', '', {en:'Article unavailable', zh:'暂时无法读取这篇文章'}), element('p', '', {en:'Return to the notebook or try refreshing later.', zh:'请返回笔记首页，或稍后刷新重试。'}));
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
        if (article) { article.replaceChildren(element('p', '', {en:'Content unavailable. Please try again later.', zh:'暂时无法读取内容，请稍后重试。'})); render(); }
      }
    }
  })();
})();

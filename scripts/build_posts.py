#!/usr/bin/env python3
"""Build website article data from Markdown using only Python's standard library."""
import datetime
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def bilingual(text):
    return {'en': text, 'zh': text}

def blocks(markdown):
    result, paragraph, index = [], [], 0
    lines = markdown.splitlines()
    def flush():
        if paragraph:
            result.append({'type': 'paragraph', 'text': bilingual(' '.join(paragraph))})
            paragraph.clear()
    while index < len(lines):
        line = lines[index]
        fence = re.match(r'^\s*(`{3,}|~{3,})(.*)$', line)
        heading = re.match(r'^(#{1,6})\s+(.+)$', line)
        bullet = re.match(r'^\s*(?:([-+*])|\d+[.)])\s+(.+)$', line)
        if fence:
            flush()
            marker, language = fence.groups()
            code = []
            index += 1
            while index < len(lines) and not re.fullmatch(r'\s*' + re.escape(marker[0]) + '{' + str(len(marker)) + r',}\s*', lines[index]):
                code.append(lines[index]); index += 1
            if index == len(lines):
                raise ValueError('代码块缺少结束标记')
            block = {'type': 'code', 'text': bilingual('\n'.join(code))}
            language = language.strip()
            if language:
                if not re.fullmatch(r'[A-Za-z0-9_+.\-]{1,40}', language): raise ValueError('代码语言标记格式错误')
                block['language'] = language
            result.append(block)
        elif heading:
            flush()
            result.append({'type': 'heading', 'level': min(4, max(2, len(heading[1]))), 'text': bilingual(heading[2])})
        elif line.startswith('> '):
            flush()
            result.append({'type': 'quote', 'text': bilingual(line[2:])})
        elif bullet:
            flush()
            ordered = bullet[1] is None
            if result and result[-1]['type'] == 'list' and result[-1]['ordered'] == ordered:
                result[-1]['items'].append(bilingual(bullet[2]))
            else:
                result.append({'type': 'list', 'ordered': ordered, 'items': [bilingual(bullet[2])]})
        elif not line.strip():
            flush()
        else:
            paragraph.append(line)
        index += 1
    flush()
    return result

def parse(path, root=ROOT):
    text = path.read_text(encoding='utf-8-sig')
    meta = {}
    if text.startswith('---\n'):
        split = text.split('\n---', 1)
        if len(split) != 2:
            raise ValueError(f'{path.name}: 文件头缺少结束 ---')
        for line in split[0][4:].splitlines():
            if not line.strip() or line.lstrip().startswith('#'): continue
            key, sep, value = line.partition(':')
            if not sep: raise ValueError(f'{path.name}: 文件头必须使用 key: value')
            value = value.strip()
            if value.startswith('"') and value.endswith('"'): value = json.loads(value)
            elif value.startswith("'") and value.endswith("'"): value = value[1:-1].replace("''", "'")
            meta[key.strip()] = value
        text = split[1].lstrip('\r\n')
    if meta.get('draft', 'false').lower() == 'true': return None
    heading = re.search(r'^#\s+(.+)$', text, re.M)
    title = meta.get('title') or (heading[1] if heading else path.stem)
    if heading: text = text[:heading.start()] + text[heading.end():]
    relative = path.relative_to(root / 'posts').as_posix()
    default_id = re.sub(r'[^a-z0-9]+', '-', path.stem.lower()).strip('-')
    if not default_id: default_id = 'post-' + hashlib.sha256(relative.encode()).hexdigest()[:12]
    post_id = meta.get('slug', default_id)
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', post_id): raise ValueError(f'{path.name}: slug 格式错误')
    date = meta.get('date')
    if not date:
        filename_date = re.match(r'^(\d{4}-\d{2}-\d{2})', path.name)
        if filename_date: date = filename_date[1]
        else:
            dates = subprocess.check_output(['git', '-C', str(root), 'log', '--follow', '--format=%cs', '--', str(path.relative_to(root))], text=True).splitlines()
            if not dates: raise ValueError(f'{path.name}: 未提交的文章请填写 date: YYYY-MM-DD')
            date = dates[-1]
    datetime.date.fromisoformat(date)
    body = blocks(text)
    summary = meta.get('summary') or next((item['text']['zh'][:160] for item in body if item['type'] == 'paragraph'), title)
    return {'id': post_id, 'date': date, 'title': bilingual(title), 'summary': bilingual(summary), 'category': bilingual(meta.get('category', '研究笔记')), 'body': body, 'sourcePath': 'posts/' + relative}

def build(root=ROOT):
    content_path = root / 'content/site.json'
    content = json.loads(content_path.read_text())
    posts, seen = [], set()
    for path in sorted((root / 'posts').rglob('*.md')):
        post = parse(path, root)
        if post is None: continue
        if post['id'] in seen: raise ValueError(f"文章 slug 重复: {post['id']}")
        seen.add(post['id']); posts.append(post)
    content['posts'] = sorted(posts, key=lambda p: (p['date'], p['id']), reverse=True)
    output = json.dumps(content, ensure_ascii=False, indent=2) + '\n'
    if len(output.encode()) > 950000: raise ValueError('内容超过 950 KB，请拆分或归档文章')
    content_path.write_text(output)
    print(f'Generated {len(posts)} published articles')

if __name__ == '__main__': build()

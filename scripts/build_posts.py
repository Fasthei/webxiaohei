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
    def cells(line):
        return [cell.strip().replace(r'\|', '|') for cell in re.split(r'(?<!\\)\|', line.strip().strip('|'))]
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
        elif line.strip().startswith('|') and index + 1 < len(lines) and all(re.fullmatch(r':?-{3,}:?', cell) for cell in cells(lines[index + 1])):
            flush()
            headers = cells(line)
            rows = []
            index += 2
            while index < len(lines) and lines[index].strip().startswith('|'):
                row = cells(lines[index])
                if len(row) != len(headers): raise ValueError('表格列数不一致')
                rows.append([bilingual(cell) for cell in row])
                index += 1
            result.append({'type': 'table', 'headers': [bilingual(cell) for cell in headers], 'rows': rows})
            index -= 1
        elif re.fullmatch(r'\s*(?:-{3,}|\*{3,}|_{3,})\s*', line):
            flush()
            result.append({'type': 'divider'})
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
    topic = meta.get('topic')
    if topic and topic not in {'ai', 'agents', 'cloud', 'identity', 'notes'}:
        raise ValueError(f'{path.name}: topic 必须是 ai / agents / cloud / identity / notes')
    post = {'id': post_id, 'date': date, 'title': bilingual(title), 'summary': bilingual(summary), 'category': bilingual(meta.get('category', '研究笔记')), 'body': body, 'sourcePath': 'posts/' + relative}
    if topic: post['topic'] = topic
    return post

def merge_translation(original, translated, path='article'):
    """Merge aligned English Markdown without changing the Chinese article."""
    if isinstance(original, dict):
        if not isinstance(translated, dict) or original.keys() != translated.keys():
            raise ValueError(f'{path}: translation structure differs')
        if set(original) == {'en', 'zh'}:
            return {'zh': original['zh'], 'en': translated['en']}
        return {key: merge_translation(value, translated[key], f'{path}/{key}')
                for key, value in original.items()}
    if isinstance(original, list):
        if not isinstance(translated, list) or len(original) != len(translated):
            raise ValueError(f'{path}: translation block count differs')
        return [merge_translation(a, b, f'{path}/{i}')
                for i, (a, b) in enumerate(zip(original, translated))]
    if original != translated:
        raise ValueError(f'{path}: translation structure differs')
    return original

def build(root=ROOT):
    content_path = root / 'content/site.json'
    content = json.loads(content_path.read_text())
    posts, seen = [], set()
    for path in sorted((root / 'posts').rglob('*.md')):
        if path.name.endswith('.en.md'): continue
        post = parse(path, root)
        if post is None: continue
        translation_path = path.with_suffix('.en.md')
        if translation_path.exists():
            translated = parse(translation_path, root)
            if translated is None: raise ValueError(f'{translation_path.name}: translation cannot be a draft')
            for field in ('title', 'summary', 'category', 'body'):
                post[field] = merge_translation(post[field], translated[field], field)
        if post['id'] in seen: raise ValueError(f"文章 slug 重复: {post['id']}")
        seen.add(post['id']); posts.append(post)
    content['posts'] = sorted(posts, key=lambda p: (p['date'], p['id']), reverse=True)
    output = json.dumps(content, ensure_ascii=False, indent=2) + '\n'
    if len(output.encode()) > 950000: raise ValueError('内容超过 950 KB，请拆分或归档文章')
    content_path.write_text(output)
    print(f'Generated {len(posts)} published articles')

if __name__ == '__main__': build()

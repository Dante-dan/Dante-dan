#!/usr/bin/env python3
"""Refresh bounded public-data sections; preserve each previous block on failure."""
import html
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
USER = 'Dante-dan'


def fetch(url):
    headers = {'User-Agent': 'Dante-profile', 'Accept': 'application/vnd.github+json'}
    if urllib.parse.urlparse(url).hostname == 'api.github.com':
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
                return response.read()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def clean(value, limit=140):
    text = ' '.join((value or '').split())
    text = text[:limit - 1] + '…' if len(text) > limit else text
    return html.escape(re.sub(r'([\\`*_[\]<>|])', r'\\\1', text))


def link(value):
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != 'https' or parsed.hostname not in {'github.com', 'dhpie.com'}:
        raise ValueError('Unexpected public link')
    return value.replace('(', '%28').replace(')', '%29')


def workbench():
    repos = json.loads(fetch(f'https://api.github.com/users/{USER}/repos?sort=pushed&per_page=100&type=owner'))
    repos = [r for r in repos if not r['fork'] and not r['archived'] and not r.get('private') and r['name'] != USER]
    rows = []
    for r in repos[:3]:
        detail = clean(r.get('description')) or ('Public ' + (r.get('language') or 'code') + ' project.')
        rows.append(f"- **[{clean(r['name'])}]({link(r['html_url'])})** — {detail}")
    return '\n'.join(rows)


def upstream():
    query = urllib.parse.quote(f'is:pr author:{USER} -user:{USER} is:public sort:updated-desc')
    prs = json.loads(fetch(f'https://api.github.com/search/issues?q={query}&per_page=5'))
    if prs.get('incomplete_results'):
        raise ValueError('Incomplete GitHub search')
    rows = []
    for p in prs['items']:
        repo = p['repository_url'].split('/repos/')[1]
        status = 'merged' if p['pull_request'].get('merged_at') else p['state']
        rows.append(f"- `{status}` **[{clean(repo)}#{p['number']}]({link(p['html_url'])})** — {clean(p['title'], 110)}")
    return '\n'.join(rows)


def notes():
    root = ET.fromstring(fetch('https://dhpie.com/feed'))
    rows, seen = [], set()
    for item in root.findall('.//item'):
        url = item.findtext('link', '')
        if url in seen:
            continue
        seen.add(url)
        rows.append(f"- [{clean(item.findtext('title'), 120)}]({link(url)})")
        if len(rows) == 4:
            break
    return '\n'.join(rows)


def replace_block(text, name, body):
    start, end = f'<!-- {name}:start -->', f'<!-- {name}:end -->'
    if text.count(start) != 1 or text.count(end) != 1 or text.index(start) >= text.index(end):
        raise ValueError(f'Invalid markers: {name}')
    if not body.strip():
        raise ValueError(f'Empty data: {name}')
    before, rest = text.split(start)
    _, after = rest.split(end)
    return before + start + '\n' + body + '\n' + end + after


def main():
    path = ROOT / 'README.md'
    text = path.read_text()
    failed = False
    for name, loader in [('workbench', workbench), ('upstream', upstream), ('notes', notes)]:
        try:
            text = replace_block(text, name, loader())
            print(f'Updated {name}')
        except Exception as error:
            failed = True
            print(f'::warning::{name}: keeping previous content ({type(error).__name__})')
    path.write_text(text)
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())

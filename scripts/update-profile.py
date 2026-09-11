#!/usr/bin/env python3
"""Refresh bounded public-data sections; preserve each previous block on failure."""
import html
from datetime import datetime, timedelta, timezone
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


def contributions():
    sys.path.insert(0, str(ROOT / "scripts"))
    from contributions import collect
    return collect(fetch, ROOT)


def upstream(now=None):
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=7)
    query = urllib.parse.quote(
        f'is:pr author:{USER} -user:{USER} is:public '
        f'updated:>={cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")} sort:updated-desc'
    )
    sources = json.loads((ROOT / 'scripts/contribution-sources.json').read_text())
    items, seen = [], set()
    for page in range(1, 11):
        result = json.loads(fetch(
            f'https://api.github.com/search/issues?q={query}&per_page=100&page={page}'
        ))
        if result.get('incomplete_results') or result['total_count'] > 1000:
            raise ValueError('Incomplete GitHub search')
        for pr in result['items']:
            if pr['html_url'] not in seen:
                seen.add(pr['html_url'])
                items.append(pr)
        if page * 100 >= result['total_count']:
            break
        if not result['items']:
            raise ValueError('Missing GitHub search page')
    rows, counts = [], {}
    for p in items:
        repo = p['repository_url'].split('/repos/')[1]
        status = 'merged' if p['pull_request'].get('merged_at') else p['state']
        if status == 'open' and p.get('draft'):
            status = 'draft'
        for entry in sources['integrated']:
            if repo == entry['repo'] and p['number'] == entry['source_pr'] and status == 'closed':
                integrated = json.loads(fetch(f"https://api.github.com/repos/{repo}/pulls/{entry['via_pr']}"))
                if integrated.get('merged_at'):
                    status = 'integrated'
        if status not in {'open', 'merged', 'integrated'}:
            continue
        counts[status] = counts.get(status, 0) + 1
        rows.append(f"| `{status}` | **[{clean(repo)}#{p['number']}]({link(p['html_url'])})** — {clean(p['title'], 110)} | {p['updated_at'][:10]} |")
    if not rows:
        return 'No public upstream PRs updated in the last 7 days.'
    totals = ' · '.join(f'{counts[state]} {state}' for state in
                        ('open', 'merged', 'integrated') if counts.get(state))
    return (f'<sub>{len(rows)} PRs · {totals}</sub>\n\n'
            '| Status | Pull request | Updated (UTC) |\n'
            '| :--- | :--- | :--- |\n' + '\n'.join(rows))


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


def activity():
    events = json.loads(fetch(f'https://api.github.com/users/{USER}/events/public?per_page=100'))
    rows, seen = [], set()
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    for event in events:
        if not event.get('public') or event.get('actor', {}).get('login', '').lower() != USER.lower():
            continue
        if datetime.fromisoformat(event['created_at'].replace('Z', '+00:00')) < cutoff:
            continue
        payload = event.get('payload', {})
        repo = event.get('repo', {}).get('name', '')
        kind = event.get('type')
        if kind == 'IssueCommentEvent':
            item, response, verb = payload.get('issue', {}), payload.get('comment', {}), 'Commented'
        elif kind == 'IssuesEvent':
            item, response, verb = payload.get('issue', {}), {}, payload.get('action', 'Updated').capitalize()
        elif kind in {'PullRequestReviewEvent', 'PullRequestReviewCommentEvent'}:
            item = payload.get('pull_request', {})
            response = payload.get('review', payload.get('comment', {}))
            verb = 'Reviewed' if kind == 'PullRequestReviewEvent' else 'Commented'
        else:
            continue
        number = item.get('number', payload.get('number'))
        url = response.get('html_url') or item.get('html_url')
        if not number or not url or (repo, number) in seen or repo.lower() == f'{USER}/{USER}'.lower():
            continue
        seen.add((repo, number))
        date = event['created_at'][:10]
        title = clean(item.get('title'), 100)
        suffix = f' — {title}' if title else ''
        rows.append(f'- `{date}` {verb} on **[{clean(repo)}#{number}]({link(url)})**{suffix}')
        if len(rows) == 4:
            break
    return '\n'.join(rows) or 'No public conversations in the last 30 days.'


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
    for name, loader in [('contributions', contributions), ('workbench', workbench), ('upstream', upstream), ('notes', notes), ('activity', activity)]:
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

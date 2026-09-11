"""Verified upstream contributions, with a rolling-year shelf and historical archive."""
import html
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

CODE = {'.js', '.ts', '.tsx', '.jsx', '.vue', '.svelte', '.py', '.rs', '.go', '.java', '.c', '.cpp', '.h', '.cs', '.rb', '.sh', '.swift', '.kt'}


def render(projects, now=None):
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=365)
    recent, older = [], []
    for p in sorted(projects, key=lambda p: p['accepted_at'], reverse=True):
        stamp = datetime.fromisoformat(p['accepted_at'].replace('Z', '+00:00'))
        (recent if stamp >= cutoff else older).append(p)

    def cards(items):
        rows = []
        for p in items:
            repo = html.escape(p['repo'], quote=True)
            name = html.escape(p.get('name', p['repo'].split('/')[-1]))
            icon = html.escape(p['icon'], quote=True)
            evidence = html.escape(p['evidence'], quote=True)
            history = 'https://github.com/' + repo + '/pulls?q=is%3Apr+author%3ADante-dan'
            rows.append(f'<table align="left" width="390"><tr><td width="64" valign="middle"><a href="https://github.com/{repo}"><img src="{icon}" width="56" height="56" alt="{name} icon" /></a></td><td width="300" valign="middle"><a href="https://github.com/{repo}"><strong>{name}</strong></a><br /><sub><a href="{evidence}">{p["status"]} contribution</a><br /><a href="{history}">all PRs ↗</a></sub></td></tr></table>')
        return '\n'.join(rows) + '\n<br clear="all" />'

    body = '<sub>Code accepted upstream · last 12 months</sub>\n\n'
    body += cards(recent) if recent else 'No accepted code contributions in the last 12 months.'
    if older:
        body += '\n\n<details>\n<summary>Earlier contributions</summary>\n\n' + cards(older) + '\n\n</details>'
    return body


def collect(fetch, root):
    def api(path):
        return json.loads(fetch('https://api.github.com/' + path))

    query = quote('is:pr author:Dante-dan -user:Dante-dan is:public is:merged sort:updated-desc')
    items = []
    page = 1
    while True:
        result = api(f'search/issues?q={query}&per_page=100&page={page}')
        if result.get('incomplete_results') or result['total_count'] > 1000:
            raise ValueError('Incomplete contribution inventory; preserve previous shelf')
        items.extend(result['items'])
        if len(items) >= result['total_count']:
            break
        if not result['items']:
            raise ValueError('Truncated contribution inventory')
        page += 1
    config = json.loads((root / 'scripts/contribution-sources.json').read_text())
    projects = {}
    for item in items:
        repo = item['repository_url'].split('/repos/')[1]
        pr = api(f'repos/{repo}/pulls/{item["number"]}')
        if not pr.get('merged_at') or pr['user']['login'] != 'Dante-dan':
            continue
        if repo in projects and projects[repo]['accepted_at'] >= pr['merged_at']:
            continue
        files = api(f'repos/{repo}/pulls/{item["number"]}/files?per_page=100')
        if not any(Path(f['filename']).suffix.lower() in CODE for f in files):
            if pr['changed_files'] > 100:
                raise ValueError('File coverage incomplete')
            continue
        projects[repo] = dict(repo=repo, accepted_at=pr['merged_at'], evidence=pr['html_url'], status='merged')
    for entry in config['integrated']:
        repo = entry['repo']
        pr = api(f'repos/{repo}/pulls/{entry["via_pr"]}')
        if not pr.get('merged_at'):
            raise ValueError('Integration PR no longer verified')
        for sha in entry['commits']:
            commit = api(f'repos/{repo}/commits/{sha}')
            compare = api(f'repos/{repo}/compare/{sha}...{pr["merge_commit_sha"]}')
            if (commit.get('author') or {}).get('login') != 'Dante-dan' or compare['merge_base_commit']['sha'] != sha:
                raise ValueError('Authorship or integration ancestry not verified')
        if repo not in projects or projects[repo]['accepted_at'] < pr['merged_at']:
            projects[repo] = dict(repo=repo, accepted_at=pr['merged_at'], evidence=f'https://github.com/{repo}/commit/{entry["commits"][0]}', status='integrated')
    assets = root / 'assets/projects'
    assets.mkdir(parents=True, exist_ok=True)
    for repo, p in projects.items():
        custom = config['logos'].get(repo, {})
        metadata = api(f'repos/{repo}')
        source = custom.get('url') or metadata['owner']['avatar_url']
        suffix = '.svg' if source.endswith('.svg') else '.png'
        relative = 'assets/projects/' + repo.replace('/', '--') + suffix
        destination = root / relative
        if not destination.exists():
            data = fetch(source)
            if not (data.startswith(b'\x89PNG') or b'<svg' in data[:1000] or data.startswith(b'\xff\xd8')):
                raise ValueError('Unexpected project image')
            destination.write_bytes(data)
        p['icon'] = relative
        p['name'] = custom.get('name', repo.split('/')[-1])
    return render(list(projects.values()))

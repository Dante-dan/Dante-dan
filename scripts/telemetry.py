"""Fetch recent public reactions and record successful card refreshes."""
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
GROUPS = {'stats': ['stats-dark.svg', 'stats-light.svg'],
          'time': ['time-dark.svg', 'time-light.svg'], 'reactions': ['reactions.svg']}
REACTIONS = [('THUMBS_UP', '👍'), ('THUMBS_DOWN', '👎'), ('LAUGH', '😄'),
             ('HEART', '❤️'), ('CONFUSED', '😕'), ('EYES', '👀'),
             ('ROCKET', '🚀'), ('HOORAY', '🎉')]
QUERY = '''query {
  user(login: "Dante-dan") {
    issueComments(last: 100) { nodes {
      createdAt isMinimized repository { isPrivate }
      reactionGroups { content users { totalCount } }
    } }
    issues(last: 50) { nodes {
      createdAt repository { isPrivate }
      reactionGroups { content users { totalCount } }
    } }
  }
}'''


def reaction_counts(response, now):
    # GraphQL can return HTTP 200 with partial data and errors. Never publish it.
    if response.get('errors'):
        raise ValueError('GitHub GraphQL returned errors; retaining the previous card')
    user = response['data']['user']
    cutoff = now - timedelta(days=90)
    counts, sampled = Counter(), 0
    for kind in ('issueComments', 'issues'):
        for node in user[kind]['nodes']:
            created = datetime.fromisoformat(node['createdAt'].replace('Z', '+00:00'))
            if node['repository']['isPrivate'] or node.get('isMinimized') or not cutoff <= created <= now:
                continue
            sampled += 1
            for group in node['reactionGroups']:
                counts[group['content']] += group['users']['totalCount']
    return counts, sampled


def render_reactions(counts, sampled):
    cells = []
    for index, (name, emoji) in enumerate(REACTIONS):
        x = 34 + index * 76
        cells.append(f'<text x="{x}" y="102" font-size="23">{emoji}</text>'
                     f'<text x="{x + 12}" y="133" text-anchor="middle" '
                     f'font-size="17">{counts[name]}</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="650" height="168" viewBox="0 0 650 168" role="img" aria-labelledby="title desc">
<title id="title">Recent public reactions</title>
<desc id="desc">{sum(counts.values())} reactions on {sampled} sampled public comments and issue bodies created in the last 90 days.</desc>
<style>
text {{ font-family: 'Segoe UI', Ubuntu, sans-serif; fill: #24292f; }}
.bg {{ fill: #ffffff; }} .heading {{ fill: #0969da; }} .muted {{ fill: #57606a; }}
@media (prefers-color-scheme: dark) {{ text {{ fill: #c9d1d9; }} .bg {{ fill: #0d1117; }} .heading {{ fill: #58a6ff; }} .muted {{ fill: #8b949e; }} }}
</style>
<rect class="bg" width="650" height="168" rx="6"/>
<text class="heading" x="25" y="32" font-size="18" font-weight="600">Recent public reactions · {sum(counts.values())}</text>
<text class="muted" x="25" y="56" font-size="12">Last 90 days · {sampled} sampled comments / issue bodies</text>
{''.join(cells)}
<text class="muted" x="25" y="157" font-size="10">Sample: latest 100 issue comments + 50 issues · excludes private / minimized content</text>
</svg>'''


def refresh_reactions(root=ROOT):
    request = urllib.request.Request('https://api.github.com/graphql',
        data=json.dumps({'query': QUERY}).encode(), headers={
            'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
            'User-Agent': 'Dante-profile', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=45) as response:
        counts, sampled = reaction_counts(json.load(response), datetime.now(timezone.utc))
    svg = render_reactions(counts, sampled)
    ET.fromstring(svg)
    (root / 'assets/reactions.svg').write_text(svg)
    print(f'Refreshed reactions: {sum(counts.values())} on {sampled} public items')


def finalize(successful, root=ROOT, now=None):
    now = now or datetime.now(timezone.utc)
    path = root / 'assets/telemetry-refresh.json'
    state = json.loads(path.read_text()) if path.exists() else {}
    readme = (root / 'README.md').read_text()
    for group, files in GROUPS.items():
        if group in successful:
            for filename in files:
                svg = ET.fromstring((root / 'assets' / filename).read_text())
                if svg.tag != '{http://www.w3.org/2000/svg}svg':
                    raise ValueError(f'Invalid SVG: {filename}')
            state[group] = {'last_success_at': now.strftime('%Y-%m-%dT%H:%M:%SZ')}
        for filename in files:
            digest = hashlib.sha256((root / 'assets' / filename).read_bytes()).hexdigest()[:16]
            # A changed card gets a new image URL instead of reusing a cached URL.
            readme = re.sub(r'(assets/' + re.escape(filename) + r')(?:\?v=[a-f0-9]+)?(?=")',
                            lambda match: match[1] + '?v=' + digest, readme)
    labels = {'stats': 'Totals', 'time': 'Commit hours', 'reactions': 'Reactions'}
    stamps = [f'{labels[group]}: {state[group]["last_success_at"].replace("T", " ").replace("Z", " UTC")}'
              if group in state else f'{labels[group]}: refresh pending' for group in GROUPS]
    block = '<!-- telemetry-refresh:start -->\n<sub>Fetched every 8 hours · last successful fetch<br>' + ' · '.join(stamps) + '</sub>\n<!-- telemetry-refresh:end -->'
    if '<!-- telemetry-refresh:start -->' in readme:
        readme = re.sub(r'<!-- telemetry-refresh:start -->.*?<!-- telemetry-refresh:end -->',
                        lambda _: block, readme, flags=re.S)
    else:
        readme = readme.replace('### `~/arcade`', block + '\n\n### `~/arcade`')
    path.write_text(json.dumps(state, indent=2) + '\n')
    (root / 'README.md').write_text(readme)


if __name__ == '__main__':
    if sys.argv[1] == 'reactions':
        refresh_reactions()
    elif sys.argv[1] == 'finalize':
        finalize([name for name in GROUPS if os.environ.get(name.upper() + '_OK') == 'true'])
    else:
        raise SystemExit('Expected reactions or finalize')

# Profile automation

Daily at 06:23 Asia/Singapore (`22:23 UTC`), or manually from **Actions → Refresh profile**.
Bomberman updates at 06:43 via `bomberman.yml`. GitHub schedules may run late; inactive repositories may have
scheduled workflows disabled by GitHub after 60 days.

- `workbench`: three most recently pushed public, owned, non-archived repositories; excludes forks and this profile. Descriptions come from repository metadata.
- `upstream`: five most recently updated public PRs authored by Dante-dan in other accounts. Shows open, closed or merged status.
- `activity`: four distinct public issue/comment/review conversations from the latest 100 public events, within 30 days. Links directly to comments when available. PR-open/push events are omitted to avoid repeating the PR list. This is a bounded activity sample, not a complete audit trail.
- `notes`: four latest unique entries from https://dhpie.com/feed, including posts and short notes, in feed order.

Text updates only replace marked blocks. An unavailable source retains its prior block;
other sources still update and the workflow reports a failure. Empty projects/posts/PR
responses also preserve previous content. Only public data is requested.

## Visual sources

| Generator | Displayed information |
| --- | --- |
| [GitHub Readme Stats Action](https://github.com/stats-organization/github-readme-stats-action) | Contribution totals; no rank or second language chart |
| [GitHub Profile Summary Cards](https://github.com/vn7n24fzkq/github-profile-summary-cards) | Commit time distribution, UTC+8; other generated cards are discarded |
| [lowlighter/metrics](https://github.com/lowlighter/metrics) | Reactions on recent comments |
| [Arcade Contribution Graph](https://github.com/abozanona/pacman-contribution-graph) | Bomberman contribution animation, always visible with light/dark variants |

SVGs are committed to `assets/`; Bomberman lives on `output`. Light/dark variants follow
GitHub's color scheme. `style-cards.py` aligns Summary Cards typography/colors without
changing its data. The repository-scoped built-in token restricts Metrics' GraphQL repository dataset
in practice; its language card only counted this profile repository. That misleading
card is intentionally omitted. Overall contribution totals and reactions were verified
separately. A future language card needs independently verified public-repository data.
Reactions cover a bounded sample of comments and issue/PR bodies from 90 days, not lifetime totals.

The Metrics recent-activity plugin currently crashes on reduced GitHub event payloads
(`pull_request.user` missing, even with PR events filtered out). The native Markdown
activity section handles missing fields and avoids that dependency.

All workflows use the repository's built-in `GITHUB_TOKEN`; no PAT or service keys are
needed. Third-party actions are pinned to commit SHAs (Metrics additionally uses its
upstream prebuilt image). Stats fetch errors and Metrics plugin errors fail rather than
publishing error cards. Scheduled updates do not recursively trigger themselves.

Run locally: `GH_TOKEN="$(gh auth token)" python3 scripts/update-profile.py`.
Validate: `python3 -m unittest discover -s scripts -p 'test_*.py'`.

## Accepted contribution shelf

The existing daily Action now refreshes `contributions`. Wrapping fixed-width project cards (three, two or one per row as space allows)
sit above the latest PR feed, following the restrained linked typography of
[antfu](https://github.com/antfu/antfu) and generated sections of
[simonw](https://github.com/simonw/simonw). Each project links to its repository,
accepted contribution evidence, and the author's PR history.

The shelf shows projects whose latest accepted code PR is within a rolling 365 days.
Older projects remain in **Earlier contributions**, a collapsed archive. A new accepted
contribution moves a project back to the visible shelf. Public merged PRs to other
accounts are discovered on every refresh; documentation-only changes are omitted
using changed-file source extensions. Tests count as code. This is a PR-based code
contribution showcase, not an exhaustive commit inventory (direct pushes and unknown
cherry-picks are not inferred). Search pagination/incomplete results and upstream
failures preserve the previous shelf and fail the feed step honestly.

`scripts/contribution-sources.json` holds logo overrides and verified integrations
whose original PR was closed instead of merged. ECC #3044 is linked to actual
Dante-authored commits integrated through #3071; each refresh verifies attribution
and ancestry. Its latest-PR label is `integrated`. Future such cases need an explicit
source/commit mapping rather than guessing from comments. Conventional merged PRs
are automatic. Logos are stored in `assets/projects`; official project assets are
preferred, otherwise the repository owner's GitHub avatar is used. The JSON records
custom image sources, while fallback avatars come from the GitHub repository API.

Cards use independent left-aligned tables and a clear break, preserving real links
within GitHub sanitization. Icon and text cells both use vertical middle alignment.
Verified on the live profile at desktop width and a 390px viewport.

Each card targets 270px and preserves independently clickable project and contribution
links. Cards wrap naturally rather than stretching to fill every row.

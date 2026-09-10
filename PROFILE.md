# Profile automation

Daily at 06:23 Asia/Singapore (`22:23 UTC`), or manually from **Actions → Refresh profile**.
The snake updates at 06:43. GitHub schedules may run late; inactive repositories may have
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
| [lowlighter/metrics](https://github.com/lowlighter/metrics) | Public repository language mix and reactions on recent comments |
| [Platane/snk](https://github.com/Platane/snk) | Optional contribution animation inside a disclosure |

SVGs are committed to `assets/`; the snake lives on `output`. Light/dark variants follow
GitHub's color scheme. `style-cards.py` aligns Summary Cards typography/colors without
changing its data. Language percentages reflect repository code volume, not proficiency. The Metrics
viewer-affiliation filter is disabled because the built-in token represents this
repository; filtering by that viewer would incorrectly count only the profile repo.
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

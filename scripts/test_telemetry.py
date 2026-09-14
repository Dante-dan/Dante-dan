from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import telemetry as t

NOW = datetime(2026, 9, 14, tzinfo=timezone.utc)


def node(age, count=1, private=False, minimized=False):
    return {'createdAt': (NOW - timedelta(days=age)).isoformat(),
            'repository': {'isPrivate': private}, 'isMinimized': minimized,
            'reactionGroups': [{'content': 'THUMBS_UP', 'users': {'totalCount': count}}]}


def response(comments, issues=()):
    return {'data': {'user': {'issueComments': {'nodes': comments}, 'issues': {'nodes': list(issues)}}}}


class TelemetryTests(unittest.TestCase):
    def test_recent_window_boundary_privacy_and_full_reaction_counts(self):
        data = response([node(0, 150), node(90, 2), node(91, 1000),
                         node(-1, 1000), node(1, 1000, private=True),
                         node(1, 1000, minimized=True)], [node(2, 3)])
        counts, sampled = t.reaction_counts(data, NOW)
        self.assertEqual(counts, {'THUMBS_UP': 155})
        self.assertEqual(sampled, 3)

    def test_partial_graphql_errors_are_not_published(self):
        with self.assertRaises(ValueError):
            t.reaction_counts({**response([node(1)]), 'errors': [{'message': 'denied'}]}, NOW)

    def test_empty_recent_sample_is_valid_zero_not_stale_data(self):
        counts, sampled = t.reaction_counts(response([node(91)]), NOW)
        self.assertEqual((counts, sampled), (Counter(), 0))
        self.assertIn('0 reactions on 0 sampled', t.render_reactions(counts, sampled))

    def test_fetch_failure_preserves_previous_svg(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'assets').mkdir()
            card = root / 'assets/reactions.svg'
            card.write_text('previous card')
            with patch.dict(t.os.environ, {'GH_TOKEN': 'test'}), patch.object(t.urllib.request, 'urlopen', side_effect=TimeoutError):
                with self.assertRaises(TimeoutError):
                    t.refresh_reactions(root)
            self.assertEqual(card.read_text(), 'previous card')

    def test_fetch_timestamp_and_url_version_have_distinct_meanings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'assets').mkdir()
            images = []
            for files in t.GROUPS.values():
                for filename in files:
                    (root / 'assets' / filename).write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
                    images.append(f'<img src="assets/{filename}"/>')
            (root / 'README.md').write_text('\n'.join(images) + '\n### `~/arcade`')
            t.finalize(['stats', 'reactions'], root, NOW)
            first = (root / 'README.md').read_text()
            self.assertIn(f'src="{t.RAW_ASSETS}stats-dark.svg?v=', first)
            self.assertIn('Commit hours: refresh pending', first)
            t.finalize(['stats'], root, NOW + timedelta(hours=8))
            second = (root / 'README.md').read_text()
            self.assertEqual(first.split('<!-- telemetry-refresh:start -->')[0], second.split('<!-- telemetry-refresh:start -->')[0])
            state = json.loads((root / 'assets/telemetry-refresh.json').read_text())
            self.assertEqual(state['stats']['last_success_at'], '2026-09-14T08:00:00Z')
            self.assertEqual(state['reactions']['last_success_at'], '2026-09-14T00:00:00Z')
            (root / 'assets/stats-dark.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"><title>new data</title></svg>')
            t.finalize(['stats'], root, NOW + timedelta(hours=16))
            third = (root / 'README.md').read_text()
            self.assertNotEqual(second.splitlines()[0], third.splitlines()[0])
            self.assertEqual(third.count('<!-- telemetry-refresh:start -->'), 1)
            self.assertEqual(third.count(t.RAW_ASSETS), 5)


if __name__ == '__main__':
    unittest.main()

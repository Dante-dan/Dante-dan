import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('profile', Path(__file__).with_name('update-profile.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ProfileTests(unittest.TestCase):
    def test_one_failed_source_keeps_its_previous_content(self):
        original = '\n'.join(f'<!-- {n}:start -->\nold {n}\n<!-- {n}:end -->' for n in ('contributions', 'workbench', 'upstream', 'notes', 'activity'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'README.md'
            path.write_text(original)
            with patch.object(m, 'ROOT', Path(directory)), patch.object(m, 'contributions', side_effect=TimeoutError), patch.object(m, 'workbench', return_value='new projects'), patch.object(m, 'upstream', side_effect=TimeoutError), patch.object(m, 'notes', return_value='new posts'), patch.object(m, 'activity', return_value='new conversations'):
                self.assertEqual(m.main(), 1)
            result = path.read_text()
            self.assertIn('old upstream', result)
            self.assertIn('old contributions', result)
            self.assertIn('new projects', result)
            self.assertIn('new posts', result)

    def test_untrusted_feed_title_cannot_inject_markup(self):
        title = '<img src=x> [bad](javascript:x)\n<!-- notes:end -->'
        rendered = m.clean(title)
        self.assertNotIn('<img', rendered)
        self.assertNotIn('<!--', rendered)
        self.assertIn('\\[bad\\]', rendered)
        with self.assertRaises(ValueError):
            m.link('https://evil.example/post')

    def test_activity_handles_reduced_payloads_and_deduplicates_threads(self):
        import json
        from datetime import datetime, timezone
        def event(kind, payload):
            return dict(type=kind, public=True, actor={'login': 'Dante-dan'}, repo={'name': 'team/project'}, created_at=datetime.now(timezone.utc).isoformat(), payload=payload)
        comment = event('IssueCommentEvent', {'issue': {'number': 1, 'title': 'A discussion'}, 'comment': {'html_url': 'https://github.com/team/project/issues/1#issuecomment-2'}})
        events = [event('PullRequestEvent', {'pull_request': {}}), event('PullRequestReviewEvent', {}), comment, comment]
        with patch.object(m, 'fetch', return_value=json.dumps(events).encode()):
            result = m.activity()
        self.assertEqual(result.count('team/project#1'), 1)
        self.assertIn('#issuecomment-2', result)

    def test_empty_or_duplicate_markers_do_not_erase_content(self):
        source = '<!-- notes:start -->old<!-- notes:end -->'
        for body, text in [('', source), ('new', source + source)]:
            with self.assertRaises(ValueError):
                m.replace_block(text, 'notes', body)

    def test_projects_exclude_forks_archived_and_private(self):
        import json
        repos = [dict(name=n, fork=f, archived=a, private=p, description='test', html_url=f'https://github.com/Dante-dan/{n}') for n, f, a, p in [('fork', True, False, False), ('archive', False, True, False), ('secret', False, False, True), ('Dante-dan', False, False, False), ('visible', False, False, False)]]
        with patch.object(m, 'fetch', return_value=json.dumps(repos).encode()):
            result = m.workbench()
        self.assertIn('visible', result)
        for name in ('fork', 'archive', 'secret'):
            self.assertNotIn(name, result)


if __name__ == '__main__':
    unittest.main()

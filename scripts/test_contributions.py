import unittest
from datetime import datetime, timezone
from contributions import render


class ContributionTests(unittest.TestCase):
    def test_old_projects_are_archived_not_removed(self):
        base = dict(repo='team/project', icon='assets/projects/a.png', evidence='https://github.com/team/project/pull/1', status='merged')
        data = [dict(base, name='Recent', accepted_at='2026-08-01T00:00:00Z'), dict(base, name='Older', accepted_at='2024-01-01T00:00:00Z')]
        text = render(data, datetime(2026, 9, 11, tzinfo=timezone.utc))
        self.assertLess(text.index('Recent'), text.index('<details>'))
        self.assertGreater(text.index('Older'), text.index('<details>'))
        later = render(data, datetime(2028, 9, 11, tzinfo=timezone.utc))
        self.assertGreater(later.index('Recent'), later.index('<details>'))
        self.assertIn('Older', later)

    def test_names_are_escaped_and_integrated_credit_is_explicit(self):
        text = render([dict(repo='affaan-m/ECC', name='<unsafe>', icon='assets/a.svg', evidence='https://github.com/affaan-m/ECC/commit/123', status='integrated', accepted_at='2026-09-10T00:00:00Z')], datetime(2026, 9, 11, tzinfo=timezone.utc))
        self.assertNotIn('<unsafe>', text)
        self.assertIn('integrated contribution', text)
        self.assertIn('/commit/123', text)

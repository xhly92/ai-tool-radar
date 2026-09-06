import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import update_research as app

class CollectorTests(unittest.TestCase):
    def test_rss_strips_markup_and_uses_publication_date(self):
        xml = b'<rss><channel><item><title>AI &amp; Markets</title><link>https://bofaglobalresearch.podbean.com/e/test/</link><pubDate>Fri, 04 Sep 2026 15:32:39 -0400</pubDate><description>&lt;p&gt;Public summary&lt;/p&gt;</description></item></channel></rss>'
        with patch.object(app, 'fetch', return_value=xml):
            row = app.collect('bofa')[0]
        self.assertEqual(row['date'], '2026-09-04')
        self.assertEqual(row['summary'], 'Public summary')
        self.assertEqual(row['topic'], '科技AI')

    def test_rejects_foreign_links_and_missing_dates(self):
        with self.assertRaises(ValueError):
            app.report('ms', 'Title', '2026-09-04', 'https://example.com/')
        with self.assertRaises((ValueError, AttributeError)):
            app.report('ms', 'Title', '', 'https://www.morganstanley.com/insights/test')

    def test_total_outage_preserves_previous_data_and_success_time(self):
        row = app.report('ms', 'Title', app.dt.date.today().isoformat(), 'https://www.morganstanley.com/insights/test')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'research.json'
            path.write_text(json.dumps({'reports': [row], 'sources': {}, 'lastSuccessAt': '2026-09-01T00:00:00Z'}), encoding='utf-8')
            with patch.object(app, 'OUTPUT', path), patch.object(app, 'collect', side_effect=RuntimeError('unavailable')):
                self.assertEqual(app.main(), 1)
            data = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(data['reports'], [row])
            self.assertEqual(data['lastSuccessAt'], '2026-09-01T00:00:00Z')
            self.assertTrue(all(s['status'] == 'error' for s in data['sources'].values()))

if __name__ == '__main__':
    unittest.main()

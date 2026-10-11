import unittest
import username_tracker

class TestLiveAccuracy(unittest.TestCase):
    def test_fake_username_has_zero_false_positives(self):
        """Verify that a random non-existent username produces zero false positives across core sites."""
        fake_user = "ghost_test_nonexistent_xyz_998877"
        # Test a selection of core sites known for soft-404s
        sites_to_test = [
            s for s in username_tracker.DEFAULT_SITES
            if s['name'] in ('Telegram', 'Pinterest', 'GitHub', 'Medium')
        ]
        results = username_tracker.search_username(fake_user, sites=sites_to_test, timeout=5)
        for r in results:
            self.assertNotEqual(
                r['status'],
                'FOUND',
                f"False positive detected on {r['name']} for fake user: {r}"
            )

    def test_real_username_detection(self):
        """Verify that a known active public user (github on GitHub) is detected."""
        github_site = [s for s in username_tracker.DEFAULT_SITES if s['name'] == 'GitHub']
        results = username_tracker.search_username("github", sites=github_site, timeout=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['status'], 'FOUND')

if __name__ == '__main__':
    unittest.main()

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run


class CollectionTests(unittest.TestCase):
    def test_sources_are_capped_and_collected_concurrently(self):
        sources = [
            {"name": "High volume", "max_items": 15},
            {"name": "Lower configured", "max_items": 3},
        ]
        observed = []

        def fake_collect(source):
            observed.append((source["name"], source["max_items"]))
            return [{"source": source["name"]}]

        with patch.object(run, "collect", side_effect=fake_collect):
            groups, errors = run.collect_sources(sources, item_limit=5, workers=2)

        self.assertEqual(sorted(observed), [("High volume", 5), ("Lower configured", 3)])
        self.assertEqual(set(groups), {"High volume", "Lower configured"})
        self.assertEqual(errors, {})
        self.assertEqual(sources[0]["max_items"], 15)


if __name__ == "__main__":
    unittest.main()

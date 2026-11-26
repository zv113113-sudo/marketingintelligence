import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run


class MediaPreviewTests(unittest.TestCase):
    def test_page_data_extracts_open_graph_image_as_absolute_url(self):
        page = """
        <html><head><meta property="og:image" content="/assets/cover.jpg"></head>
        <body><article><p>{}</p><p>{}</p></article></body></html>
        """.format("Useful editorial content " * 20, "Second paragraph " * 20)
        with patch.object(run, "text", return_value=page):
            body, published_at, image_url = run.page_data("https://news.example/story/1")
        self.assertTrue(body)
        self.assertEqual(published_at, "")
        self.assertEqual(image_url, "https://news.example/assets/cover.jpg")

    def test_rss_media_thumbnail_is_selected(self):
        item = ET.fromstring(
            '<item xmlns:media="http://search.yahoo.com/mrss/">'
            '<media:thumbnail url="https://news.example/thumb.jpg" />'
            '</item>'
        )
        self.assertEqual(
            run.rss_image_url(item), "https://news.example/thumb.jpg"
        )

    def test_gigachat_image_id_is_extracted_from_response_markup(self):
        content = 'Here is the illustration <img src="a598ae3d-d3eb-454e-a8bf-0848193a603e" fuse="true"/>'
        self.assertEqual(
            run.generated_image_id(content),
            "a598ae3d-d3eb-454e-a8bf-0848193a603e",
        )

    def test_calibration_pass_keeps_relevance_and_evidence_gates(self):
        candidate = {
            "relevant": True,
            "score": 6.5,
            "marketing_relevance": 8,
            "evidence": 6,
            "novelty": 6,
            "fact_confidence": 6,
            "freshness": 6,
            "reader_value": 6.5,
            "content_depth": 6,
            "transferability": 5,
            "commerciality": 6,
            "public_content": True,
        }
        self.assertTrue(run.passes_calibration(candidate))
        candidate["marketing_relevance"] = 7.9
        self.assertFalse(run.passes_calibration(candidate))

    def test_daily_selection_caps_total_at_four_and_adds_at_most_two(self):
        primary = [
            {"url": f"https://example.com/main-{i}", "title": f"Main {i}", "selection_score": 8-i}
            for i in range(2)
        ]
        near_misses = [
            {
                "url": f"https://example.com/extra-{i}",
                "title": f"Extra {i}",
                "selection_score": 6,
                "relevant": True,
                "score": 6.5,
                "marketing_relevance": 8,
                "evidence": 6,
                "novelty": 6,
                "fact_confidence": 6,
                "freshness": 6,
                "reader_value": 6.5,
                "content_depth": 6,
                "transferability": 5,
                "commerciality": 6,
                "public_content": True,
            }
            for i in range(5)
        ]

        def fake_select(items, limit):
            ranked = sorted(items, key=lambda item: item.get("calibration_card", False))
            return ranked[:limit]

        with patch.object(run, "select_final", side_effect=fake_select):
            selected = run.daily_selection(primary, near_misses, limit=7)
        self.assertEqual(len(selected), 4)
        self.assertEqual(sum(bool(item.get("calibration_card")) for item in selected), 2)


if __name__ == "__main__":
    unittest.main()

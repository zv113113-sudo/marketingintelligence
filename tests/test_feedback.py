import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import feedback
import subscriber_bot


class FeedbackStorageTests(unittest.TestCase):
    def test_vote_is_bound_to_delivered_message_and_can_be_updated(self):
        article = {
            "url": "https://example.com/story",
            "title": "A useful market signal",
            "source": "Example",
            "region": "RU",
            "topic_track": "consumer",
            "narrow_topic": "retail",
            "category": "research",
            "editorial_score": 8.2,
        }
        with tempfile.TemporaryDirectory() as folder:
            state_dir = Path(folder)
            key = feedback.item_key(article)
            feedback.record_delivery(article, "366007726", 91, state_dir=state_dir)

            rejected = feedback.record_vote(
                key, "366007726", "999", 91, "like", state_dir=state_dir
            )
            self.assertEqual(rejected, "not_delivered")

            first = feedback.record_vote(
                key, "366007726", "366007726", 91, "like", state_dir=state_dir
            )
            changed = feedback.record_vote(
                key, "366007726", "366007726", 91, "dislike", state_dir=state_dir
            )

            self.assertEqual(first, "saved")
            self.assertEqual(changed, "updated")
            votes = json.loads((state_dir / "feedback_votes.json").read_text())[
                "votes"
            ]
            self.assertEqual(len(votes), 1)
            self.assertEqual(votes[0]["reaction"], "dislike")
            self.assertEqual(votes[0]["source"], "Example")

    def test_personalization_waits_for_a_minimum_number_of_ratings(self):
        candidate = {
            "source": "Example",
            "source_class": "editorial",
            "region": "RU",
            "topic_track": "consumer",
            "narrow_topic": "retail",
        }
        votes = [
            {**candidate, "reaction": "like"}
            for _ in range(4)
        ]
        self.assertEqual(feedback.personalization_delta(candidate, votes), 0.0)

    def test_personalization_is_bounded_and_uses_reaction_direction(self):
        candidate = {
            "source": "Example",
            "source_class": "editorial",
            "region": "RU",
            "topic_track": "consumer",
            "narrow_topic": "retail",
        }
        likes = [{**candidate, "reaction": "like"} for _ in range(5)]
        dislikes = [{**candidate, "reaction": "dislike"} for _ in range(5)]
        positive = feedback.personalization_delta(candidate, likes)
        negative = feedback.personalization_delta(candidate, dislikes)
        self.assertGreater(positive, 0)
        self.assertLess(negative, 0)
        self.assertLessEqual(abs(positive), 0.5)
        self.assertLessEqual(abs(negative), 0.5)


class CallbackTests(unittest.TestCase):
    def test_callback_saves_vote_and_updates_its_buttons(self):
        update = {
            "callback_query": {
                "id": "query-1",
                "from": {"id": 366007726},
                "data": "mi:like:" + "a" * 40,
                "message": {"message_id": 91, "chat": {"id": 366007726}},
            }
        }
        calls = []

        def fake_api(method, payload=None):
            calls.append((method, payload))
            return {"ok": True}

        with patch.object(subscriber_bot, "record_vote", return_value="saved"), patch.object(
            subscriber_bot, "api", side_effect=fake_api
        ):
            subscriber_bot.handle_callback(update["callback_query"])

        self.assertEqual(calls[0][0], "answerCallbackQuery")
        self.assertEqual(calls[1][0], "editMessageReplyMarkup")
        self.assertIn("✅", calls[1][1]["reply_markup"]["inline_keyboard"][0][0]["text"])


if __name__ == "__main__":
    unittest.main()

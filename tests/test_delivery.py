import unittest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run


class TelegramDeliveryTests(unittest.TestCase):
    def test_send_raises_when_telegram_returns_ok_false(self):
        with patch.object(run, "load_subscribers", return_value=["123"]), patch.object(
            run, "j", return_value={"ok": False, "description": "chat not found"}
        ):
            with self.assertRaisesRegex(RuntimeError, "chat not found"):
                run.send("test")


if __name__ == "__main__":
    unittest.main()

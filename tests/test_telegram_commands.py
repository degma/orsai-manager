import unittest
from app.services.telegram_commands import parse_command, CommandError

class TelegramCommandTests(unittest.TestCase):
    def test_parse_score_with_notes(self):
        cmd = parse_command('/match 12 score 3-1 notes "Great first half"')
        self.assertEqual(cmd["type"], "score")
        self.assertEqual(cmd["match_id"], 12)
        self.assertEqual(cmd["home_score"], 3)
        self.assertEqual(cmd["away_score"], 1)
        self.assertEqual(cmd["notes"], "Great first half")

    def test_parse_stats(self):
        cmd = parse_command('/match 5 stats Luca goals=2 y=1 r=0 played=1')
        self.assertEqual(cmd["type"], "stats")
        self.assertEqual(cmd["player_identifier"], "Luca")
        self.assertEqual(cmd["goals"], 2)
        self.assertEqual(cmd["yellow_cards"], 1)
        self.assertEqual(cmd["red_cards"], 0)
        self.assertTrue(cmd["played"])

    def test_parse_invalid(self):
        with self.assertRaises(CommandError):
            parse_command('/match 5 score 1-x')

if __name__ == "__main__":
    unittest.main()

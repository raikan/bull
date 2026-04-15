from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import notify_daily_menu


class ExtractMenuTextTests(unittest.TestCase):
    def test_extracts_inline_month_day_menu(self) -> None:
        text = """
        4/14 ハヤシライス
        4/15 ごはん さばの味噌煮 けんちん汁
        4/16 カレーライス
        """

        menu = notify_daily_menu.extract_menu_text(text, date(2026, 4, 15))

        self.assertEqual(menu, "ごはん さばの味噌煮 けんちん汁")

    def test_extracts_following_lines_when_date_is_header(self) -> None:
        text = """
        15(水)
        ごはん
        鶏の唐揚げ
        味噌汁
        16(木)
        パン
        """

        menu = notify_daily_menu.extract_menu_text(text, date(2026, 4, 15))

        self.assertEqual(menu, "ごはん\n鶏の唐揚げ\n味噌汁")

    def test_raises_when_date_is_missing(self) -> None:
        with self.assertRaises(RuntimeError):
            notify_daily_menu.extract_menu_text("4/14 ハヤシライス", date(2026, 4, 15))


if __name__ == "__main__":
    unittest.main()

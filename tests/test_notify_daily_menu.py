from __future__ import annotations

import sys
import tempfile
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


class FormatMenuMessageTests(unittest.TestCase):
    def test_formats_bulleted_message(self) -> None:
        message = notify_daily_menu.format_menu_message(
            date(2026, 4, 15),
            "ごはん\n鶏の唐揚げ\n味噌汁",
        )

        self.assertEqual(
            message,
            "【今日の給食】2026-04-15（水）\n・ごはん\n・鶏の唐揚げ\n・味噌汁",
        )


class ResolvePdfPathTests(unittest.TestCase):
    def test_prefers_local_pdf_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "latest.pdf"
            pdf_path.write_bytes(b"dummy")

            resolved = notify_daily_menu.resolve_local_pdf_path(str(pdf_path))

            self.assertEqual(resolved, pdf_path)

    def test_returns_none_when_local_pdf_is_missing(self) -> None:
        resolved = notify_daily_menu.resolve_local_pdf_path("menus/missing.pdf")

        self.assertIsNone(resolved)


if __name__ == "__main__":
    unittest.main()

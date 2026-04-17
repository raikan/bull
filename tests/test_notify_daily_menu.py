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
        with self.assertRaises(notify_daily_menu.MenuNotFoundError):
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

    def test_formats_meal_sections_message(self) -> None:
        message = notify_daily_menu.format_meal_sections_message(
            date(2026, 4, 17),
            {
                "朝おやつ": ["蒸しかぼちゃ", "牛乳"],
                "昼食": ["ご飯", "パイナップル", "ヨーグルト(苺)", "ワンタンスープ", "麻婆豆腐", "カリカリしらすともやしの和え物"],
                "午後おやつ": ["ほうじ茶", "ウエハース"],
                "延長おやつ": ["ぽたぽた焼き", "ほうじ茶"],
            },
        )

        self.assertEqual(
            message,
            "【今日の給食】2026-04-17（金）\n"
            "朝おやつ\n・蒸しかぼちゃ\n・牛乳\n"
            "昼食\n・ご飯\n・パイナップル\n・ヨーグルト(苺)\n・ワンタンスープ\n・麻婆豆腐\n・カリカリしらすともやしの和え物\n"
            "午後おやつ\n・ほうじ茶\n・ウエハース\n"
            "延長おやつ\n・ぽたぽた焼き\n・ほうじ茶",
        )


class ResolveTargetDateTests(unittest.TestCase):
    def test_accepts_dashed_date(self) -> None:
        resolved = notify_daily_menu.resolve_target_date("2026-04-16", "Asia/Tokyo")

        self.assertEqual(resolved, date(2026, 4, 16))

    def test_accepts_compact_date(self) -> None:
        resolved = notify_daily_menu.resolve_target_date("20260416", "Asia/Tokyo")

        self.assertEqual(resolved, date(2026, 4, 16))

    def test_rejects_invalid_date_format(self) -> None:
        with self.assertRaises(RuntimeError):
            notify_daily_menu.resolve_target_date("2026/04/16", "Asia/Tokyo")


class LayoutMealParsingTests(unittest.TestCase):
    def test_extracts_four_meal_sections_from_layout_lines(self) -> None:
        lines = [
            "     蒸しかぼちゃ         ご飯                      パイナップル                 ヨーグルト(苺)       牛乳、木綿豆腐、豚肉、減塩み           米、ワンタン、ごま油、三温糖、片          かぼちゃ、干ししいたけ、水菜、人",
            "17 金 牛乳             ワンタンスープ                 ほうじ茶                   ウエハース          そ、しらす、ヨーグルト（苺)           栗粉、ウエハース                  参、長ねぎ、しょうが、にんにく、も         ぽたぽた焼き",
            "                    麻婆豆腐                                           ほう じ茶                                                              やし、ほうれん草、パイナップル           ほうじ茶",
            "                    カリカリしらすともやしの和え物",
            "     ハイハイン          焼きそば                                           ビスケット          牛乳、豚肉                    ハイハイン、蒸し中華麺、油、三温          キャベツ、玉ねぎ、人参、青のり、",
            "18 土 牛乳             かぼちゃとしめじの甘辛和え                                  牛乳                                      糖、マリービスケット                南瓜、しめじ、オレンジ               味しらべ",
        ]

        sections = notify_daily_menu.extract_meal_sections_from_layout_lines(lines, date(2026, 4, 17))

        self.assertEqual(sections["朝おやつ"], ["蒸しかぼちゃ", "牛乳"])
        self.assertEqual(sections["昼食"], ["ご飯", "パイナップル", "ヨーグルト(苺)", "ワンタンスープ", "麻婆豆腐", "カリカリしらすともやしの和え物"])
        self.assertEqual(sections["午後おやつ"], ["ほうじ茶", "ウエハース"])
        self.assertEqual(sections["延長おやつ"], ["ぽたぽた焼き", "ほうじ茶"])

    def test_raises_menu_not_found_when_date_is_missing(self) -> None:
        lines = [
            "17 金 牛乳             ワンタンスープ                 ほうじ茶                   ウエハース",
            "18 土 牛乳             かぼちゃとしめじの甘辛和え                                  牛乳",
        ]

        with self.assertRaises(notify_daily_menu.MenuNotFoundError):
            notify_daily_menu.extract_meal_sections_from_layout_lines(lines, date(2026, 4, 20))

    def test_extracts_items_in_correct_sections_when_afternoon_snack_starts_on_first_line(self) -> None:
        lines = [
            "     蒸しかぼちゃ         ご飯                      パイナップル                 ヨーグルト(苺)       牛乳、木綿豆腐、豚肉、減塩み           米、ワンタン、ごま油、三温糖、片          かぼちゃ、干ししいたけ、水菜、人",
            "17 金 牛乳             ワンタンスープ                 ほうじ茶                   ウエハース          そ、しらす、ヨーグルト（苺)           栗粉、ウエハース                  参、長ねぎ、しょうが、にんにく、も         ぽたぽた焼き",
            "                    麻婆豆腐                                           ほう じ茶                                                              やし、ほうれん草、パイナップル           ほうじ茶",
            "                    カリカリしらすともやしの和え物",
            "     ハイハイン          焼きそば                                           ビスケット          牛乳、豚肉                    ハイハイン、蒸し中華麺、油、三温          キャベツ、玉ねぎ、人参、青のり、",
            "18 土 牛乳             かぼちゃとしめじの甘辛和え                                  牛乳                                      糖、マリービスケット                南瓜、しめじ、オレンジ               味しらべ",
            "                    オレンジ                                                                                                                                       ほうじ茶",
            "                    ほうじ茶",
        ]

        sections = notify_daily_menu.extract_meal_sections_from_layout_lines(lines, date(2026, 4, 18))

        self.assertEqual(sections["朝おやつ"], ["ハイハイン", "牛乳"])
        self.assertNotIn("ビスケット", sections["昼食"])
        self.assertEqual(sections["午後おやつ"][:2], ["ビスケット", "牛乳"])
        self.assertEqual(sections["延長おやつ"], ["味しらべ", "ほうじ茶"])


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

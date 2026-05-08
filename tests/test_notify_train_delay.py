from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import notify_train_delay


class ParseTrainStatusTests(unittest.TestCase):
    def test_parses_normal_status_from_line_specific_summary(self) -> None:
        html = """
        <html>
          <head>
            <title>学園都市線の運行情報 - Yahoo!路線情報</title>
            <meta name="description" content="学園都市線は現在、遅れに関する情報はありません。">
          </head>
          <body>
            <main>
              <h1>学園都市線</h1>
              <p>現在、遅れに関する情報はありません。</p>
            </main>
          </body>
        </html>
        """

        status = notify_train_delay.parse_train_status(
            html,
            ("学園都市線", "札沼線"),
            "https://example.com/status",
            "2026-05-08T08:10:00+09:00",
        )

        self.assertEqual(status.state, "normal")
        self.assertIn("遅れに関する情報はありません", status.summary)

    def test_parses_delay_status_from_nearby_lines(self) -> None:
        html = """
        <html>
          <body>
            <div>函館本線 平常どおり運転しています。</div>
            <div>学園都市線</div>
            <div>強風の影響で一部列車に遅れが発生しています。</div>
          </body>
        </html>
        """

        status = notify_train_delay.parse_train_status(
            html,
            ("学園都市線", "札沼線"),
            "https://example.com/status",
            "2026-05-08T08:10:00+09:00",
        )

        self.assertEqual(status.state, "delay")
        self.assertIn("学園都市線", status.summary)
        self.assertIn("遅れが発生しています", status.summary)

    def test_raises_when_status_cannot_be_determined(self) -> None:
        html = "<html><body><p>学園都市線</p><p>最新情報を確認してください。</p></body></html>"

        with self.assertRaises(RuntimeError):
            notify_train_delay.parse_train_status(
                html,
                ("学園都市線", "札沼線"),
                "https://example.com/status",
                "2026-05-08T08:10:00+09:00",
            )


class StateHandlingTests(unittest.TestCase):
    def make_status(self, state: str, summary: str) -> notify_train_delay.TrainStatus:
        return notify_train_delay.TrainStatus(
            state=state,
            summary=summary,
            source_url="https://example.com/status",
            checked_at="2026-05-08T08:10:00+09:00",
        )

    def test_notifies_when_status_changes_to_delay(self) -> None:
        current = self.make_status("delay", "学園都市線は遅れが発生しています。")

        self.assertTrue(notify_train_delay.should_notify(current, {"state": "normal"}))

    def test_skips_duplicate_delay_notifications(self) -> None:
        current = self.make_status("delay", "学園都市線は遅れが発生しています。")

        self.assertFalse(
            notify_train_delay.should_notify(
                current,
                {
                    "state": "delay",
                    "summary": "学園都市線は遅れが発生しています。",
                },
            )
        )

    def test_updates_when_delay_summary_changes(self) -> None:
        current = self.make_status("delay", "学園都市線は運転を見合わせています。")

        self.assertTrue(
            notify_train_delay.should_notify(
                current,
                {
                    "state": "delay",
                    "summary": "学園都市線は遅れが発生しています。",
                },
            )
        )

    def test_does_not_notify_for_normal_state(self) -> None:
        current = self.make_status("normal", "遅れに関する情報はありません。")

        self.assertFalse(notify_train_delay.should_notify(current, {"state": "delay"}))

    def test_saves_and_loads_state_file(self) -> None:
        status = self.make_status("delay", "学園都市線は遅れが発生しています。")

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            notify_train_delay.save_state(path, status)

            loaded = notify_train_delay.load_state(path)

        self.assertEqual(loaded["state"], "delay")
        self.assertEqual(loaded["summary"], "学園都市線は遅れが発生しています。")


class FormatDelayMessageTests(unittest.TestCase):
    def test_formats_message(self) -> None:
        status = notify_train_delay.TrainStatus(
            state="delay",
            summary="学園都市線は強風の影響で遅れが発生しています。",
            source_url="https://example.com/status",
            checked_at="2026-05-08T08:10:00+09:00",
        )

        message = notify_train_delay.format_delay_message(status, "学園都市線", "拓北〜札幌")

        self.assertEqual(
            message,
            "【JR北海道 運行情報】学園都市線（拓北〜札幌）\n"
            "学園都市線は強風の影響で遅れが発生しています。\n"
            "確認時刻: 2026-05-08 08:10\n"
            "取得元: https://example.com/status",
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

DATE_SPLITTER_PATTERN = re.compile(r"(?<!\d)(?:\d{1,2}/\d{1,2}|\d{1,2}月\d{1,2}日|\d{1,2}日)(?:\s*[（(][月火水木金土日][）)])?")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Notify today's lunch menu from a PDF.")
    parser.add_argument("--date", dest="target_date", help="Target date in YYYY-MM-DD format.")
    return parser.parse_args()


def resolve_target_date(target_date: str | None, timezone_name: str) -> date:
    if target_date:
        return datetime.strptime(target_date, "%Y-%m-%d").date()
    return datetime.now(ZoneInfo(timezone_name)).date()


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required.")
    return value


def download_pdf(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "bull-menu-notifier/1.0"})
    try:
        with urlopen(request) as response:  # noqa: S310
            if response.status != 200:
                raise RuntimeError(f"Failed to fetch PDF: HTTP {response.status}")
            destination.write_bytes(response.read())
    except HTTPError as exc:
        raise RuntimeError(f"Failed to fetch PDF: HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to fetch PDF: {exc.reason}") from exc


def extract_pdf_text(pdf_path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.replace("\u3000", " ")).strip()


def split_lines(text: str) -> list[str]:
    lines = [normalize_line(line) for line in text.splitlines()]
    return [line for line in lines if line]


def month_day_patterns(target_date: date) -> list[re.Pattern[str]]:
    month = target_date.month
    day = target_date.day
    weekday = "月火水木金土日"[target_date.weekday()]
    variants = [
        rf"{month}/{day}",
        rf"{month:02d}/{day:02d}",
        rf"{month}月{day}日",
        rf"{month:02d}月{day:02d}日",
        rf"{day}[（(]{weekday}[）)]",
        rf"{day}日[（(]{weekday}[）)]",
        rf"{day}日",
    ]
    return [re.compile(rf"(?<!\d){variant}(?!\d)") for variant in variants]


def day_only_patterns(target_date: date) -> list[re.Pattern[str]]:
    day = target_date.day
    weekday = "月火水木金土日"[target_date.weekday()]
    variants = [
        rf"^\s*{day}(?!\d)",
        rf"^\s*{day}日(?!\d)",
        rf"^\s*{day}\s*[（(]{weekday}[）)]",
        rf"^\s*{day}日?\s*[（(]{weekday}[）)]",
    ]
    return [re.compile(variant) for variant in variants]


def is_new_date_section(line: str, target_date: date) -> bool:
    other_date = DATE_SPLITTER_PATTERN.search(line)
    if not other_date:
        return False
    return not any(pattern.search(line) for pattern in month_day_patterns(target_date) + day_only_patterns(target_date))


def strip_date_prefix(line: str, patterns: Iterable[re.Pattern[str]]) -> str:
    for pattern in patterns:
        match = pattern.search(line)
        if match and match.start() == 0:
            trimmed = line[match.end() :].lstrip(" 　:：|-－―/\\")
            return trimmed.strip()
    return line


def collect_menu(lines: list[str], index: int, target_date: date, max_lines: int = 3) -> str:
    patterns = month_day_patterns(target_date) + day_only_patterns(target_date)
    collected: list[str] = []

    first_line = strip_date_prefix(lines[index], patterns)
    if first_line and first_line != lines[index]:
        collected.append(first_line)

    cursor = index + 1
    while cursor < len(lines) and len(collected) < max_lines:
        line = lines[cursor]
        if is_new_date_section(line, target_date):
            break
        collected.append(line)
        cursor += 1

    return "\n".join(collected).strip()


def extract_menu_text(text: str, target_date: date, max_lines: int = 3) -> str:
    lines = split_lines(text)
    primary_patterns = month_day_patterns(target_date)
    fallback_patterns = day_only_patterns(target_date)

    for patterns in (primary_patterns, fallback_patterns):
        for index, line in enumerate(lines):
            if any(pattern.search(line) for pattern in patterns):
                menu = collect_menu(lines, index, target_date, max_lines=max_lines)
                if menu:
                    return menu

    raise RuntimeError(f"Menu for {target_date.isoformat()} was not found in the PDF.")


def send_line_message(channel_access_token: str, message: str) -> None:
    payload = {
        "messages": [{"type": "text", "text": message[:5000]}],
    }
    request = Request(
        "https://api.line.me/v2/bot/message/broadcast",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {channel_access_token}",
        },
        method="POST",
    )
    try:
        with urlopen(request) as response:  # noqa: S310
            if response.status >= 400:
                raise RuntimeError(f"LINE API returned HTTP {response.status}")
    except HTTPError as exc:
        raise RuntimeError(f"LINE API returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to call LINE API: {exc.reason}") from exc


def main() -> int:
    args = parse_args()
    timezone_name = os.getenv("MENU_TIMEZONE", "Asia/Tokyo")
    target_date = resolve_target_date(args.target_date, timezone_name)
    pdf_url = require_env("MENU_PDF_URL")
    channel_access_token = require_env("LINE_CHANNEL_ACCESS_TOKEN")

    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_path = Path(temp_dir) / "menu.pdf"
        download_pdf(pdf_url, pdf_path)
        text = extract_pdf_text(pdf_path)

    menu = extract_menu_text(text, target_date)
    message = f"【今日の給食】{target_date.strftime('%Y-%m-%d')}\n{menu}"
    send_line_message(channel_access_token, message)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

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
LAYOUT_DATE_PATTERN = re.compile(r"^\s*(\d{1,2})\s+([月火水木金土日])\b")
JAPANESE_SPACE_PATTERN = re.compile(r"(?<=[ぁ-んァ-ン一-龠])\s+(?=[ぁ-んァ-ン一-龠])")
MEAL_SECTION_ORDER = ("朝おやつ", "昼食", "午後おやつ", "延長おやつ")
LAYOUT_COLUMN_SLICES = {
    "朝おやつ": (5, 20),
    "昼食": (20, 44),
    "午後おやつ": (44, 82),
    "3色分類": (82, 159),
    "延長おやつ": (159, None),
}


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


def optional_env(name: str) -> str:
    return os.getenv(name, "").strip()


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


def resolve_local_pdf_path(local_pdf_path: str) -> Path | None:
    candidate = Path(local_pdf_path)
    if candidate.is_file():
        return candidate
    return None


def extract_pdf_text(pdf_path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def extract_pdf_layout_lines(pdf_path: Path) -> list[str]:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    lines: list[str] = []
    for page in reader.pages:
        text = page.extract_text(extraction_mode="layout") or ""
        lines.extend(line.rstrip() for line in text.splitlines() if line.strip())
    return lines


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


def normalize_layout_item(item: str) -> str:
    compact = JAPANESE_SPACE_PATTERN.sub("", item)
    compact = re.sub(r"\s+", " ", compact).strip()
    return compact.replace("ほう じ茶", "ほうじ茶")


def split_layout_segment(segment: str) -> list[str]:
    cleaned = segment.rstrip()
    if not cleaned:
        return []
    parts = re.split(r"\s{2,}", cleaned)
    items = [normalize_layout_item(part) for part in parts]
    return [item for item in items if item]


def extract_meal_sections_from_layout_lines(lines: list[str], target_date: date) -> dict[str, list[str]]:
    target_weekday = "月火水木金土日"[target_date.weekday()]
    date_line_indexes = [
        index
        for index, line in enumerate(lines)
        if (match := LAYOUT_DATE_PATTERN.match(line))
        and int(match.group(1)) == target_date.day
        and match.group(2) == target_weekday
    ]

    if not date_line_indexes:
        raise RuntimeError(f"Menu for {target_date.isoformat()} was not found in the PDF layout.")

    date_line_index = date_line_indexes[0]
    next_date_line_index = next(
        (index for index in range(date_line_index + 1, len(lines)) if LAYOUT_DATE_PATTERN.match(lines[index])),
        len(lines),
    )
    block_start = max(0, date_line_index - 1)
    block_end = max(block_start, next_date_line_index - 1)
    block_lines = lines[block_start:block_end]

    sections = {name: [] for name in MEAL_SECTION_ORDER}
    for line_index, line in enumerate(block_lines):
        if line_index == 0:
            sections["朝おやつ"].extend(
                split_layout_segment(line[LAYOUT_COLUMN_SLICES["朝おやつ"][0] : LAYOUT_COLUMN_SLICES["朝おやつ"][1]])
            )
            sections["昼食"].extend(
                split_layout_segment(line[LAYOUT_COLUMN_SLICES["昼食"][0] : LAYOUT_COLUMN_SLICES["3色分類"][0]])
            )
            sections["延長おやつ"].extend(split_layout_segment(line[LAYOUT_COLUMN_SLICES["延長おやつ"][0] :]))
            continue

        for section_name in MEAL_SECTION_ORDER:
            start, end = LAYOUT_COLUMN_SLICES[section_name]
            segment = line[start:end] if end is not None else line[start:]
            sections[section_name].extend(split_layout_segment(segment))

    for section_name in MEAL_SECTION_ORDER:
        deduped: list[str] = []
        for item in sections[section_name]:
            if item not in deduped:
                deduped.append(item)
        sections[section_name] = deduped

    return sections


def format_menu_message(target_date: date, menu: str) -> str:
    weekday = "月火水木金土日"[target_date.weekday()]
    menu_lines = [line.strip().lstrip("・- ") for line in menu.splitlines() if line.strip()]
    if not menu_lines:
        raise RuntimeError("Menu text is empty.")
    body = "\n".join(f"・{line}" for line in menu_lines)
    return f"【今日の給食】{target_date.strftime('%Y-%m-%d')}（{weekday}）\n{body}"


def format_meal_sections_message(target_date: date, sections: dict[str, list[str]]) -> str:
    weekday = "月火水木金土日"[target_date.weekday()]
    parts = [f"【今日の給食】{target_date.strftime('%Y-%m-%d')}（{weekday}）"]

    for section_name in MEAL_SECTION_ORDER:
        items = sections.get(section_name, [])
        body = items or ["なし"]
        parts.append(section_name)
        parts.extend(f"・{item}" for item in body)

    return "\n".join(parts)


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
    pdf_url = optional_env("MENU_PDF_URL")
    local_pdf_path = os.getenv("MENU_PDF_PATH", "menus/latest.pdf")
    channel_access_token = require_env("LINE_CHANNEL_ACCESS_TOKEN")

    pdf_path = resolve_local_pdf_path(local_pdf_path)
    if pdf_path is not None:
        layout_lines = extract_pdf_layout_lines(pdf_path)
    elif pdf_url:
        with tempfile.TemporaryDirectory() as temp_dir:
            downloaded_pdf_path = Path(temp_dir) / "menu.pdf"
            download_pdf(pdf_url, downloaded_pdf_path)
            layout_lines = extract_pdf_layout_lines(downloaded_pdf_path)
    else:
        raise RuntimeError("No PDF source was found. Set MENU_PDF_URL or commit a PDF to menus/latest.pdf.")

    sections = extract_meal_sections_from_layout_lines(layout_lines, target_date)
    message = format_meal_sections_message(target_date, sections)
    send_line_message(channel_access_token, message)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

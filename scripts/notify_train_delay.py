from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

NORMAL_MARKERS = (
    "平常どおり運転しています",
    "平常通り運転しています",
    "平常運転",
    "遅れに関する情報はありません",
    "遅延・運休情報はありません",
    "現在、運行情報はありません",
    "現在運行情報はありません",
)
DISRUPTION_MARKERS = (
    "運転見合わせ",
    "運転を見合わせ",
    "運休",
    "遅れが発生",
    "遅延",
    "遅れ",
    "ダイヤ乱れ",
    "乱れ",
    "折返し運転",
    "一部列車",
    "運転を取りやめ",
    "運転再開",
)


@dataclass
class TrainStatus:
    state: str
    summary: str
    source_url: str
    checked_at: str


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required.")
    return value


def optional_env(name: str) -> str:
    return os.getenv(name, "").strip()


def resolve_status_urls(value: str) -> list[str]:
    candidates = re.split(r"[\n,]+", value)
    return [candidate.strip() for candidate in candidates if candidate.strip()]


def normalize_text(value: str) -> str:
    compact = value.replace("\u3000", " ")
    compact = re.sub(r"\s+", " ", compact)
    return compact.strip()


def classify_state(text: str) -> str | None:
    normalized = normalize_text(text)
    if any(marker in normalized for marker in NORMAL_MARKERS):
        return "normal"
    if any(marker in normalized for marker in DISRUPTION_MARKERS):
        return "delay"
    return None


def strip_html_tags(html: str) -> list[str]:
    without_scripts = re.sub(r"(?is)<script\b[^>]*>.*?</script\s*>", " ", html)
    without_styles = re.sub(r"(?is)<style\b[^>]*>.*?</style\s*>", " ", without_scripts)
    text = re.sub(r"(?is)<[^>]+>", "\n", without_styles)
    return [normalize_text(line) for line in unescape(text).splitlines() if normalize_text(line)]


def extract_metadata_candidates(html: str) -> list[str]:
    candidates: list[str] = []
    for pattern in (
        r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        r'(?is)<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']',
        r"(?is)<title>(.*?)</title>",
    ):
        for match in re.finditer(pattern, html):
            candidate = normalize_text(unescape(match.group(1)))
            if candidate:
                candidates.append(candidate)
    return candidates


def find_status_summary(html: str, line_aliases: tuple[str, ...]) -> str | None:
    lines = extract_metadata_candidates(html) + strip_html_tags(html)

    for line in lines:
        if any(alias in line for alias in line_aliases) and classify_state(line):
            return line

    for index, line in enumerate(lines):
        if any(alias in line for alias in line_aliases):
            window = normalize_text(" ".join(lines[index : index + 3]))
            if classify_state(window):
                return window

    for line in lines:
        if classify_state(line):
            return line

    return None


def parse_train_status(html: str, line_aliases: tuple[str, ...], source_url: str, checked_at: str) -> TrainStatus:
    summary = find_status_summary(html, line_aliases)
    if not summary:
        raise RuntimeError("Could not find a train status summary in the source page.")

    state = classify_state(summary)
    if not state:
        raise RuntimeError("Could not determine whether the train status is normal or delayed.")

    return TrainStatus(
        state=state,
        summary=summary,
        source_url=source_url,
        checked_at=checked_at,
    )


def validate_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError(f"Unsupported URL: {url}")


def fetch_url(url: str) -> str:
    validate_http_url(url)
    request = Request(url, headers={"User-Agent": "bull-train-delay-notifier/1.0"})
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - validated http/https URL
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status}")
            body = response.read()
            charsets = [
                response.headers.get_content_charset(),
                "utf-8",
                "cp932",
                "shift_jis",
                "euc-jp",
            ]
            for charset in charsets:
                if not charset:
                    continue
                try:
                    return body.decode(charset)
                except UnicodeDecodeError:
                    continue
            return body.decode("utf-8", errors="ignore")
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc


def fetch_train_status(urls: list[str], line_aliases: tuple[str, ...], timezone_name: str) -> TrainStatus:
    checked_at = datetime.now(ZoneInfo(timezone_name)).isoformat(timespec="seconds")
    errors: list[str] = []

    for url in urls:
        try:
            html = fetch_url(url)
            return parse_train_status(html, line_aliases, url, checked_at)
        except Exception as exc:
            errors.append(f"{url}: {exc}")

    raise RuntimeError("Failed to fetch train status.\n" + "\n".join(errors))


def load_state(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, status: TrainStatus) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(status), ensure_ascii=False, indent=2), encoding="utf-8")


def is_truthy(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "on"}


def should_notify(current: TrainStatus, previous: Mapping[str, str] | None, force_notify: bool = False) -> bool:
    previous = previous or {}
    if current.state != "delay":
        return False
    if force_notify:
        return True
    if previous.get("state") != "delay":
        return True
    return previous.get("summary") != current.summary


def format_delay_message(status: TrainStatus, line_name: str, section_label: str) -> str:
    checked_at = datetime.fromisoformat(status.checked_at)
    timestamp = checked_at.strftime("%Y-%m-%d %H:%M")
    section = f"（{section_label}）" if section_label else ""
    return (
        f"【JR北海道 運行情報】{line_name}{section}\n"
        f"{status.summary}\n"
        f"確認時刻: {timestamp}\n"
        f"取得元: {status.source_url}"
    )


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
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed LINE Messaging API endpoint
            if response.status >= 400:
                raise RuntimeError(f"LINE API returned HTTP {response.status}")
    except HTTPError as exc:
        raise RuntimeError(f"LINE API returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to call LINE API: {exc.reason}") from exc


def main() -> int:
    channel_access_token = require_env("LINE_CHANNEL_ACCESS_TOKEN")
    timezone_name = os.getenv("TRAIN_STATUS_TIMEZONE", "Asia/Tokyo")
    line_name = os.getenv("TRAIN_LINE_NAME", "学園都市線").strip() or "学園都市線"
    section_label = optional_env("TRAIN_COMMUTE_SECTION")
    state_path = Path(os.getenv("TRAIN_STATUS_STATE_PATH", ".cache/train-delay-state.json"))
    force_notify = is_truthy(optional_env("TRAIN_FORCE_NOTIFY"))

    status_urls = resolve_status_urls(
        optional_env("TRAIN_STATUS_URLS")
        or "https://www3.jrhokkaido.co.jp/webunkou/\nhttps://transit.yahoo.co.jp/diainfo/12/0"
    )
    if not status_urls:
        raise RuntimeError("TRAIN_STATUS_URLS must contain at least one URL.")

    line_aliases = tuple(
        alias.strip()
        for alias in os.getenv("TRAIN_LINE_ALIASES", "学園都市線,札沼線").split(",")
        if alias.strip()
    )
    previous_state = load_state(state_path)
    current_status = fetch_train_status(status_urls, line_aliases, timezone_name)

    if should_notify(current_status, previous_state, force_notify=force_notify):
        message = format_delay_message(current_status, line_name, section_label)
        send_line_message(channel_access_token, message)
        print("Delay detected. Notification sent.")
    else:
        print(f"No notification sent. Current state: {current_status.state}")

    save_state(state_path, current_status)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

"""KINTEX(킨텍스) 전시 일정 크롤러."""

import logging
import re
from datetime import datetime
from typing import List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://kintex.com/web/ko/event/list.do"
DETAIL_URL = "https://kintex.com/web/ko/event/view.do"
SITE_ORIGIN = "https://kintex.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
}
TIMEOUT = 10
MAX_PAGES = 10
DATE_PATTERN = re.compile(r"(\d{4}\.\d{2}\.\d{2})~(\d{4}\.\d{2}\.\d{2})")
SEQ_PATTERN = re.compile(r"fnView\([^,]+,\s*(\d+)\)")


def _request_with_retry(url: str, params: dict, max_retries: int = 1) -> requests.Response:
    """GET 요청. 실패 시 max_retries만큼 재시도."""
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            if attempt < max_retries:
                logger.warning("요청 실패 (시도 %d/%d): %s", attempt + 1, max_retries + 1, e)
                continue
            raise


def _parse_date(dot_date: str) -> str:
    """'2026.03.25' → '2026-03-25'"""
    return dot_date.replace(".", "-")


def fetch_events() -> List[dict]:
    """KINTEX 행사 목록을 크롤링하여 반환한다.

    Returns:
        행사 정보 딕셔너리 리스트. 파싱 실패 시 빈 리스트.
    """
    events: List[dict] = []

    try:
        today = datetime.now()
        end = datetime(today.year, 12, 31)

        for page in range(1, MAX_PAGES + 1):
            params = {
                "pageIndex": page,
                "searchStartDt": today.strftime("%Y.%m.%d"),
                "searchEndDt": end.strftime("%Y.%m.%d"),
            }
            resp = _request_with_retry(BASE_URL, params)
            soup = BeautifulSoup(resp.text, "html.parser")

            # fnView 호출이 포함된 <a> 태그가 이벤트 카드
            cards = soup.select("a[href*='fnView']")
            if not cards:
                break

            for card in cards:
                try:
                    # 행사명: div.item-subject
                    subj = card.select_one(".item-subject")
                    if subj is None:
                        continue
                    name = subj.get_text(strip=True)

                    # 날짜: div.item-date, 장소: div.item-client
                    date_el = card.select_one(".item-date")
                    venue_el = card.select_one(".item-client")
                    date_text = date_el.get_text(strip=True) if date_el else ""
                    raw_venue = venue_el.get_text(" ", strip=True) if venue_el else ""
                    venue = re.sub(r"\s*,\s*", ", ", raw_venue).strip(", ")

                    match = DATE_PATTERN.search(date_text)
                    if not match:
                        logger.warning("날짜 파싱 실패, 건너뜀: %s", name)
                        continue

                    start_date = _parse_date(match.group(1))
                    end_date = _parse_date(match.group(2))

                    # eventSeq 추출 → 상세 URL 생성
                    href = card.get("href", "")
                    seq_match = SEQ_PATTERN.search(href)
                    detail_url = (
                        f"{DETAIL_URL}?eventSeq={seq_match.group(1)}"
                        if seq_match
                        else ""
                    )

                    img = card.select_one("img")
                    image_url = ""
                    if img is not None:
                        src = img.get("src") or img.get("data-src") or ""
                        image_url = urljoin(SITE_ORIGIN, src) if src else ""

                    events.append({
                        "name": name,
                        "start_date": start_date,
                        "end_date": end_date,
                        "venue": venue,
                        "url": detail_url,
                        "image_url": image_url,
                        "source": "KINTEX",
                    })
                except Exception:
                    logger.exception("카드 파싱 중 오류 발생, 건너뜀")
                    continue

    except Exception:
        logger.exception("KINTEX 크롤링 실패")
        return []

    # 중복 제거
    seen = set()
    unique = []
    for e in events:
        key = (e["name"], e["start_date"], e["end_date"])
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique

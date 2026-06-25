import logging
import re
from datetime import datetime, timedelta
from typing import List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.coex.co.kr/event/full-schedules/"
SITE_ORIGIN = "https://www.coex.co.kr"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
}
TIMEOUT = 10
MAX_PAGES = 20
DATE_PATTERN = re.compile(r"(\d{4}\.\d{2}\.\d{2})\s*-\s*(\d{4}\.\d{2}\.\d{2})")


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
    """'2026.04.08' → '2026-04-08'"""
    return dot_date.replace(".", "-")


def fetch_events() -> List[dict]:
    """COEX 향후 3개월 행사 목록을 크롤링하여 반환한다.

    Returns:
        행사 정보 딕셔너리 리스트. 파싱 실패 시 빈 리스트.
    """
    today = datetime.now()
    end = datetime(today.year, 12, 31)
    params_base = {
        "search_start_date": today.strftime("%Y.%m.%d"),
        "search_end_date": end.strftime("%Y.%m.%d"),
        "list_type": "LIST",
    }

    events: List[dict] = []

    try:
        for page in range(1, MAX_PAGES + 1):
            params = {**params_base, "var_page": page}
            resp = _request_with_retry(BASE_URL, params)
            soup = BeautifulSoup(resp.text, "html.parser")

            cards = soup.select("a h4")
            if not cards:
                break

            for h4 in cards:
                try:
                    card_link = h4.find_parent("a")
                    if card_link is None:
                        continue

                    name = h4.get_text(strip=True)

                    date_div = card_link.select_one(".BlogEventItemCont-date")
                    hall_div = card_link.select_one(".BlogEventItemCont-hall")
                    date_text = date_div.get_text(strip=True) if date_div else ""
                    venue = hall_div.get_text(strip=True) if hall_div else ""

                    match = DATE_PATTERN.search(date_text)
                    if not match:
                        logger.warning("날짜 파싱 실패, 건너뜀: %s", name)
                        continue

                    start_date = _parse_date(match.group(1))
                    end_date = _parse_date(match.group(2))

                    href = card_link.get("href", "")
                    detail_url = urljoin(SITE_ORIGIN, href) if href else ""

                    img = card_link.select_one("img")
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
                        "source": "COEX",
                    })
                except Exception:
                    logger.exception("카드 파싱 중 오류 발생, 건너뜀")
                    continue

    except Exception:
        logger.exception("COEX 크롤링 실패")
        return []

    # 중복 제거 (동일 이벤트가 2번 렌더링되는 경우)
    seen = set()
    unique = []
    for e in events:
        key = (e["name"], e["start_date"], e["end_date"])
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique

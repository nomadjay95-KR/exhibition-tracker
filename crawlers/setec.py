import logging
import re
from typing import List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

LIST_URL = "https://www.setec.or.kr/front/schedule/list.do"
VIEW_URL = "https://www.setec.or.kr/front/schedule/view.do"
SITE_ORIGIN = "https://www.setec.or.kr"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
}
TIMEOUT = 10
MAX_PAGES = 10
DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})\s*~\s*(\d{4}-\d{2}-\d{2})")
# onclick="fn_view('2258')" — 숫자가 따옴표로 감싸진 경우까지 허용
SIDX_PATTERN = re.compile(r"fn_view\(\s*['\"]?(\d+)['\"]?\s*\)")


def _post_with_retry(url: str, data: dict, max_retries: int = 1) -> requests.Response:
    """POST 요청. 실패 시 max_retries만큼 재시도."""
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(url, data=data, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            if attempt < max_retries:
                logger.warning("요청 실패 (시도 %d/%d): %s", attempt + 1, max_retries + 1, e)
                continue
            raise


def _parse_event_card(li_tag) -> dict | None:
    """단일 <li> 이벤트 카드를 파싱하여 dict로 반환. 실패 시 None."""
    link = li_tag.find("a")
    if not link:
        return None

    # sIdx 추출 (onclick="fn_view(66)")
    onclick = link.get("onclick", "")
    sidx_match = SIDX_PATTERN.search(onclick)
    detail_url = ""
    if sidx_match:
        detail_url = f"{VIEW_URL}?sIdx={sidx_match.group(1)}"

    # 행사명
    strong = link.find("strong")
    if not strong:
        return None
    name = strong.get_text(strip=True)

    # 기간 / 장소 — 내부 <ul><li> 목록
    inner_items = link.select("ul li")
    start_date = ""
    end_date = ""
    venue = ""
    for item in inner_items:
        text = item.get_text(strip=True)
        if text.startswith("기간"):
            m = DATE_PATTERN.search(text)
            if m:
                start_date = m.group(1)
                end_date = m.group(2)
        elif text.startswith("장소"):
            venue = text.replace("장소", "", 1).lstrip(" :：").strip()

    if not start_date:
        logger.warning("날짜 파싱 실패, 건너뜀: %s", name)
        return None

    # 목록에 썸네일이 있으면 수집 (없으면 빈 문자열 → 프론트 플레이스홀더)
    img = link.find("img")
    image_url = ""
    if img is not None:
        src = img.get("src") or img.get("data-src") or ""
        image_url = urljoin(SITE_ORIGIN, src) if src else ""

    return {
        "name": name,
        "start_date": start_date,
        "end_date": end_date,
        "venue": venue,
        "url": detail_url,
        "image_url": image_url,
        "source": "SETEC",
    }


def fetch_events() -> List[dict]:
    """SETEC 전시 일정을 크롤링하여 반환한다.

    Returns:
        행사 정보 딕셔너리 리스트. 파싱 실패 시 빈 리스트.
    """
    events: List[dict] = []

    try:
        for page in range(1, MAX_PAGES + 1):
            data = {"pageIndex": page}
            resp = _post_with_retry(LIST_URL, data)
            soup = BeautifulSoup(resp.text, "html.parser")

            # 이벤트 카드: 최상위 <li> 안에 <a> → <strong> 구조
            cards = soup.select("li:has(> a strong)")
            if not cards:
                break

            for card in cards:
                try:
                    event = _parse_event_card(card)
                    if event:
                        events.append(event)
                except Exception:
                    logger.exception("카드 파싱 중 오류 발생, 건너뜀")
                    continue

    except Exception:
        logger.exception("SETEC 크롤링 실패")
        return []

    return events

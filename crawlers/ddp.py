"""DDP(동대문디자인플라자) 전시·행사 일정 크롤러."""

import html
import logging
import re
from typing import List

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://ddp.or.kr"
PAGE_URL = f"{BASE_URL}/page.html"
DETAIL_URL = f"{BASE_URL}/index.html"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": f"{BASE_URL}/?menuno=239",
}
TIMEOUT = 15
MAX_PAGES = 20

# ztag: base64-encoded Java serialized string for board config
ZTAG = (
    "rO0ABXQAPjxjYWxsIHR5cGU9ImJvYXJkIiBubz0iMTUiIHNraW49InBob3Rv"
    "dGh1bWJfdm9sdW50ZWVyIj48L2NhbGw+"
)

# boardno → 카테고리: 15=전시, 16=행사, 21=상설, 145=투어, 147=버스킹
CATEGORY_SCHEDS = ["15", "16", "21", "145", "147"]


def _build_form_data(page: int, subno: str) -> str:
    """AJAX POST 요청에 사용할 폼 데이터를 생성한다."""
    cate_params = "&".join(f"cateSched={c}" for c in CATEGORY_SCHEDS)
    return (
        f"subno={subno}&cond2=3&skeyword=&sdate2=&edate2="
        f"&ztag={ZTAG}&key=&boardno=15&{cate_params}"
        f"&siteno=2&cates=&maxIdx=52&page={page}"
        f"&ROLE_USERID=&pageIndex={page}"
    )


def _unescape(text: str) -> str:
    """HTML 엔티티(&lt; 등)를 일반 문자로 변환한다."""
    return html.unescape(text) if text else ""


# 썸네일 파일명은 17자리 타임스탬프 + 확장자 (예: 20260512044856736.jpg)
_THUMB_NAME = re.compile(r"^\d{17}\.(jpg|jpeg|png|gif)$", re.IGNORECASE)
# 썸네일 파일명이 담기는 필드 우선순위 (DDB CMS의 generic 컬럼)
_THUMB_FIELDS = ("place", "etc9", "etc2", "etc5")
# board_thumb 디렉터리 번호는 JSON에 없고 서버가 정하므로 가장 흔한 0을 사용한다.
# 다른 디렉터리(zboardphotogallery1/64 등)에 있는 일부는 404 → 프론트가 플레이스홀더 처리.
_THUMB_BASE = f"{BASE_URL}/usr/upload/board_thumb/zboardphotogallery0"


def _extract_image_url(item: dict) -> str:
    """JSON 항목에서 썸네일 파일명을 찾아 board_thumb URL로 반환한다 (best-effort)."""
    filename = ""
    for key in _THUMB_FIELDS:
        value = item.get(key, "")
        if isinstance(value, str) and _THUMB_NAME.match(value):
            filename = value
            break
    if not filename:
        for value in item.values():
            if isinstance(value, str) and _THUMB_NAME.match(value):
                filename = value
                break
    return f"{_THUMB_BASE}/{filename}" if filename else ""


def fetch_events() -> List[dict]:
    """DDP 행사 목록을 크롤링하여 반환한다.

    진행 중(subno=1)과 예정(subno=2) 행사를 모두 수집한다.

    Returns:
        행사 정보 딕셔너리 리스트. 파싱 실패 시 빈 리스트.
    """
    events: List[dict] = []

    try:
        session = requests.Session()
        session.headers.update(HEADERS)

        # 세션 쿠키(JSESSIONID) 획득을 위해 메인 페이지 방문
        session.get(f"{BASE_URL}/?menuno=239", timeout=TIMEOUT)

        for subno in ("1", "2", "3"):  # 진행 중 + 예정 + 아카이브
            for page in range(1, MAX_PAGES + 1):
                try:
                    resp = session.post(
                        PAGE_URL,
                        data=_build_form_data(page, subno),
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=TIMEOUT,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception:
                    logger.exception("DDP 페이지 요청 실패 (subno=%s, page=%d)", subno, page)
                    break

                items = data.get("list", [])
                if not items:
                    break

                # 아카이브는 최신→과거 순이므로 2026년 이전이면 중단
                stop_paging = False

                for item in items:
                    try:
                        name = _unescape(item.get("bbstitle", "")).strip()
                        sdate = item.get("sdate", "")
                        edate = item.get("edate", "")
                        venue_raw = item.get("etc10") or ""
                        venue = f"DDP {venue_raw}".strip() if venue_raw and venue_raw != "None" else "DDP"
                        bbsno = item.get("bbsno", "")
                        boardno = item.get("boardno", "")

                        if not name or not sdate or not edate:
                            continue

                        # 2026년 1월 이전 행사는 수집하지 않음
                        if edate < "2026-01-01":
                            stop_paging = True
                            continue

                        detail_url = (
                            f"{DETAIL_URL}?menuno=239&siteno=2"
                            f"&bbsno={bbsno}&boardno={boardno}&act=view"
                        )

                        events.append({
                            "name": name,
                            "start_date": sdate,
                            "end_date": edate,
                            "venue": venue,
                            "url": detail_url,
                            "image_url": _extract_image_url(item),
                            "source": "DDP",
                        })
                    except Exception:
                        logger.exception("DDP 항목 파싱 중 오류, 건너뜀")
                        continue

                # 2026년 이전 도달 시 또는 마지막 페이지면 중단
                if stop_paging:
                    break
                page_max = int(data.get("input", {}).get("pageMax", 1))
                if page >= page_max:
                    break

    except Exception:
        logger.exception("DDP 크롤링 실패")
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

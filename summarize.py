"""행사 상세 페이지를 Claude API로 3줄 개조식 요약한다 (best-effort).

- 기존 docs/exhibitions.json을 캐시로 재사용 → 매 실행 시 신규 행사만 요약 (비용 최소화)
- ANTHROPIC_API_KEY가 없거나 anthropic 미설치면 요약을 건너뛴다 (사이트는 정상 동작)
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5"  # 3줄 요약엔 충분하고 대량 반복에 비용 효율적
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
}
TIMEOUT = 10
MAX_TEXT = 3000  # 상세 페이지에서 LLM에 넘길 본문 길이 상한

# 구조화 출력: 요약 줄 배열. (배열 길이 제약은 스키마로 강제 불가 → 프롬프트로 3줄 유도)
_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "array", "items": {"type": "string"}}},
    "required": ["summary"],
    "additionalProperties": False,
}

_PROMPT = """다음은 전시·행사 정보야. 방문 여부를 빠르게 판단할 수 있도록 핵심을 한국어 개조식으로 정확히 3줄 요약해줘.

규칙:
- 각 줄은 명사형으로 끝내고, 맨 앞에 어울리는 이모지 1개를 붙일 것
- "무엇을 보는/하는 행사인지, 주요 대상·규모·특징" 위주로
- 상세 정보가 부족하면 지어내지 말고 제공된 기간·장소·출처 사실만 활용할 것
- 각 줄은 40자 이내로 간결하게

[행사명] {name}
[기간] {start} ~ {end}
[장소] {venue}
[출처] {source}
[상세 페이지 내용]
{detail}"""


def _event_key(e: dict):
    return (e.get("name", ""), e.get("start_date", ""))


def _load_existing_summaries(path: Path) -> dict:
    """이전 결과 파일에서 (행사명, 시작일) → summary 매핑을 로드 (캐시)."""
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for e in data.get("events", []):
        if e.get("summary"):
            out[_event_key(e)] = e["summary"]
    return out


def _fetch_detail_text(url: str) -> str:
    """상세 페이지의 가독 텍스트를 best-effort로 추출한다."""
    if not url:
        return ""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return ""
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    return text[:MAX_TEXT]


def _summarize_one(client, event: dict, detail: str) -> List[str]:
    prompt = _PROMPT.format(
        name=event.get("name", ""),
        start=event.get("start_date", ""),
        end=event.get("end_date", ""),
        venue=event.get("venue", ""),
        source=event.get("source", ""),
        detail=detail or "(상세 내용 없음)",
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=400,
        output_config={"format": {"type": "json_schema", "schema": _SUMMARY_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "")
    data = json.loads(text)
    return [s.strip() for s in data.get("summary", []) if s.strip()][:3]


def enrich_with_summaries(events: List[dict], existing_path) -> List[dict]:
    """각 이벤트에 summary(3줄 리스트)를 부여한다. 기존 요약은 재사용, 신규만 생성."""
    existing = _load_existing_summaries(existing_path)

    todo = []
    for e in events:
        cached = existing.get(_event_key(e))
        if cached:
            e["summary"] = cached
        else:
            todo.append(e)

    if not todo:
        logger.info("요약: 신규 0건 — 전부 캐시 재사용")
        return events

    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.warning("ANTHROPIC_API_KEY 없음 — 신규 %d건 요약 건너뜀", len(todo))
        return events

    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic 패키지 미설치 — 요약 건너뜀")
        return events

    client = anthropic.Anthropic()
    done = 0
    for e in todo:
        try:
            detail = _fetch_detail_text(e.get("url", ""))
            bullets = _summarize_one(client, e, detail)
            if bullets:
                e["summary"] = bullets
                done += 1
        except Exception:
            logger.exception("요약 실패: %s", e.get("name", ""))

    logger.info("요약: 신규 %d건 생성, 캐시 재사용 %d건", done, len(events) - len(todo))
    return events

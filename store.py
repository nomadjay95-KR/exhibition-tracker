"""크롤링 결과를 정적 웹페이지용 JSON 파일로 저장한다 (Notion 적재 대체)."""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List

from filter import is_relevant

logger = logging.getLogger(__name__)

# 프론트엔드(docs/)가 fetch로 읽는 데이터 파일
DEFAULT_PATH = Path(__file__).parent / "docs" / "exhibitions.json"

KST = timezone(timedelta(hours=9))


def _dedupe(events: List[dict]) -> List[dict]:
    """출처 통합 후 (행사명, 시작일, 종료일) 기준으로 중복 제거한다."""
    seen = set()
    unique = []
    for e in events:
        key = (e.get("name"), e.get("start_date"), e.get("end_date"))
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique


def save_to_json(events: List[dict], path: Path = DEFAULT_PATH) -> int:
    """행사 목록을 JSON 파일로 저장한다.

    - 중복 제거 후 시작일 오름차순 정렬
    - 각 이벤트에 filter.is_relevant() 결과를 relevant 필드로 부여
    - generated_at(KST) 타임스탬프 포함

    Returns:
        저장된 행사 건수
    """
    unique = _dedupe(events)
    unique.sort(key=lambda e: e.get("start_date", ""))

    for e in unique:
        e["relevant"] = is_relevant(e)
        e.setdefault("image_url", "")

    payload = {
        "generated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "count": len(unique),
        "events": unique,
    }

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.info("JSON 저장 완료 — %d건 → %s", len(unique), path)
    return len(unique)

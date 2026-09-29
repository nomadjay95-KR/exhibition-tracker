import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

from crawlers.coex import fetch_events as fetch_coex
from crawlers.ddp import fetch_events as fetch_ddp
from crawlers.kintex import fetch_events as fetch_kintex
from crawlers.setec import fetch_events as fetch_setec
from filter import filter_relevant
from store import save_to_json, DEFAULT_PATH
from summarize import enrich_with_summaries

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

CRAWLERS = {
    "COEX": fetch_coex,
    "DDP": fetch_ddp,
    "KINTEX": fetch_kintex,
    "SETEC": fetch_setec,
}


def _run_crawlers() -> dict[str, list[dict]]:
    """크롤러를 병렬 실행하고 출처별 결과를 반환한다. 실패한 출처는 빈 리스트."""
    results: dict[str, list[dict]] = {}

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(fn): name for name, fn in CRAWLERS.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                events = future.result()
                logger.info("%s: %d건 수집", name, len(events))
            except Exception:
                logger.exception("%s 크롤링 실패", name)
                events = []
            results[name] = events

    return results


def _load_previous_events(path: Path) -> list[dict]:
    """이전 실행 결과(docs/exhibitions.json)의 이벤트 목록. 없거나 깨졌으면 빈 리스트."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")).get("events", [])
    except (OSError, ValueError):
        return []


def _with_fallback(results: dict[str, list[dict]], previous_path: Path) -> list[dict]:
    """0건인 출처는 이전 결과에서 아직 끝나지 않은 행사를 재사용해 합친다.

    사이트 접속 장애(타임아웃, 인증서 오류 등)로 한 출처가 통째로 사라지는 것을 막는다.
    """
    today = date.today().isoformat()
    previous = _load_previous_events(previous_path)
    merged: list[dict] = []

    for name, events in results.items():
        if events:
            merged.extend(events)
            continue
        kept = [
            e for e in previous
            if e.get("source") == name and e.get("end_date", "") >= today
        ]
        logger.warning("%s: 수집 0건 → 이전 데이터 %d건 유지", name, len(kept))
        merged.extend(kept)

    return merged


def main() -> None:
    logger.info("=== Exhibition Tracker 실행 시작 ===")

    # 1. 크롤링 (0건인 출처는 이전 결과로 폴백)
    all_events = _with_fallback(_run_crawlers(), DEFAULT_PATH)
    total = len(all_events)

    # 2. 필터링 (참고용 — 관련도는 저장 시 각 이벤트에 자동 태깅됨)
    filtered = filter_relevant(all_events)

    # 3. 요약 (기존 결과 캐시 재사용, 신규 행사만 Claude API로 3줄 요약)
    try:
        all_events = enrich_with_summaries(all_events, DEFAULT_PATH)
    except Exception:
        logger.exception("요약 중 오류 발생 — 요약 없이 계속 진행")

    # 4. JSON 저장 (전체 이벤트, 관련도 자동 태깅)
    try:
        saved = save_to_json(all_events)
    except Exception:
        logger.exception("JSON 저장 중 오류 발생")
        saved = 0

    # 4. 요약
    logger.info("=== 실행 결과 요약 ===")
    logger.info("총 수집: %d개", total)
    logger.info("관련 행사: %d개", len(filtered))
    logger.info("JSON 저장: %d개", saved)


if __name__ == "__main__":
    main()

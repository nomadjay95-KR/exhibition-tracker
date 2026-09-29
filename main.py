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


def _merge_with_previous(results: dict[str, list[dict]], previous_path: Path) -> list[dict]:
    """이번 수집 결과에 이전 결과의 미종료 행사를 출처별로 합친다 (중복은 store가 제거).

    - 크롤러가 중간에 실패해 일부 페이지만 수집했거나 0건이어도 출처가 사이트에서 사라지지 않는다.
    - 목록이 '오늘 이후 시작' 기준인 사이트(COEX·KINTEX)에서 이미 시작한 진행중 행사도 유지된다.
    - 이전 행사는 end_date가 지나면 자연히 빠진다.
    """
    today = date.today().isoformat()
    previous = _load_previous_events(previous_path)
    merged: list[dict] = []

    for name, events in results.items():
        new_keys = {(e.get("name"), e.get("start_date"), e.get("end_date")) for e in events}
        kept = [
            e for e in previous
            if e.get("source") == name
            and e.get("end_date", "") >= today
            and (e.get("name"), e.get("start_date"), e.get("end_date")) not in new_keys
        ]
        log = logger.warning if not events else logger.info
        log("%s: 신규 %d건 + 이전 데이터 유지 %d건", name, len(events), len(kept))
        merged.extend(events)
        merged.extend(kept)

    return merged


def main() -> None:
    logger.info("=== Exhibition Tracker 실행 시작 ===")

    # 1. 크롤링 + 이전 결과의 미종료 행사 병합 (부분 실패·0건 대비)
    all_events = _merge_with_previous(_run_crawlers(), DEFAULT_PATH)
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

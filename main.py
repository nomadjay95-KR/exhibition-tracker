import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

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


def _run_crawlers() -> list[dict]:
    """세 크롤러를 병렬 실행하고 결과를 합친다."""
    all_events: list[dict] = []

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(fn): name for name, fn in CRAWLERS.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                events = future.result()
                logger.info("%s: %d건 수집", name, len(events))
                all_events.extend(events)
            except Exception:
                logger.exception("%s 크롤링 실패, 건너뜀", name)

    return all_events


def main() -> None:
    logger.info("=== Exhibition Tracker 실행 시작 ===")

    # 1. 크롤링
    all_events = _run_crawlers()
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

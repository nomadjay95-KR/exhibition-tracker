import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from crawlers.coex import fetch_events as fetch_coex
from crawlers.kintex import fetch_events as fetch_kintex
from crawlers.setec import fetch_events as fetch_setec
from filter import filter_relevant
from notifier import push_to_notion

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

CRAWLERS = {
    "COEX": fetch_coex,
    "KINTEX": fetch_kintex,
    "SETEC": fetch_setec,
}


def _run_crawlers() -> list[dict]:
    """세 크롤러를 병렬 실행하고 결과를 합친다."""
    all_events: list[dict] = []

    with ThreadPoolExecutor(max_workers=3) as pool:
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

    # 2. 필터링
    filtered = filter_relevant(all_events)

    # 3. Notion 적재
    try:
        created, skipped = push_to_notion(filtered)
    except Exception:
        logger.exception("Notion 적재 중 오류 발생")
        created, skipped = 0, 0

    # 4. 요약
    logger.info("=== 실행 결과 요약 ===")
    logger.info("총 수집: %d개", total)
    logger.info("필터링 후: %d개", len(filtered))
    logger.info("Notion 신규 등록: %d개", created)
    logger.info("스킵(중복): %d개", skipped)


if __name__ == "__main__":
    main()

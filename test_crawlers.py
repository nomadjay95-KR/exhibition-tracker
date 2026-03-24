"""각 크롤러를 독립적으로 실행·검증하는 CLI 테스트 스크립트 (dry-run)."""

import sys

from filter import filter_relevant

try:
    from crawlers.coex import fetch_events as fetch_coex
except Exception:
    fetch_coex = None

try:
    from crawlers.kintex import fetch_events as fetch_kintex
except Exception:
    fetch_kintex = None

try:
    from crawlers.setec import fetch_events as fetch_setec
except Exception:
    fetch_setec = None

CRAWLERS = {
    "coex": ("COEX", fetch_coex),
    "kintex": ("KINTEX", fetch_kintex),
    "setec": ("SETEC", fetch_setec),
}


def format_event(event: dict, show_source: bool = False) -> str:
    """이벤트 한 줄 포맷."""
    start = event.get("start_date", "")
    end = event.get("end_date", "")

    # end_date가 start_date와 같은 연도면 MM-DD만 표시
    if start[:4] == end[:4] and len(end) >= 10:
        end_display = end[5:]
    else:
        end_display = end

    name = event.get("name", "")
    venue = event.get("venue", "")

    line = f"  ✓ {start} ~ {end_display} | {name} | {venue}"
    if show_source:
        line += f" ({event.get('source', '')})"
    return line


def run_crawler(label: str, fetch_fn) -> list[dict]:
    """크롤러 하나를 실행하고 결과를 출력한다."""
    if fetch_fn is None:
        print(f"[{label}] 크롤러 미구현")
        return []

    try:
        events = fetch_fn()
    except Exception as e:
        print(f"[{label}] 에러 발생: {e}")
        return []

    print(f"[{label}] 총 {len(events)}개 수집")
    for ev in events:
        print(format_event(ev))
    return events


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1].lower() not in (*CRAWLERS, "all"):
        print("Usage: python test_crawlers.py <coex|kintex|setec|all>")
        sys.exit(1)

    target = sys.argv[1].lower()

    if target == "all":
        all_events: list[dict] = []
        for key, (label, fetch_fn) in CRAWLERS.items():
            result = run_crawler(label, fetch_fn)
            all_events.extend(result)
            print()

        filtered = filter_relevant(all_events)
        print(f"--- 필터링 결과: {len(all_events)}개 중 {len(filtered)}개 선별 ---")
        for ev in filtered:
            print(format_event(ev, show_source=True))
    else:
        label, fetch_fn = CRAWLERS[target]
        run_crawler(label, fetch_fn)


if __name__ == "__main__":
    main()

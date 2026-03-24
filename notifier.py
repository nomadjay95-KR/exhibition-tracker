import logging
import os
from datetime import date
from typing import List, Set, Tuple

from dotenv import load_dotenv
from notion_client import Client

load_dotenv()
logger = logging.getLogger(__name__)

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")


def _get_client() -> Client:
    if not NOTION_TOKEN:
        raise RuntimeError("NOTION_TOKEN 환경변수가 설정되지 않았습니다")
    return Client(auth=NOTION_TOKEN)


def _get_data_source_id(client: Client) -> str:
    """Database ID로부터 data_source_id를 조회한다 (notion-client 3.x)."""
    db = client.databases.retrieve(database_id=NOTION_DATABASE_ID)
    data_sources = db.get("data_sources", [])
    if not data_sources:
        raise RuntimeError("데이터베이스에서 data_source를 찾을 수 없습니다")
    return data_sources[0]["id"]


def _fetch_existing(client: Client) -> Set[Tuple[str, str]]:
    """DB에 이미 존재하는 (행사명, 시작일) 쌍을 조회한다."""
    existing: Set[Tuple[str, str]] = set()
    ds_id = _get_data_source_id(client)
    start_cursor = None

    while True:
        resp = client.data_sources.query(
            data_source_id=ds_id,
            start_cursor=start_cursor,
        )
        for page in resp["results"]:
            props = page["properties"]
            title_parts = props.get("행사명", {}).get("title", [])
            name = title_parts[0]["plain_text"] if title_parts else ""
            start_obj = props.get("시작일", {}).get("date")
            start_date = start_obj["start"] if start_obj else ""
            if name and start_date:
                existing.add((name, start_date))

        if not resp.get("has_more"):
            break
        start_cursor = resp.get("next_cursor")

    return existing


def _build_page_properties(event: dict) -> dict:
    today = date.today().isoformat()
    return {
        "행사명": {"title": [{"text": {"content": event["name"]}}]},
        "시작일": {"date": {"start": event["start_date"]}},
        "종료일": {"date": {"start": event["end_date"]}},
        "장소": {"rich_text": [{"text": {"content": event.get("venue", "")}}]},
        "출처": {"select": {"name": event.get("source", "")}},
        "URL": {"url": event.get("url") or None},
        "수집일": {"date": {"start": today}},
        "관련도": {"select": {"name": "미분류"}},
    }


def push_to_notion(events: List[dict]) -> tuple[int, int]:
    """필터링된 행사를 Notion DB에 적재한다. 중복은 건너뛴다.

    Returns:
        (신규 등록 건수, 중복 스킵 건수)
    """
    if not events:
        logger.info("적재할 행사가 없습니다")
        return 0, 0

    client = _get_client()
    ds_id = _get_data_source_id(client)
    existing = _fetch_existing(client)
    logger.info("기존 DB 항목 %d건 조회 완료", len(existing))

    created = 0
    skipped = 0
    for event in events:
        key = (event["name"], event["start_date"])
        if key in existing:
            skipped += 1
            continue

        try:
            client.pages.create(
                parent={"data_source_id": ds_id},
                properties=_build_page_properties(event),
            )
            existing.add(key)
            created += 1
        except Exception:
            logger.exception("Notion 적재 실패: %s", event["name"])

    logger.info("Notion 적재 완료 — 신규 %d건, 중복 스킵 %d건", created, skipped)
    return created, skipped

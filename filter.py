import logging
from typing import List

logger = logging.getLogger(__name__)

KEYWORDS = [
    # 로봇·자동화
    "로봇", "robot", "자동화", "automation",
    # AI·데이터
    "AI", "인공지능", "머신러닝", "딥러닝", "빅데이터",
    # 제조·기계·설비
    "제조", "manufacturing", "기계", "machine", "장비", "설비",
    "공장", "factory", "스마트팩토리", "smart factory",
    "포장", "패키징", "packaging", "금형", "용접", "레이저",
    "CNC", "공작기계", "산업자동화",
    # 전자·반도체·디스플레이
    "전자", "electronic", "반도체", "semiconductor",
    "디스플레이", "display", "배터리", "battery", "PCB",
    # 에너지·환경
    "에너지", "energy", "전력", "태양광", "수소",
    "친환경", "탄소", "ESG", "기후",
    # 물류·모빌리티
    "물류", "logistics", "모빌리티", "mobility",
    "자율주행", "autonomous", "드론", "drone", "EV",
    "콜드체인", "supply chain", "공급망",
    # IT·소프트웨어
    "IoT", "클라우드", "cloud", "보안", "security",
    "소프트웨어", "software", "블록체인", "blockchain",
    "메타버스", "metaverse", "양자", "quantum",
    "디지털전환", "DX", "SaaS", "5G", "6G",
    # 바이오·제약 (제조 연관)
    "바이오", "bio", "제약",
    # 기타
    "스마트", "smart", "자율", "테크", "tech",
]
_KEYWORDS_LOWER = [k.lower() for k in KEYWORDS]

# 키워드 매칭이지만 관련 없는 행사를 제외하는 패턴
EXCLUDE_KEYWORDS = [
    "재테크", "피부", "모발", "미용", "뷰티", "화장품", "코스메틱",
    "푸드테크", "에듀테크",
]
_EXCLUDE_LOWER = [k.lower() for k in EXCLUDE_KEYWORDS]


def is_relevant(event: dict) -> bool:
    """개별 이벤트의 관련 여부를 판단한다."""
    name = event.get("name", "").lower()
    if any(ex in name for ex in _EXCLUDE_LOWER):
        return False
    return any(kw in name for kw in _KEYWORDS_LOWER)


def filter_relevant(events: List[dict]) -> List[dict]:
    """행사명에 키워드가 하나라도 포함된 행사만 필터링한다."""
    result = [e for e in events if is_relevant(e)]
    logger.info("전체 %d개 중 %d개 선별", len(events), len(result))
    return result
